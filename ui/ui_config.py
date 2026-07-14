"""UI-only constants.

Deliberately not named `config.py` — `server/config.py` is also importable as bare
`config` once server_bridge runs, and reusing the name would risk a confusing
shadow-import bug.
"""

from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent / "assets"

# Which sprite set to draw pieces with (ui/assets/<SKIN>/<CODE>/states/...).
SKIN = "pieces1"
