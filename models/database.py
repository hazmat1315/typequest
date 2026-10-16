"""SQLite database access.  Owner: Henry (H1, H2, H7, H8, H10-H18, H20, H22, F6).

H22: every query uses ? placeholders (parameters) instead of joining strings together,
which stops SQL injection. tests/test_reliability.py searches this file and app.py for
string-joined SQL to check it stays that way.
"""

import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta

from werkzeug.security import generate_password_hash

from models.user import User

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
MODES = ("test", "game", "drill")  # H18: every activity is saved in the one results table

# The tables from Section 5.1 of the Iteration 1 and Iteration 2 specifications, plus the
# Iteration 3 settings columns. key_stats is George's table; it is created here
# so the whole database is set up in one place.
SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    created       TEXT NOT NULL,
    personal_best REAL NOT NULL DEFAULT 0,
    sound_on      INTEGER NOT NULL DEFAULT 0,
    slow_mode     INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS results (
    result_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL REFERENCES users (user_id),
    wpm           REAL NOT NULL,
    accuracy      REAL NOT NULL,
    level         TEXT CHECK (level IN ('easy', 'medium', 'hard')),
    date          TEXT NOT NULL,
    mode          TEXT NOT NULL DEFAULT 'test' CHECK (mode IN ('test', 'game', 'drill')),
    score         INTEGER,
    level_reached INTEGER
);

CREATE TABLE IF NOT EXISTS key_stats (
    user_id INTEGER NOT NULL REFERENCES users (user_id),
    key     TEXT NOT NULL,
    presses INTEGER NOT NULL DEFAULT 0,
    errors  INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, key)
);

CREATE TABLE IF NOT EXISTS last_tips (
    user_id INTEGER NOT NULL REFERENCES users (user_id),
    key     TEXT NOT NULL,
    tip     TEXT NOT NULL,
    PRIMARY KEY (user_id, key)
);
"""

# Made after the migration, because an Iteration 1 database has no mode column yet.
INDEXES = """
CREATE INDEX IF NOT EXISTS results_by_user ON results (user_id, mode);
CREATE INDEX IF NOT EXISTS results_by_mode ON results (mode, date);
"""

# Iteration 3 columns added to an older users table: (column name, SQL to add it).
NEW_USER_COLUMNS = (
    ("sound_on", "ALTER TABLE users ADD COLUMN sound_on INTEGER NOT NULL DEFAULT 0"),
    ("slow_mode", "ALTER TABLE users ADD COLUMN slow_mode INTEGER NOT NULL DEFAULT 0"),
)

# The columns a User is made from.
USER_SELECT = "SELECT user_id, username, password_hash, personal_best, sound_on, slow_mode FROM users "

# Iteration 1 results table -> Iteration 2. SQLite cannot remove the NOT NULL rule from
# the level column (games and drills have no level), so the table is copied into a new one.
MIGRATE_RESULTS = """
ALTER TABLE results RENAME TO results_iteration1;
CREATE TABLE results (
    result_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL REFERENCES users (user_id),
    wpm           REAL NOT NULL,
    accuracy      REAL NOT NULL,
    level         TEXT CHECK (level IN ('easy', 'medium', 'hard')),
    date          TEXT NOT NULL,
    mode          TEXT NOT NULL DEFAULT 'test' CHECK (mode IN ('test', 'game', 'drill')),
    score         INTEGER,
    level_reached INTEGER
);
INSERT INTO results (result_id, user_id, wpm, accuracy, level, date, mode)
    SELECT result_id, user_id, wpm, accuracy, level, date, 'test' FROM results_iteration1;
