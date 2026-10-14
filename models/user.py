"""User accounts.  Owner: Henry (H1, H3, H4).

Only a username is stored for each student (no real names, emails or photos)
because our users are under 18.
"""

import re

from werkzeug.security import check_password_hash

# H1: a username is 3 to 20 letters or numbers, a password is at least 6 characters.
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9]{3,20}$")
MIN_PASSWORD_LENGTH = 6


class User:
    """One student account, as loaded from the users table."""

    def __init__(self, user_id, username, password_hash):
        self.user_id = user_id
        self.username = username
        self.password_hash = password_hash

    def check_password(self, password):
        """Return True if the typed password matches the saved hash (H4)."""
        return check_password_hash(self.password_hash, password)


def registration_error(username, password):
    """Check a new username and password against H1.

    Returns an error message written for a 12 year old, or None if both are fine.
    """
    if not USERNAME_PATTERN.match(username):
        return "Your username must be 3 to 20 letters or numbers, with no spaces."
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Your password must be {MIN_PASSWORD_LENGTH} or more characters long."
    return None
