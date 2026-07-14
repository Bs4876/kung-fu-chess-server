from model.position import Position
from config import MOVE_TRAVEL_TIME_PER_CELL, JUMP_TRAVEL_TIME


def _sign(n):
    return (n > 0) - (n < 0)


class Motion:
    def __init__(self, piece_token: str, src: Position, dst: Position, start_time: int, travel_time: int = None,
                 expected_target: str = None):
        self.piece_token = piece_token
        self.src = src
        self.dst = dst
        self.start_time = start_time
        self.expected_target = expected_target
        if travel_time is not None:
            self.arrival_time = start_time + travel_time
        else:
            distance = max(abs(dst.row - src.row), abs(dst.col - src.col))
            self.arrival_time = start_time + distance * MOVE_TRAVEL_TIME_PER_CELL

    def is_straight_line(self) -> bool:
        dr = abs(self.dst.row - self.src.row)
        dc = abs(self.dst.col - self.src.col)
        return self.src != self.dst and (dr == 0 or dc == 0 or dr == dc)

    def path_positions(self):
        """(absolute_time, Position) for each cell stepped through: src exclusive, dst inclusive.
        Knight-shaped motions jump over intermediate cells, so they have no path."""
        if not self.is_straight_line():
            return []
        dr = _sign(self.dst.row - self.src.row)
        dc = _sign(self.dst.col - self.src.col)
        distance = max(abs(self.dst.row - self.src.row), abs(self.dst.col - self.src.col))
        per_cell = (self.arrival_time - self.start_time) // distance
        return [
            (self.start_time + i * per_cell, Position(self.src.row + dr * i, self.src.col + dc * i))
            for i in range(1, distance + 1)
        ]


class ArrivalEvent:
    def __init__(self, piece_token: str, src: Position, dst: Position, airborne_dsts: dict = None,
                 expected_target: str = None, is_jump: bool = False):
        self.piece_token = piece_token
        self.src = src
        self.dst = dst
        self.airborne_dsts = airborne_dsts or {}
        self.expected_target = expected_target
        self.is_jump = is_jump


class CollisionEvent:
    def __init__(self, piece_token: str, pos: Position):
        self.piece_token = piece_token
        self.pos = pos
