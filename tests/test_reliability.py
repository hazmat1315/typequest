"""Iteration 3 reliability tests: T38-T49 from the test plan, plus H19-H23, L19-L22 and G16-G19.

Owners: Henry (T38-T41), Lucas (T42-T45), George (T46-T49).
T42 and T43 also run against typing.js in tests/js/typing.test.js. T44 and T45 (resizing
and switching tabs in the game) need a real browser; see TEST_RESULTS.md.
"""

import json
import re
import time
from pathlib import Path

import pytest

from app import IDLE_LIMIT_SECONDS, app
from conftest import login, page_text, register
from models.database import Database
from models.drill_generator import DrillGenerator
from models.key_stats import KeyStats
from models.passage import Passage
from models.tip_engine import HOME_ROW, TIPS_FILE, TipEngine
from models.typing_session import TypingSession

ROOT = Path(__file__).resolve().parent.parent


# =====================================================================
# Henry: error pages, database, input checks, safe queries, session expiry
# =====================================================================


def test_T38_404_page(client):
    response = client.get("/nothing")
    html = page_text(response)
    assert response.status_code == 404
    assert "Page not found" in html and "TypeQuest" in html
    assert 'href="/"' in html and "Go to the home page" in html
    assert "Not Found" not in html  # not Flask's own error page


def test_H19_500_page(client, tmp_path):
    # A database that can't be opened (a folder, not a file) makes the page crash.
    app.config["PROPAGATE_EXCEPTIONS"] = False
    try:
        register(client)
        app.config["DATABASE"] = tmp_path
        response = client.get("/home")
    finally:
        app.config["PROPAGATE_EXCEPTIONS"] = None
    assert response.status_code == 500
    html = page_text(response)
    assert "Something went wrong" in html and "Go to the home page" in html
    assert "Traceback" not in html and "sqlite3" not in html


def test_H19_errors_are_json_for_the_pages_javascript(client):
    register(client)
    client.post("/game/start")
    response = client.post("/game/result", data="x" * 70_000, content_type="application/json")
    assert response.status_code == 413
    assert "error" in response.get_json()


def test_T39_missing_database_is_created(client, tmp_path):
    new_file = tmp_path / "brand-new.db"
    app.config["DATABASE"] = new_file
    assert not new_file.exists()
    assert client.get("/login").status_code == 200
    assert new_file.exists()
    assert {"users", "results", "key_stats", "last_tips"} <= tables_in(new_file)
    assert register(client).headers["Location"] == "/home"


def test_H20_database_deleted_while_running_is_made_again(client, db):
    register(client)
    Path(db.db_path).unlink()
    # The old login no longer has an account, so the student is sent to log in again.
    assert client.get("/home").headers["Location"] == "/login"
    assert "users" in tables_in(db.db_path)


def tables_in(path):
    with Database(path).connect() as connection:
        rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {row["name"] for row in rows}


@pytest.mark.parametrize("username", ["' OR 1=1 --", "typer01' --", "\" OR \"\"=\""])
def test_T40_sql_injection_attempt(client, username):
    register(client)
    client.get("/logout")
    response = login(client, username=username, password="anything")
    assert response.status_code == 200
    assert "Incorrect username or password" in page_text(response)
    assert client.get("/home").headers["Location"] == "/login"


def test_H21_huge_password_refused_without_error(client):
    register(client)
    client.get("/logout")
    assert "Incorrect username or password" in page_text(login(client, password="x" * 10_000))
    response = register(client, username="typer02", password="x" * 101)
    assert "100 characters or fewer" in page_text(response)


@pytest.mark.parametrize("query", ["period=year", "period=", "period=week'--"])
def test_H21_leaderboard_filter_checked_on_server(client, query):
    register(client)
    response = client.get(f"/leaderboard?{query}")
    assert response.status_code == 404
    assert "error" in response.get_json()


def test_H21_unknown_settings_form_refused(client):
    register(client)
    assert client.post("/settings", data={"form": "hack"}).status_code == 400


