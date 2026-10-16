"""Tests for progress, leaderboard and home (Henry): T17-T24 from the Iteration 2 test plan,
plus H12-H18 and the database migration."""

import json
import re
import sqlite3
import time
from datetime import date, datetime, timedelta

import pytest

from conftest import page_text, register
from models.database import Database
from models.user import User, improvement

TODAY = date(2026, 10, 14)


def user_id_of(db, username="typer01"):
    return db.get_user(username).user_id


def days_ago(days):
    return datetime.now() - timedelta(days=days)


def graph_data(html):
    """The JSON the progress page hands to Chart.js."""
    match = re.search(r"data-graph='([^']*)'", html)
    return json.loads(match.group(1)) if match else None


def finish_test(client, correct, total=None, seconds=60.0, key_errors=None):
    """Do what typing.js does at the end of a test."""
    client.get("/test?level=hard")
    return client.post("/result", json={
        "level": "hard", "correct": correct, "total": total or correct, "characters": correct,
        "seconds": seconds,
        "wpm": 0, "accuracy": 0, "key_errors": key_errors or {},
    })


# ---------- Test plan ----------


def test_T17_progress_graph_with_results(client, db):
    register(client)
    me = user_id_of(db)
    for days, wpm in [(4, 20.0), (3, 24.5), (2, 23.0), (1, 27.0), (0, 30.0)]:
        db.save_result(me, wpm, 90.0, "easy", when=days_ago(days))
    graph = graph_data(page_text(client.get("/progress")))
    assert graph["wpm"] == [20.0, 24.5, 23.0, 27.0, 30.0]  # 5 points, oldest first
    assert graph["labels"] == ["Test 1", "Test 2", "Test 3", "Test 4", "Test 5"]


def test_T17_graph_only_shows_typing_tests(client, db):
    register(client)
    me = user_id_of(db)
    db.save_result(me, 20.0, 90.0, "easy")
    db.save_result(me, 5.0, 80.0, mode="game", score=50, level_reached=1)
    db.save_result(me, 15.0, 95.0, mode="drill")
    assert graph_data(page_text(client.get("/progress")))["wpm"] == [20.0]


def test_T18_progress_graph_with_no_results(client):
    register(client)
    html = page_text(client.get("/progress"))
    assert "Do a test to see your progress" in html
    assert graph_data(html) is None


def test_T19_improvement_with_6_or_more_results():
    assert improvement([20, 22, 21, 30, 31, 32]) == 10.0  # 31 minus 21


def test_T19_improvement_shown_on_progress_page(client, db):
    register(client)
    me = user_id_of(db)
    for wpm in (20, 22, 21, 30, 31, 32):
        db.save_result(me, wpm, 90.0, "easy")
    assert "+10 WPM" in page_text(client.get("/progress"))


def test_T20_leaderboard_tie_goes_to_higher_accuracy(db):
    lower = db.add_user("aaron", "secret12")
    higher = db.add_user("zoe", "secret12")
    db.save_result(lower, 40.0, 90.0, "easy")
    db.save_result(higher, 40.0, 95.0, "easy")
    board = db.top_scores()
    assert [row["username"] for row in board] == ["zoe", "aaron"]
    assert [row["rank"] for row in board] == [1, 2]


def test_T21_rank_outside_top_10(client, db):
    for number in range(1, 15):  # 14 faster typists
        other = db.add_user(f"fast{number}", "secret12")
        db.save_result(other, 100.0 - number, 95.0, "easy")
    register(client)
    db.save_result(user_id_of(db), 28.0, 90.0, "easy")

    assert db.get_rank(user_id_of(db))["rank"] == 15
    html = page_text(client.get("/progress"))
    assert "You: 15th, 28.0 WPM" in html
    assert "typer01 (you)" not in html  # not in the top 10 table
    board = client.get("/leaderboard?period=all").get_json()
    assert len(board["rows"]) == 10
    assert board["you"] == {"rank": 15, "place": "15th", "wpm": 28.0, "in_top": False}


def test_T22_personal_best(client, db):
    register(client)
    finish_test(client, correct=150)  # 30 WPM
    assert db.get_user("typer01").personal_best == 30.0

    finish_test(client, correct=160)  # 32 WPM
    assert "New personal best!" in page_text(client.get("/results"))
    assert db.get_user("typer01").personal_best == 32.0


def test_T22_no_badge_when_slower(client, db):
    register(client)
    finish_test(client, correct=160)  # 32 WPM
    finish_test(client, correct=150)  # 30 WPM
    assert "New personal best!" not in page_text(client.get("/results"))
    assert db.get_user("typer01").personal_best == 32.0


def test_T23_streak_continues():
    dates = {TODAY, TODAY - timedelta(days=1), TODAY - timedelta(days=2)}
    assert User.streak(dates, today=TODAY) == 3


def test_T24_streak_broken():
    dates = {TODAY, TODAY - timedelta(days=3)}
    assert User.streak(dates, today=TODAY) == 1


# ---------- H11: improvement ----------


