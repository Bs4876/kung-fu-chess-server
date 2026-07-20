import sqlite3

import pytest

from config import DEFAULT_ELO
from persistence.db import connect
from persistence.users_repository import UsersRepository


def repo_for(tmp_path) -> UsersRepository:
    return UsersRepository(connect(tmp_path / "test.db"))


def test_create_user_defaults_to_the_configured_starting_elo(tmp_path):
    repo = repo_for(tmp_path)
    user = repo.create_user("alice")
    assert user.username == "alice"
    assert user.elo == DEFAULT_ELO


def test_create_user_with_a_taken_username_raises(tmp_path):
    repo = repo_for(tmp_path)
    repo.create_user("alice")
    with pytest.raises(sqlite3.IntegrityError):
        repo.create_user("alice")


def test_get_by_username_returns_none_for_an_unknown_user(tmp_path):
    repo = repo_for(tmp_path)
    assert repo.get_by_username("nobody") is None


def test_get_by_username_finds_a_created_user(tmp_path):
    repo = repo_for(tmp_path)
    repo.create_user("alice")
    found = repo.get_by_username("alice")
    assert found is not None
    assert found.username == "alice"


def test_update_elo_persists_the_new_rating(tmp_path):
    repo = repo_for(tmp_path)
    repo.create_user("alice")
    repo.update_elo("alice", 1350)
    assert repo.get_by_username("alice").elo == 1350


def test_data_survives_a_fresh_connection_to_the_same_file(tmp_path):
    db_path = tmp_path / "test.db"
    UsersRepository(connect(db_path)).create_user("alice")
    reopened = UsersRepository(connect(db_path))
    assert reopened.get_by_username("alice").elo == DEFAULT_ELO
