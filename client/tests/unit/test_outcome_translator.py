from engine.game_engine import Arrived, Captured, Halted, Promoted
from model.position import Position
from state.game_events import PieceArrived, PieceCaptured, PieceHalted, Promotion
from state.outcome_translator import translate


def test_translates_arrived():
    event = translate(Arrived(Position(0, 0), Position(0, 3), "wR", is_jump=True))
    assert event == PieceArrived(source=Position(0, 0), destination=Position(0, 3), token="wR", is_jump=True)


def test_translates_captured():
    event = translate(Captured(Position(0, 0), Position(0, 3), "bN", "wR"))
    assert event == PieceCaptured(position=Position(0, 3), captured_token="bN", by_token="wR")


def test_translates_halted():
    event = translate(Halted(Position(2, 0), Position(1, 1), "wB"))
    assert event == PieceHalted(source=Position(2, 0), resting_at=Position(1, 1), token="wB")


def test_translates_promoted():
    event = translate(Promoted(Position(1, 0), Position(0, 0), "wP", "wQ"))
    assert event == Promotion(position=Position(0, 0), from_token="wP", to_token="wQ")
