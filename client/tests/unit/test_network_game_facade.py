"""Tests NetworkGameFacade against a fake transport (queued wire messages in,
sent messages out) rather than a real socket - the real end-to-end socket
path is covered once in client/tests/integration/test_ws_client_integration.py.
Board/motion/event behavior is exercised here the same way
client/tests/unit/test_game_facade.py exercises the real GameFacade, so the two
can be compared side by side.
"""

import pytest

from chess_io.board_parser import BoardParser
from engine.game_engine import Arrived, Captured, GameSnapshot, Halted, MoveResult, Promoted
from model.position import Position
from net import protocol
from network.network_game_facade import MatchmakingError, NetworkGameFacade, wait_for_game_start
from state.game_events import (
    GameOver, MoveAccepted, MoveRejected, OpponentDisconnected, OpponentReconnected, PieceArrived, PieceCaptured,
    PieceHalted, Promotion,
)


class FakeWsClient:
    """Stands in for WsClient: game_start is fixed at construction time (as
    the real one is, by the time NetworkGameFacade's constructor returns),
    further inbound messages are queued explicitly by each test, and every
    send() call is recorded for assertions."""

    def __init__(self, board_text: str, game_id: str = "1", color: str = "white"):
        board = BoardParser().parse(board_text)
        self._game_start = protocol.game_start(game_id, color, 0, GameSnapshot(board, game_over=False))
        self._queue: list = []
        self.sent: list = []

    def recv_one_blocking(self, timeout: float = 5.0) -> dict:
        return self._game_start

    def send(self, message: dict) -> None:
        self.sent.append(message)

    def queue(self, message: dict) -> None:
        self._queue.append(message)

    def recv_all(self) -> list:
        messages, self._queue = self._queue, []
        return messages


class FakeBlockingClient:
    """For testing wait_for_game_start in isolation: recv_one_blocking pops
    from a preset queue of messages, in arrival order, and records every
    timeout it was called with."""

    def __init__(self, messages: list):
        self._messages = list(messages)
        self.timeouts: list = []

    def recv_one_blocking(self, timeout: float = 5.0) -> dict:
        self.timeouts.append(timeout)
        return self._messages.pop(0)


def test_wait_for_game_start_skips_preamble_messages_before_game_start():
    board = BoardParser().parse("wQ . .\n. . .\n. . .")
    start = protocol.game_start("1", "white", 0, GameSnapshot(board, game_over=False))
    client = FakeBlockingClient([protocol.matchmaking_status("searching"), start])
    assert wait_for_game_start(client) == start


def test_wait_for_game_start_raises_matchmaking_error_on_an_error_message():
    client = FakeBlockingClient([
        protocol.matchmaking_status("searching"),
        protocol.error("no_opponent_found", "no opponent found within the time limit"),
    ])
    with pytest.raises(MatchmakingError) as exc_info:
        wait_for_game_start(client)
    assert exc_info.value.code == "no_opponent_found"
    assert exc_info.value.message == "no opponent found within the time limit"


def test_wait_for_game_start_defaults_to_a_timeout_comfortably_above_matchmaking_wait():
    board = BoardParser().parse("wQ . .\n. . .\n. . .")
    start = protocol.game_start("1", "white", 0, GameSnapshot(board, game_over=False))
    client = FakeBlockingClient([protocol.matchmaking_status("searching"), start])
    wait_for_game_start(client)
    assert client.timeouts == [65.0, 65.0]


def test_wait_for_game_start_forwards_an_explicit_timeout_to_every_call():
    board = BoardParser().parse("wQ . .\n. . .\n. . .")
    start = protocol.game_start("1", "white", 0, GameSnapshot(board, game_over=False))
    client = FakeBlockingClient([protocol.matchmaking_status("searching"), start])
    wait_for_game_start(client, timeout=None)
    assert client.timeouts == [None, None]


def facade_for(board_text: str, event_logger=None) -> tuple[NetworkGameFacade, FakeWsClient]:
    client = FakeWsClient(board_text)
    return NetworkGameFacade(client, client._game_start, event_logger=event_logger), client


def events_from(facade: NetworkGameFacade) -> list:
    received = []
    facade.subscribe_moves(received.append)
    facade.subscribe_outcomes(received.append)
    facade.subscribe_game_over(received.append)
    facade.subscribe_opponent_status(received.append)
    return received


