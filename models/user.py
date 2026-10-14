"""User accounts.  Owner: Henry (H1, H3, H4, H15, H16).

Only a username is stored for each student (no real names, emails or photos)
because our users are under 18.
"""

import re
from datetime import date, timedelta

from werkzeug.security import check_password_hash

# H1: a username is 3 to 20 letters or numbers, a password is at least 6 characters.
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9]{3,20}$")
MIN_PASSWORD_LENGTH = 6


class User:
    """One student account, as loaded from the users table."""

    def __init__(self, user_id, username, password_hash, personal_best=0.0):
        self.user_id = user_id
        self.username = username
        self.password_hash = password_hash
        self.personal_best = personal_best

    def check_password(self, password):
        """Return True if the typed password matches the saved hash (H4)."""
        return check_password_hash(self.password_hash, password)

    def update_best(self, wpm):
        """H15: if wpm beats the personal best, make it the new best and return True."""
        if wpm > self.personal_best:
            self.personal_best = wpm
            return True
        return False

    @staticmethod
    def streak(dates, today=None):
        """H16: how many days in a row (ending today or yesterday) had any activity.

        `dates` is the set of days from Database.activity_dates(). This is the
        algorithm from Section 2.4 of the Iteration 2 specification.
        """
        today = today or date.today()
        day = today
        if today not in dates:
            day = today - timedelta(days=1)  # the streak still counts until the end of today
        streak = 0
        while day in dates:
            streak = streak + 1
            day = day - timedelta(days=1)
        return streak


def registration_error(username, password):
    """Check a new username and password against H1.

    Returns an error message written for a 12 year old, or None if both are fine.
    """
    if not USERNAME_PATTERN.match(username):
        return "Your username must be 3 to 20 letters or numbers, with no spaces."
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Your password must be {MIN_PASSWORD_LENGTH} or more characters long."
    return None


def improvement(wpms):
    """H11: how much faster the user has got, using the formula in Section 2.4.

    With 6 or more results: (average of last 3) - (average of first 3).
    With 2 to 5 results: latest - first. With fewer than 2, None (not enough to tell).
    Rounded to 1 decimal place.
    """
    if len(wpms) < 2:
        return None
    if len(wpms) >= 6:
        change = sum(wpms[-3:]) / 3 - sum(wpms[:3]) / 3
    else:
        change = wpms[-1] - wpms[0]
    return round(change, 1)
