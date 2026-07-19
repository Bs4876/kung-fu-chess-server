"""Manual create/join/cancel room list - a second, human-driven way into a
networked game alongside net/matchmaking.py's automatic ELO pairing. Both
terminate in an identical GameRoom construction (via the same injected
new_room factory) - nothing about engine/tick-loop/ELO wiring is duplicated
between the two entry paths.

Room capacity is fixed at 2, matching GameRoom's own white/black seating -
"join" always fills the last (second) empty slot and the room stops being
listed the instant that happens.
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


class RoomRegistry:
    def __init__(self, new_room):
        """new_room() -> a fresh, started, empty GameRoom - the same
        factory net/matchmaking.py takes, so rooms created either way are
        built identically."""
        self._new_room = new_room
        self._pending: dict[str, _PendingRoom] = {}

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
        (already filled, cancelled, or never existed)."""
        pending = self._pending.pop(room_id, None)
        if pending is None:
            return None
        game_room = self._new_room()
        game_room.join(pending.websocket, player=pending.user)
        game_room.join(websocket, player=user)
        pending.future.set_result(game_room)
        return game_room

    def cancel_room(self, room_id: str, websocket) -> bool:
        """Withdraw room_id - only its own creator's websocket may do this.
        Returns whether anything was actually cancelled."""
        pending = self._pending.get(room_id)
        if pending is None or pending.websocket is not websocket:
            return False
        del self._pending[room_id]
        return True

    def list_rooms(self) -> list[dict]:
        return [
            {"id": pending.id, "name": pending.name, "occupants": 1, "capacity": 2}
            for pending in self._pending.values()
        ]