def test_H11_improvement_needs_2_results():
    assert improvement([]) is None
    assert improvement([25.0]) is None
    assert improvement([25.0, 31.0]) == 6.0


def test_H11_averages_use_3_results_each():
    # Found by planting a bug: T19's numbers give the same answer if only the first 2 are averaged.
    assert improvement([10, 20, 30, 40, 50, 60]) == 30.0  # 50 minus 20


def test_H11_fewer_than_6_uses_latest_minus_first():
    assert improvement([30, 50, 50, 50, 25]) == -5.0  # can go down too


def test_H11_improvement_shown_with_sign(client, db):
    register(client)
    me = user_id_of(db)
    for wpm in (30.0, 27.5):
        db.save_result(me, wpm, 90.0, "easy")
    assert "-2.5 WPM" in page_text(client.get("/progress"))


# ---------- H12, H13, H14: leaderboard ----------


def test_H12_one_row_per_user_using_best_wpm(db):
    me = db.add_user("typer01", "secret12")
    for wpm in (20.0, 35.0, 30.0):
        db.save_result(me, wpm, 90.0, "easy")
    board = db.top_scores()
    assert len(board) == 1 and board[0]["wpm"] == 35.0


def test_H12_users_own_tie_uses_their_better_accuracy(db):
    steady = db.add_user("steady", "secret12")
    twice = db.add_user("twice", "secret12")
    db.save_result(steady, 40.0, 95.0, "easy")
    db.save_result(twice, 40.0, 90.0, "easy")
    db.save_result(twice, 40.0, 96.0, "easy")  # same best WPM, better accuracy
    board = db.top_scores()
    assert [(row["username"], row["accuracy"]) for row in board] == [("twice", 96.0), ("steady", 95.0)]


def test_H12_games_and_drills_do_not_count(db):
    me = db.add_user("typer01", "secret12")
    db.save_result(me, 20.0, 90.0, "easy")
    db.save_result(me, 60.0, 90.0, mode="drill")
    assert db.top_scores()[0]["wpm"] == 20.0


def test_H12_only_top_10_and_you_highlighted(client, db):
    for number in range(12):
        other = db.add_user(f"user{number}", "secret12")
        db.save_result(other, 10.0 + number, 90.0, "easy")
    register(client)
    db.save_result(user_id_of(db), 50.0, 90.0, "easy")
    board = client.get("/leaderboard").get_json()
    assert len(board["rows"]) == 10
    assert board["rows"][0] == {"rank": 1, "username": "typer01", "wpm": 50.0, "accuracy": 90.0, "you": True}
    assert board["you"]["in_top"] is True
    assert '<tr class="you">' in page_text(client.get("/progress"))


def test_H13_ordinal_places():
    from app import ordinal
    assert [ordinal(n) for n in (1, 2, 3, 4, 11, 12, 13, 21, 22, 23, 101, 111)] == [
        "1st", "2nd", "3rd", "4th", "11th", "12th", "13th", "21st", "22nd", "23rd", "101st", "111th"]


def test_H14_this_week_filter(client, db):
    old = db.add_user("oldtimer", "secret12")
    db.save_result(old, 90.0, 99.0, "hard", when=days_ago(10))
    register(client)
    db.save_result(user_id_of(db), 25.0, 90.0, "easy")

    week = client.get("/leaderboard?period=week").get_json()
    assert [row["username"] for row in week["rows"]] == ["typer01"]
    every = client.get("/leaderboard?period=all").get_json()
    assert [row["username"] for row in every["rows"]] == ["oldtimer", "typer01"]
    assert client.get("/leaderboard?period=year").status_code == 404


def test_H14_no_test_this_week_means_no_rank(client, db):
    register(client)
    db.save_result(user_id_of(db), 25.0, 90.0, "easy", when=days_ago(8))
    assert client.get("/leaderboard?period=week").get_json()["you"] is None


def test_privacy_leaderboard_shows_usernames_only(client, db):
    register(client)
    db.save_result(user_id_of(db), 25.0, 90.0, "easy")
    row = client.get("/leaderboard").get_json()["rows"][0]
    assert set(row) == {"rank", "username", "wpm", "accuracy", "you"}  # no user_id, hash or dates


def test_privacy_username_cannot_inject_html(client, db):
    register(client)
    with db.connect() as connection:  # can't happen through the form (H1), but just in case
        connection.execute("UPDATE users SET username = '<b>x</b>'")
    db.save_result(1, 25.0, 90.0, "easy")
    assert "<b>x</b>" not in page_text(client.get("/progress"))


def test_performance_leaderboard_with_100_users(db):
    with db.connect() as connection:
        connection.executemany(
            "INSERT INTO users (username, password_hash, created) VALUES (?, 'x', '2026-10-14')",
            [(f"user{n}",) for n in range(100)],
        )
        connection.executemany(
            "INSERT INTO results (user_id, wpm, accuracy, level, date, mode) "
            "VALUES (?, ?, 90, 'easy', '2026-10-14 10:00:00', 'test')",
            [(1 + n % 100, n % 70) for n in range(2000)],
        )
    start = time.perf_counter()
    db.top_scores(10)
    db.get_rank(50)
    assert time.perf_counter() - start < 1.0


