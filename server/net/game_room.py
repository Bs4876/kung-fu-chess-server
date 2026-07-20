"""One active game: owns a GameEngine and drives it forward in real time on
its own asyncio task, independent of whether either player is connected - a
disconnected client can never stall the simulation for the other one.
"""

import asyncio
from dataclasses import dataclass

from bus.event_bus import EventBus
from config import DISCONNECT_GRACE_MS, TICK_MS
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


async def _safe_send(socket, text: str) -> None:
    """Broadcasting is best-effort: a socket can close in the moment between
    being read from self._sockets and this fire-and-forget send actually
    running (e.g. right as a disconnect is being processed) - that race is
    already handled by the disconnect-grace/forfeit machinery, so a failed
    send here just gets silently dropped instead of surfacing as an
    unretrieved-exception warning on this fire-and-forget task."""
    try:
        await socket.send(text)
    except Exception:
        pass


@dataclass
class GameEnded:
    """Published onto the bus (alongside the wire-level game_over broadcast)
    the instant a game ends, carrying whichever opaque "player" object (if
    any - see GameRoom.join) each color was seated with - a bus subscriber
    like persistence.elo_updater.EloUpdater reacts to this generically,
    without GameRoom needing to know anything about ELO/persistence itself."""

    game_id: str
    white_player: object | None
    black_player: object | None
    winner: str | None


