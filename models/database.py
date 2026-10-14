"""SQLite database access.  Owner: Henry (H1, H2, H7, H8).

Every query uses ? placeholders (parameters) instead of joining strings together,
which stops SQL injection.
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime

from werkzeug.security import generate_password_hash

from models.user import User

# The three tables from Section 5.1 of the project specification.
# key_stats is George's table; it is created here so the whole database is set up in one place.
SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    created       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS results (
    result_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id   INTEGER NOT NULL REFERENCES users (user_id),
    wpm       REAL NOT NULL,
    accuracy  REAL NOT NULL,
    level     TEXT NOT NULL CHECK (level IN ('easy', 'medium', 'hard')),
    date      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS key_stats (
    user_id INTEGER NOT NULL REFERENCES users (user_id),
    key     TEXT NOT NULL,
    presses INTEGER NOT NULL DEFAULT 0,
    errors  INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, key)
);
"""


def now():
    """The current date and time as text, e.g. 2026-10-12 09:15:02."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class Database:
    """Reads and writes the TypeQuest SQLite database file."""

    def __init__(self, db_path):
        self.db_path = db_path

    @contextmanager
    def connect(self):
        """Open a connection, commit if everything worked, and always close it."""
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row  # lets us read columns by name
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def create_tables(self):
        """Make the tables if they do not exist yet. Safe to run every time the app starts."""
        with self.connect() as connection:
            connection.executescript(SCHEMA)

    # ---------- users ----------

    def add_user(self, username, password):
        """Save a new user with a hashed password (H1, H3).

        Returns the new user_id, or None if the username is already taken (H2).
        The plain password is never stored.
        """
        password_hash = generate_password_hash(password)
        try:
            with self.connect() as connection:
                cursor = connection.execute(
                    "INSERT INTO users (username, password_hash, created) VALUES (?, ?, ?)",
                    (username, password_hash, now()),
                )
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            # The UNIQUE rule on username blocked a duplicate row.
            return None

    def get_user(self, username):
        """Find a user by username (not case sensitive). Returns a User or None."""
        with self.connect() as connection:
            row = connection.execute(
                "SELECT user_id, username, password_hash FROM users WHERE username = ?",
                (username,),
            ).fetchone()
        if row is None:
            return None
        return User(row["user_id"], row["username"], row["password_hash"])

    # ---------- results ----------

    def save_result(self, user_id, wpm, accuracy, level):
        """Add one test result to the results table (H7). Returns the new result_id."""
        with self.connect() as connection:
            cursor = connection.execute(
                "INSERT INTO results (user_id, wpm, accuracy, level, date) VALUES (?, ?, ?, ?, ?)",
                (user_id, wpm, accuracy, level, now()),
            )
            return cursor.lastrowid

    def get_latest_result(self, user_id):
        """The user's most recent result as a dictionary, or None if they have no results."""
        with self.connect() as connection:
            row = connection.execute(
                "SELECT result_id, wpm, accuracy, level, date FROM results "
                "WHERE user_id = ? ORDER BY result_id DESC LIMIT 1",
                (user_id,),
            ).fetchone()
        return dict(row) if row else None

    def get_stats(self, user_id):
        """Best WPM and number of tests done for the home page (H8).

        best_wpm is None when the user has not done a test yet.
        """
        with self.connect() as connection:
            row = connection.execute(
                "SELECT MAX(wpm) AS best_wpm, COUNT(*) AS tests_done FROM results WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        return {"best_wpm": row["best_wpm"], "tests_done": row["tests_done"]}
