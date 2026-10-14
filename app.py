"""TypeQuest: a typing tutor for Year 7/8 students.  Iteration 1: core working prototype.

Run it with:   python app.py   then open http://127.0.0.1:5000 in Chrome.

Routes are grouped by the team member who owns them:
    Henry  - accounts and data:  /, /register, /login, /logout, /home
    Lucas  - typing engine:      /test, /passage/<level>, POST /result
    George - tips:               /results (tips section)
"""

import os
import secrets
import sqlite3
from functools import wraps
from pathlib import Path

from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for

from models.database import Database
from models.key_stats import KeyStats
from models.passage import LEVELS, Passage
from models.tip_engine import TipEngine
from models.typing_session import TEST_SECONDS, TypingSession
from models.user import registration_error

BASE_DIR = Path(__file__).resolve().parent
SECRET_KEY_FILE = BASE_DIR / ".secret_key"


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
app.config["DATABASE"] = BASE_DIR / "typequest.db"
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"  # other websites cannot send forms using our login

tip_engine = TipEngine()  # loads tips.json once when the app starts


def database():
    """The Database object for the current database file (tests swap in a temporary one)."""
    return Database(app.config["DATABASE"])


def login_required(view):
    """H6: send logged-out visitors to the login page instead of showing the page."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            if request.is_json:
                return jsonify(error="Please log in again."), 401
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


def start_session(user_id, username):
    """Log a user in by remembering who they are in the signed session cookie (H4)."""
    session.clear()
    session["user_id"] = user_id
    session["username"] = username


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
    """H8: welcome message with best WPM and number of tests done."""
    stats = database().get_stats(session["user_id"])
    return render_template("home.html", username=session["username"], stats=stats)


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
    """L7, H7, G1, G2: check and save a finished test, then add to the key statistics."""
    current = session.get("passage")
    if current is None or current["submitted"]:
        return jsonify(error="This test has already been saved. Press Restart to try again."), 400

    passage = Passage(current["text"], current["level"])
    try:
        typing_session = TypingSession.from_json(request.get_json(silent=True) or {}, passage)
    except ValueError as problem:
        return jsonify(error=f"Your result could not be saved: {problem}"), 400

    db = database()
    user_id = session["user_id"]
    try:
        db.save_result(user_id, **typing_session.to_result())
        key_stats = KeyStats.load(db, user_id)
        key_stats.update(typing_session.key_errors)
        key_stats.save(db, user_id)
    except sqlite3.IntegrityError:
        # The account no longer exists (for example, the database was reset).
        session.clear()
        return jsonify(error="Please log in again."), 401

    session["passage"] = {**current, "submitted": True}
    return jsonify(redirect=url_for("results"))


# =====================================================================
# Results (Lucas) and tips (George)
# =====================================================================


@app.route("/results")
@login_required
def results():
    """L5, G3-G7: the latest WPM and accuracy, plus up to 3 tips for the weakest keys."""
    db = database()
    user_id = session["user_id"]
    result = db.get_latest_result(user_id)
    tips = []
    if result is not None:
        weak_keys = KeyStats.load(db, user_id).weakest(3)
        tips = tip_engine.tips_for(weak_keys)
    return render_template("results.html", result=result, tips=tips)


if __name__ == "__main__":
    database().create_tables()
    app.run(debug=True)
