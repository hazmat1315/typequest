"""T16: the full journey through all three parts of the app (whole team)."""

from conftest import page_text, register


def finish_test(client, key_errors, correct=40, total=50, seconds=60.0):
    """Do what typing.js does at the end of a test."""
    client.get("/test?level=hard")
    with client.session_transaction() as session:
        level = session["passage"]["level"]
    return client.post("/result", json={
        "level": level, "correct": correct, "total": total, "seconds": seconds,
        "wpm": 0, "accuracy": 0, "key_errors": key_errors,
    })


def test_T16_full_journey_register_test_results(client, db):
    # Register (Henry)
    assert register(client).headers["Location"] == "/home"

    # Results page before any test
    assert "No results yet" in page_text(client.get("/results"))

    # Typing test (Lucas): E is often wrong, A is fine
    response = finish_test(client, {
        "e": {"presses": 20, "errors": 5},
        "a": {"presses": 15, "errors": 0},
    })
    assert response.get_json() == {"redirect": "/results"}

    # Results and tips (Lucas + George)
    results = page_text(client.get("/results"))
    assert "8.0" in results       # (40 / 5) / 1 minute
    assert "80.0%" in results     # 40 / 50
    assert "E (25.0% wrong)" in results
    assert "left middle finger" in results

    # Saved to the account (Henry)
    user_id = db.get_user("typer01").user_id
    assert db.get_stats(user_id) == {"best_wpm": 8.0, "tests_done": 1}
    assert "8.0" in page_text(client.get("/home"))


def test_T16_tips_improve_as_student_practises(client):
    register(client)
    finish_test(client, {"e": {"presses": 20, "errors": 5}})
    assert "E (25.0% wrong)" in page_text(client.get("/results"))

    # A second, much better test brings E down to 5 / 60 = 8.3%, so it is no longer weak.
    finish_test(client, {"e": {"presses": 40, "errors": 0}})
    results = page_text(client.get("/results"))
    assert "E (" not in results
    assert "Great job" in results


def test_T16_journey_survives_logout_and_login(client):
    register(client)
    finish_test(client, {"r": {"presses": 20, "errors": 8}})
    client.get("/logout")
    client.post("/login", data={"username": "typer01", "password": "secret12"})
    assert "R (40.0% wrong)" in page_text(client.get("/results"))
    assert ">1<" in page_text(client.get("/home"))
