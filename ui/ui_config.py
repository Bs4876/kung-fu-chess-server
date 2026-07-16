"""UI-only constants.

Deliberately not named `config.py` — `server/config.py` is also importable as bare
`config` once server_bridge runs, and reusing the name would risk a confusing
shadow-import bug.
"""

from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent / "assets"

# Which sprite set to draw pieces with (ui/assets/<SKIN>/<CODE>/states/...).
SKIN = "pieces4"

WINDOW_TITLE = "Kung Fu Chess"

PANEL_WIDTH = 220  # width of each side panel (left=White, right=Black)

# graphics/hud_renderer.py's sidebar layout.
HUD_PANEL_BG_COLOR    = (210, 220, 235, 255)  # BGRA creamy-white
HUD_TITLE_COLOR       = (30,  60,  90,  255)  # BGRA dark brown-blue  (name)
HUD_SCORE_COLOR       = (40,  80,  130, 255)  # BGRA medium brown-blue (score)
HUD_TEXT_COLOR        = (50,  70,  100, 255)  # BGRA dark brown        (moves)
HUD_DIVIDER_COLOR     = (160, 180, 200, 255)  # BGRA muted line
HUD_TITLE_FONT_SIZE   = 0.75
HUD_SCORE_FONT_SIZE   = 0.60
HUD_LINE_FONT_SIZE    = 0.48
HUD_LINE_HEIGHT_PX    = 24
HUD_LEFT_PADDING_PX   = 14
HUD_TOP_PADDING_PX    = 28
HUD_SCORE_TO_MOVES_GAP_PX = 36

# ui_components/halt_flash.py
HALT_FLASH_DURATION_MS = 600

# ui_components/moves_log_panel.py
MOVES_LOG_MAX_VISIBLE_LINES = 20

# graphics/window.py
WINDOW_ESC_KEY = 27
