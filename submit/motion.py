from position import Position
from config import MOVE_TRAVEL_TIME_PER_CELL, JUMP_TRAVEL_TIME


class Motion:
    def __init__(self, piece_token: str, src: Position, dst: Position, start_time: int, travel_time: int = None):
        self.piece_token = piece_token
        self.src = src
        self.dst = dst
        if travel_time is not None:
            self.arrival_time = start_time + travel_time
        else:
            distance = max(abs(dst.row - src.row), abs(dst.col - src.col))
            self.arrival_time = start_time + distance * MOVE_TRAVEL_TIME_PER_CELL


class ArrivalEvent:
    def __init__(self, piece_token: str, src: Position, dst: Position, airborne_dsts: dict = None):
        self.piece_token = piece_token
        self.src = src
        self.dst = dst
        self.airborne_dsts = airborne_dsts or {}
