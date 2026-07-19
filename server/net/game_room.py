"""One active game: owns a GameEngine and drives it forward in real time on
its own asyncio task, independent of whether either player is connected - a
disconnected client can never stall the simulation for the other one.
"""

import asyncio

from bus.event_bus import EventBus
from config import TICK_MS
from engine.game_engine import Arrived, Captured, GameEngine, Halted, Promoted
from model.board import Board
from net import protocol

COLORS = ("white", "black")

_OUTCOME_TYPE = {
    Arrived: protocol.ARRIVED,
    Captured: protocol.CAPTURED,
    Halted: protocol.HALTED,
    Promoted: protocol.PROMOTED,
}


class GameRoom:
    """Seats up to two sockets (one per color), forwards their move/jump
    commands to a GameEngine, and broadcasts every resulting wire message to
    both. Re-publishes each engine outcome onto the shared EventBus first, so
    anything else interested (the write-log, later an ELO updater) sees it
    the same instant connected clients do.
    """

    def __init__(self, game_id: str, board: Board, bus: EventBus):
        self.game_id = game_id
        self.state_version = 0
        self._engine = GameEngine(board)
        self._bus = bus
        self._sockets: dict[str, object] = {}
        self._tick_task: asyncio.Task | None = None
        self._engine.subscribe(self._on_engine_outcome)

    def start(self) -> None:
        """Begin ticking the engine on its own periodic task."""
        self._tick_task = asyncio.create_task(self._tick_loop())

    def stop(self) -> None:
        if self._tick_task is not None:
            self._tick_task.cancel()

    def snapshot(self):
        return self._engine.snapshot()

    def join(self, websocket) -> str | None:
        """Seat websocket in the first free color slot. Returns the assigned
        color, or None if the room already has two players."""
        for color in COLORS:
            if color not in self._sockets:
                self._sockets[color] = websocket
                return color
        return None

    def leave(self, websocket) -> None:
        for color, socket in list(self._sockets.items()):
            if socket is websocket:
                del self._sockets[color]

    def handle_request_move(self, message: dict) -> None:
        source = protocol.position_from_wire(message["source"])
        destination = protocol.position_from_wire(message["destination"])
        result = self._engine.request_move(source, destination)
        self._broadcast(protocol.move_result(self.game_id, source, destination, result))

    def handle_request_jump(self, message: dict) -> None:
        source = protocol.position_from_wire(message["source"])
        destination = protocol.position_from_wire(message["destination"])
        self._engine.request_jump(source, destination)
        self._broadcast(protocol.jump_started(self.game_id, source, destination))

    async def _tick_loop(self) -> None:
        while not self._engine.game_over:
            await asyncio.sleep(TICK_MS / 1000)
            self._engine.wait(TICK_MS)

    def _on_engine_outcome(self, outcome) -> None:
        self.state_version += 1
        self._bus.publish(f"game.{self.game_id}", outcome)
        self._broadcast(protocol.outcome(_OUTCOME_TYPE[type(outcome)], self.game_id, self.state_version, outcome))
        if self._engine.game_over:
            self._broadcast(protocol.game_over(self.game_id, self.state_version, "king_capture", self._winner(outcome)))

    @staticmethod
    def _winner(ending_outcome) -> str | None:
        """The captured king's color lost; the other color won. Only
        meaningful when this outcome is the one that just ended the game."""
        if not isinstance(ending_outcome, Captured):
            return None
        captured_color = "white" if ending_outcome.captured_token[0] == "w" else "black"
        return "black" if captured_color == "white" else "white"

    def _broadcast(self, message: dict) -> None:
        text = protocol.encode(message)
        for socket in self._sockets.values():
            asyncio.create_task(socket.send(text))
