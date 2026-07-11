from typing import List
from motion import Motion, ArrivalEvent
from config import JUMP_TRAVEL_TIME
from position import Position


class RealTimeArbiter:
    def __init__(self):
        self._clock = 0
        self._motions: List[Motion] = []
        self._jumps: List[Motion] = []

    def has_active_motion(self) -> bool:
        return len(self._motions) > 0

    def airborne_destinations(self) -> dict:
        return {m.dst: m.piece_token for m in self._jumps}

    def start_motion(self, piece_token: str, src: Position, dst: Position) -> None:
        self._motions.append(Motion(piece_token, src, dst, self._clock))

    def start_jump(self, piece_token: str, pos: Position) -> None:
        self._jumps.append(Motion(piece_token, pos, pos, self._clock, JUMP_TRAVEL_TIME))

    def advance_time(self, ms: int) -> List[ArrivalEvent]:
        self._clock += ms
        arrived_jumps = [m for m in self._jumps if self._clock >= m.arrival_time]
        self._jumps = [m for m in self._jumps if self._clock < m.arrival_time]
        arrived_moves = [m for m in self._motions if self._clock >= m.arrival_time]
        self._motions = [m for m in self._motions if self._clock < m.arrival_time]
        airborne_dsts = {m.dst: m.piece_token for m in self._jumps + arrived_jumps}
        events = [ArrivalEvent(m.piece_token, m.src, m.dst, airborne_dsts) for m in arrived_moves]
        events += [ArrivalEvent(m.piece_token, m.src, m.dst, {}) for m in arrived_jumps]
        return events