def test_H22_no_string_joined_sql():
    """Every SQL statement must use ? parameters, never f-strings, %, .format() or + with
    a variable. (USER_SELECT + "WHERE ..." joins two fixed pieces of SQL, which is safe.)"""
    sql = re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE|PRAGMA|CREATE|DROP)\b")
    built = re.compile(r'\bf"|\bf\'|\.format\(|"\s*%\s*\(|"\s*\+\s*[a-z_]+\b(?!\s*\+?\s*")')
    for path in [*ROOT.glob("*.py"), *(ROOT / "models").glob("*.py")]:
        for number, line in enumerate(path.read_text().splitlines(), start=1):
            assert not (built.search(line) and sql.search(line)), f"{path.name} line {number}: {line.strip()}"


def test_T41_session_expiry(client):
    register(client)
    with client.session_transaction() as session:
        session["last_seen"] = time.time() - IDLE_LIMIT_SECONDS - 60
    response = client.get("/home")
    assert response.headers["Location"] == "/login"
    assert "used for 2 hours" in page_text(client.get("/login"))
    assert client.get("/home").headers["Location"] == "/login"


def test_H23_still_logged_in_just_under_2_hours(client):
    register(client)
    with client.session_transaction() as session:
        session["last_seen"] = time.time() - IDLE_LIMIT_SECONDS + 60
    assert client.get("/home").status_code == 200


def test_H23_every_page_resets_the_idle_timer(client):
    register(client)
    with client.session_transaction() as session:
        session["last_seen"] = time.time() - IDLE_LIMIT_SECONDS + 60
    client.get("/home")
    with client.session_transaction() as session:
        assert time.time() - session["last_seen"] < 5


def test_H23_expired_json_request_gets_401(client):
    register(client)
    with client.session_transaction() as session:
        session["last_seen"] = time.time() - IDLE_LIMIT_SECONDS - 60
    response = client.post("/result", json={})
    assert response.status_code == 401
    assert "2 hours" in response.get_json()["error"]


# =====================================================================
# Lucas: typing after time is up, Backspace, game resizing and tab switching
# =====================================================================

THE_CAT = Passage("The cat", "easy")


def test_T42_server_never_counts_more_than_60_seconds():
    # The browser sends 60.8 s because the result was sent just after 0:00.
    data = {"level": "easy", "correct": 7, "total": 7, "characters": 7, "seconds": 60.8,
            "key_errors": {}}
    assert TypingSession.from_json(data, THE_CAT).seconds == 60


def test_T43_backspace_result_accepted_and_mistake_still_counts():
    # Typed "Thw", Backspace, "e": 4 key presses, 3 correct, and "The" is right.
    data = {"level": "easy", "correct": 3, "total": 4, "characters": 3, "seconds": 3.0,
            "key_errors": {"e": {"presses": 2, "errors": 1}}}
    session = TypingSession.from_json(data, THE_CAT)
    assert session.accuracy() == 75.0
    assert session.wpm() == 12.0  # 3 letters / 5 / 0.05 minutes


def test_L20_more_key_presses_than_letters_is_fine_with_backspace():
    data = {"level": "easy", "correct": 9, "total": 12, "characters": 7, "seconds": 10.0,
            "key_errors": {}}
    assert TypingSession.from_json(data, THE_CAT).wpm() == 8.4  # WPM uses the 7 right letters


def test_L20_test_page_explains_backspace(client):
    register(client)
    assert "Press Backspace to fix one" in page_text(client.get("/test"))


def test_T44_game_handles_resizing():
    game_js = (ROOT / "static/js/game.js").read_text()
    assert 'addEventListener("resize"' in game_js
    # Words are kept inside the play area however narrow it gets.
    assert "width - Number(element.dataset.width)" in game_js


def test_T45_game_pauses_when_tab_is_hidden():
    game_js = (ROOT / "static/js/game.js").read_text()
    assert re.search(r'"visibilitychange".*\n.*document\.hidden\) pause\(\)', game_js)
    assert 'window.addEventListener("blur", pause)' in game_js


# =====================================================================
# George: divide by zero, missing tips, small word banks, brand-new users
# =====================================================================


