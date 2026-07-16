"""Maps GameEngine's outcome types (Arrived/Captured/Halted/Promoted) to the
state/game_events.py types log/score panels subscribe to - a pure lookup,
no bookkeeping (see state/motion_tracker.py for that).
"""

from engine.game_engine import Arrived, Captured, Halted, Promoted

from state.game_events import PieceArrived, PieceCaptured, PieceHalted, Promotion

_TRANSLATORS = {
    Arrived: lambda o: PieceArrived(source=o.source, destination=o.destination, token=o.token, is_jump=o.is_jump),
    Captured: lambda o: PieceCaptured(position=o.position, captured_token=o.captured_token, by_token=o.by_token,
                                       is_jump=o.is_jump),
    Halted: lambda o: PieceHalted(source=o.source, resting_at=o.resting_at, token=o.token, is_jump=o.is_jump),
    Promoted: lambda o: Promotion(position=o.position, from_token=o.from_token, to_token=o.to_token,
                                   is_jump=o.is_jump),
}


def translate(outcome):
    """Turn one of GameEngine.wait()'s domain outcomes into the matching
    state/game_events.py type that log/score panels actually subscribe to."""
    return _TRANSLATORS[type(outcome)](outcome)
