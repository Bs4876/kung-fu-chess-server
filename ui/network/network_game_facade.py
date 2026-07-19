"""Client-side counterpart to state/game_facade.GameFacade, backed by a
WebSocket connection instead of an in-process GameEngine.

Exposes the exact same public surface GameFacade does (request_move,
request_jump, snapshot, pending_motions, legal_destinations, tick,
game_over, subscribe_moves/outcomes/game_over) so ui/main.py's render loop
and every renderer/animation module run completely unmodified whether the
facade they're given is a GameFacade or a NetworkGameFacade.

Unlike GameFacade, request_move/request_jump here are pure fire-and-forget
sends - there's no synchronous confirmation the way a direct in-process
engine call has one. Motion prediction and every MoveAccepted/MoveRejected/
outcome event are instead driven uniformly, inside tick(), by whatever the
server broadcasts back - for both this client's own moves and the
opponent's. That's simpler and more correct than trying to optimistically
predict "my own" move locally the way GameFacade does: over a real network
the server might still reject it, and treating every broadcast the same
way regardless of who moved avoids ever double-counting a motion.

This client keeps its own local Board, replaying each already-resolved
server outcome onto it (see _apply_to_board) instead of re-deriving
anything - the server stays the sole authority for *what* happened; the
client's job is just to mirror it. legal_destinations() is the one
deliberate exception: it runs the same RuleEngine algorithm the server
itself uses, directly against this local board, purely to predict move-hint
highlighting - never authoritative, since the actual move request still
goes to the server, which is free to reject it regardless of what was
highlighted.
"""

from config import JUMP_TRAVEL_TIME, MOVE_TRAVEL_TIME_PER_CELL
from engine.game_engine import Arrived, Captured, GameSnapshot, Halted, Promoted
from model.board import EMPTY, Board
from model.position import Position
from net import protocol
from network.ws_client import WsClient
from rules.rule_engine import RuleEngine
from state.game_events import GameOver, MoveAccepted, MoveRejected
from state.motion_tracker import MotionTracker
from state.observer import Subject
from state.outcome_translator import translate


def connect(uri: str) -> "NetworkGameFacade":
    """Connect to uri and block until the server's game_start arrives."""
    return NetworkGameFacade(WsClient(uri))


def _chebyshev_distance(a: Position, b: Position) -> int:
    return max(abs(a.row - b.row), abs(a.col - b.col))


