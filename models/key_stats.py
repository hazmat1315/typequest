"""Per-key mistake tracking, weak keys and heatmap bands.  Owner: George (G1-G4, G8).

key_errors is the dictionary typing.js sends after each test. For every key the
student was supposed to press, it says how many times that key came up and how
many times they pressed something else instead:

    {"e": {"presses": 20, "errors": 5}, "space": {"presses": 31, "errors": 1}}
"""

import string

TRACKED_KEYS = tuple(string.ascii_lowercase) + ("space",)  # 26 letters and space
MIN_PRESSES = 10         # G3: keys pressed fewer times than this are ignored
WEAK_THRESHOLD = 15      # G4: a key is weak if its error rate is ABOVE this percentage
FINE_THRESHOLD = 5       # G8: a key is fine (green) if its error rate is BELOW this percentage


class KeyStats:
    """Running totals of presses and mistakes for each key, for one user."""

    def __init__(self, presses=None, errors=None):
        """Start from saved totals, or empty ones for a new user."""
        self.presses = presses or {}
        self.errors = errors or {}

    def update(self, key_errors):
        """Add one test's key counts onto the running totals (G1).

        Keys that are not a letter or space (numbers, punctuation) and impossible
        counts are skipped, so bad data can never be saved.
        """
        for key, counts in key_errors.items():
            if key not in TRACKED_KEYS or not isinstance(counts, dict):
                continue
            presses = counts.get("presses")
            errors = counts.get("errors")
            if not (isinstance(presses, int) and isinstance(errors, int)):
                continue
            if not 0 <= errors <= presses:
                continue
            self.presses[key] = self.presses.get(key, 0) + presses
            self.errors[key] = self.errors.get(key, 0) + errors

    def error_rate(self, key):
        """Error rate % = mistakes on that key / times it was pressed x 100 (G3).

        Returns None if the key has been pressed fewer than 10 times, because a
        couple of slips on a rare key (like Q) would not be a fair result.
        """
        presses = self.presses.get(key, 0)
        if presses < MIN_PRESSES:
            return None
        return self.errors.get(key, 0) * 100 / presses

    def band(self, key):
        """G8: the heatmap colour for a key, using the bands in Section 2.4.

        grey   = fewer than 10 presses (not enough data yet)
        green  = below 5%
        orange = 5% to 15%
        red    = above 15% (the same rule as a weak key in G4)
        """
        rate = self.error_rate(key)
        if rate is None:
            return "grey"
        if rate < FINE_THRESHOLD:
            return "green"
        if rate <= WEAK_THRESHOLD:
            return "orange"
        return "red"

    def weakest(self, n=3):
        """The n worst keys with an error rate above 15%, worst first (G4).

        Returns a list of (key, error_rate) pairs. If two keys have the same rate,
        the one with more mistakes comes first, then alphabetical order.
        """
        weak_keys = []
        for key in self.presses:
            rate = self.error_rate(key)
            if rate is not None and rate > WEAK_THRESHOLD:
                weak_keys.append((key, rate))
        weak_keys.sort(key=lambda pair: (-pair[1], -self.errors.get(pair[0], 0), pair[0]))
        return weak_keys[:n]

    # ---------- saving and loading (G2) ----------

    @classmethod
    def load(cls, database, user_id):
        """Read a user's running totals from the key_stats table."""
        with database.connect() as connection:
            rows = connection.execute(
                "SELECT key, presses, errors FROM key_stats WHERE user_id = ?", (user_id,)
            ).fetchall()
        presses = {row["key"]: row["presses"] for row in rows}
        errors = {row["key"]: row["errors"] for row in rows}
        return cls(presses, errors)

    def save(self, database, user_id):
        """Write the running totals back, adding a row for any key seen for the first time."""
        rows = [(user_id, key, self.presses[key], self.errors.get(key, 0)) for key in self.presses]
        with database.connect() as connection:
            connection.executemany(
                "INSERT INTO key_stats (user_id, key, presses, errors) VALUES (?, ?, ?, ?) "
                "ON CONFLICT (user_id, key) DO UPDATE "
                "SET presses = excluded.presses, errors = excluded.errors",
                rows,
            )