def test_legal_destinations_splits_empty_from_capturable():
    facade, _client = facade_for("wQ . bP . . . . .\n" + ". . . . . . . .\n" * 7)
    empty_cells, capturable_cells = facade.legal_destinations(Position(0, 0))
    assert Position(0, 2) in capturable_cells
    assert Position(0, 2) not in empty_cells
    assert Position(0, 1) in empty_cells
    assert Position(0, 1) not in capturable_cells


def test_request_move_sends_a_request_move_wire_message_and_predicts_nothing_yet():
    facade, client = facade_for("wQ . . . . . . .\n" + ". . . . . . . .\n" * 7)
    facade.request_move(Position(0, 0), Position(0, 3))
    assert client.sent == [protocol.request_move("1", Position(0, 0), Position(0, 3))]
    assert facade.pending_motions() == {}  # only the server's broadcast starts prediction


def test_request_jump_sends_a_request_jump_wire_message():
    facade, client = facade_for("wQ . . . . . . .\n" + ". . . . . . . .\n" * 7)
    facade.request_jump(Position(0, 0), Position(2, 2))
    assert client.sent == [protocol.request_jump("1", Position(0, 0), Position(2, 2))]


def test_move_accepted_broadcast_predicts_duration_from_server_config_not_a_guess():
    facade, client = facade_for("wQ . . . . . . .\n" + ". . . . . . . .\n" * 7)
    client.queue(protocol.move_result("1", Position(0, 0), Position(0, 3), MoveResult(True, "ok")))
    facade.tick(0)
    motion = facade.pending_motions()[Position(0, 0)]
    assert motion.duration_ms == 3000  # 3 cells * MOVE_TRAVEL_TIME_PER_CELL(1000)


def test_move_accepted_broadcast_publishes_move_accepted():
    facade, client = facade_for("wQ . . . . . . .\n" + ". . . . . . . .\n" * 7)
    events = events_from(facade)
    client.queue(protocol.move_result("1", Position(0, 0), Position(0, 2), MoveResult(True, "ok")))
    facade.tick(0)
    assert len(events) == 1
    assert events[0] == MoveAccepted(Position(0, 0), Position(0, 2), "wQ", 0, 2000)


def test_move_rejected_broadcast_publishes_move_rejected_and_starts_no_motion():
    facade, client = facade_for("wQ . . . . . . .\n" + ". . . . . . . .\n" * 7)
    events = events_from(facade)
    client.queue(protocol.move_result("1", Position(0, 0), Position(5, 3), MoveResult(False, "illegal_piece_move")))
    facade.tick(0)
    assert events == [MoveRejected(Position(0, 0), Position(5, 3), "illegal_piece_move")]
    assert facade.pending_motions() == {}


def test_jump_started_broadcast_predicts_motion():
    facade, client = facade_for("wQ . . . . . . .\n" + ". . . . . . . .\n" * 7)
    client.queue(protocol.jump_started("1", Position(0, 0), Position(2, 2)))
    facade.tick(0)
    assert Position(0, 0) in facade.pending_motions()


def test_plain_arrival_moves_the_piece_on_the_local_board_and_publishes_piece_arrived():
    facade, client = facade_for("wQ . . . . . . .\n" + ". . . . . . . .\n" * 7)
    events = events_from(facade)
    client.queue(protocol.move_result("1", Position(0, 0), Position(0, 3), MoveResult(True, "ok")))
    facade.tick(0)

    arrived = Arrived(source=Position(0, 0), destination=Position(0, 3), token="wQ", is_jump=False)
    client.queue(protocol.outcome(protocol.ARRIVED, "1", 1, arrived))
    snapshot = facade.tick(0)

    assert snapshot.get_piece(Position(0, 0)) == "."
    assert snapshot.get_piece(Position(0, 3)) == "wQ"
    assert Position(0, 0) not in facade.pending_motions()
    assert [e for e in events if isinstance(e, PieceArrived)] == [
        PieceArrived(Position(0, 0), Position(0, 3), "wQ")
    ]


def test_arrival_capture_moves_the_capturing_piece_onto_the_captured_cell():
    facade, client = facade_for("wQ . . . . . . .\n" + ". . . . . . . .\n" * 7)
    captured = Captured(source=Position(0, 0), position=Position(0, 3), captured_token="bP", by_token="wQ")
    client.queue(protocol.outcome(protocol.CAPTURED, "1", 1, captured))
    snapshot = facade.tick(0)

    assert snapshot.get_piece(Position(0, 0)) == "."
    assert snapshot.get_piece(Position(0, 3)) == "wQ"


