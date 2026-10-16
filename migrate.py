"""Bring an older typequest.db (Iteration 1 or 2) up to date.  Owner: Henry.

Run it with:   python migrate.py

It adds results.mode, results.score, results.level_reached and users.personal_best
(Iteration 2), and users.sound_on and users.slow_mode (Iteration 3), keeping every
account and result. The app also does this
automatically, so running this script by hand is optional.
"""

from app import app
from models.database import Database

if __name__ == "__main__":
    db = Database(app.config["DATABASE"])
    changes = db.migrate() if db.columns("results") else []
    db.create_tables()  # makes any missing tables and indexes
    for change in changes or ["Already up to date. Nothing to change."]:
        print(change)
    print(f"Database: {db.db_path}")
    print("results columns:", ", ".join(db.columns("results")))
    print("users columns:  ", ", ".join(db.columns("users")))
