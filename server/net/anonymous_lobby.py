"""Deliberately trivial pairing for the first networked vertical slice: holds
at most one waiting connection; the next one to arrive is immediately paired
with it into a new GameRoom. No usernames, no ELO, no queue beyond size 1.

This is explicit throwaway scaffolding, fully superseded once real
ELO-authenticated matchmaking exists (net/matchmaking.py) - kept this simple
on purpose so the very first end-to-end networked game didn't have to wait
on login/ELO to exist first.

Known limitation, accepted for scope: a connection that disconnects while
still waiting (never got paired) leaves the lobby's waiting slot pointing at
a dead socket, wedging all future pairing until the process restarts. Not
worth guarding against here - net/matchmaking.py's replacement seats sockets
into a GameRoom immediately (which already handles disconnects), rather than
leaving one parked in an unstructured pre-room wait the way this does.
"""

import asyncio

from bus.event_bus import EventBus
from net.game_room import GameRoom


class AnonymousLobby:
    def __init__(self, bus: EventBus, board_factory):
        self._bus = bus
        self._board_factory = board_factory
        self._waiting: tuple[object, "asyncio.Future[GameRoom]"] | None = None
        self._next_room_id = 1

    async def join(self, websocket) -> GameRoom:
        """Block until paired with a second connection; returns the shared
        GameRoom both ended up seated in (call room.color_of(websocket)
        afterwards to find out which color this particular socket got)."""
        if self._waiting is None:
            future = asyncio.get_running_loop().create_future()
            self._waiting = (websocket, future)
            return await future

        other_socket, other_future = self._waiting
        self._waiting = None
        room = self._start_room()
        room.join(other_socket)
        room.join(websocket)
        other_future.set_result(room)
        return room

    def _start_room(self) -> GameRoom:
        room = GameRoom(str(self._next_room_id), self._board_factory(), self._bus)
        self._next_room_id += 1
        room.start()
        return room
