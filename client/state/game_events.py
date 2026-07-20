"""Domain events GameFacade publishes for observers (moves log, score, ...)."""

from dataclasses import dataclass

from model.position import Position


@dataclass
class MoveAccepted:
    """A request_move/request_jump call was accepted - published synchronously,
    straight from the engine's own MoveResult, no diffing needed."""

    source: Position
    destination: Position
    token: str
    timestamp_ms: int = 0
    duration_ms: int = 0


@dataclass
class MoveRejected:
    source: Position
    destination: Position
    reason: str


@dataclass
class PieceArrived:
    """A piece completed its travel onto a previously-empty destination cell."""

    source: Position
    destination: Position
    token: str
    is_jump: bool = False


@dataclass
class PieceCaptured:
    """An enemy piece is gone: either captured on arrival, or killed mid-flight
    (in which case by_token is unknown and left as None)."""

    position: Position
    captured_token: str
    by_token: str | None
    is_jump: bool = False


@dataclass
class PieceHalted:
    """A piece stopped short of its intended destination - a mid-flight
    same-color collision - resting at some other cell instead. Only ever
    happens on a move: the arbiter's mid-flight collision math only runs
    against other moves, never jumps."""

    source: Position
    resting_at: Position
    token: str
    is_jump: bool = False


@dataclass
class Promotion:
    position: Position
    from_token: str
    to_token: str
    is_jump: bool = False


@dataclass
class GameOver:
    pass


@dataclass
class OpponentDisconnected:
    """The opponent's connection dropped - the server holds their seat for
    forfeit_in_ms before auto-resigning the game in this player's favor."""

    forfeit_in_ms: int


@dataclass
class OpponentReconnected:
    """The opponent reconnected within the grace window - whatever
    forfeit countdown was showing should be cleared."""