class GameRoom:
    """Seats up to two sockets (one per color), forwards their move/jump
    commands to a GameEngine, and broadcasts every resulting wire message to
    both. Re-publishes each engine outcome onto the shared EventBus first, so
    anything else interested (the write-log, an ELO updater) sees it the
    same instant connected clients do.

    Tracks a grace-then-forfeit timer per color when its socket disconnects
    mid-game (see leave()/rejoin()) - the tick loop itself never depends on
    either player being connected, so a disconnect can only ever affect
    fairness/outcome, never stall the simulation.
    """

    def __init__(
        self, game_id: str, board: Board, bus: EventBus,
        disconnect_grace_ms: int = DISCONNECT_GRACE_MS, tick_ms: int = TICK_MS,
    ):
        self.game_id = game_id
        self.state_version = 0
        self._engine = GameEngine(board)
        self._bus = bus
        self._disconnect_grace_ms = disconnect_grace_ms
        self._tick_ms = tick_ms
        self._sockets: dict[str, object] = {}
        self._players: dict[str, object | None] = {}
        self._viewers: list = []
        self._disconnect_tasks: dict[str, asyncio.Task] = {}
        self._ended = False  # set once the game ends for any reason: king capture or forfeit
        self._tick_task: asyncio.Task | None = None
        self._engine.subscribe(self._on_engine_outcome)

    def start(self) -> None:
        """Begin ticking the engine on its own periodic task."""
        self._tick_task = asyncio.create_task(self._tick_loop())

    def stop(self) -> None:
        if self._tick_task is not None:
            self._tick_task.cancel()
        for task in self._disconnect_tasks.values():
            task.cancel()
        self._disconnect_tasks.clear()

    @property
    def ended(self) -> bool:
        return self._ended

    def snapshot(self):
        return self._engine.snapshot()

    def legal_destinations(self, source):
        return self._engine.legal_destinations(source)

    def join(self, websocket, player=None) -> str | None:
        """Seat websocket in the first free color slot. Returns the assigned
        color, or None if the room already has two players.

        player is an opaque identity (typically a persistence.users_repository.User,
        None for anonymous/unauthenticated) carried through to GameEnded once
        the game ends - GameRoom never inspects it itself."""
        for color in COLORS:
            if color not in self._sockets:
                self._sockets[color] = websocket
                self._players[color] = player
                return color
        return None

    def add_viewer(self, websocket) -> None:
        """Seat websocket as a read-only spectator - not one of the two
        color slots, never subject to the disconnect-grace/forfeit timer,
        and every subsequent broadcast (outcomes, game_over) reaches it too
        (see _broadcast). Callers are responsible for sending it an initial
        snapshot to catch up on the game already in progress."""
        self._viewers.append(websocket)

    def leave_viewer(self, websocket) -> None:
        """A viewer's connection dropped - just stop broadcasting to it, no
        forfeit/grace timer involved (a viewer leaving never affects the
        game's outcome)."""
        if websocket in self._viewers:
            self._viewers.remove(websocket)

    def leave(self, websocket) -> None:
        """A connection dropped. If the game is still running, start a
        grace-then-forfeit timer for whichever color it held - the tick loop
        keeps running throughout (see module docstring); only a forfeit, not
        a stall, is ever at stake."""
        color = self.color_of(websocket)
        for c, socket in list(self._sockets.items()):
            if socket is websocket:
                del self._sockets[c]
        if color is not None and not self._ended:
            self._start_disconnect_timer(color)

    def rejoin(self, websocket, color: str) -> None:
        """Re-seat websocket in color - a previously-disconnected player
        reconnecting within the grace window - and cancel its pending
        forfeit timer, telling the other side so it can clear its own
        on-screen countdown instead of it just running out with no visible
        explanation once the forfeit silently never happens."""
        self._sockets[color] = websocket
        task = self._disconnect_tasks.pop(color, None)
        if task is not None:
            task.cancel()
            self._broadcast(protocol.opponent_reconnected(self.game_id))

    def color_of(self, websocket) -> str | None:
        for color, socket in self._sockets.items():
            if socket is websocket:
                return color
        return None

    def color_of_player(self, player) -> str | None:
        """Which color, if any, player was seated as - used to resolve a
        rejoin_game request back to a color. Matched by username rather than
        object identity: a reconnecting session's User comes from a fresh
        DB query (net/auth.py's handle_login), never the same Python object
        the original connection's join() call stored."""
        if player is None:
            return None
        for color, seated in self._players.items():
            if seated is not None and seated.username == player.username:
                return color
        return None

    def handle_request_move(self, message: dict) -> None:
        if self._ended:
            return
        source = protocol.position_from_wire(message["source"])
        destination = protocol.position_from_wire(message["destination"])
        result = self._engine.request_move(source, destination)
        self._broadcast(protocol.move_result(self.game_id, source, destination, result))

    def handle_request_jump(self, message: dict) -> None:
        if self._ended:
            return
        source = protocol.position_from_wire(message["source"])
        destination = protocol.position_from_wire(message["destination"])
        self._engine.request_jump(source, destination)
        self._broadcast(protocol.jump_started(self.game_id, source, destination))

    async def _tick_loop(self) -> None:
        while not self._engine.game_over:
            await asyncio.sleep(self._tick_ms / 1000)
            self._engine.wait(self._tick_ms)

    def _on_engine_outcome(self, outcome) -> None:
        self.state_version += 1
        self._bus.publish(f"game.{self.game_id}", outcome)
        self._broadcast(protocol.outcome(_OUTCOME_TYPE[type(outcome)], self.game_id, self.state_version, outcome))
        if self._engine.game_over:
            self._end_game("king_capture", self._winner(outcome))

    @staticmethod
    def _winner(ending_outcome) -> str | None:
        """The captured king's color lost; the other color won. Only
        meaningful when this outcome is the one that just ended the game."""
        if not isinstance(ending_outcome, Captured):
            return None
        captured_color = "white" if ending_outcome.captured_token[0] == "w" else "black"
        return "black" if captured_color == "white" else "white"

    def _start_disconnect_timer(self, color: str) -> None:
        self._disconnect_tasks[color] = asyncio.create_task(self._forfeit_after_grace(color))
        self._broadcast(protocol.opponent_disconnected(self.game_id, self._disconnect_grace_ms))

    async def _forfeit_after_grace(self, color: str) -> None:
        await asyncio.sleep(self._disconnect_grace_ms / 1000)
        del self._disconnect_tasks[color]
        winner = "black" if color == "white" else "white"
        self._end_game("opponent_disconnected", winner)

    def _end_game(self, reason: str, winner: str | None) -> None:
        # This check-then-set is only safe because this method has no
        # `await` between them - asyncio can't interleave another caller
        # (e.g. a forfeit timer firing the same instant as a king capture)
        # into that gap. If this method ever grows an `await` before
        # `self._ended = True`, that guarantee breaks and this needs a lock.
        if self._ended:
            return
        self._ended = True
        self.stop()
        self.state_version += 1
        self._broadcast(protocol.game_over(self.game_id, self.state_version, reason, winner))
        self._bus.publish(
            f"game.{self.game_id}",
            GameEnded(self.game_id, self._players.get("white"), self._players.get("black"), winner),
        )

    def _broadcast(self, message: dict) -> None:
        text = protocol.encode(message)
        for socket in list(self._sockets.values()) + self._viewers:
            asyncio.create_task(_safe_send(socket, text))
