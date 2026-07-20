"""Puts server/ on sys.path before collecting any test that imports a client/
module reaching into the server package (config, model, engine, ...) -
the same thing client/server_bridge.py does for the real app, but for pytest.
"""

import sys
from pathlib import Path

_SERVER_DIR = Path(__file__).resolve().parent.parent.parent / "server"

if str(_SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(_SERVER_DIR))