DROP TABLE results_iteration1;
"""


def now():
    """The current date and time as text, e.g. 2026-10-12 09:15:02."""
    return datetime.now().strftime(DATE_FORMAT)


class Database:
    """Reads and writes the TypeQuest SQLite database file."""

    def __init__(self, db_path):
        """Remember which database file to use."""
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
        """H20: make the tables if they do not exist yet, then bring an old database up to date.

        Safe to run every time the app starts, and makes a brand new typequest.db if the
        file is missing.
        """
        with self.connect() as connection:
            connection.executescript(SCHEMA)
        self.migrate()
        with self.connect() as connection:
            connection.executescript(INDEXES)

    def columns(self, table):
        """The column names of a table."""
        with self.connect() as connection:
            rows = connection.execute("SELECT name FROM pragma_table_info(?)", (table,))
            return [row["name"] for row in rows]

    def migrate(self):
        """Add the Iteration 2 and 3 columns to an older database, keeping all its data.

        Returns a list of the changes made (empty if the database was already up to date).
        """
        changes = []
        if "mode" not in self.columns("results"):
            with self.connect() as connection:
                connection.executescript(MIGRATE_RESULTS)
            changes.append("results: added mode, score and level_reached; old results are mode 'test'")
        if "personal_best" not in self.columns("users"):
            with self.connect() as connection:
                connection.execute(
                    "ALTER TABLE users ADD COLUMN personal_best REAL NOT NULL DEFAULT 0"
                )
                # Start everyone's personal best at their best Iteration 1 test.
                connection.execute(
                    "UPDATE users SET personal_best = COALESCE("
                    "(SELECT MAX(wpm) FROM results WHERE results.user_id = users.user_id"
                    " AND mode = 'test'), 0)"
                )
            changes.append("users: added personal_best, set from each user's best test")
        user_columns = self.columns("users")
        for column, sql in NEW_USER_COLUMNS:
            if column not in user_columns:
                with self.connect() as connection:
                    connection.execute(sql)
                changes.append(f"users: added {column}")
        return changes

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
            row = connection.execute(USER_SELECT + "WHERE username = ?", (username,)).fetchone()
        return make_user(row)

    def get_user_by_id(self, user_id):
        """Find a user by user_id. Returns a User or None."""
        with self.connect() as connection:
            row = connection.execute(USER_SELECT + "WHERE user_id = ?", (user_id,)).fetchone()
        return make_user(row)

    def save_personal_best(self, user):
        """Write a User's personal_best back to the users table (H15)."""
        with self.connect() as connection:
            connection.execute(
                "UPDATE users SET personal_best = ? WHERE user_id = ?",
                (user.personal_best, user.user_id),
            )

    # ---------- settings (F6) ----------

    def save_settings(self, user_id, sound_on, slow_mode):
        """Save a user's game settings: sound effects and slow mode, each True or False."""
        with self.connect() as connection:
            connection.execute(
                "UPDATE users SET sound_on = ?, slow_mode = ? WHERE user_id = ?",
                (int(sound_on), int(slow_mode), user_id),
            )

    # ---------- results ----------

    def save_result(self, user_id, wpm, accuracy, level=None, mode="test", score=None,
                    level_reached=None, when=None):
        """Add one test, game or drill result to the results table (H7, H18).

        Returns the new result_id. `when` is only used by the tests, to save results
        on earlier days.
        """
        if mode not in MODES:
            raise ValueError(f"Unknown mode: {mode}")
        when = when.strftime(DATE_FORMAT) if when else now()
        with self.connect() as connection:
            cursor = connection.execute(
                "INSERT INTO results (user_id, wpm, accuracy, level, date, mode, score, level_reached) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (user_id, wpm, accuracy, level, when, mode, score, level_reached),
            )
            return cursor.lastrowid

    def get_latest_result(self, user_id):
        """The user's most recent typing test as a dictionary, or None if they have not done one."""
        with self.connect() as connection:
            row = connection.execute(
                "SELECT result_id, wpm, accuracy, level, date FROM results "
                "WHERE user_id = ? AND mode = 'test' ORDER BY result_id DESC LIMIT 1",
                (user_id,),
            ).fetchone()
        return dict(row) if row else None

    def get_results(self, user_id):
        """Every typing test the user has done, oldest first (H10)."""
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT result_id, wpm, accuracy, level, date FROM results "
                "WHERE user_id = ? AND mode = 'test' ORDER BY date, result_id",
                (user_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_stats(self, user_id):
        """Best WPM and number of typing tests done for the home page (H8).

        best_wpm is None when the user has not done a test yet.
        """
        with self.connect() as connection:
            row = connection.execute(
                "SELECT MAX(wpm) AS best_wpm, COUNT(*) AS tests_done FROM results "
                "WHERE user_id = ? AND mode = 'test'",
                (user_id,),
            ).fetchone()
        return {"best_wpm": row["best_wpm"], "tests_done": row["tests_done"]}

    def average_accuracy(self, user_id):
        """Average accuracy of the user's typing tests to 1 decimal place, or None (H17)."""
        with self.connect() as connection:
            row = connection.execute(
                "SELECT AVG(accuracy) AS average FROM results WHERE user_id = ? AND mode = 'test'",
                (user_id,),
            ).fetchone()
        return None if row["average"] is None else round(row["average"], 1)

    def activity_dates(self, user_id):
        """The set of days (date objects) the user did any test, game or drill (H16)."""
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT DISTINCT substr(date, 1, 10) AS day FROM results WHERE user_id = ?",
                (user_id,),
            ).fetchall()
        return {date.fromisoformat(row["day"]) for row in rows}

    # ---------- leaderboard (H12, H13, H14) ----------

    # One row per user: the typing test with their best WPM (and the better accuracy if
    # they got that WPM twice). Ties between users go to higher accuracy, then A to Z.
    LEADERBOARD_SQL = """
        SELECT username, wpm, accuracy, user_id FROM (
            SELECT users.username, results.wpm, results.accuracy, results.user_id,
                   ROW_NUMBER() OVER (
                       PARTITION BY results.user_id
                       ORDER BY results.wpm DESC, results.accuracy DESC
                   ) AS place_for_user
            FROM results JOIN users ON users.user_id = results.user_id
            WHERE results.mode = 'test' AND results.date >= ?
        )
        WHERE place_for_user = 1
        ORDER BY wpm DESC, accuracy DESC, username COLLATE NOCASE
    """

    def leaderboard(self, since=None):
        """Every user who has done a test since `since` (a datetime), best first.

        Each row is {"rank", "user_id", "username", "wpm", "accuracy"}. No other
        details about a student are ever loaded, so none can be shown (privacy).
        """
        since_text = since.strftime(DATE_FORMAT) if since else ""
        with self.connect() as connection:
            rows = connection.execute(self.LEADERBOARD_SQL, (since_text,)).fetchall()
        return [{"rank": number, **dict(row)} for number, row in enumerate(rows, start=1)]

    def top_scores(self, limit=10, since=None):
        """The top `limit` rows of the leaderboard (H12)."""
        return self.leaderboard(since)[:limit]

    def get_rank(self, user_id, since=None):
        """The user's own leaderboard row, or None if they have no tests in that time (H13)."""
        for row in self.leaderboard(since):
            if row["user_id"] == user_id:
                return row
        return None


def make_user(row):
    """Turn a row from the users table into a User, or None if there is no row."""
    if row is None:
        return None
    return User(row["user_id"], row["username"], row["password_hash"], row["personal_best"],
                bool(row["sound_on"]), bool(row["slow_mode"]))


def week_ago():
    """The date and time exactly 7 days ago, for the "This week" leaderboard (H14)."""
    return datetime.now() - timedelta(days=7)
