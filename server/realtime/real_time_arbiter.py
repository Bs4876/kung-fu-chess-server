import math
from typing import Dict, List
from model.position import Position
from realtime.motion import Motion, ArrivalEvent, CollisionEvent, straight_line_meeting_time
from config import JUMP_TRAVEL_TIME


class RealTimeArbiter:
    def __init__(self):
        self._clock = 0
        self._motions: List[Motion] = []
        self._jumps: List[Motion] = []
        self._cooldowns: Dict[Position, int] = {}

    def has_active_motion(self) -> bool:
        return len(self._motions) > 0

    def has_active_motion_for(self, pos: Position) -> bool:
        return any(m.src == pos for m in self._motions) or any(m.src == pos for m in self._jumps)

    def start_cooldown(self, pos: Position, duration_ms: int) -> None:
        self._cooldowns[pos] = self._clock + duration_ms

    def is_on_cooldown(self, pos: Position) -> bool:
        return self._cooldowns.get(pos, -1) > self._clock

    def airborne_destinations(self) -> dict:
        return {m.dst: m.piece_token for m in self._jumps}

    def start_motion(self, piece_token: str, src: Position, dst: Position) -> None:
        self._motions.append(Motion(piece_token, src, dst, self._clock))

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
        events = [ArrivalEvent(m.piece_token, m.src, m.dst, airborne_dsts) for m in arrived_moves]
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
                meet_time = self._first_meeting(a, b, old_clock, new_clock)
                if meet_time is None:
                    continue
                earlier, later = (a, b) if a.start_time <= b.start_time else (b, a)
                if earlier.piece_token[0] == later.piece_token[0]:
                    removed.add(later)
                    safe_cell = self._safe_stop_before(later, meet_time)
                    events.append(ArrivalEvent(later.piece_token, later.src, safe_cell, is_halt=True))
                else:
                    removed.add(earlier)
                    events.append(CollisionEvent(earlier.piece_token, earlier.src))
        if removed:
            self._motions = [m for m in self._motions if m not in removed]
        return events

    @staticmethod
    def _first_meeting(a: Motion, b: Motion, old_clock: int, new_clock: int):
        """The real-valued instant (not necessarily on a cell boundary) a and
        b's continuous paths cross, if that instant falls within this tick
        (old_clock, new_clock] and both motions are actually still active
        then - straight cell-matching would miss e.g. two same-speed movers
        crossing head-on over an odd number of cells, who pass through each
        other exactly between two cell centers."""
        meet_time = straight_line_meeting_time(a, b)
        if meet_time is None:
            return None
        window_start = max(a.start_time, b.start_time, old_clock)
        window_end = min(a.arrival_time, b.arrival_time, new_clock)
        return meet_time if window_start < meet_time <= window_end else None

    @staticmethod
    def _safe_stop_before(motion: Motion, meet_time: float) -> Position:
        """The last whole cell motion had strictly already reached before
        meet_time - not the cell it's still mid-crossing-into right as the
        collision happens, even if meet_time lands exactly on that cell's own
        arrival instant (arriving and colliding at the same instant is still
        not a safe arrival). Only ever called on a motion straight_line_meeting_time
        already confirmed is_straight_line() (see _first_meeting) - a knight-shaped
        motion can never reach here."""
        distance = motion.distance()
        per_cell = (motion.arrival_time - motion.start_time) / distance
        raw_cells = (meet_time - motion.start_time) / per_cell
        rounded = round(raw_cells)
        cells_completed = rounded - 1 if math.isclose(raw_cells, rounded, abs_tol=1e-9) else math.floor(raw_cells)
        cells_completed = max(0, min(cells_completed, distance))
        return motion.cell_at(cells_completed)
