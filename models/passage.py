"""Typing passages.  Owner: Lucas (L1, L2)."""

import json
import random
from pathlib import Path

PASSAGES_FILE = Path(__file__).resolve().parent.parent / "data" / "passages.json"
LEVELS = ("easy", "medium", "hard")


class Passage:
    """One piece of text for a student to type, at a difficulty level."""

    _bank = None  # every passage from passages.json, loaded the first time it is needed

    def __init__(self, text, level):
        """Make a passage from its text and level."""
        self.text = text
        self.level = level

    def length(self):
        """Number of characters in the passage."""
        return len(self.text)

    @classmethod
    def all(cls):
        """Every passage in the bank, loaded from passages.json once and then reused."""
        if cls._bank is None:
            with open(PASSAGES_FILE, encoding="utf-8") as file:
                cls._bank = [cls(item["text"], item["level"]) for item in json.load(file)]
        return cls._bank

    @classmethod
    def random(cls, level, exclude=None):
        """Pick a random passage of the given level (L2).

        `exclude` is the text of the passage the student just typed, so pressing
        Restart or Try again always shows a different passage.
        """
        if level not in LEVELS:
            raise ValueError(f"Unknown level: {level}")
        choices = [p for p in cls.all() if p.level == level and p.text != exclude]
        return random.choice(choices)
