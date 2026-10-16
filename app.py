"""TypeQuest: a typing tutor for Year 7/8 students.  Iteration 3: refined final version.

Run it with:   python app.py   then open http://127.0.0.1:5000 in Chrome.
Demo data:     python app.py --demo   (uses demo.db, made by make_demo_db.py)

Routes are grouped by the team member who owns them:
    Henry  - accounts and data:  /, /register, /login, /logout, /home, /progress, /leaderboard,
                                 error pages
    Lucas  - typing engine:      /test, /passage/<level>, POST /result,
             game:               /game, POST /game/start, POST /game/result, /settings
    George - tips and practice:  /results (tips, heatmap and finger guide), /practice,
                                 /practice/drill, POST /practice/result
"""

import os
import secrets
import sqlite3
import sys
import time
from functools import wraps
from pathlib import Path

from flask import (Flask, abort, flash, g, jsonify, redirect, render_template, request, session,
                   url_for)

from models import game as game_rules
from models.database import Database, week_ago
from models.drill_generator import DrillGenerator
from models.finger_guide import FingerGuide
from models.game import Game, load_game_words
from models.key_stats import KeyStats
from models.passage import LEVELS, Passage
from models.tip_engine import TipEngine, key_label
from models.typing_session import TEST_SECONDS, TypingSession
from models.user import (MAX_PASSWORD_LENGTH, USERNAME_PATTERN, User, improvement,
                         registration_error)

BASE_DIR = Path(__file__).resolve().parent
SECRET_KEY_FILE = BASE_DIR / ".secret_key"
DEMO_DATABASE = BASE_DIR / "demo.db"


def load_secret_key():
    """Flask signs the session cookie with this key so it cannot be faked.

    It comes from the SECRET_KEY environment variable if one is set. Otherwise a
    random key is made the first time the app runs and kept in .secret_key
    (ignored by git), so students stay logged in when the app restarts.
    """
    if os.environ.get("SECRET_KEY"):
        return os.environ["SECRET_KEY"]
    if not SECRET_KEY_FILE.exists():
        SECRET_KEY_FILE.write_text(secrets.token_hex(32))
    return SECRET_KEY_FILE.read_text().strip()


app = Flask(__name__)
app.config["SECRET_KEY"] = load_secret_key()
app.config["DATABASE"] = os.environ.get("TYPEQUEST_DB", BASE_DIR / "typequest.db")
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"  # other websites cannot send forms using our login
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024     # H21: a typing result is tiny, so refuse huge requests

tip_engine = TipEngine()            # loads tips.json once when the app starts
drill_generator = DrillGenerator()  # loads words.json once
GAME_WORDS = load_game_words()      # loads game_words.json once
DRILL_MAX_SECONDS = 10 * 60         # a drill has no timer, but nobody needs 10 minutes for 20 words
LEADERBOARD_SIZE = 10
IDLE_LIMIT_SECONDS = 2 * 60 * 60    # H23: log out after 2 hours without using TypeQuest
LEADERBOARD_PERIODS = ("week", "all")

_checked_databases = set()  # database files already set up since the app started (H20)


def database():
    """The Database object for the current database file (tests swap in a temporary one)."""
    return Database(app.config["DATABASE"])


# =====================================================================
# Run before every request (Henry): database, session expiry
# =====================================================================


@app.before_request
def make_database_if_missing():
    """H20: if typequest.db is missing, create every table before anything else happens.

    This runs on the first request (so `flask run` works as well as `python app.py`) and
    again if the file is deleted while the app is running.
    """
    db_path = app.config["DATABASE"]
    if db_path not in _checked_databases or not Path(db_path).exists():
        database().create_tables()
        _checked_databases.add(db_path)


@app.before_request
def log_out_idle_users():
    """H23: a user who hasn't used TypeQuest for 2 hours is logged out and sent to the
    login page with a message (for example, a shared school laptop left logged in)."""
    if "user_id" not in session or request.endpoint == "static":
        return None
    now = time.time()
    if now - session.get("last_seen", now) > IDLE_LIMIT_SECONDS:
        session.clear()
        message = "You were logged out because TypeQuest wasn't used for 2 hours. Please log in again."
        if request.is_json:
            return jsonify(error=message), 401
        flash(message, "error")
        return redirect(url_for("login"))
    session["last_seen"] = now
    return None


