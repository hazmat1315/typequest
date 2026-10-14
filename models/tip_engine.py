"""Turns weak keys into personalised tips.  Owner: George (G5, G6, G7)."""

import json
from pathlib import Path

TIPS_FILE = Path(__file__).resolve().parent.parent / "data" / "tips.json"
GREAT_JOB = "great_job"


class TipEngine:
    """Looks up the tip for each weak key in tips.json."""

    def __init__(self, tips_file=TIPS_FILE):
        with open(tips_file, encoding="utf-8") as file:
            self.tips = json.load(file)

    def tips_for(self, weak_keys):
        """Make one tip per weak key, or a single "great job" tip if there are none (G6, G7).

        weak_keys is the list from KeyStats.weakest(), e.g. [("e", 25.0), ("r", 18.2)].
        Each tip is a dictionary the results page can show:
            {"key": "E", "percent": 25.0, "text": "Use your left middle finger ..."}
        The percentage keeps 1 decimal place so a key at 15.3% never shows as "15%",
        which would look like it should not count as weak.
        """
        if not weak_keys:
            return [{"key": None, "percent": None, "text": self.tips[GREAT_JOB]}]

        return [
            {
                "key": "Space" if key == "space" else key.upper(),
                "percent": round(rate, 1),
                "text": self.tips[key],
            }
            for key, rate in weak_keys
        ]
