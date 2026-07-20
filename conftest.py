"""Running `pytest` from the repo root needs both server/ and client/ on sys.path -
each suite's bare imports (server's `from model.board import Board`, client's
`import ui_config`) only resolve today because each is normally run with its
own directory as cwd (`cd server && pytest`, client/tests/conftest.py for the
other direction). This does the same thing for a root-level collection run.
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent


def _promote(path: str) -> None:
    """Force path to sys.path[0], regardless of whether it's already present
    somewhere else - pytest's own rootdir/conftest-loading machinery can
    already have put server/ (or client/) on sys.path at some other position
    before this module's top-level code even runs, which would silently
    defeat a naive "insert(0, path) only if not already present"."""
    while path in sys.path:
        sys.path.remove(path)
    sys.path.insert(0, path)


# client/ is promoted first so server/ ends up ahead of it - server must win
# any bare module name both sides happen to share (e.g. both have their own
# main.py: server/tests/unit/test_main.py does `import main` expecting
# server/main.py). Nothing on the client/ side relies on the reverse.
_promote(str(_ROOT / "client"))
_promote(str(_ROOT / "server"))
