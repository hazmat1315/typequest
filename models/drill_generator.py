"""Adaptive practice drills built from a student's weak keys.  Owner: George (G9-G11, G14).

Follows the adaptive drill generator flowchart in the Iteration 2 specification:
keep the words that contain weak keys, score each one, then pick the drill at
random from the highest-scoring words so no two drills are the same.
"""

import json
import random
from pathlib import Path

WORDS_FILE = Path(__file__).resolve().parent.parent / "data" / "words.json"
DRILL_WORDS = 20      # G10: words in one drill
TOP_WORDS = 40        # G11: the drill is picked at random from the 40 best-scoring words
MAX_REPEATS = 2       # G11: no word appears more than twice in one drill


class DrillGenerator:
    """Builds practice drills from the word bank in words.json."""

    def __init__(self, words_file=WORDS_FILE):
        with open(words_file, encoding="utf-8") as file:
            self.word_bank = json.load(file)

    @staticmethod
    def score_word(word, weak_keys):
        """G10: how many letters in the word are weak keys (repeats count).

        Example: weak keys E and R. "error" scores 4 (e, r, r, r), "tree" 3, "cat" 0.
        """
        weak_letters = {key.lower() for key in weak_keys}
        return sum(1 for letter in word.lower() if letter in weak_letters)

    def make_drill(self, weak_keys, n=DRILL_WORDS):
        """G10, G11, G14: a list of n words that practise the weak keys.

        weak_keys is a list of key names, e.g. ["e", "r", "o"]. Space is not a letter,
        so it is left out of the scoring (every drill practises space anyway).
        With no weak letters the drill is a random mix of words (G14).
        """
        weak_letters = [key for key in weak_keys if len(key) == 1]
        if not weak_letters:
            return random.sample(self.word_bank, n)

        # Keep words with weak keys (list comprehension), then sort best first.
        # Shuffling first means words with the same score come out in a random order.
        candidates = [word for word in self.word_bank if self.score_word(word, weak_letters) > 0]
        random.shuffle(candidates)
        candidates.sort(key=lambda word: self.score_word(word, weak_letters), reverse=True)
        top = candidates[:TOP_WORDS]

        drill = random.sample(top, min(n, len(top)))
        # A rare weak key (like Q) might have fewer than n words, so each word may be
        # used a second time, and any space left is filled with other words.
        if len(drill) < n:
            drill += random.sample(top, min(n - len(drill), len(top)))
        if len(drill) < n:
            others = [word for word in self.word_bank if word not in drill]
            drill += random.sample(others, n - len(drill))

        random.shuffle(drill)
        return drill
