from typing import List
from position import Position
from motion import Motion, ArrivalEvent, CollisionEvent
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

    def start_jump(self, piece_token: str, src: Position, dst: Position) -> None:
        self._jumps.append(Motion(piece_token, src, dst, self._clock, JUMP_TRAVEL_TIME))

    def advance_time(self, ms: int) -> List:
        old_clock = self._clock
        self._clock += ms
        crossing_events = self._resolve_collisions(old_clock, self._clock)

        arrived_jumps = [m for m in self._jumps if self._clock >= m.arrival_time]
        self._jumps = [m for m in self._jumps if self._clock < m.arrival_time]
        arrived_moves = sorted(
            (m for m in self._motions if self._clock >= m.arrival_time),
            key=lambda m: m.arrival_time,
        )
        self._motions = [m for m in self._motions if self._clock < m.arrival_time]
        airborne_dsts = {m.dst: m.piece_token for m in self._jumps + arrived_jumps}
        events = [ArrivalEvent(m.piece_token, m.src, m.dst, airborne_dsts, m.expected_target) for m in arrived_moves]
        events += [ArrivalEvent(m.piece_token, m.src, m.dst, {}, is_jump=True) for m in arrived_jumps]
        return crossing_events + events

    def _resolve_collisions(self, old_clock: int, new_clock: int) -> List:
        """Resolve two moving pieces whose paths cross at the same instant.

        Different colors: whichever motion started later wins and eats the earlier one,
        continuing on unaffected. Same color: the later motion halts at the last safe
        cell before the meeting point instead of colliding.
        """
        removed = set()
        events = []
        for i in range(len(self._motions)):
            for j in range(i + 1, len(self._motions)):
                a, b = self._motions[i], self._motions[j]
                if a in removed or b in removed:
                    continue
                meeting = self._first_meeting(a, b, old_clock, new_clock)
                if meeting is None:
                    continue
                meet_time, _ = meeting
                earlier, later = (a, b) if a.start_time <= b.start_time else (b, a)
                if earlier.piece_token[0] == later.piece_token[0]:
                    removed.add(later)
                    safe_cell = self._safe_stop_before(later, meet_time)
                    events.append(ArrivalEvent(later.piece_token, later.src, safe_cell))
                else:
                    removed.add(earlier)
                    events.append(CollisionEvent(earlier.piece_token, earlier.src))
        if removed:
            self._motions = [m for m in self._motions if m not in removed]
        return events

    @staticmethod
    def _first_meeting(a: Motion, b: Motion, old_clock: int, new_clock: int):
        b_steps = set(b.path_positions())
        matches = [(t, pos) for t, pos in a.path_positions() if old_clock < t <= new_clock and (t, pos) in b_steps]
        return min(matches, key=lambda tp: tp[0]) if matches else None

    @staticmethod
    def _safe_stop_before(motion: Motion, meet_time: int) -> Position:
        prior = [pos for t, pos in motion.path_positions() if t < meet_time]
        return prior[-1] if prior else motion.src