def login_required(view):
    """H6: send logged-out visitors to the login page instead of showing the page.

    The logged-in User is loaded into g.user for the page to use. If the account no
    longer exists (for example the database was deleted), the user is logged out.
    """

    @wraps(view)
    def wrapped(*args, **kwargs):
        """Run the page only if a logged-in account is found."""
        user = database().get_user_by_id(session["user_id"]) if "user_id" in session else None
        if user is None:
            session.clear()
            if request.is_json:
                return jsonify(error="Please log in again."), 401
            return redirect(url_for("login"))
        g.user = user
        return view(*args, **kwargs)

    return wrapped


def ordinal(number):
    """1 -> "1st", 2 -> "2nd", 11 -> "11th", 23 -> "23rd" (H13)."""
    if number % 100 in (11, 12, 13):
        return f"{number}th"
    endings = {1: "st", 2: "nd", 3: "rd"}
    return str(number) + endings.get(number % 10, "th")


def save_key_stats(db, user_id, key_errors):
    """Add one activity's key presses and mistakes to the user's running totals (G1, G2).

    Tests, games and drills all call this, so the heatmap and drills use all typing.
    Returns the updated KeyStats.
    """
    key_stats = KeyStats.load(db, user_id)
    key_stats.update(key_errors)
    key_stats.save(db, user_id)
    return key_stats


def start_session(user_id, username):
    """Log a user in by remembering who they are in the signed session cookie (H4)."""
    session.clear()
    session["user_id"] = user_id
    session["username"] = username
    session["last_seen"] = time.time()  # H23


# =====================================================================
# Accounts and data (Henry)
# =====================================================================


