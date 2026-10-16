"""Falling words game.  Owner: Lucas (L10-L17, L21, F5, F6).

The game itself runs in the browser (static/js/game.js). This class holds the same
rules on the server, so the server can check a game result is possible before it is
saved (L16), and so the rules can be tested with pytest.

Game inherits from TypingSession: a game is a typing session with a score, a level
and lives added. wpm(), accuracy() and the key_errors handling are reused as they are.
"""

import json
from pathlib import Path

from models.typing_session import MAX_WPM, TypingSession

GAME_WORDS_FILE = Path(__file__).resolve().parent.parent / "data" / "game_words.json"

START_LIVES = 3
POINTS_PER_WORD = 10      # L11
FIRST_LEVEL_WORDS = 3     # F5: 3 words to get from level 1 to level 2 ...
EXTRA_WORDS_PER_LEVEL = 2  # ... then each level needs 2 more words than the last (3, 5, 7, 9 ...)
BASE_SPEED = 0.12         # L13: share of the play area a word falls each second at level 1 (about 8 s)
SPEED_GROWTH = 1.15       # fall speed = base speed x 1.15^(level - 1)
SLOW_MODE_SPEED = 0.6     # F6: slow mode makes words fall at 60% of the normal speed
BASE_SPAWN_SECONDS = 2.5  # time between new words = 2.5 / (1 + 0.1 x (level - 1))
MIN_WORD_LETTERS = 3      # the shortest word in game_words.json
MAX_GAME_SECONDS = 60 * 60

# L14: game_words.json has one list of words per band. Levels 1-2 use short words,
# 3-4 medium words and 5 or more long words.
BANDS = ("short", "medium", "long")


def band_for_level(level):
    """The word band used at a level: short (3-4 letters), medium (5-6) or long (7+)."""
    return BANDS[min((level - 1) // 2, len(BANDS) - 1)]


def words_to_next_level(level):
    """F5: how many words take you from this level to the next: 3, then 5, then 7 ..."""
    return FIRST_LEVEL_WORDS + EXTRA_WORDS_PER_LEVEL * (level - 1)


def level_for_score(score):
    """F5: the level for a score. Level 2 after 3 words, level 3 after 5 more (8 in total),
    level 4 after 7 more (15 in total), and so on.

    Client feedback in Iteration 2 was that the game should start really easy, so the
    first level up comes quickly and later ones take longer, instead of every 10 words.
    """
    words = score // POINTS_PER_WORD
    level = 1
    # Spend the words one level at a time until there aren't enough for the next level.
    while words >= words_to_next_level(level):
        words -= words_to_next_level(level)
        level += 1
    return level


def spawn_seconds(level):
    """L13: seconds between new words = 2.5 / (1 + 0.1 x (level - 1))."""
    return BASE_SPAWN_SECONDS / (1 + 0.1 * (level - 1))


def fall_speed(level):
    """L13: fall speed = base speed x 1.15^(level - 1)."""
    return BASE_SPEED * SPEED_GROWTH ** (level - 1)


def load_game_words(path=GAME_WORDS_FILE):
    """The word lists from game_words.json, e.g. {"short": ["cat", ...], ...}."""
    with open(path, encoding="utf-8") as file:
        return json.load(file)


class Game(TypingSession):
    """One game of falling words: score, level and lives on top of a typing session."""

    def __init__(self, score=0, level=1, lives=START_LIVES, correct=0, total=0,
                 key_errors=None, seconds=0.0):
        """Start a game, or rebuild a finished one sent by game.js."""
        super().__init__(None, correct, total, key_errors or {}, seconds)
        self.score = score
        self.level = level
        self.lives = lives
        self.falling = []  # the words on screen right now

    def check_word(self, word):
        """L11: if the typed word matches a falling word, remove it and add 10 points.

        Returns True if it matched. The level is checked straight after scoring.
        """
        if word not in self.falling:
            return False
        self.falling.remove(word)
        self.score += POINTS_PER_WORD
        self.level_up()
        return True

    def word_landed(self, word):
        """L12: a word reached the ground, so it is removed and a life is lost."""
        if word in self.falling:
            self.falling.remove(word)
            self.lives -= 1

    def level_up(self):
        """F5: move up a level when the score is high enough. Returns True if it went up."""
        new_level = level_for_score(self.score)
        if new_level > self.level:
            self.level = new_level
            return True
        return False

    def is_over(self):
        """L12: the game is over when there are no lives left."""
        return self.lives <= 0

    def fall_speed(self):
        """How fast words fall at the current level."""
        return fall_speed(self.level)

    def to_result(self):
        """The values that get saved in the results table (H18)."""
        return {
            "wpm": self.wpm(),
            "accuracy": self.accuracy(),
            "level": None,
            "mode": "game",
            "score": self.score,
            "level_reached": self.level,
        }

    # ---------- checking a result sent by game.js (L15, L16, fairness) ----------

    @staticmethod
    def max_score(seconds):
        """The highest score anyone could get in this many seconds of play.

        Words only appear one at a time (every spawn_seconds), so even a perfect
        player cannot type more words than have appeared. This works out how many
        could have appeared if every word was typed the moment it showed up, which
        makes the level (and the spawn rate) go up as fast as possible.
        """
        words = 0
        clock = 0.0
        while clock <= seconds:
            words += 1
            clock += spawn_seconds(level_for_score(words * POINTS_PER_WORD))
        return words * POINTS_PER_WORD

    @classmethod
    def from_json(cls, data, max_seconds=MAX_GAME_SECONDS):
        """Build a finished game from the JSON sent by game.js, checking every value.

        max_seconds is how long ago the server handed out the game page, so the
        browser cannot claim to have played for longer than it did. Raises
        ValueError with a short reason if anything is missing or impossible.
        """
        try:
            score = int(data["score"])
            level_reached = int(data["level_reached"])
            correct = int(data["correct"])
            total = int(data["total"])
            seconds = float(data["seconds"])
            key_errors = data["key_errors"]
        except (KeyError, TypeError, ValueError):
            raise ValueError("The result is missing some numbers.")

        if score < 0 or score % POINTS_PER_WORD != 0:
            raise ValueError("That score is not possible.")
        if level_reached != level_for_score(score):
            raise ValueError("The level does not match the score.")
        if not 0 <= correct <= total:
            raise ValueError("The key press counts are not possible.")
        # Every word scored needs at least 3 correct letters typed.
        if correct < score // POINTS_PER_WORD * MIN_WORD_LETTERS:
            raise ValueError("That score needs more correct letters than were typed.")
        if not 0 < seconds <= min(max_seconds, MAX_GAME_SECONDS) + 1:
            raise ValueError("The game time is not possible.")
        if score > cls.max_score(seconds):
            raise ValueError("That score is too high for the time played.")
        if not isinstance(key_errors, dict):
            raise ValueError("key_errors must be a dictionary.")

        game = cls(score, level_reached, 0, correct, total, key_errors, seconds)
        if game.wpm() > MAX_WPM:
            raise ValueError("That was too fast to be real typing.")
        return game
