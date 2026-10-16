"""Tests for game mode and UI (Lucas): T25-T30 from the Iteration 2 test plan, plus L10-L18
and the Iteration 3 level change (F5).

The game runs in the browser, so the rules are tested twice: here against the
Game class the server uses, and in tests/js/game.test.js against game.js (run by
test_game_js_rules below). T29 (pause) needs a real browser; see TEST_RESULTS.md.
"""

import json
import re
import shutil
import subprocess
import time
from pathlib import Path

import pytest

from conftest import page_text, register
from models.game import (BANDS, Game, band_for_level, fall_speed, level_for_score, load_game_words,
                         spawn_seconds, words_to_next_level)
from models.typing_session import TypingSession

ROOT = Path(__file__).resolve().parent.parent


def game_json(**changes):
    data = {"score": 120, "level_reached": 3, "correct": 60, "total": 66, "seconds": 75.0,
            "key_errors": {"e": {"presses": 12, "errors": 2}}}
    data.update(changes)
    return data


def play_game(client, seconds_ago=120):
    """Press Start, and pretend it was pressed `seconds_ago` seconds ago."""
    client.post("/game/start")
    with client.session_transaction() as session:
        session["game"] = {"started": time.time() - seconds_ago, "submitted": False}


# ---------- Test plan ----------


def test_T25_word_matched():
    game = Game()
    game.falling = ["rocket", "river"]
    assert game.check_word("rocket") is True
    assert game.falling == ["river"]
    assert game.score == 10


def test_T25_wrong_word_does_nothing():
    game = Game()
    game.falling = ["rocket"]
    assert game.check_word("rock") is False
    assert game.score == 0


def test_T26_word_hits_ground():
    game = Game()
    game.falling = ["cat"]
    game.word_landed("cat")
    assert game.lives == 2
    assert game.falling == []


def test_T27_level_up_at_exactly_3_words():
    # F5 changed the boundary: level 2 now comes after 3 words (30 points), not 100 points.
    game = Game(score=20)
    game.falling = ["cat"]
    slow = game.fall_speed()
    game.check_word("cat")
    assert (game.score, game.level) == (30, 2)
    assert game.fall_speed() > slow


def test_T27_no_level_up_at_2_words():
    game = Game(score=10)
    game.falling = ["cat"]
    game.check_word("cat")
    assert game.level == 1


# ---------- F5: each level needs more words than the last ----------


def test_T51_F5_words_needed_go_up_by_2_each_level():
    assert [words_to_next_level(level) for level in (1, 2, 3, 4, 5)] == [3, 5, 7, 9, 11]


@pytest.mark.parametrize("words, level", [
    (0, 1), (2, 1),      # level 2 needs 3 words
    (3, 2), (7, 2),      # level 3 needs 3 + 5 = 8 words
    (8, 3), (14, 3),     # level 4 needs 8 + 7 = 15 words
    (15, 4), (23, 4),    # level 5 needs 15 + 9 = 24 words
    (24, 5), (99, 10),
])
def test_T51_F5_level_boundaries(words, level):
    assert level_for_score(words * 10) == level


def test_T51_F5_game_climbs_one_level_at_a_time():
    game = Game()
    levels = []
    for number in range(15):
        word = f"word{number}"
        game.falling = [word]
        game.check_word(word)
        levels.append(game.level)
    # Level 2 after the 3rd word, level 3 after the 8th, level 4 after the 15th.
    assert levels == [1, 1, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 3, 4]


def test_T28_game_over_after_3_lives():
    game = Game()
    game.falling = ["cat", "dog", "sun"]
    for word in ("cat", "dog", "sun"):
        assert not game.is_over()
        game.word_landed(word)
    assert game.is_over()


def test_T28_game_result_sent_and_saved(client, db):
    register(client)
    play_game(client)
    response = client.post("/game/result", json=game_json())
    assert response.status_code == 200
    assert response.get_json() == {"saved": True, "score": 120, "level": 3}
    with db.connect() as connection:
        row = connection.execute("SELECT mode, score, level_reached, wpm, accuracy FROM results").fetchone()
    assert tuple(row) == ("game", 120, 3, 9.6, 90.9)  # 60 chars / 5 / 1.25 min


@pytest.mark.parametrize("score", [99999, 99990])
def test_T30_impossible_score_rejected(client, db, score):
    register(client)
    play_game(client)
    response = client.post("/game/result", json=game_json(score=score, level_reached=level_for_score(score),
                                                           correct=40000, total=40000))
    assert response.status_code == 400
    assert "could not be saved" in response.get_json()["error"]
    with db.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM results").fetchone()[0] == 0


# ---------- L13: formulas ----------


def test_L13_fall_speed_formula():
    assert fall_speed(1) == pytest.approx(0.12)
    assert fall_speed(3) == pytest.approx(0.12 * 1.15 ** 2)


def test_L13_spawn_time_formula():
    assert spawn_seconds(1) == 2.5
    assert spawn_seconds(6) == pytest.approx(2.5 / 1.5)


# ---------- L14: word list ----------


