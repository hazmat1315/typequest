"""Turns weak keys into personalised tips and heatmap colours.  Owner: George (G5-G8, G15, G17)."""

import json
import random
from datetime import date
from pathlib import Path

TIPS_FILE = Path(__file__).resolve().parent.parent / "data" / "tips.json"
GREAT_JOB = "great_job"
TIP_OF_THE_DAY = "tip_of_the_day"
HOME_ROW = "home_row"  # G17: the general tip used for a key that has no tips of its own

# G8: the letter rows of a QWERTY keyboard, top to bottom. Space gets its own row.
KEYBOARD_ROWS = ("qwertyuiop", "asdfghjkl", "zxcvbnm")


def key_label(key):
    """How a key name is shown to students: "e" -> "E", "space" -> "Space"."""
    return "Space" if key == "space" else key.upper()


class TipEngine:
    """Looks up tips for each weak key in tips.json and colours the heatmap."""

    def __init__(self, tips_file=TIPS_FILE):
        """Load every tip from tips.json."""
        with open(tips_file, encoding="utf-8") as file:
            # {"e": ["tip 1", "tip 2"], ..., "great_job": "...", "tip_of_the_day": [...]}
            self.tips = json.load(file)

    # ---------- tips (G6, G7, G15, G17) ----------

    def tips_for_key(self, key):
        """The list of tips for a key. G17: if tips.json has no tips for it (for example
        someone deleted Q by mistake), the general home row tip is used instead of crashing."""
        return self.tips.get(key) or [self.tips[HOME_ROW]]

    def next_tip(self, key, last_tip=None):
        """G15: a random tip for the key that is different from the last one the student saw.

        If the student has never had a tip for this key, the first tip counts as the
        last one, because that is the one the results page showed them.
        """
        key_tips = self.tips_for_key(key)
        last_tip = last_tip or key_tips[0]
        choices = [tip for tip in key_tips if tip != last_tip]
        return random.choice(choices or key_tips)

    def choose_tips(self, weak_keys, last_tips):
        """G15: pick the next tip for every weak key. Called once each time a test is saved.

        weak_keys is the list from KeyStats.weakest(); last_tips is {key: tip text}
        from load_last_tips(). Returns {key: new tip text}.
        """
        return {key: self.next_tip(key, last_tips.get(key)) for key, _ in weak_keys}

    def tips_for(self, weak_keys, chosen=None):
        """Make one tip per weak key, or a single "great job" tip if there are none (G6, G7).

        weak_keys is the list from KeyStats.weakest(), e.g. [("e", 25.0), ("r", 18.2)].
        chosen is {key: tip text} saved by choose_tips(), so refreshing the results page
        keeps showing the same tips. Each tip is a dictionary the results page can show:
            {"key": "E", "percent": 25.0, "text": "Use your left middle finger ..."}
        The percentage keeps 1 decimal place so a key at 15.3% never shows as "15%",
        which would look like it should not count as weak.
        """
        if not weak_keys:
            return [{"key": None, "percent": None, "text": self.tips[GREAT_JOB]}]

        chosen = chosen or {}
        tips = []
        for key, rate in weak_keys:
            text = chosen.get(key)
            key_tips = self.tips_for_key(key)
            if text not in key_tips:  # never chosen yet, or tips.json has changed
                text = key_tips[0]
            tips.append({"key": key_label(key), "percent": round(rate, 1), "text": text})
        return tips

    def tip_of_the_day(self, today=None):
        """The general tip for the home page. It changes every day (Mockup 2)."""
        today = today or date.today()
        general = self.tips[TIP_OF_THE_DAY]
        return general[today.toordinal() % len(general)]

    # ---------- heatmap (G8) ----------

    def heatmap_colours(self, stats):
        """G8: the keyboard for the results page heatmap, one list of keys per row.

        Each key is {"name": "e", "label": "E", "band": "red", "percent": 25.0,
        "presses": 20}. percent is None for grey keys (fewer than 10 presses).
        """
        rows = [list(row) for row in KEYBOARD_ROWS] + [["space"]]
        keyboard = []
        for row in rows:
            keys = []
            for key in row:
                rate = stats.error_rate(key)
                keys.append({
                    "name": key,
                    "label": key_label(key),
                    "band": stats.band(key),
                    "percent": None if rate is None else round(rate, 1),
                    "presses": stats.presses.get(key, 0),
                })
            keyboard.append(keys)
        return keyboard

    # ---------- the tip each student saw last (G15) ----------

    @staticmethod
    def load_last_tips(database, user_id):
        """{key: tip text} of the tip the user was last shown for each key."""
        with database.connect() as connection:
            rows = connection.execute(
                "SELECT key, tip FROM last_tips WHERE user_id = ?", (user_id,)
            ).fetchall()
        return {row["key"]: row["tip"] for row in rows}

    @staticmethod
    def save_last_tips(database, user_id, tips):
        """Remember the tips just chosen for the user, replacing older ones for those keys."""
        with database.connect() as connection:
            connection.executemany(
                "INSERT INTO last_tips (user_id, key, tip) VALUES (?, ?, ?) "
                "ON CONFLICT (user_id, key) DO UPDATE SET tip = excluded.tip",
                [(user_id, key, tip) for key, tip in tips.items()],
            )
