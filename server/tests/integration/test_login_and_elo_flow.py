"""Scripted end-to-end test of login -> play -> ELO update, wiring the real
SQLite-backed UsersRepository, EventBus, EloUpdater, and GameRoom together
in-process (no socket - net/ws_server.py doesn't gate room entry on login
yet, that lands once real matchmaking replaces the anonymous lobby, so
there's no live connection flow to script this through yet). Matches this
repo's existing "integration test" style (server/tests/integration/test_integration.py):
several real modules wired together, nothing mocked.
"""

from bus.event_bus import EventBus
from model.board import Board
from model.position import Position
from net.auth import handle_login
from net.game_room import GameRoom
from net.session import Session
from persistence.db import connect
from persistence.elo import update_ratings
from persistence.elo_updater import EloUpdater
from persistence.users_repository import UsersRepository


def board_with_a_king_capture_one_move_away():
    return Board([row.split() for row in ["wR . bK", ". . .", ". . ."]])


class FakeSocket:
    """GameRoom broadcasts to every seated socket on every outcome - this
    test doesn't care what gets sent, just that join()/broadcast() don't
    need a real connection to run the game to completion."""

    async def send(self, text: str) -> None:
        pass


async def test_two_logged_in_users_play_to_king_capture_and_both_elo_ratings_update(tmp_path):
    users = UsersRepository(connect(tmp_path / "test.db"))
    bus = EventBus()
    bus.subscribe_all(EloUpdater(users))

    alice_session, bob_session = Session(), Session()
    assert handle_login({"username": "alice"}, alice_session, users)["success"]  # creates the account
    assert handle_login({"username": "bob"}, bob_session, users)["success"]

    room = GameRoom("1", board_with_a_king_capture_one_move_away(), bus)
    room.join(FakeSocket(), player=alice_session.user)  # white
    room.join(FakeSocket(), player=bob_session.user)  # black

    room.handle_request_move({"source": {"row": 0, "col": 0}, "destination": {"row": 0, "col": 2}})
    room._engine.wait(2000)  # 2 cells * MOVE_TRAVEL_TIME_PER_CELL(1000) -> king capture

    expected_alice, expected_bob = update_ratings(alice_session.user.elo, bob_session.user.elo, score_a=1.0)
    assert users.get_by_username("alice").elo == expected_alice
    assert users.get_by_username("bob").elo == expected_bob
