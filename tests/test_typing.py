"""Tests for the typing engine (Lucas): T9, T10 from the test plan, plus L1, L2, L5-L8.

T7, T8 and T11 (timer, green/red letters, paste) happen in the browser, so they
are checked by hand in Chrome; see TEST_RESULTS.md.
"""

import pytest

from conftest import register
from models.passage import LEVELS, Passage
from models.typing_session import TypingSession

EASY = Passage("the cat sat on the mat", "easy")


def session_with(correct, total, seconds):
    return TypingSession(EASY, correct, total, {}, seconds)


# ---------- Test plan ----------


def test_T9_wpm_calculation():
    assert session_with(150, 150, 60).wpm() == 30.0


def test_T10_accuracy_calculation():
    assert session_with(90, 100, 60).accuracy() == 90.0


# ---------- L1, L2: passages ----------


@pytest.mark.parametrize("level", LEVELS)
def test_L1_at_least_5_passages_per_level(level):
    assert len([p for p in Passage.all() if p.level == level]) >= 5


def test_L1_passages_only_use_keyboard_characters():
    for passage in Passage.all():
        assert passage.text.isascii(), passage.text[:30]
        assert passage.text == passage.text.strip()
        assert "  " not in passage.text


def test_L2_random_passage_has_the_right_level():
    for level in LEVELS:
        assert Passage.random(level).level == level


def test_L2_random_never_repeats_the_last_passage():
    previous = Passage.random("medium")
    for _ in range(50):
        passage = Passage.random("medium", exclude=previous.text)
        assert passage.text != previous.text
        previous = passage


def test_L2_unknown_level_is_an_error():
    with pytest.raises(ValueError):
        Passage.random("impossible")


def test_passage_length():
    assert EASY.length() == 22


# ---------- L5: formulas ----------


def test_L5_wpm_uses_actual_time_when_finished_early():
    # 100 correct characters in 30 seconds = 20 words in half a minute = 40 WPM
    assert session_with(100, 100, 30).wpm() == 40.0


def test_L5_results_rounded_to_1_decimal_place():
    session = session_with(97, 113, 60)
    assert session.wpm() == 19.4        # 19.4
    assert session.accuracy() == 85.8   # 85.8407...


def test_L5_no_divide_by_zero():
    assert session_with(0, 0, 0).wpm() == 0.0
    assert session_with(0, 0, 0).accuracy() == 0.0


def test_to_result():
    assert session_with(150, 150, 60).to_result() == {"wpm": 30.0, "accuracy": 100.0, "level": "easy"}


# ---------- from_json: checking what the browser sends ----------


def good_json(**changes):
    data = {"level": "easy", "correct": 20, "total": 22, "seconds": 10.5,
            "wpm": 22.9, "accuracy": 90.9, "key_errors": {"t": {"presses": 3, "errors": 1}}}
    data.update(changes)
    return data


def test_from_json_accepts_a_good_result():
    session = TypingSession.from_json(good_json(), EASY)
    assert (session.correct, session.total, session.seconds) == (20, 22, 10.5)


@pytest.mark.parametrize("changes", [
    {"level": "hard"},              # not the level of the passage
    {"correct": 23, "total": 23},   # more key presses than letters in the passage
    {"correct": 5, "total": 4},     # more correct than total
    {"total": 0, "correct": 0},     # nothing typed
    {"seconds": 0},
    {"seconds": 500},
    {"correct": "lots"},
    {"key_errors": "e"},
    {"seconds": 0.2},               # 20 correct letters in 0.2 s = 1200 WPM, not a real person
])
def test_from_json_rejects_impossible_results(changes):
    with pytest.raises(ValueError):
        TypingSession.from_json(good_json(**changes), EASY)


def test_from_json_accepts_fast_but_human_speed():
    # 20 correct letters in 2 seconds = 120 WPM: fast, but real typists can do it
    assert TypingSession.from_json(good_json(seconds=2), EASY).wpm() == 120.0


def test_from_json_rejects_missing_fields():
    data = good_json()
    del data["seconds"]
    with pytest.raises(ValueError):
        TypingSession.from_json(data, EASY)


# ---------- L7, L8: routes ----------


def current_passage(client):
    with client.session_transaction() as session:
        return session["passage"]


def test_L7_post_result_saves_and_server_recalculates(client, db):
    register(client)
    client.get("/test?level=easy")
    passage = current_passage(client)
    # The page claims 999 WPM, but the server works it out from the counts.
    response = client.post("/result", json=good_json(wpm=999, accuracy=100, correct=50, total=50, seconds=60))
    assert response.status_code == 200
    assert response.get_json() == {"redirect": "/results"}
    latest = db.get_latest_result(db.get_user("typer01").user_id)
    assert latest["wpm"] == 10.0
    assert latest["accuracy"] == 100.0
    assert latest["level"] == passage["level"]


def test_L7_same_test_cannot_be_saved_twice(client, db):
    register(client)
    client.get("/test?level=easy")
    assert client.post("/result", json=good_json()).status_code == 200
    assert client.post("/result", json=good_json()).status_code == 400
    assert db.get_stats(db.get_user("typer01").user_id)["tests_done"] == 1


def test_L7_bad_result_is_not_saved(client, db):
    register(client)
    client.get("/test?level=easy")
    response = client.post("/result", json=good_json(level="hard"))
    assert response.status_code == 400
    assert "error" in response.get_json()
    assert db.get_stats(db.get_user("typer01").user_id)["tests_done"] == 0


def test_L8_new_passage_route(client):
    register(client)
    client.get("/test?level=easy")
    first = current_passage(client)["text"]
    reply = client.get("/passage/hard").get_json()
    assert reply["level"] == "hard"
    assert current_passage(client)["text"] == reply["text"] != first


def test_L8_unknown_level_route(client):
    register(client)
    assert client.get("/passage/extreme").status_code == 404


def test_test_page_shows_passage_and_level_buttons(client):
    register(client)
    html = client.get("/test?level=medium").get_data(as_text=True)
    assert 'data-level="medium"' in html
    for label in ("Easy", "Medium", "Hard", "Restart", "Time left"):
        assert label in html


def test_test_page_remembers_last_level(client):
    register(client)
    client.get("/test?level=hard")
    client.get("/test")
    assert current_passage(client)["level"] == "hard"
