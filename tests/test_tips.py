"""Tests for tips and weak keys (George): T12-T15 from the test plan, plus G1, G2, G5, G6."""

import string

from models.key_stats import TRACKED_KEYS, KeyStats
from models.tip_engine import TipEngine


def stats_from(**counts):
    """stats_from(e=(20, 5)) makes KeyStats where E was pressed 20 times with 5 mistakes."""
    stats = KeyStats()
    stats.update({key: {"presses": p, "errors": e} for key, (p, e) in counts.items()})
    return stats


# ---------- Test plan ----------


def test_T12_weak_key_found():
    stats = stats_from(e=(20, 5))
    assert stats.weakest() == [("e", 25.0)]


def test_T13_error_rate_at_boundary_is_not_weak():
    stats = stats_from(r=(20, 3))
    assert stats.error_rate("r") == 15.0
    assert stats.weakest() == []


def test_T14_too_few_presses_ignored():
    stats = stats_from(q=(4, 2))
    assert stats.error_rate("q") is None
    assert stats.weakest() == []


def test_T14_exactly_10_presses_is_counted():
    stats = stats_from(q=(10, 2))
    assert stats.error_rate("q") == 20.0
    assert stats.weakest() == [("q", 20.0)]


def test_T15_no_weak_keys_gives_great_job_tip():
    engine = TipEngine()
    stats = stats_from(a=(50, 2), s=(40, 0), space=(60, 3))
    tips = engine.tips_for(stats.weakest())
    assert len(tips) == 1
    assert tips[0]["text"] == engine.tips["great_job"]
    assert tips[0]["text"].startswith("Great job")


# ---------- G1, G2: recording and storing ----------


def test_G1_update_adds_to_running_totals():
    stats = stats_from(e=(10, 1))
    stats.update({"e": {"presses": 5, "errors": 2}, "space": {"presses": 8, "errors": 0}})
    assert stats.presses == {"e": 15, "space": 8}
    assert stats.errors == {"e": 3, "space": 0}


def test_G1_bad_key_data_is_ignored():
    stats = KeyStats()
    stats.update({
        "1": {"presses": 10, "errors": 1},        # not a letter or space
        "E": {"presses": 10, "errors": 1},        # must already be lower case
        "a": {"presses": 5, "errors": 9},         # more mistakes than presses
        "b": {"presses": -3, "errors": 0},
        "c": {"presses": "ten", "errors": 0},
        "d": "nonsense",
        "f": {"presses": 12, "errors": 2},        # the only valid one
    })
    assert stats.presses == {"f": 12}


def test_G2_key_stats_saved_and_carried_across_tests(db):
    user_id = db.add_user("typer01", "secret12")

    first = KeyStats.load(db, user_id)
    first.update({"e": {"presses": 12, "errors": 2}})
    first.save(db, user_id)

    second = KeyStats.load(db, user_id)
    second.update({"e": {"presses": 8, "errors": 3}, "r": {"presses": 4, "errors": 0}})
    second.save(db, user_id)

    final = KeyStats.load(db, user_id)
    assert final.presses == {"e": 20, "r": 4}
    assert final.errors == {"e": 5, "r": 0}


def test_G2_each_user_has_their_own_key_stats(db):
    me = db.add_user("typer01", "secret12")
    other = db.add_user("typer02", "secret12")
    stats = stats_from(e=(20, 10))
    stats.save(db, other)
    assert KeyStats.load(db, me).presses == {}


# ---------- G4: weakest keys ----------


def test_G4_three_worst_returned_worst_first():
    stats = stats_from(
        a=(20, 4),    # 20%
        e=(20, 10),   # 50%
        r=(20, 6),    # 30%
        t=(20, 5),    # 25%
        o=(20, 2),    # 10% - not weak
    )
    assert stats.weakest() == [("e", 50.0), ("r", 30.0), ("t", 25.0)]
    assert stats.weakest(n=1) == [("e", 50.0)]


def test_G4_tie_goes_to_key_with_more_mistakes():
    stats = stats_from(k=(10, 2), j=(40, 8))  # both 20%
    assert [key for key, _ in stats.weakest()] == ["j", "k"]


# ---------- G5, G6: tip bank and tips ----------


def test_G5_tip_for_every_letter_and_space():
    tips = TipEngine().tips
    assert set(TRACKED_KEYS) == set(string.ascii_lowercase) | {"space"}
    for key in TRACKED_KEYS:
        assert tips.get(key), f"missing tip for {key}"
    assert tips.get("great_job")


def test_G5_tips_name_the_finger_and_home_key():
    tips = TipEngine().tips
    fingers = ("pinky", "ring", "middle", "pointer", "thumb")
    for key in string.ascii_lowercase:
        assert any(finger in tips[key] for finger in fingers), key
        assert any(home in tips[key] for home in "ASDFJKL;"), key
    assert "thumb" in tips["space"] and "home row" in tips["space"]


def test_G6_one_tip_per_weak_key_with_percentage():
    tips = TipEngine().tips_for([("e", 25.0), ("space", 16.666)])
    assert [tip["key"] for tip in tips] == ["E", "Space"]
    assert [tip["percent"] for tip in tips] == [25.0, 16.7]
    assert "left middle finger" in tips[0]["text"]
