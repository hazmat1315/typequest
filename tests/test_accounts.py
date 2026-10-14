"""Tests for accounts and data (Henry): T1-T6 from the test plan, plus H3, H6-H9."""

import pytest

from conftest import login, page_text, register


def count_users(db):
    with db.connect() as connection:
        return connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]


# ---------- Test plan ----------


def test_T1_register_valid_new_user(client, db):
    response = register(client)
    assert response.status_code == 302
    assert response.headers["Location"] == "/home"
    assert db.get_user("typer01") is not None
    assert "Hi typer01!" in page_text(client.get("/home"))


def test_T2_register_taken_username(client, db):
    register(client)
    client.get("/logout")
    response = register(client, password="different1")
    assert "That username is taken" in page_text(response)
    assert count_users(db) == 1


def test_T2_taken_username_ignores_capital_letters(client, db):
    register(client)
    client.get("/logout")
    response = register(client, username="TYPER01")
    assert "That username is taken" in page_text(response)
    assert count_users(db) == 1


def test_T3_register_short_password_boundary(client, db):
    response = register(client, password="12345")  # 5 characters
    assert "6 or more characters" in page_text(response)
    assert count_users(db) == 0


def test_T3_password_of_exactly_6_is_accepted(client, db):
    register(client, password="123456")
    assert count_users(db) == 1


def test_T4_login_correct_details(client):
    register(client)
    client.get("/logout")
    response = login(client)
    assert response.headers["Location"] == "/home"
    assert "Hi typer01!" in page_text(client.get("/home"))


def test_T5_login_wrong_password(client):
    register(client)
    client.get("/logout")
    response = login(client, password="wrong")
    assert response.status_code == 200  # stays on the login page
    assert "Incorrect username or password" in page_text(response)
    assert client.get("/home").headers["Location"] == "/login"


def test_T5_login_unknown_username_gives_same_message(client):
    response = login(client, username="nobody")
    assert "Incorrect username or password" in page_text(response)


@pytest.mark.parametrize("url", ["/home", "/test", "/results"])
def test_T6_logged_out_users_are_redirected(client, url):
    response = client.get(url)
    assert response.status_code == 302
    assert response.headers["Location"] == "/login"


# ---------- Other H requirements ----------


@pytest.mark.parametrize("username", ["ab", "a" * 21, "has space", "bad!name", ""])
def test_H1_invalid_usernames_are_rejected(client, db, username):
    response = register(client, username=username)
    assert "3 to 20 letters or numbers" in page_text(response)
    assert count_users(db) == 0


@pytest.mark.parametrize("username", ["abc", "a" * 20, "Speedy12"])
def test_H1_valid_username_lengths(client, db, username):
    register(client, username=username)
    assert db.get_user(username) is not None


def test_H3_only_a_hash_is_stored(client, db):
    register(client)
    with db.connect() as connection:
        stored = connection.execute("SELECT password_hash FROM users").fetchone()[0]
    assert stored != "secret12"
    assert "secret12" not in stored
    assert db.get_user("typer01").check_password("secret12")


def test_H6_saving_a_result_needs_login(client):
    response = client.post("/result", json={})
    assert response.status_code == 401


def test_H7_save_result_adds_a_row(db):
    user_id = db.add_user("typer01", "secret12")
    db.save_result(user_id, 31.4, 89.0, "medium")
    latest = db.get_latest_result(user_id)
    assert (latest["wpm"], latest["accuracy"], latest["level"]) == (31.4, 89.0, "medium")
    assert latest["date"]


def test_H8_home_page_stats(client, db):
    register(client)
    assert "You haven't done a test yet" in page_text(client.get("/home"))

    user_id = db.get_user("typer01").user_id
    for wpm in (22.5, 34.0, 28.1):
        db.save_result(user_id, wpm, 90.0, "easy")
    assert db.get_stats(user_id) == {"best_wpm": 34.0, "tests_done": 3}
    home = page_text(client.get("/home"))
    assert "34.0" in home and ">3<" in home


def test_H8_stats_only_count_your_own_results(db):
    me = db.add_user("typer01", "secret12")
    other = db.add_user("typer02", "secret12")
    db.save_result(other, 80.0, 99.0, "hard")
    assert db.get_stats(me) == {"best_wpm": None, "tests_done": 0}


def test_H9_logout_clears_session(client):
    register(client)
    response = client.get("/logout")
    assert response.headers["Location"] == "/login"
    assert client.get("/home").headers["Location"] == "/login"


def test_sql_injection_attempt_does_not_log_in(client):
    register(client)
    client.get("/logout")
    response = login(client, username="typer01' --", password="anything")
    assert "Incorrect username or password" in page_text(response)
