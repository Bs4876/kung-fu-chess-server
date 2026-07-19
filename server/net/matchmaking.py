"""ELO-range matchmaking: queues authenticated sessions behind the "play"
command, pairs any two within elo_range on a fixed interval, and gives up
(resolving to no match) after wait_ms with no human found.

Supersedes the earlier anonymous-lobby pairing now that login/ELO exist to
actually match on.
"""

import asyncio
import time

from config import MATCH_ELO_RANGE, MATCHMAKING_TICK_MS, MATCHMAKING_WAIT_MS


class _Waiting:
    def __init__(self, websocket, user, joined_at: float, future: "asyncio.Future"):
        self.websocket = websocket
        self.user = user
        self.joined_at = joined_at
        self.future = future


class Matchmaking:
    def __init__(
        self, new_room, clock=time.monotonic,
        elo_range: int = MATCH_ELO_RANGE, tick_ms: int = MATCHMAKING_TICK_MS, wait_ms: int = MATCHMAKING_WAIT_MS,
    ):
        """new_room() -> a fresh, started, empty GameRoom - injected so this
        module never has to import net/game_room.py itself, pure queue/timing
        logic. clock/elo_range/tick_ms/wait_ms are all injectable so tests
        can run matchmaking's timing deterministically fast instead of
        waiting on real wall-clock seconds (see
        server/tests/unit/test_matchmaking.py)."""
        self._new_room = new_room
        self._clock = clock
        self._elo_range = elo_range
        self._tick_ms = tick_ms
        self._wait_ms = wait_ms
        self._waiting: list[_Waiting] = []
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._run())

    def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()

    async def play(self, websocket, user) -> "GameRoom | None":
        """Queue websocket/user for matchmaking; blocks until paired with a
        human within elo_range, or resolves to None if wait_ms elapses with
        no match found."""
        future = asyncio.get_running_loop().create_future()
        self._waiting.append(_Waiting(websocket, user, self._clock(), future))
        return await future

    def cancel(self, websocket) -> None:
        self._waiting = [w for w in self._waiting if w.websocket is not websocket]

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(self._tick_ms / 1000)
            self._match_pairs()
            self._expire_after_wait()

    def _match_pairs(self) -> None:
        matched_ids = set()
        for i, a in enumerate(self._waiting):
            if id(a) in matched_ids:
                continue
            for b in self._waiting[i + 1:]:
                if id(b) in matched_ids:
                    continue
                if abs(a.user.elo - b.user.elo) <= self._elo_range:
                    matched_ids.add(id(a))
                    matched_ids.add(id(b))
                    room = self._new_room()
                    room.join(a.websocket, player=a.user)
                    room.join(b.websocket, player=b.user)
                    a.future.set_result(room)
                    b.future.set_result(room)
                    break
        self._waiting = [w for w in self._waiting if id(w) not in matched_ids]

    def _expire_after_wait(self) -> None:
        now = self._clock()
        still_waiting = []
        for entry in self._waiting:
            if (now - entry.joined_at) * 1000 >= self._wait_ms:
                entry.future.set_result(None)
            else:
                still_waiting.append(entry)
        self._waiting = still_waiting
