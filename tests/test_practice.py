"""Tests for the heatmap, drills and tips (George): T31-T36 from the Iteration 2 test plan,
plus G8-G15."""

import json
import re
import string
from collections import Counter

import pytest

from conftest import page_text, register
from models.drill_generator import DrillGenerator
from models.key_stats import TRACKED_KEYS, KeyStats
from models.tip_engine import TIP_OF_THE_DAY, TipEngine


def stats_from(**counts):
    """stats_from(e=(20, 5)) makes KeyStats where E was pressed 20 times with 5 mistakes."""
    stats = KeyStats()
    stats.update({key: {"presses": p, "errors": e} for key, (p, e) in counts.items()})
    return stats


def finish_test(client, key_errors):
    client.get("/test?level=hard")
    return client.post("/result", json={
        "level": "hard", "correct": 40, "total": 50, "seconds": 60.0, "key_errors": key_errors,
    })


def current_drill(client):
    with client.session_transaction() as session:
        return session["drill"]


# ---------- Test plan ----------


def test_T31_heatmap_colours():
    stats = stats_from(e=(20, 5), t=(20, 2), a=(50, 1), q=(4, 0))  # 25%, 10%, 2%, 4 presses
    assert [stats.band(key) for key in "etaq"] == ["red", "orange", "green", "grey"]


def test_T31_heatmap_on_results_page(client):
    register(client)
    finish_test(client, {"e": {"presses": 20, "errors": 5}, "a": {"presses": 50, "errors": 1}})
    html = page_text(client.get("/results"))
    assert "Mistake heatmap" in html
    assert re.search(r'class="key red"[^>]*title="E: 25.0% wrong"', html)
    assert 'title="A: 2.0% wrong"' in html
    assert 'title="Q: not enough presses yet (0)"' in html


def test_T32_word_scoring():
    assert DrillGenerator.score_word("error", ["e", "r"]) == 4
    assert DrillGenerator.score_word("tree", ["e", "r"]) == 3
    assert DrillGenerator.score_word("cat", ["e", "r"]) == 0


def test_T33_drill_uses_weak_keys():
    drill = DrillGenerator().make_drill(["e", "r", "o"])
    assert len(drill) == 20
    with_weak_keys = [word for word in drill if set(word) & {"e", "r", "o"}]
    assert len(with_weak_keys) >= 15  # most words (in fact all of them)


def test_T34_two_drills_differ():
    generator = DrillGenerator()
    assert generator.make_drill(["e", "r"]) != generator.make_drill(["e", "r"])


def test_T35_no_weak_keys_gives_mixed_drill_with_message(client):
    register(client)
    html = page_text(client.get("/practice"))
    assert "have any weak keys yet, so this drill is a random mix of words" in html
    assert "None yet" in html
    assert len(current_drill(client)["text"].split()) == 20


def test_T36_tip_rotation(client, db):
    register(client)
    shown = []
    for _ in range(4):  # E stays weak for every test
        finish_test(client, {"e": {"presses": 20, "errors": 10}})
        html = page_text(client.get("/results"))
        shown.append(re.search(r"E \(\d+\.\d% wrong\):</strong>\s*(.+?)\s*</li>", html).group(1))
    for first, second in zip(shown, shown[1:]):
        assert first != second
    # Refreshing the results page keeps the same tip.
    assert shown[-1] in page_text(client.get("/results"))


# ---------- G8: heatmap ----------


def test_G8_band_boundaries():
    stats = stats_from(a=(100, 4), b=(100, 5), c=(100, 15), d=(100, 16), e=(9, 9), f=(10, 0))
    assert [stats.band(key) for key in "abcdef"] == ["green", "orange", "orange", "red", "grey", "green"]


def test_G8_heatmap_keyboard_layout():
    keyboard = TipEngine().heatmap_colours(KeyStats())
    rows = ["".join(key["name"] for key in row) for row in keyboard[:3]]
    assert rows == ["qwertyuiop", "asdfghjkl", "zxcvbnm"]
    assert keyboard[3][0]["name"] == "space"
    assert all(key["band"] == "grey" for row in keyboard for key in row)


def test_G8_heatmap_shows_percent_on_hover():
    keyboard = TipEngine().heatmap_colours(stats_from(e=(30, 4)))
    e = next(key for key in keyboard[0] if key["name"] == "e")
    assert e == {"name": "e", "label": "E", "band": "orange", "percent": 13.3, "presses": 30}


# ---------- G9, G10, G11: word bank and drills ----------


def test_G9_word_bank_has_500_words():
    words = DrillGenerator().word_bank
    assert len(words) >= 500
    assert len(set(words)) == len(words)
    assert all(word.isalpha() and word.islower() for word in words)


def test_G10_score_counts_repeats_and_ignores_case():
    assert DrillGenerator.score_word("mirror", ["R"]) == 3
    assert DrillGenerator.score_word("cat", []) == 0


def test_G10_drill_uses_highest_scoring_words():
    generator = DrillGenerator()
    drill = generator.make_drill(["e", "r"])
    lowest = min(generator.score_word(word, "er") for word in drill)
    scores = sorted((generator.score_word(word, "er") for word in generator.word_bank), reverse=True)
    assert lowest >= scores[39]  # every word is from the top 40


