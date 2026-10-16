"""One finished typing test.  Owner: Lucas (L5, L7, L16, L19, L20).

The browser (typing.js) counts key presses while the student types, then sends
the totals to POST /result. The server rebuilds the test as a TypingSession and
works out the WPM and accuracy itself, so the saved numbers always use the
Section 2.4 formulas and cannot be faked by editing the page.

Since Iteration 3 students can fix mistakes with Backspace (L20), so there are two counts:
    correct    = correct key presses, for accuracy (a fixed mistake still counts against you)
    characters = letters that are right in the finished text, for WPM
"""

TEST_SECONDS = 60          # L4: every test is 60 seconds long
CHARACTERS_PER_WORD = 5    # the standard typing-test "word"
MAX_WPM = 250              # faster than any human record, so a higher result must be fake
MAX_KEYS_PER_SECOND = 20   # 240 WPM worth of key presses; nobody presses keys faster than this


class TypingSession:
    """The totals from one typing test."""

    def __init__(self, passage, correct, total, key_errors, seconds, characters=None):
        """Keep the totals sent by the browser."""
        self.passage = passage          # the Passage that was typed
        self.correct = correct          # correct key presses
        self.total = total              # all key presses
        self.key_errors = key_errors    # {"e": {"presses": 20, "errors": 5}, ...}
        self.seconds = seconds          # how long the test took
        # Correct letters in the finished text. Without Backspace (the game) this is the
        # same as the correct key presses.
        self.characters = correct if characters is None else characters

    def wpm(self):
        """WPM = (correct characters / 5) / minutes taken, to 1 decimal place."""
        if self.seconds <= 0:
            return 0.0
        minutes = self.seconds / 60
        return round(self.characters / CHARACTERS_PER_WORD / minutes, 1)

    def accuracy(self):
        """Accuracy % = correct key presses / total key presses x 100, to 1 decimal place."""
        if self.total == 0:
            return 0.0
        return round(self.correct / self.total * 100, 1)

    def to_result(self):
        """The values that get saved in the results table."""
        return {"wpm": self.wpm(), "accuracy": self.accuracy(), "level": self.passage.level}

    @classmethod
    def from_json(cls, data, passage, max_seconds=TEST_SECONDS):
        """Build a session from the JSON sent by typing.js, checking every value.

        Raises ValueError with a short reason if anything is missing or impossible,
        e.g. more correct letters than the passage has. Practice drills have no
        timer, so they pass a longer max_seconds.
        """
        try:
            correct = int(data["correct"])
            total = int(data["total"])
            characters = int(data["characters"])
            seconds = float(data["seconds"])
            key_errors = data["key_errors"]
        except (KeyError, TypeError, ValueError):
            raise ValueError("The result is missing some numbers.")

        if data.get("level") != passage.level:
            raise ValueError("The level does not match the passage.")
        if total == 0:
            raise ValueError("No keys were pressed.")
        # Every right letter in the text took a correct key press, and every correct key
        # press is a key press. With Backspace, total can be more than the passage length.
        if not 0 <= characters <= passage.length() or not characters <= correct <= total:
            raise ValueError("The key press counts are not possible.")
        # Allow a little extra time for the browser to send the result.
        if not 0 < seconds <= max_seconds + 1:
            raise ValueError("The test time is not possible.")
        if total > MAX_KEYS_PER_SECOND * max(seconds, 1):
            raise ValueError("That was too fast to be real typing.")
        if not isinstance(key_errors, dict):
            raise ValueError("key_errors must be a dictionary.")

        # L19: a test can never count more than its 60 seconds, even if the browser is late.
        session = cls(passage, correct, total, key_errors, min(seconds, max_seconds), characters)
        # Found in testing: a script typed a whole passage in a split second and
        # saved 16,720 WPM. No person can type that fast, so it is not saved.
        if session.wpm() > MAX_WPM:
            raise ValueError("That was too fast to be real typing.")
        return session