class NetworkGameFacade:
    def __init__(self, client):
        """client: anything shaped like WsClient (send(message)/recv_all()/
        recv_one_blocking()) - real WsClient in production, a fake in tests
        (see ui/tests/unit/test_network_game_facade.py)."""
        self._client = client
        self._rule_engine = RuleEngine()
        self._motions = MotionTracker()
        self._moves_events = Subject()
        self._outcomes_events = Subject()
        self._game_over_events = Subject()
        self._elapsed_ms = 0
        self._game_over = False
        self._handlers = {
            protocol.MOVE_ACCEPTED: self._handle_move_result,
            protocol.MOVE_REJECTED: self._handle_move_result,
            protocol.JUMP_STARTED: self._handle_jump_started,
            protocol.ARRIVED: self._handle_outcome,
            protocol.CAPTURED: self._handle_outcome,
            protocol.HALTED: self._handle_outcome,
            protocol.PROMOTED: self._handle_outcome,
            protocol.GAME_OVER: self._handle_game_over,
            protocol.ERROR: self._handle_error,
        }

        start = self._client.recv_one_blocking()
        self.game_id: str = start["game_id"]
        self.color: str = start["color"]
        self._board = Board(start["snapshot"]["board"])

    @property
    def game_over(self) -> bool:
        return self._game_over

    def subscribe_moves(self, callback) -> None:
        self._moves_events.subscribe(callback)

    def subscribe_outcomes(self, callback) -> None:
        self._outcomes_events.subscribe(callback)

    def subscribe_game_over(self, callback) -> None:
        self._game_over_events.subscribe(callback)

    def snapshot(self) -> GameSnapshot:
        return GameSnapshot(self._board, self._game_over)

    def pending_motions(self) -> dict:
        """Read-only view of in-flight motions, keyed by their source cell."""
        return self._motions.pending()

    def legal_destinations(self, source: Position) -> tuple[list, list]:
        """(empty_cells, capturable_cells): a client-side prediction only -
        see the module docstring for why this is the one thing NetworkGameFacade
        computes itself instead of waiting on the server."""
        destinations = self._rule_engine.legal_destinations(self._board, source)
        empty_cells = [pos for pos in destinations if self._board.get_piece(pos) == EMPTY]
        capturable_cells = [pos for pos in destinations if self._board.get_piece(pos) != EMPTY]
        return empty_cells, capturable_cells

    def request_move(self, source: Position, destination: Position) -> None:
        self._client.send(protocol.request_move(self.game_id, source, destination))

    def request_jump(self, source: Position, destination: Position) -> None:
        self._client.send(protocol.request_jump(self.game_id, source, destination))

    def tick(self, dt_ms: int) -> GameSnapshot:
        """Drain every message the server sent since the last tick, apply it,
        and advance predicted in-flight motion. Returns the fresh snapshot."""
        self._elapsed_ms += dt_ms
        for message in self._client.recv_all():
            self._handlers[message["type"]](message)
        self._motions.advance_all(dt_ms)
        return self.snapshot()

    def _handle_move_result(self, message: dict) -> None:
        source = protocol.position_from_wire(message["source"])
        destination = protocol.position_from_wire(message["destination"])
        if message["type"] == protocol.MOVE_ACCEPTED:
            token = self._board.get_piece(source)
            duration_ms = _chebyshev_distance(source, destination) * MOVE_TRAVEL_TIME_PER_CELL
            self._motions.start(source, destination, token, duration_ms, is_jump=False)
            self._moves_events.publish(MoveAccepted(source, destination, token, self._elapsed_ms, duration_ms))
        else:
            self._moves_events.publish(MoveRejected(source, destination, message["reason"]))

    def _handle_jump_started(self, message: dict) -> None:
        source = protocol.position_from_wire(message["source"])
        destination = protocol.position_from_wire(message["destination"])
        token = self._board.get_piece(source)
        # Mirrors GameFacade.request_jump's own guard: request_jump has no
        # accept/reject signal, so a jump broadcast for an already-empty
        # source (silently ignored server-side) just never starts a motion.
        if token != EMPTY:
            self._motions.start(source, destination, token, JUMP_TRAVEL_TIME, is_jump=True)

    def _handle_outcome(self, message: dict) -> None:
        outcome = _reconstruct_outcome(message)
        self._apply_to_board(outcome)
        self._motions.reconcile(outcome)
        self._outcomes_events.publish(translate(outcome))

    def _apply_to_board(self, outcome) -> None:
        """Replay an already-resolved server outcome onto the local board -
        mirrors exactly what GameEngine._apply_arrival/_apply_collision does
        server-side, but as a pure replay: the server already decided what
        happened, this just makes the local board agree with it."""
        if isinstance(outcome, Arrived):
            self._board.move_piece(outcome.source, outcome.destination)
        elif isinstance(outcome, Captured):
            if outcome.source == outcome.position:
                # Destroyed mid-flight/airborne: it never actually left its
                # source cell on the board, so there's nothing to move.
                self._board.replace_piece(outcome.position, EMPTY)
            else:
                self._board.move_piece(outcome.source, outcome.position)
        elif isinstance(outcome, Halted):
            self._board.move_piece(outcome.source, outcome.resting_at)
        elif isinstance(outcome, Promoted):
            self._board.move_piece(outcome.source, outcome.position)
            self._board.replace_piece(outcome.position, outcome.to_token)

    def _handle_game_over(self, message: dict) -> None:
        self._game_over = True
        self._game_over_events.publish(GameOver())

    @staticmethod
    def _handle_error(message: dict) -> None:
        # TODO: surface this to the UI (a toast/banner) instead of stderr,
        # once there's a screen to show it on (see the home-screen stage).
        print(f"[server error] {message['code']}: {message['message']}")


def _reconstruct_outcome(message: dict):
    """Inverse of net.protocol.outcome(): rebuild the real engine dataclass
    from a decoded wire message, so the rest of this module (and the
    already-tested state/outcome_translator.py + state/motion_tracker.py it
    reuses unchanged) never has to know it came over a socket."""
    outcome_type = message["type"]
    if outcome_type == protocol.ARRIVED:
        return Arrived(
            source=protocol.position_from_wire(message["source"]),
            destination=protocol.position_from_wire(message["destination"]),
            token=message["token"],
            is_jump=message["is_jump"],
        )
    if outcome_type == protocol.CAPTURED:
        return Captured(
            source=protocol.position_from_wire(message["source"]),
            position=protocol.position_from_wire(message["position"]),
            captured_token=message["captured_token"],
            by_token=message["by_token"],
            is_jump=message["is_jump"],
        )
    if outcome_type == protocol.HALTED:
        return Halted(
            source=protocol.position_from_wire(message["source"]),
            resting_at=protocol.position_from_wire(message["resting_at"]),
            token=message["token"],
            is_jump=message["is_jump"],
        )
    if outcome_type == protocol.PROMOTED:
        return Promoted(
            source=protocol.position_from_wire(message["source"]),
            position=protocol.position_from_wire(message["position"]),
            from_token=message["from_token"],
            to_token=message["to_token"],
            is_jump=message["is_jump"],
        )
    raise ValueError(f"not an outcome message type: {outcome_type}")