def test_G11_picked_from_top_40_not_just_top_20():
    generator = DrillGenerator()
    seen = set()
    for _ in range(15):
        seen.update(generator.make_drill(["e", "r"]))
    # Words with the same score are shuffled, so which 40 make the cut can change a
    # little each time; test_G10 checks every word is still a top-40 score.
    assert len(seen) > 20


def test_G11_no_word_more_than_twice():
    generator = DrillGenerator()
    for weak in (["e", "r", "o"], ["q"], ["z"], ["x", "q"]):  # q, z and x have few words
        for _ in range(20):
            drill = generator.make_drill(weak)
            assert len(drill) == 20
            assert max(Counter(drill).values()) <= 2, (weak, drill)


def test_G11_rare_key_still_practised():
    drill = DrillGenerator().make_drill(["q"])
    assert sum("q" in word for word in drill) >= 6


def test_G14_space_only_is_a_mixed_drill():
    drill = DrillGenerator().make_drill(["space"])
    assert len(drill) == 20


# ---------- G12, G13: practice page ----------


def test_G12_practice_page_shows_weak_keys_and_drill(client):
    register(client)
    finish_test(client, {"e": {"presses": 20, "errors": 10}, "r": {"presses": 20, "errors": 4}})
    html = page_text(client.get("/practice"))
    assert '<li class="key red" title="E: 50.0% wrong">E</li>' in html
    assert '<li class="key red" title="R: 20.0% wrong">R</li>' in html
    assert "picked because they have lots of your weak letters" in html
    assert "js/typing.js" in html and "js/practice.js" in html  # reuses the typing engine
    drill = json.loads(re.search(r"data-drill='([^']*)'", html).group(1))
    assert drill["text"] == current_drill(client)["text"]
    assert all(set(word) & {"e", "r"} for word in drill["text"].split())


def test_G12_new_drill_button(client):
    register(client)
    first = client.get("/practice/drill").get_json()
    second = client.get("/practice/drill").get_json()
    assert first["text"] != second["text"]
    assert current_drill(client)["text"] == second["text"]


def drill_json(text, correct, total, key_errors, seconds=30.0):
    return {"level": None, "correct": correct, "total": total, "seconds": seconds,
            "wpm": 0, "accuracy": 0, "key_errors": key_errors}


def test_G13_before_and_after(client, db):
    register(client)
    finish_test(client, {"e": {"presses": 20, "errors": 5}})  # E 25%
    client.get("/practice")
    text = current_drill(client)["text"]
    response = client.post("/practice/result", json=drill_json(text, 60, 60, {"e": {"presses": 20, "errors": 1}}))
    reply = response.get_json()
    assert response.status_code == 200
    assert reply["focus"] == [{"key": "E", "before": 25.0, "after": 15.0}]  # 6 / 40
    with db.connect() as connection:
        assert connection.execute("SELECT mode, level FROM results ORDER BY result_id DESC").fetchone()[0] == "drill"


def test_G13_drill_cannot_be_saved_twice_or_faked(client):
    register(client)
    client.get("/practice")
    text = current_drill(client)["text"]
    assert client.post("/practice/result", json=drill_json(text, 10, len(text) + 1, {})).status_code == 400
    assert client.post("/practice/result", json=drill_json(text, 10, 12, {})).status_code == 200
    assert client.post("/practice/result", json=drill_json(text, 10, 12, {})).status_code == 400


def test_G13_drill_without_practice_page_is_refused(client):
    register(client)
    assert client.post("/practice/result", json=drill_json("x", 1, 1, {})).status_code == 400


# ---------- G15: rotating tips ----------


def test_G15_every_key_has_at_least_2_different_tips():
    tips = TipEngine().tips
    for key in TRACKED_KEYS:
        assert len(set(tips[key])) >= 2, key
    assert len(tips[TIP_OF_THE_DAY]) >= 2


def test_G15_next_tip_is_never_the_last_one():
    engine = TipEngine()
    for key in string.ascii_lowercase:
        last = engine.tips[key][0]
        for _ in range(10):
            tip = engine.next_tip(key, last)
            assert tip != last and tip in engine.tips[key]
            last = tip


def test_G15_first_tip_counts_as_seen():
    engine = TipEngine()
    assert engine.next_tip("e") != engine.tips["e"][0]


def test_G15_last_tips_saved_per_user(db):
    me = db.add_user("typer01", "secret12")
    other = db.add_user("typer02", "secret12")
    TipEngine.save_last_tips(db, me, {"e": "tip one"})
    TipEngine.save_last_tips(db, me, {"e": "tip two", "r": "tip three"})
    assert TipEngine.load_last_tips(db, me) == {"e": "tip two", "r": "tip three"}
    assert TipEngine.load_last_tips(db, other) == {}


@pytest.mark.parametrize("weak", [[("e", 25.0)], []])
def test_G15_tips_for_uses_chosen_tip(weak):
    engine = TipEngine()
    chosen = {"e": engine.tips["e"][1]}
    tips = engine.tips_for(weak, chosen)
    if weak:
        assert tips[0]["text"] == engine.tips["e"][1]
    else:
        assert tips[0]["text"].startswith("Great job")
