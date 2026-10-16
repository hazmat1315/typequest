"""Make demo.db: a small database of sample users so every feature can be seen working.
Owner: Henry (Section 8.3 of the Iteration 3 specification).

Run it with:   python make_demo_db.py      then   python app.py --demo

It makes 8 students with about two weeks of tests, games and drills, and key
statistics with some weak keys. Every account's password is demo123.
The same random seed is used every time, so the demo data is always the same.
"""

import random
from datetime import datetime, timedelta
from pathlib import Path

from models.database import Database
from models.game import level_for_score
from models.key_stats import KeyStats
from models.tip_engine import KEYBOARD_ROWS
from models.user import User

DEMO_FILE = "demo.db"
PASSWORD = "demo123"

# username: (starting WPM, WPM gained per test, number of tests, weak keys)
STUDENTS = {
    "speedyfingers12": (24, 1.4, 10, "ero"),
    "typingtiger": (31, 0.9, 8, "pq"),
    "rocketkeys": (18, 1.8, 7, "bnm"),
    "quietcoder": (38, 0.5, 6, "z"),
    "starfish22": (14, 1.1, 5, "tyh"),
    "newbie01": (0, 0, 0, ""),          # registered but hasn't started
    "keyboardking": (49, 0.4, 9, ""),   # no weak keys: gets the "Great job" tip
    "fastfox7": (42, 0.7, 6, "x"),
}


def fake_key_stats(weak_keys, tests):
    """Running key totals for a student: weak keys around 20-30% wrong, the rest low."""
    stats = KeyStats()
    for key in "".join(KEYBOARD_ROWS) + " ":
        name = "space" if key == " " else key
        presses = random.randint(8, 30) * tests
        rate = random.uniform(0.18, 0.32) if key in weak_keys else random.uniform(0, 0.08)
        stats.update({name: {"presses": presses, "errors": round(presses * rate)}})
    return stats


def make_demo(path=DEMO_FILE):
    """Delete any old demo database and fill a new one. Returns the Database."""
    random.seed(7)
    Path(path).unlink(missing_ok=True)
    db = Database(path)
    db.create_tables()

    now = datetime.now().replace(microsecond=0)
    for username, (start_wpm, gain, tests, weak_keys) in STUDENTS.items():
        user_id = db.add_user(username, PASSWORD)
        if tests == 0:
            continue
        best = 0.0
        for number in range(tests):
            # One test a day, ending today, so the streak and "This week" both have data.
            when = now - timedelta(days=tests - 1 - number, hours=random.randint(0, 3))
            wpm = round(start_wpm + gain * number + random.uniform(-2, 2), 1)
            accuracy = round(random.uniform(86, 98), 1)
            db.save_result(user_id, wpm, accuracy, random.choice(("easy", "medium", "hard")), when=when)
            best = max(best, wpm)
            if number % 3 == 1:
                score = random.randint(4, 16) * 10
                db.save_result(user_id, round(wpm * 0.6, 1), accuracy, mode="game", score=score,
                               level_reached=level_for_score(score), when=when + timedelta(minutes=5))
            if number % 4 == 2:
                db.save_result(user_id, round(wpm * 0.9, 1), accuracy, mode="drill",
                               when=when + timedelta(minutes=10))
        db.save_personal_best(User(user_id, username, "", best))
        fake_key_stats(weak_keys, tests).save(db, user_id)
    return db


if __name__ == "__main__":
    make_demo()
    print(f"Made {DEMO_FILE}. Start the app with:  python app.py --demo")
    print(f"Log in as: speedyfingers12 / {PASSWORD}   (or any student in make_demo_db.py)")
