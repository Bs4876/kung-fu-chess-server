"""UI-only constants - internal ones not meant to be user-tuned. See
user_settings.py (backed by settings.json) for the ones that are.

Deliberately not named `config.py` — `server/config.py` is also importable as bare
`config` once server_bridge runs, and reusing the name would risk a confusing
shadow-import bug.
"""

from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent / "assets"

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
HUD_TITLE_THICKNESS   = 2
HUD_LINE_HEIGHT_PX    = 24
HUD_LEFT_PADDING_PX   = 14
HUD_TOP_PADDING_PX    = 28
HUD_TITLE_TO_SCORE_GAP_PX = 4   # extra gap under the name, on top of one line height
HUD_SCORE_TO_DIVIDER_GAP_PX = 10
HUD_SCORE_TO_MOVES_GAP_PX = 36

# graphics/overlay_renderer.py's game-over banner.
GAME_OVER_BANNER_FONT_SIZE = 1.6
GAME_OVER_BANNER_COLOR     = (0, 0, 255, 255)  # BGRA red
GAME_OVER_BANNER_THICKNESS = 3

# graphics/sprite_loader.py's cooldown-fade overlay.
COOLDOWN_FADE_COLOR = (150, 255, 255)  # BGR pale yellow
COOLDOWN_FADE_ALPHA = 160

# graphics/sprite_loader.py's legal-destination move-hint overlays.
LEGAL_MOVE_COLOR = (90, 200, 90)     # BGR green - an empty square the selected piece could move to
LEGAL_CAPTURE_COLOR = (70, 70, 220)  # BGR red - an enemy square the selected piece could capture
LEGAL_DESTINATION_ALPHA = 110

# ui_components/halt_flash.py
HALT_FLASH_DURATION_MS = 600

# ui_components/moves_log_panel.py
MOVES_LOG_MAX_VISIBLE_LINES = 20
BOARD_ROWS = 8  # for converting a row index to algebraic rank notation (row 7 = rank 1)

# graphics/window.py
WINDOW_ESC_KEY = 27

# ui_components/sound_player.py
SOUNDS_DIR = ASSETS_DIR / "sounds"
SOUND_MOVE = SOUNDS_DIR / "move.wav"
SOUND_CAPTURE = SOUNDS_DIR / "capture.wav"
SOUND_PROMOTION = SOUNDS_DIR / "promotion.wav"
SOUND_GAME_OVER = SOUNDS_DIR / "game_over.wav"
SOUND_ILLEGAL_MOVE = SOUNDS_DIR / "illegal_move.wav"
