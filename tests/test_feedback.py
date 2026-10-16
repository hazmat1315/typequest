"""Iteration 3 changes from client feedback (Section 2.1): one test group per F-change.

    T51  F5  Lucas   Levels need 3, 5, 7 ... words (in test_game.py and tests/js/game.test.js)
    T52  F6  Lucas   Settings page: sound effects and slow mode
    T53  F7  George  Finger guide
"""

import json
import re

import pytest

from conftest import page_text, register
from models.finger_guide import KEYS_FOR_FINGER, FingerGuide
from models.game import SLOW_MODE_SPEED


def finish_test(client, correct, key_errors=None):
    """Do what typing.js does at the end of a 60 second test."""
    client.get("/test?level=hard")
    return client.post("/result", json={
        "level": "hard", "correct": correct, "total": correct, "characters": correct,
        "seconds": 60.0, "key_errors": key_errors or {},
    })


# =====================================================================
# T52, F6: settings page with sound effects and slow mode (Lucas)
# =====================================================================


def test_F6_migration_adds_settings_columns(tmp_path):
    from models.database import Database
    db = Database(tmp_path / "old.db")
    with db.connect() as connection:  # an Iteration 2 users table
        connection.execute("CREATE TABLE users (user_id INTEGER PRIMARY KEY AUTOINCREMENT, "
                           "username TEXT NOT NULL UNIQUE COLLATE NOCASE, password_hash TEXT NOT NULL, "
                           "created TEXT NOT NULL, personal_best REAL NOT NULL DEFAULT 0)")
        connection.execute("INSERT INTO users (username, password_hash, created) VALUES ('old', 'x', 'now')")
    db.create_tables()
    assert {"sound_on", "slow_mode"} <= set(db.columns("users"))
    old = db.get_user("old")
    assert (old.sound_on, old.slow_mode) == (False, False)
    assert db.migrate() == []  # running it again changes nothing


def game_settings(client):
    html = page_text(client.get("/game"))
    return json.loads(re.search(r"data-settings='([^']*)'", html).group(1))


def test_T52_settings_off_by_default(client):
    register(client)
    settings = game_settings(client)
    assert settings["soundOn"] is False and settings["slowMode"] is False
    assert settings["slowModeSpeed"] == SLOW_MODE_SPEED < 1


def test_T52_settings_saved_and_used_by_game(client, db):
    register(client)
    response = client.post("/settings", data={"form": "game", "sound_on": "on", "slow_mode": "on"})
    assert response.headers["Location"] == "/settings"
    user = db.get_user("typer01")
    assert user.sound_on and user.slow_mode
    settings = game_settings(client)
    assert settings["soundOn"] is True and settings["slowMode"] is True
    assert "Slow mode is on and sound is on" in page_text(client.get("/game"))

    # Unticking a box turns it off again (an unticked checkbox isn't sent at all).
    client.post("/settings", data={"form": "game", "sound_on": "on"})
    settings = game_settings(client)
    assert settings["soundOn"] is True and settings["slowMode"] is False


def test_T52_settings_page(client):
    register(client)
    html = page_text(client.get("/settings"))
    for text in ("Sound effects", "Slow mode for beginners", "Save game settings"):
        assert text in html


def test_F5_game_page_explains_levels(client):
    register(client)
    html = page_text(client.get("/game"))
    assert "Destroy 3 words to reach level 2" in html
    assert "3 words to level 2" in html
    settings = game_settings(client)
    assert (settings["firstLevelWords"], settings["extraWordsPerLevel"]) == (3, 2)


# =====================================================================
# T53, F7: finger guide (George)
# =====================================================================


def test_T53_every_letter_has_exactly_one_finger():
    letters = "".join(KEYS_FOR_FINGER.values())
    assert sorted(letters) == list("abcdefghijklmnopqrstuvwxyz")
    assert FingerGuide.finger_for("space") == "right_thumb"
    assert FingerGuide.finger_for("1") is None


@pytest.mark.parametrize("key, finger", [("e", "left_middle"), ("b", "left_pointer"), ("y", "right_pointer"),
                                         ("p", "right_pinky"), ("a", "left_pinky"), ("k", "right_middle")])
def test_T53_fingers_match_the_tips(key, finger):
    assert FingerGuide.finger_for(key) == finger


def test_T53_describe():
    assert FingerGuide.describe("e") == "E: use your left middle finger. It starts on D."
    assert FingerGuide.describe("d") == "D: use your left middle finger. This is its home key."
    assert FingerGuide.describe("space").startswith("Space: use one thumb")


def test_T53_guide_highlights_weak_fingers():
    guide = FingerGuide.guide(["e", "space"])
    weak_keys = [key["name"] for row in guide["keyboard"] for key in row if key["weak"]]
    weak_fingers = [finger["id"] for finger in guide["hands"] if finger["weak"]]
    assert weak_keys == ["e", "space"]
    assert weak_fingers == ["left_middle", "left_thumb", "right_thumb"]
    assert len(guide["steps"]) == 2
    assert len(guide["hands"]) == 10


def test_T53_finger_guide_on_results_page(client):
    register(client)
    finish_test(client, 40, {"e": {"presses": 20, "errors": 5}})
    html = page_text(client.get("/results"))
    assert "Which finger?" in html
    assert re.search(r'class="key finger-key finger-middle weak"\s+role="listitem" tabindex="0" data-key="e"', html)
    assert 'data-finger="left_middle"' in html
    assert "E: use your left middle finger. It starts on D." in html


def test_T53_finger_guide_on_practice_page_and_new_drill(client):
    register(client)
    finish_test(client, 40, {"r": {"presses": 20, "errors": 8}})
    assert "R: use your left pointer finger" in page_text(client.get("/practice"))
    drill = client.get("/practice/drill").get_json()
    assert drill["finger_guide"]["steps"] == ["R: use your left pointer finger. It starts on F."]
