"""User-facing settings, editable in settings.json without touching code -
see ui_config.py for internal constants that aren't meant to be tuned this
way (colors, pixel offsets, timings tied to how the rendering/animation code
actually works).

Loaded once, here, at import time. Any field missing from the file - or the
file itself missing or unparsable - falls back to the default below, so a
half-edited or deleted settings.json never crashes the game.
"""

import json
from pathlib import Path

_SETTINGS_PATH = Path(__file__).resolve().parent / "settings.json"

_DEFAULTS = {
    "skin": "pieces4",
    "sound_enabled": True,
    "white_name": "White",
    "black_name": "Black",
}


def _load() -> dict:
    try:
        data = json.loads(_SETTINGS_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    return {**_DEFAULTS, **data}


_settings = _load()

# Which sprite set to draw pieces with (ui/assets/<SKIN>/<CODE>/states/...).
SKIN = _settings["skin"]

SOUND_ENABLED = _settings["sound_enabled"]

WHITE_NAME = _settings["white_name"]
BLACK_NAME = _settings["black_name"]
