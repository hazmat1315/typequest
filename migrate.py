"""Bring an Iteration 1 typequest.db up to date for Iteration 2.  Owner: Henry.

Run it with:   python migrate.py

It adds results.mode, results.score, results.level_reached and users.personal_best,
keeping every account and result. `python app.py` also does this automatically
when it starts, so running this script by hand is optional.
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
