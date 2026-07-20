from pathlib import Path

# --- Engine / real-time motion -------------------------------------------
CELL_SIZE = 100
PIECE_SPEED = 100  # pixels per second
MOVE_TRAVEL_TIME_PER_CELL = 1000  # ms per cell
JUMP_TRAVEL_TIME = 1000  # ms
MOVE_COOLDOWN_MS = 5000  # ms a piece must rest after a normal move before it can act again
JUMP_COOLDOWN_MS = 2000  # ms a piece must rest after a jump before it can act again

# --- Event bus / write-log -------------------------------------------------
GAME_LOG_DIR = Path(__file__).resolve().parent / "data" / "game_logs"  # durable per-game/system event log

# --- WebSocket transport -----------------------------------------------
SCHEMA_VERSION = 1  # bumped when a wire message's shape changes incompatibly
WS_HOST = "localhost"
WS_PORT = 8765
TICK_MS = 100  # how often each GameRoom advances its GameEngine's real-time clock

# --- Accounts / ELO ----------------------------------------------------
DB_PATH = Path(__file__).resolve().parent / "data" / "kungfuchess.db"
DEFAULT_ELO = 1200  # a commonly-recognized "average new player" anchor, not slide-mandated
ELO_K_FACTOR = 32  # standard default for lower-rated/provisional players, not slide-mandated

# --- Matchmaking / disconnect handling ----------------------------------
MATCH_ELO_RANGE = 100  # per the slide's "+-100"
MATCHMAKING_TICK_MS = 500  # how often the waiting queue is rescanned for pairs/timeouts
MATCHMAKING_WAIT_MS = 60_000  # how long to wait for a human match before giving up (spec: "e.g. one minute")
DISCONNECT_GRACE_MS = 20_000  # how long a disconnected player's seat is held before forfeit (spec: exactly 20s)
