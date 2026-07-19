import math

from model.position import Position
from config import MOVE_TRAVEL_TIME_PER_CELL, JUMP_TRAVEL_TIME


def _sign(n):
    return (n > 0) - (n < 0)


def _axis_rate(motion: "Motion", axis: str) -> float:
    """Constant rate of change (cells per ms) of one axis over this motion's
    whole active window."""
    duration = motion.arrival_time - motion.start_time
    return (getattr(motion.dst, axis) - getattr(motion.src, axis)) / duration


def _axis_meeting_time(a: "Motion", b: "Motion", axis: str):
    """When a and b's positions coincide on one axis, each moving at its own
    constant rate: pos_a(t) - pos_b(t) is itself linear in t, so it has at
    most one root. Returns that time, "always" if the two are already equal
    on this axis for every t (parallel movement, e.g. both stuck on the same
    row), or None if they're never equal (parallel but offset)."""
    rate_a, rate_b = _axis_rate(a, axis), _axis_rate(b, axis)
    a_src, b_src = getattr(a.src, axis), getattr(b.src, axis)
    gap_at_zero = (a_src - rate_a * a.start_time) - (b_src - rate_b * b.start_time)
    relative_rate = rate_a - rate_b
    if math.isclose(relative_rate, 0, abs_tol=1e-9):
        return "always" if math.isclose(gap_at_zero, 0, abs_tol=1e-9) else None
    return -gap_at_zero / relative_rate


def straight_line_meeting_time(a: "Motion", b: "Motion"):
    """The one real-valued instant (not necessarily on a cell boundary) at
    which a and b's continuous straight-line paths occupy the exact same
    (row, col), or None if their paths never coincide.

    Solved per axis as a linear equation in t (see _axis_meeting_time), since
    each axis moves at a constant rate for a motion's whole duration - a true
    coincidence needs both axes to agree on the same t, or one axis to
    already coincide at every t while the other pins down when. Knight-shaped
    motions have no path at all (see Motion.is_straight_line) and can never
    meet this way.
    """
    if not (a.is_straight_line() and b.is_straight_line()):
        return None
    row_t = _axis_meeting_time(a, b, "row")
    col_t = _axis_meeting_time(a, b, "col")
    if row_t is None or col_t is None:
        return None
    if row_t == "always":
        return col_t if col_t != "always" else max(a.start_time, b.start_time)
    if col_t == "always":
        return row_t
    return row_t if math.isclose(row_t, col_t, abs_tol=1e-6) else None


class Motion:
    def __init__(self, piece_token: str, src: Position, dst: Position, start_time: int, travel_time: int = None):
        self.piece_token = piece_token
        self.src = src
        self.dst = dst
        self.start_time = start_time
        if travel_time is not None:
            self.arrival_time = start_time + travel_time
        else:
            distance = max(abs(dst.row - src.row), abs(dst.col - src.col))
            self.arrival_time = start_time + distance * MOVE_TRAVEL_TIME_PER_CELL

    def is_straight_line(self) -> bool:
        dr = abs(self.dst.row - self.src.row)
        dc = abs(self.dst.col - self.src.col)
        return self.src != self.dst and (dr == 0 or dc == 0 or dr == dc)

    def distance(self) -> int:
        return max(abs(self.dst.row - self.src.row), abs(self.dst.col - self.src.col))

    def cell_at(self, cells_traveled: int) -> Position:
        """The whole-cell Position after traveling exactly this many cells
        along this straight-line path (0 = src, distance() = dst)."""
        dr = _sign(self.dst.row - self.src.row)
        dc = _sign(self.dst.col - self.src.col)
        return Position(self.src.row + dr * cells_traveled, self.src.col + dc * cells_traveled)

    def path_positions(self):
        """(absolute_time, Position) for each cell stepped through: src exclusive, dst inclusive.
        Knight-shaped motions jump over intermediate cells, so they have no path."""
        if not self.is_straight_line():
            return []
        distance = self.distance()
        per_cell = (self.arrival_time - self.start_time) // distance
        return [
            (self.start_time + i * per_cell, self.cell_at(i))
            for i in range(1, distance + 1)
        ]


class ArrivalEvent:
    def __init__(self, piece_token: str, src: Position, dst: Position, airborne_dsts: dict = None,
                 is_jump: bool = False, is_halt: bool = False):
        self.piece_token = piece_token
        self.src = src
        self.dst = dst
        self.airborne_dsts = airborne_dsts or {}
        self.is_jump = is_jump
        # True when dst is a mid-flight same-color halt cell, not the motion's
        # original requested destination - GameEngine needs this to report a
        # PieceHalted outcome instead of a plain arrival.
        self.is_halt = is_halt


class CollisionEvent:
    def __init__(self, piece_token: str, pos: Position):
        self.piece_token = piece_token
        self.pos = pos
