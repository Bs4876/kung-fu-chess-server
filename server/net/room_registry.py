"""Manual create/join/cancel/watch room list - a second, human-driven way
into a networked game alongside net/matchmaking.py's automatic ELO pairing.
Both terminate in an identical GameRoom construction (via the same injected
new_room factory) - nothing about engine/tick-loop/ELO wiring is duplicated
between the two entry paths.

Player capacity is fixed at 2, matching GameRoom's own white/black seating -
"join" always fills the last (second) empty slot, at which point the room
starts and stops accepting new *players*. It stays discoverable/joinable as
a *viewer* after that though (see watch_room) - Stage E's spec: the first
two into a room are players, anyone after that is a read-only spectator.
"""

import asyncio
import uuid


class _PendingRoom:
    def __init__(self, room_id: str, name: str, websocket, user, future: "asyncio.Future"):
        self.id = room_id
        self.name = name
        self.websocket = websocket
        self.user = user
        self.future = future


class _RunningRoom:
    def __init__(self, room_id: str, name: str, game_room):
        self.id = room_id
        self.name = name
        self.game_room = game_room


class RoomRegistry:
    def __init__(self, new_room):
        """new_room() -> a fresh, started, empty GameRoom - the same
        factory net/matchmaking.py takes, so rooms created either way are
        built identically."""
        self._new_room = new_room
        self._pending: dict[str, _PendingRoom] = {}
        self._running: dict[str, _RunningRoom] = {}

    def create_room(self, name: str, websocket, user) -> str:
        """Register a new pending (1-occupant) room and return its id right
        away - call await_join(room_id) afterward to block until a second
        player joins, the same two-step shape net/ws_server.py already uses
        for matchmaking's play()."""
        room_id = uuid.uuid4().hex[:8]
        future = asyncio.get_running_loop().create_future()
        self._pending[room_id] = _PendingRoom(room_id, name, websocket, user, future)
        return room_id

    async def await_join(self, room_id: str) -> "GameRoom":
        return await self._pending[room_id].future

    def join_room(self, room_id: str, websocket, user) -> "GameRoom | None":
        """Seat websocket/user as the second occupant of room_id, starting
        the game. Returns the new GameRoom, or None if room_id doesn't exist
        (already filled, cancelled, or never existed). The room keeps
        appearing in list_rooms()/being reachable via watch_room afterward,
        now as a running (viewer-joinable) room instead of a pending one."""
        pending = self._pending.pop(room_id, None)
        if pending is None:
            return None
        game_room = self._new_room()
        game_room.join(pending.websocket, player=pending.user)
        game_room.join(websocket, player=user)
        pending.future.set_result(game_room)
        self._running[room_id] = _RunningRoom(room_id, pending.name, game_room)
        return game_room

    def watch_room(self, room_id: str) -> "GameRoom | None":
        """The already-running GameRoom for room_id, or None if it doesn't
        exist or hasn't started yet (still pending its second player)."""
        running = self._running.get(room_id)
        return running.game_room if running is not None else None

    def cancel_room(self, room_id: str, websocket) -> bool:
        """Withdraw room_id - only its own creator's websocket may do this.
        Returns whether anything was actually cancelled."""
        pending = self._pending.get(room_id)
        if pending is None or pending.websocket is not websocket:
            return False
        del self._pending[room_id]
        return True

    def list_rooms(self) -> list[dict]:
        waiting = [
            {"id": pending.id, "name": pending.name, "occupants": 1, "capacity": 2, "status": "waiting"}
            for pending in self._pending.values()
        ]
        running = [
            {"id": running.id, "name": running.name, "occupants": 2, "capacity": 2, "status": "running"}
            for running in self._running.values()
        ]
        return waiting + running