def test_mid_flight_capture_only_clears_the_source_cell():
    facade, client = facade_for("wQ . . . . . . .\n" + ". . . . . . . .\n" * 7)
    captured = Captured(source=Position(0, 0), position=Position(0, 0), captured_token="wQ", by_token=None)
    events = events_from(facade)
    client.queue(protocol.outcome(protocol.CAPTURED, "1", 1, captured))
    snapshot = facade.tick(0)

    assert snapshot.get_piece(Position(0, 0)) == "."
    assert [e for e in events if isinstance(e, PieceCaptured)] == [
        PieceCaptured(Position(0, 0), "wQ", None)
    ]


def test_halted_outcome_moves_the_piece_to_resting_at_not_its_intended_destination():
    facade, client = facade_for("wQ . . . . . . .\n" + ". . . . . . . .\n" * 7)
    halted = Halted(source=Position(0, 0), resting_at=Position(0, 1), token="wQ")
    events = events_from(facade)
    client.queue(protocol.outcome(protocol.HALTED, "1", 1, halted))
    snapshot = facade.tick(0)

    assert snapshot.get_piece(Position(0, 1)) == "wQ"
    assert [e for e in events if isinstance(e, PieceHalted)] == [
        PieceHalted(Position(0, 0), Position(0, 1), "wQ")
    ]


def test_promoted_outcome_upgrades_the_token_at_destination():
    facade, client = facade_for("wP . . . . . . .\n" + ". . . . . . . .\n" * 7)
    promoted = Promoted(source=Position(0, 0), position=Position(0, 0), from_token="wP", to_token="wQ")
    events = events_from(facade)
    client.queue(protocol.outcome(protocol.PROMOTED, "1", 1, promoted))
    snapshot = facade.tick(0)

    assert snapshot.get_piece(Position(0, 0)) == "wQ"
    assert [e for e in events if isinstance(e, Promotion)] == [
        Promotion(Position(0, 0), "wP", "wQ")
    ]


def test_game_over_message_sets_game_over_and_publishes_exactly_once():
    facade, client = facade_for("wQ . . . . . . .\n" + ". . . . . . . .\n" * 7)
    events = events_from(facade)
    client.queue(protocol.game_over("1", 1, "king_capture", "white"))
    facade.tick(0)
    facade.tick(0)  # a later tick with nothing new queued must not re-publish

    assert facade.game_over
    assert [e for e in events if isinstance(e, GameOver)] == [GameOver()]


def test_error_message_does_not_raise_and_publishes_no_event():
    facade, client = facade_for("wQ . . . . . . .\n" + ". . . . . . . .\n" * 7)
    events = events_from(facade)
    client.queue(protocol.error("bad_message", "oops"))
    facade.tick(0)
    assert events == []


def test_opponent_disconnected_message_publishes_opponent_disconnected_with_forfeit_time():
    facade, client = facade_for("wQ . . . . . . .\n" + ". . . . . . . .\n" * 7)
    events = events_from(facade)
    client.queue(protocol.opponent_disconnected("1", 20_000))
    facade.tick(0)
    assert events == [OpponentDisconnected(20_000)]


def test_opponent_reconnected_message_publishes_opponent_reconnected():
    facade, client = facade_for("wQ . . . . . . .\n" + ". . . . . . . .\n" * 7)
    events = events_from(facade)
    client.queue(protocol.opponent_reconnected("1"))
    facade.tick(0)
    assert events == [OpponentReconnected()]


def test_event_logger_receives_moves_outcomes_and_game_over_under_the_game_topic():
    logged = []
    facade, client = facade_for("wQ . . . . . . .\n" + ". . . . . . . .\n" * 7, event_logger=logged.append)

    client.queue(protocol.move_result("1", Position(0, 0), Position(0, 2), MoveResult(True, "ok")))
    arrived = Arrived(source=Position(0, 0), destination=Position(0, 2), token="wQ", is_jump=False)
    client.queue(protocol.outcome(protocol.ARRIVED, "1", 1, arrived))
    client.queue(protocol.game_over("1", 1, "king_capture", "white"))
    facade.tick(0)

    assert [topic for topic, _event in logged] == ["game.1", "game.1", "game.1"]
    assert isinstance(logged[0][1], MoveAccepted)
    assert isinstance(logged[1][1], PieceArrived)
    assert isinstance(logged[2][1], GameOver)