@app.route("/")
def index():
    """Send people to the right starting page."""
    if "user_id" in session:
        return redirect(url_for("home"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    """H1, H2, H3: create an account, then log straight in."""
    username = ""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # H21: everything is checked here in Python, not just by the browser.
        error = registration_error(username, password)
        if error is None:
            user_id = database().add_user(username, password)
            if user_id is None:
                error = "That username is taken. Please try a different one."
            else:
                start_session(user_id, username)
                flash(f"Welcome to TypeQuest, {username}! Your account is ready.")
                return redirect(url_for("home"))
        flash(error, "error")

    return render_template("register.html", username=username)


@app.route("/login", methods=["GET", "POST"])
def login():
    """H4, H5: check the username and password against the database."""
    username = ""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # H21: a username that could never have been registered (like ' OR 1=1 --) is
        # refused without even asking the database.
        user = None
        if USERNAME_PATTERN.match(username) and len(password) <= MAX_PASSWORD_LENGTH:
            user = database().get_user(username)
        if user is not None and user.check_password(password):
            start_session(user.user_id, user.username)
            return redirect(url_for("home"))
        # Same message whether the username or the password was wrong, so nobody
        # can use the login page to find out which usernames exist.
        flash("Incorrect username or password. Please check them and try again.", "error")

    return render_template("login.html", username=username)


@app.route("/logout")
def logout():
    """H9: forget the user and go back to the login page."""
    session.clear()
    flash("You have logged out. See you next time!")
    return redirect(url_for("login"))


@app.route("/home")
@login_required
def home():
    """H8, H17: the dashboard with best WPM, average accuracy, tests done and streak."""
    db = database()
    user_id = session["user_id"]
    stats = db.get_stats(user_id)
    stats["avg_accuracy"] = db.average_accuracy(user_id)
    stats["streak"] = User.streak(db.activity_dates(user_id))
    return render_template("home.html", username=session["username"], stats=stats,
                           tip_of_the_day=tip_engine.tip_of_the_day())


@app.route("/progress")
@login_required
def progress():
    """H10, H11, H12, H13: WPM-over-time graph, improvement stat and the leaderboard."""
    db = database()
    user_id = session["user_id"]
    results = db.get_results(user_id)
    graph = {
        "labels": [f"Test {number}" for number in range(1, len(results) + 1)],
        "dates": [result["date"][:10] for result in results],
        "wpm": [result["wpm"] for result in results],
    }
    change = improvement(graph["wpm"])
    return render_template("progress.html", results=results, graph=graph, improvement=change,
                           board=leaderboard_data(db, user_id, "all"))


def leaderboard_data(db, user_id, period):
    """H12-H14: the top 10 for a period ("week" or "all") and the user's own rank.

    Only usernames, WPM and accuracy are included (privacy).
    """
    since = week_ago() if period == "week" else None
    rows = [
        {"rank": row["rank"], "username": row["username"], "wpm": row["wpm"],
         "accuracy": row["accuracy"], "you": row["user_id"] == user_id}
        for row in db.top_scores(LEADERBOARD_SIZE, since)
    ]
    mine = db.get_rank(user_id, since)
    you = None
    if mine is not None:
        you = {"rank": mine["rank"], "place": ordinal(mine["rank"]), "wpm": mine["wpm"],
               "in_top": mine["rank"] <= LEADERBOARD_SIZE}
    return {"period": period, "rows": rows, "you": you}


@app.route("/leaderboard")
@login_required
def leaderboard():
    """H14: the leaderboard as JSON, so the This week / All time buttons don't reload the page."""
    period = request.args.get("period", "all")
    # H21: the filter is checked here, not just by the buttons on the page.
    if period not in LEADERBOARD_PERIODS:
        return jsonify(error="Unknown period."), 404
    return jsonify(leaderboard_data(database(), session["user_id"], period))


# =====================================================================
# Settings (Lucas) - F6
# =====================================================================


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    """F6: game settings: sound effects and slow mode."""
    if request.method == "POST":
        if request.form.get("form") != "game":
            abort(400)
        # A checkbox is only sent when it is ticked.
        sound_on = request.form.get("sound_on") == "on"
        slow_mode = request.form.get("slow_mode") == "on"
        database().save_settings(g.user.user_id, sound_on, slow_mode)
        flash("Game settings saved.")
        return redirect(url_for("settings"))
    return render_template("settings.html", user=g.user)


# =====================================================================
# Typing engine (Lucas)
# =====================================================================


def serve_passage(level):
    """Pick a new random passage (never the one just typed) and remember it in the session.

    The server keeps its own copy of the passage so POST /result can check the
    numbers it receives against the real passage.
    """
    previous_text = session.get("passage", {}).get("text")
    passage = Passage.random(level, exclude=previous_text)
    session["passage"] = {"text": passage.text, "level": passage.level, "submitted": False}
    session["level"] = level
    return passage


@app.route("/test")
@login_required
def typing_test():
    """L1-L4: the typing test page. The level comes from ?level= or the last one used."""
    level = request.args.get("level", session.get("level", "easy"))
    if level not in LEVELS:
        level = "easy"
    passage = serve_passage(level)
    return render_template("test.html", passage=passage, levels=LEVELS, test_seconds=TEST_SECONDS)


@app.route("/passage/<level>")
@login_required
def new_passage(level):
    """L2, L8: a new passage as JSON, used by the Restart and difficulty buttons."""
    if level not in LEVELS:
        return jsonify(error="Unknown level."), 404
    passage = serve_passage(level)
    return jsonify(text=passage.text, level=passage.level)


@app.route("/result", methods=["POST"])
@login_required
def save_result():
    """L7, H7, H15, G1, G2, G15: check and save a finished test, update the key
    statistics and personal best, and choose the tips for the results page."""
    current = session.get("passage")
    if current is None or current["submitted"]:
        return jsonify(error="This test has already been saved. Press Restart to try again."), 400

    passage = Passage(current["text"], current["level"])
    try:
        typing_session = TypingSession.from_json(request.get_json(silent=True) or {}, passage)
    except ValueError as problem:
        return jsonify(error=f"Your result could not be saved: {problem}"), 400

    db = database()
    user = g.user  # @login_required has already checked the account still exists
    user_id = user.user_id

    result = typing_session.to_result()
    result_id = db.save_result(user_id, **result)
    key_stats = save_key_stats(db, user_id, typing_session.key_errors)

    # H15: personal best. The results page shows the badge for this result only.
    session.pop("new_best", None)
    if user.update_best(result["wpm"]):
        db.save_personal_best(user)
        session["new_best"] = result_id

    # G15: a different tip from last time for each weak key.
    chosen = tip_engine.choose_tips(key_stats.weakest(3), TipEngine.load_last_tips(db, user_id))
    TipEngine.save_last_tips(db, user_id, chosen)

    session["passage"] = {**current, "submitted": True}
    return jsonify(redirect=url_for("results"))


# =====================================================================
# Game mode (Lucas)
# =====================================================================


@app.route("/game")
@login_required
def game():
    """L10-L14, L17, F5, F6: the falling words game page. The game runs in game.js.

    The rules come from models/game.py, so the browser and the server use the same
    numbers. Sound and slow mode come from the user's settings.
    """
    game_settings = {
        "words": GAME_WORDS,
        "startLives": game_rules.START_LIVES,
        "pointsPerWord": game_rules.POINTS_PER_WORD,
        "firstLevelWords": game_rules.FIRST_LEVEL_WORDS,
        "extraWordsPerLevel": game_rules.EXTRA_WORDS_PER_LEVEL,
        "baseSpeed": game_rules.BASE_SPEED,
        "speedGrowth": game_rules.SPEED_GROWTH,
        "slowMode": g.user.slow_mode,
        "slowModeSpeed": game_rules.SLOW_MODE_SPEED,
        "soundOn": g.user.sound_on,
        "baseSpawnSeconds": game_rules.BASE_SPAWN_SECONDS,
    }
    return render_template("game.html", settings=game_settings)


@app.route("/game/start", methods=["POST"])
@login_required
def start_game():
    """Remember when a game started, so the server knows how long it could have lasted."""
    session["game"] = {"started": time.time(), "submitted": False}
    return jsonify(started=True)


@app.route("/game/result", methods=["POST"])
@login_required
def save_game_result():
    """L15, L16, H18: check a finished game is possible, then save it and its key errors."""
    current = session.get("game")
    if current is None or current["submitted"]:
        return jsonify(error="This game has already been saved. Press Play again for a new game."), 400

    try:
        played = Game.from_json(request.get_json(silent=True) or {},
                                max_seconds=time.time() - current["started"])
    except ValueError as problem:
        return jsonify(error=f"Your score could not be saved: {problem}"), 400

    db = database()
    user_id = session["user_id"]
    try:
        db.save_result(user_id, **played.to_result())
        save_key_stats(db, user_id, played.key_errors)
    except sqlite3.IntegrityError:
        session.clear()
        return jsonify(error="Please log in again."), 401

    session["game"] = {**current, "submitted": True}
    return jsonify(saved=True, score=played.score, level=played.level)


# =====================================================================
# Results (Lucas), personal best (Henry), tips, heatmap and finger guide (George)
# =====================================================================


@app.route("/results")
@login_required
def results():
    """L5, H15, G3-G8, F7: the latest WPM and accuracy, personal best badge, up to 3 tips
    for the weakest keys, the keyboard mistake heatmap and the finger guide."""
    db = database()
    user_id = session["user_id"]
    result = db.get_latest_result(user_id)
    tips, heatmap, new_best, finger_guide = [], [], False, None
    if result is not None:
        key_stats = KeyStats.load(db, user_id)
        weak_keys = key_stats.weakest(3)
        tips = tip_engine.tips_for(weak_keys, TipEngine.load_last_tips(db, user_id))
        heatmap = tip_engine.heatmap_colours(key_stats)
        new_best = session.get("new_best") == result["result_id"]
        finger_guide = FingerGuide.guide([key for key, _ in weak_keys])
    return render_template("results.html", result=result, tips=tips, heatmap=heatmap,
                           new_best=new_best, finger_guide=finger_guide)


# =====================================================================
# Adaptive practice (George)
# =====================================================================


def new_drill(db, user_id):
    """G10, G14, F7: build a drill from the user's 3 weakest keys and remember it in the session.

    The error rate of each focus key is kept too, for the before and after (G13), and the
    finger guide shows which finger to use for each focus key.
    """
    key_stats = KeyStats.load(db, user_id)
    weak_keys = key_stats.weakest(3)
    focus = [key for key, _ in weak_keys]
    text = " ".join(drill_generator.make_drill(focus))
    session["drill"] = {
        "text": text,
        "before": [[key, round(rate, 1)] for key, rate in weak_keys],  # worst key first
        "submitted": False,
    }

    letters = [key for key in focus if key != "space"]
    if not focus:
        message = ("You don't have any weak keys yet, so this drill is a random mix of words. "
                   "Do a few typing tests and your drills will be made just for you.")
    elif not letters:
        message = "Your weak key is Space, so this drill is a mix of words with lots of spaces."
    else:
        message = "These words were picked because they have lots of your weak letters in them."
    return {
        "text": text,
        "message": message,
        "weak_keys": [
            {"name": key, "label": key_label(key), "band": key_stats.band(key), "percent": round(rate, 1)}
            for key, rate in weak_keys
        ],
        "finger_guide": FingerGuide.guide(focus),
    }


@app.route("/practice")
@login_required
def practice():
    """G12, G14: the student's weak keys and a drill to type, using the typing engine."""
    drill = new_drill(database(), session["user_id"])
    return render_template("practice.html", drill=drill)


@app.route("/practice/drill")
@login_required
def next_drill():
    """G11: a brand new drill as JSON, used by the New drill button."""
    return jsonify(new_drill(database(), session["user_id"]))


@app.route("/practice/result", methods=["POST"])
@login_required
def save_drill_result():
    """G13, H18: save a finished drill, update key stats and show before and after."""
    current = session.get("drill")
    if current is None or current["submitted"]:
        return jsonify(error="This drill has already been saved. Press New drill to keep practising."), 400

    passage = Passage(current["text"], None)
    try:
        drill = TypingSession.from_json(request.get_json(silent=True) or {}, passage,
                                        max_seconds=DRILL_MAX_SECONDS)
    except ValueError as problem:
        return jsonify(error=f"Your drill could not be saved: {problem}"), 400

    db = database()
    user_id = session["user_id"]
    try:
        db.save_result(user_id, drill.wpm(), drill.accuracy(), mode="drill")
        key_stats = save_key_stats(db, user_id, drill.key_errors)
    except sqlite3.IntegrityError:
        session.clear()
        return jsonify(error="Please log in again."), 401

    session["drill"] = {**current, "submitted": True}
    focus = []
    for key, before in current["before"]:
        after = key_stats.error_rate(key)
        focus.append({"key": key_label(key), "before": before,
                      "after": None if after is None else round(after, 1)})
    return jsonify(wpm=drill.wpm(), accuracy=drill.accuracy(), focus=focus)


# =====================================================================
# Error pages (Henry) - H19
# =====================================================================


def error_page(status, title, message):
    """H19: a TypeQuest page with a Home link instead of Flask's plain error page.

    Requests from the page's JavaScript get the message as JSON instead.
    """
    if request.is_json or request.accept_mimetypes.best == "application/json":
        return jsonify(error=message), status
    return render_template("error.html", status=status, title=title, message=message), status


@app.errorhandler(400)
def bad_request(error):
    """Something sent to the server didn't make sense."""
    return error_page(400, "That didn't work", "Something was sent that TypeQuest didn't understand.")


@app.errorhandler(404)
def not_found(error):
    """A page that doesn't exist, e.g. /nothing."""
    return error_page(404, "Page not found", "We couldn't find that page. Check the address.")


@app.errorhandler(405)
def wrong_method(error):
    """For example, opening /result in the browser, which only accepts results sent to it."""
    return error_page(405, "Page not found", "That page can't be opened like that.")


@app.errorhandler(413)
def too_large(error):
    """H21: a request bigger than MAX_CONTENT_LENGTH."""
    return error_page(413, "Too much data", "That was too much data to save.")


@app.errorhandler(500)
def server_error(error):
    """Anything that crashed. Students see a friendly page, not the Python error."""
    return error_page(500, "Something went wrong",
                      "Sorry, TypeQuest had a problem. Go back to the home page and try again.")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        app.config["DATABASE"] = DEMO_DATABASE  # sample users and results (see README)
    database().create_tables()
    app.run(debug=True)
