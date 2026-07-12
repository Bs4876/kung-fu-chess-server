from typing import List
from model.position import Position
from realtime.motion import Motion, ArrivalEvent, CollisionEvent
from config import JUMP_TRAVEL_TIME


class RealTimeArbiter:
    def __init__(self):
        self._clock = 0
        self._motions: List[Motion] = []
        self._jumps: List[Motion] = []

    def has_active_motion(self) -> bool:
        return len(self._motions) > 0

    def has_active_motion_for(self, pos: Position) -> bool:
        return any(m.src == pos for m in self._motions) or any(m.src == pos for m in self._jumps)

    def airborne_destinations(self) -> dict:
        return {m.dst: m.piece_token for m in self._jumps}

    def start_motion(self, piece_token: str, src: Position, dst: Position, expected_target: str = None) -> None:
        self._motions.append(Motion(piece_token, src, dst, self._clock, expected_target=expected_target))

    def start_jump(self, piece_token: str, pos: Position) -> None:
        self._jumps.append(Motion(piece_token, pos, pos, self._clock, JUMP_TRAVEL_TIME))

    def advance_time(self, ms: int) -> List:
        old_clock = self._clock
        self._clock += ms
        collision_events = self._resolve_collisions(old_clock, self._clock)

        arrived_jumps = [m for m in self._jumps if self._clock >= m.arrival_time]
        self._jumps = [m for m in self._jumps if self._clock < m.arrival_time]
        arrived_moves = sorted(
            (m for m in self._motions if self._clock >= m.arrival_time),
            key=lambda m: m.arrival_time,
        )
        self._motions = [m for m in self._motions if self._clock < m.arrival_time]
        airborne_dsts = {m.dst: m.piece_token for m in self._jumps + arrived_jumps}
        events = [ArrivalEvent(m.piece_token, m.src, m.dst, airborne_dsts, m.expected_target) for m in arrived_moves]
        events += [ArrivalEvent(m.piece_token, m.src, m.dst, {}) for m in arrived_jumps]
        return collision_events + events

    def _resolve_collisions(self, old_clock: int, new_clock: int) -> List[CollisionEvent]:
        collided = set()
        for i in range(len(self._motions)):
            for j in range(i + 1, len(self._motions)):
                a, b = self._motions[i], self._motions[j]
                if a in collided or b in collided:
                    continue
                if self._paths_meet(a, b, old_clock, new_clock):
                    collided.add(a)
                    collided.add(b)
        if not collided:
            return []
        self._motions = [m for m in self._motions if m not in collided]
        return [CollisionEvent(m.piece_token, m.src) for m in collided]

    @staticmethod
    def _paths_meet(a: Motion, b: Motion, old_clock: int, new_clock: int) -> bool:
        b_steps = {(t, pos) for t, pos in b.path_positions()}
        return any(old_clock < t <= new_clock and (t, pos) in b_steps for t, pos in a.path_positions())