def test_L14_at_least_50_words_per_band():
    words = load_game_words()
    assert set(words) == set(BANDS)
    for band in BANDS:
        assert len(words[band]) >= 50, band
        assert len(set(words[band])) == len(words[band]), f"repeated word in {band}"


def test_L14_word_lengths_match_bands():
    words = load_game_words()
    assert all(3 <= len(word) <= 4 for word in words["short"])
    assert all(5 <= len(word) <= 6 for word in words["medium"])
    assert all(len(word) >= 7 for word in words["long"])
    for band in BANDS:
        assert all(word.isalpha() and word.islower() for word in words[band])


def test_L14_band_for_level():
    assert [band_for_level(level) for level in (1, 2, 3, 4, 5, 9)] == [
        "short", "short", "medium", "medium", "long", "long"]


# ---------- L15, L16: Game class and checking results ----------


def test_L16_game_inherits_typing_session():
    game = Game(correct=50, total=60, seconds=60)
    assert isinstance(game, TypingSession)
    assert game.wpm() == 10.0          # reused from TypingSession
    assert game.accuracy() == 83.3


def test_L16_from_json_accepts_a_good_game():
    game = Game.from_json(game_json())
    assert (game.score, game.level, game.seconds) == (120, 3, 75.0)
    assert game.to_result()["mode"] == "game"


@pytest.mark.parametrize("changes", [
    {"score": 125},                         # not a multiple of 10
    {"score": -10, "level_reached": 1},
    {"level_reached": 2},                   # 120 points (12 words) is level 3
    {"correct": 70, "total": 60},
    {"correct": 20},                        # 12 words need at least 36 letters
    {"seconds": 0},
    {"seconds": 20},                        # 12 words can't have appeared in 20 seconds
    {"key_errors": "e"},
    {"score": "lots"},
])
def test_L16_from_json_rejects_impossible_games(changes):
    with pytest.raises(ValueError):
        Game.from_json(game_json(**changes))


def test_L16_max_score_grows_with_time():
    assert Game.max_score(0) == 10          # the first word appears straight away
    assert Game.max_score(60) < Game.max_score(120)
    # A perfect player for 75 seconds could not reach 1000 points.
    assert Game.max_score(75) < 1000


def test_L16_cannot_claim_longer_than_really_played(client):
    register(client)
    play_game(client, seconds_ago=10)
    response = client.post("/game/result", json=game_json(seconds=75))
    assert response.status_code == 400


def test_L15_game_cannot_be_saved_twice(client):
    register(client)
    play_game(client)
    assert client.post("/game/result", json=game_json()).status_code == 200
    assert client.post("/game/result", json=game_json()).status_code == 400


def test_L15_game_without_start_is_refused(client):
    register(client)
    assert client.post("/game/result", json=game_json()).status_code == 400


def test_L15_game_key_errors_go_into_key_stats(client, db):
    from models.key_stats import KeyStats
    register(client)
    play_game(client)
    client.post("/game/result", json=game_json())
    stats = KeyStats.load(db, db.get_user("typer01").user_id)
    assert stats.presses == {"e": 12} and stats.errors == {"e": 2}


# ---------- L10, L17, L18: pages ----------


def test_L10_game_page(client):
    register(client)
    html = page_text(client.get("/game"))
    for label in ("Score", "Level", "Lives", "GROUND", "Start game", "Esc"):
        assert label in html
    settings = json.loads(re.search(r"data-settings='([^']*)'", html).group(1))
    assert settings["startLives"] == 3 and len(settings["words"]["short"]) >= 50
    assert "requestAnimationFrame" in (ROOT / "static/js/game.js").read_text()


def test_L18_every_page_uses_the_shared_nav_bar(client):
    register(client)
    client.get("/test")
    for url in ("/home", "/test", "/game", "/practice", "/progress", "/results"):
        html = page_text(client.get(url))
        assert '<header class="topbar">' in html, url
        for link in ('href="/home"', 'href="/test"', 'href="/game"', 'href="/practice"',
                     'href="/progress"', 'href="/logout"'):
            assert link in html, (url, link)
        assert html.count("style.css") == 1


def test_L18_current_page_marked_in_nav(client):
    register(client)
    assert '<a href="/game" aria-current="page">Game</a>' in page_text(client.get("/game"))


def test_L18_text_at_least_16px():
    css = (ROOT / "static/css/style.css").read_text()
    sizes = [float(size) for size in re.findall(r"font-size:\s*([\d.]+)px", css)]
    assert sizes and min(sizes) >= 16
    rems = [float(size) for size in re.findall(r"font-size:\s*([\d.]+)rem", css)]
    assert min(rems) * 16 >= 16  # 1rem = 16px in Chrome by default


@pytest.mark.parametrize("url", ["/game", "/practice", "/progress"])
def test_new_pages_need_login(client, url):
    assert client.get(url).headers["Location"] == "/login"


# ---------- game.js (run with Node) ----------


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is not installed")
def test_game_js_rules():
    """T25-T28 and F5 against the browser game engine itself."""
    result = subprocess.run(["node", "--test", "tests/js/game.test.js"], cwd=ROOT,
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