# ---------- H15, H16, H17, H18 ----------


def test_H15_update_best():
    user = User(1, "typer01", "hash", personal_best=30.0)
    assert user.update_best(30.0) is False  # equal is not a new best
    assert user.update_best(32.5) is True
    assert user.personal_best == 32.5


def test_H15_badge_only_for_that_result(client):
    register(client)
    finish_test(client, correct=150)
    assert "New personal best!" in page_text(client.get("/results"))  # first test beats 0
    client.get("/logout")
    client.post("/login", data={"username": "typer01", "password": "secret12"})
    assert "New personal best!" not in page_text(client.get("/results"))


def test_H16_streak_counts_until_end_of_today():
    dates = {TODAY - timedelta(days=1), TODAY - timedelta(days=2)}
    assert User.streak(dates, today=TODAY) == 2  # nothing today yet, but still a streak
    assert User.streak({TODAY - timedelta(days=2)}, today=TODAY) == 0
    assert User.streak(set(), today=TODAY) == 0


def test_H16_streak_counts_games_and_drills(db):
    me = db.add_user("typer01", "secret12")
    db.save_result(me, 20.0, 90.0, "easy", when=days_ago(2))
    db.save_result(me, 5.0, 90.0, mode="game", score=30, level_reached=1, when=days_ago(1))
    db.save_result(me, 15.0, 90.0, mode="drill")
    assert User.streak(db.activity_dates(me)) == 3


def test_H17_home_dashboard(client, db):
    register(client)
    me = user_id_of(db)
    db.save_result(me, 34.0, 90.0, "easy", when=days_ago(1))
    db.save_result(me, 30.0, 92.0, "easy")
    db.save_result(me, 6.0, 50.0, mode="game", score=40, level_reached=1)
    html = page_text(client.get("/home"))
    assert "34.0" in html                  # best WPM
    assert "91.0%" in html                 # average accuracy of tests only
    assert ">2<" in html                   # tests done (the game is not a test)
    assert "2 days" in html                # streak
    for label in ("Typing test", "Play game", "Practice", "Tip of the day"):
        assert label in html


def test_H17_new_user_dashboard(client):
    register(client)
    html = page_text(client.get("/home"))
    assert "0 days" in html
    assert "You haven't done a test yet" in html


def test_H18_results_table_has_mode_and_score(db):
    me = db.add_user("typer01", "secret12")
    db.save_result(me, 6.0, 80.0, mode="game", score=120, level_reached=2)
    with db.connect() as connection:
        row = connection.execute("SELECT mode, score, level_reached, level FROM results").fetchone()
    assert tuple(row) == ("game", 120, 2, None)


def test_H18_unknown_mode_is_refused(db):
    me = db.add_user("typer01", "secret12")
    with pytest.raises(ValueError):
        db.save_result(me, 6.0, 80.0, mode="race")


# ---------- Migration from an Iteration 1 database ----------

ITERATION_1_SCHEMA = """
CREATE TABLE users (user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE, password_hash TEXT NOT NULL, created TEXT NOT NULL);
CREATE TABLE results (result_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users (user_id), wpm REAL NOT NULL, accuracy REAL NOT NULL,
    level TEXT NOT NULL CHECK (level IN ('easy', 'medium', 'hard')), date TEXT NOT NULL);
CREATE TABLE key_stats (user_id INTEGER NOT NULL REFERENCES users (user_id), key TEXT NOT NULL,
    presses INTEGER NOT NULL DEFAULT 0, errors INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (user_id, key));
INSERT INTO users VALUES (1, 'typer01', 'hash', '2026-10-11 09:00:00');
INSERT INTO users VALUES (2, 'typer02', 'hash', '2026-10-11 09:00:00');
INSERT INTO results VALUES (1, 1, 22.5, 90.0, 'easy', '2026-10-11 09:05:00');
INSERT INTO results VALUES (2, 1, 31.0, 85.0, 'hard', '2026-10-12 09:05:00');
INSERT INTO key_stats VALUES (1, 'e', 20, 5);
"""


def test_migration_keeps_iteration_1_data(tmp_path):
    path = tmp_path / "old.db"
    connection = sqlite3.connect(path)
    connection.executescript(ITERATION_1_SCHEMA)
    connection.close()

    db = Database(path)
    db.create_tables()  # what python app.py does
    assert db.get_results(1) == [
        {"result_id": 1, "wpm": 22.5, "accuracy": 90.0, "level": "easy", "date": "2026-10-11 09:05:00"},
        {"result_id": 2, "wpm": 31.0, "accuracy": 85.0, "level": "hard", "date": "2026-10-12 09:05:00"},
    ]
    assert db.get_user("typer01").personal_best == 31.0
    assert db.get_user("typer02").personal_best == 0
    # New rows work, including games with no level.
    assert db.save_result(1, 5.0, 80.0, mode="game", score=20, level_reached=1) == 3
    assert db.migrate() == []  # running it again changes nothing
