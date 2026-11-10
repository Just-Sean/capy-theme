"""The image slots (logos, icon, sharing image, backgrounds), their limits and modes."""

import json
from pathlib import Path

MB = 1024 * 1024


_DATA = json.loads(Path(__file__).with_name("slots.json").read_text(encoding="utf-8"))

# From slots.json. slot: (label, max bytes, max width or height in pixels, help)
SLOTS = {
    slot: (s["label"], s["max_mb"] * MB, s["max_pixels"], s["help"])
    for slot, s in _DATA["slots"].items()
}


# Slots where SVG can't be used (a PNG, JPEG, WebP or GIF must be uploaded), and why.
NO_SVG = _DATA["no_svg"]


SLOT_CHOICES = [(slot, spec[0]) for slot, spec in SLOTS.items()]


MODES = [("light", "Light"), ("dark", "Dark")]