def test_T46_key_with_0_presses():
    stats = KeyStats({"q": 0}, {"q": 0})
    assert stats.error_rate("q") is None
    assert stats.band("q") == "grey"
    assert stats.weakest() == []
    keyboard = TipEngine().heatmap_colours(stats)
    q = next(key for row in keyboard for key in row if key["name"] == "q")
    assert (q["band"], q["percent"], q["presses"]) == ("grey", None, 0)


def test_G16_zero_presses_sent_by_browser(client):
    register(client)
    client.get("/test?level=easy")
    with client.session_transaction() as session:
        level = session["passage"]["level"]
    response = client.post("/result", json={
        "level": level, "correct": 5, "total": 5, "characters": 5, "seconds": 10.0,
        "key_errors": {"q": {"presses": 0, "errors": 0}}})
    assert response.status_code == 200
    assert client.get("/results").status_code == 200


@pytest.fixture
def tips_without_q(tmp_path):
    tips = json.loads(TIPS_FILE.read_text())
    del tips["q"]
    path = tmp_path / "tips.json"
    path.write_text(json.dumps(tips))
    return TipEngine(path)


def test_T47_missing_tip_shows_general_tip(tips_without_q):
    tips = tips_without_q.tips_for([("q", 30.0)])
    assert tips[0]["key"] == "Q"
    assert tips[0]["text"] == tips_without_q.tips[HOME_ROW]
    assert "home row" in tips[0]["text"]


def test_G17_missing_tip_does_not_crash_rotation(tips_without_q):
    assert tips_without_q.next_tip("q") == tips_without_q.tips[HOME_ROW]
    chosen = tips_without_q.choose_tips([("q", 30.0), ("e", 20.0)], {})
    assert chosen["q"] == tips_without_q.tips[HOME_ROW]


def test_T48_few_matching_words_still_20():
    drill = DrillGenerator().make_drill(["q", "z", "x"])
    assert len(drill) == 20


def small_bank(tmp_path, words):
    path = tmp_path / "words.json"
    path.write_text(json.dumps(words))
    return DrillGenerator(path)


def test_G18_topped_up_with_general_words(tmp_path):
    generator = small_bank(tmp_path, ["quiz", "queen"] + [f"word{n}" for n in range(30)])
    drill = generator.make_drill(["q"])
    assert len(drill) == 20
    assert drill.count("quiz") <= 2 and drill.count("queen") <= 2
    assert sum(word.startswith("word") for word in drill) >= 16


def test_G18_tiny_word_bank_still_makes_a_drill(tmp_path):
    generator = small_bank(tmp_path, ["cat", "dog", "sun"])
    assert len(generator.make_drill(["e"])) == 20
    assert len(generator.make_drill([])) == 20


@pytest.mark.parametrize("url", ["/home", "/test", "/results", "/practice", "/practice/drill",
                                 "/progress", "/leaderboard?period=week", "/game", "/settings"])
def test_T49_brand_new_user_every_page_works(client, url):
    register(client)
    response = client.get(url)
    assert response.status_code == 200, url
    assert "Traceback" not in page_text(response)


def test_G19_brand_new_user_messages(client):
    register(client)
    assert "No results yet" in page_text(client.get("/results"))
    assert "Do a test to see your progress" in page_text(client.get("/progress"))
    practice = page_text(client.get("/practice"))
    assert "have any weak keys yet" in practice
    assert "have any weak keys right now" in practice  # the finger guide


# =====================================================================
# Submission: demo database (Section 8.3)
# =====================================================================


def test_demo_database_shows_every_feature(tmp_path, client):
    from make_demo_db import PASSWORD, STUDENTS, make_demo
    demo = make_demo(tmp_path / "demo.db")
    assert len(demo.leaderboard()) == sum(1 for details in STUDENTS.values() if details[2])
    student = demo.get_user("speedyfingers12")
    assert student.check_password(PASSWORD)
    assert student.personal_best > 0
    assert len(KeyStats.load(demo, student.user_id).weakest(3)) == 3

    app.config["DATABASE"] = demo.db_path
    login(client, "speedyfingers12", PASSWORD)
    for url in ("/home", "/results", "/practice", "/progress", "/game", "/settings"):
        assert client.get(url).status_code == 200, url
