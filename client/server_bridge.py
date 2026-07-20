"""Puts server/ on sys.path so its bare imports (`from model.board import Board`, etc.) resolve.

Import this before any other client/ module imports something from the server package
(model, engine, rules, realtime, input, chess_io, config).
"""

import sys
from pathlib import Path

_SERVER_DIR = Path(__file__).resolve().parent.parent / "server"

if str(_SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(_SERVER_DIR))
