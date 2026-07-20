"""Tests GameFacade against a real GameEngine/Board rather than a hand-mocked
engine: the whole point of GameFacade is reconciling its own prediction against
the engine's actual real-time timing, so a mock would risk hiding exactly the
kind of integration bug a fake can't reproduce (e.g. the live-vs-frozen
snapshot bug this module's FrozenSnapshot exists to fix).
"""

from chess_io.board_parser import BoardParser
from engine.game_engine import GameEngine
from model.board import Board
from model.position import Position
from state.game_events import GameOver, PieceArrived, PieceCaptured, PieceHalted, Promotion
from state.game_facade import GameFacade


def facade_for(board_text: str) -> GameFacade:
    return GameFacade(GameEngine(BoardParser().parse(board_text)))


def events_from(facade: GameFacade) -> list:
    received = []
    facade.subscribe_moves(received.append)
    facade.subscribe_outcomes(received.append)
    facade.subscribe_game_over(received.append)
    return received


def test_legal_destinations_splits_empty_from_capturable():
    facade = facade_for("wQ . bP . . . . .\n" + ". . . . . . . .\n" * 7)
    empty_cells, capturable_cells = facade.legal_destinations(Position(0, 0))
    assert Position(0, 2) in capturable_cells
    assert Position(0, 2) not in empty_cells
    assert Position(0, 1) in empty_cells
    assert Position(0, 1) not in capturable_cells


def test_request_move_predicts_duration_from_server_config_not_a_guess():
    facade = facade_for("wQ . . . . . . .\n" + ". . . . . . . .\n" * 7)
    result = facade.request_move(Position(0, 0), Position(0, 3))
    assert result.is_accepted
    motion = facade.pending_motions()[Position(0, 0)]
    assert motion.duration_ms == 3000  # 3 cells * MOVE_TRAVEL_TIME_PER_CELL(1000)


def test_illegal_move_is_rejected_and_publishes_no_pending_motion():
    facade = facade_for("wQ . . . . . . .\n" + ". . . . . . . .\n" * 7)
    result = facade.request_move(Position(0, 0), Position(5, 3))  # neither straight nor diagonal
    assert not result.is_accepted
    assert facade.pending_motions() == {}


def test_progress_climbs_smoothly_and_engine_snapshot_lags_behind_it():
    facade = facade_for("wQ . . . . . . .\n" + ". . . . . . . .\n" * 7)
    facade.request_move(Position(0, 0), Position(0, 2))  # 2 cells -> 2000ms
    snapshot = facade.tick(1000)
    motion = facade.pending_motions()[Position(0, 0)]
    assert motion.progress == 0.5
    assert snapshot.get_piece(Position(0, 0)) == "wQ"  # engine still shows it at source


def test_motion_is_reconciled_away_once_its_predicted_duration_elapses():
    facade = facade_for("wQ . . . . . . .\n" + ". . . . . . . .\n" * 7)
    facade.request_move(Position(0, 0), Position(0, 2))
    snapshot = facade.tick(2100)
    assert Position(0, 0) not in facade.pending_motions()
    assert snapshot.get_piece(Position(0, 2)) == "wQ"


def test_move_accepted_event_fires_synchronously_not_after_a_tick():
    facade = facade_for("wQ . . . . . . .\n" + ". . . . . . . .\n" * 7)
    events = events_from(facade)
    facade.request_move(Position(0, 0), Position(0, 2))
    assert len(events) == 1
    assert events[0].source == Position(0, 0) and events[0].destination == Position(0, 2)


def test_plain_arrival_publishes_piece_arrived():
    facade = facade_for("wQ . . . . . . .\n" + ". . . . . . . .\n" * 7)
    events = events_from(facade)
    facade.request_move(Position(0, 0), Position(0, 3))
    facade.tick(3100)
    arrivals = [e for e in events if isinstance(e, PieceArrived)]
    assert len(arrivals) == 1 and arrivals[0].destination == Position(0, 3)


def test_capture_publishes_piece_captured_with_the_capturing_token():
    text = ". . . . . . . .\n" * 4 + ". . . bP . . . .\n" + ". . . . . . . .\n" * 2 + ". . . wR . . . .\n"
    facade = facade_for(text)
    events = events_from(facade)
    facade.request_move(Position(7, 3), Position(4, 3))
    facade.tick(3100)
    captures = [e for e in events if isinstance(e, PieceCaptured)]
    assert captures == [PieceCaptured(position=Position(4, 3), captured_token="bP", by_token="wR")]


def test_promotion_publishes_promotion_event():
    text = ". . . . . . . .\n" + "wP . . . . . . .\n" + ". . . . . . . .\n" * 6
    facade = facade_for(text)
    events = events_from(facade)
    facade.request_move(Position(1, 0), Position(0, 0))
    facade.tick(1100)
    promotions = [e for e in events if isinstance(e, Promotion)]
    assert promotions == [Promotion(position=Position(0, 0), from_token="wP", to_token="wQ")]


def test_mid_flight_same_color_halt_publishes_piece_halted():
    board = Board([["." for _ in range(8)] for _ in range(8)])
    board.set_piece(Position(0, 0), "wR")
    board.set_piece(Position(2, 0), "wB")
    facade = GameFacade(GameEngine(board))
    events = events_from(facade)
    facade.request_move(Position(0, 0), Position(0, 4))
    facade.request_move(Position(2, 0), Position(0, 2))
    facade.tick(2100)
    halts = [e for e in events if isinstance(e, PieceHalted)]
    assert halts == [PieceHalted(source=Position(2, 0), resting_at=Position(1, 1), token="wB")]


def test_king_capture_publishes_game_over_exactly_once():
    text = ". . . . . . . .\n" * 4 + ". . . bK . . . .\n" + ". . . . . . . .\n" * 2 + ". . . wR . . . .\n"
    facade = facade_for(text)
    events = events_from(facade)
    facade.request_move(Position(7, 3), Position(4, 3))
    facade.tick(3100)
    facade.tick(100)  # a later tick must not re-publish GameOver
    assert [e for e in events if isinstance(e, GameOver)] == [GameOver()]
    assert facade.game_over
