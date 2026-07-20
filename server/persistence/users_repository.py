"""SQLite-backed user accounts: username + ELO rating (no password - "just
for presentation" login, per the course spec)."""

import sqlite3
from dataclasses import dataclass

from config import DEFAULT_ELO


@dataclass
class User:
    id: int
    username: str
    elo: int


class UsersRepository:
    def __init__(self, connection: sqlite3.Connection):
        self._connection = connection

    def create_user(self, username: str) -> User:
        """Raises sqlite3.IntegrityError if username is already taken."""
        cursor = self._connection.execute(
            "INSERT INTO users (username, elo, created_at) VALUES (?, ?, datetime('now'))",
            (username, DEFAULT_ELO),
        )
        self._connection.commit()
        return User(id=cursor.lastrowid, username=username, elo=DEFAULT_ELO)

    def get_by_username(self, username: str) -> User | None:
        row = self._connection.execute(
            "SELECT id, username, elo FROM users WHERE username = ?", (username,)
        ).fetchone()
        return User(*row) if row is not None else None

    def update_elo(self, username: str, new_elo: int) -> None:
        self._connection.execute("UPDATE users SET elo = ? WHERE username = ?", (new_elo, username))
        self._connection.commit()
