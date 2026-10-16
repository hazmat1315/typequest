"""Which finger presses each key.  Owner: George (F7).

Client feedback: students said they wanted the app to show "which finger to use for each
key" and an "on-screen keyboard showing where fingers go". The finger guide shows a
keyboard coloured by finger and a picture of two hands, with the fingers for the
student's weak keys highlighted.

This uses the standard touch typing layout, the same one the tips in tips.json describe.
"""

from models.tip_engine import KEYBOARD_ROWS, key_label

# The 10 fingers, left to right as they sit on the keyboard, with the home key each
# one rests on.
FINGERS = (
    ("left_pinky", "left pinky", "A"),
    ("left_ring", "left ring finger", "S"),
    ("left_middle", "left middle finger", "D"),
    ("left_pointer", "left pointer finger", "F"),
    ("left_thumb", "left thumb", "Space"),
    ("right_thumb", "right thumb", "Space"),
    ("right_pointer", "right pointer finger", "J"),
    ("right_middle", "right middle finger", "K"),
    ("right_ring", "right ring finger", "L"),
    ("right_pinky", "right pinky", ";"),
)
FINGER_NAMES = {finger: name for finger, name, _ in FINGERS}
HOME_KEYS = {finger: home for finger, _, home in FINGERS}

# The keys each finger presses. Space is shown on both thumbs, because either is fine.
KEYS_FOR_FINGER = {
    "left_pinky": "qaz",
    "left_ring": "wsx",
    "left_middle": "edc",
    "left_pointer": "rfvtgb",
    "right_pointer": "yhnujm",
    "right_middle": "ik",
    "right_ring": "ol",
    "right_pinky": "p",
}


class FingerGuide:
    """Works out the finger for each key and builds the finger guide for a page."""

    @staticmethod
    def finger_for(key):
        """The finger that presses a key, e.g. "e" -> "left_middle", "space" -> "right_thumb".

        Returns None for a key the guide doesn't cover.
        """
        if key == "space":
            return "right_thumb"
        for finger, keys in KEYS_FOR_FINGER.items():
            if key in keys:
                return finger
        return None

    @classmethod
    def describe(cls, key):
        """One sentence a student can follow, e.g. "E: use your left middle finger. It
        starts on D." Returns None for a key the guide doesn't cover."""
        finger = cls.finger_for(key)
        if finger is None:
            return None
        if key == "space":
            return "Space: use one thumb, the same one every time. Keep your fingers on the home row."
        home = HOME_KEYS[finger]
        if key_label(key) == home:
            return f"{key_label(key)}: use your {FINGER_NAMES[finger]}. This is its home key."
        return f"{key_label(key)}: use your {FINGER_NAMES[finger]}. It starts on {home}."

    @classmethod
    def guide(cls, weak_keys):
        """F7: everything the finger guide on a page needs.

        weak_keys is a list of key names, e.g. ["e", "space"]. Returns
            {"keyboard": rows of {"name", "label", "finger", "weak"},
             "hands": the 10 fingers as {"id", "name", "home", "weak"},
             "steps": one describe() sentence per weak key}
        """
        weak = [key for key in weak_keys if cls.finger_for(key) is not None]
        weak_fingers = {cls.finger_for(key) for key in weak}
        if "space" in weak:
            weak_fingers.add("left_thumb")  # either thumb can press Space

        keyboard = []
        for row in [list(row) for row in KEYBOARD_ROWS] + [["space"]]:
            keyboard.append([
                {"name": key, "label": key_label(key), "finger": cls.finger_for(key), "weak": key in weak}
                for key in row
            ])
        hands = [
            {"id": finger, "name": name, "home": home, "weak": finger in weak_fingers}
            for finger, name, home in FINGERS
        ]
        return {"keyboard": keyboard, "hands": hands, "steps": [cls.describe(key) for key in weak]}
