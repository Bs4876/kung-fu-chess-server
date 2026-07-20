"""SQLite bootstrap: one connection factory that also creates the schema if
it doesn't exist yet, so callers never have to run migrations by hand for
this single-table course-project scope.
"""

import sqlite3
from pathlib import Path

from config import DB_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    elo INTEGER NOT NULL,
    created_at TEXT NOT NULL
)
"""


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Open (creating if needed) a SQLite database at db_path with the
    users table already in place."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.execute(_SCHEMA)
    connection.commit()
    return connection
