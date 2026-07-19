"""Wire message envelope, message-type constants, and dict<->engine-object
translation.

Message *shapes* are plain dicts everywhere outside this module; concentrating
the JSON-specific pieces (encode/decode) here means swapping to another wire
format later (e.g. msgpack) is a one-file change, not a protocol redesign.
"""

import json

from config import SCHEMA_VERSION
from model.position import Position

# client -> server
REQUEST_MOVE = "request_move"
REQUEST_JUMP = "request_jump"
LOGIN = "login"
REGISTER = "register"
PLAY = "play"
CANCEL_MATCHMAKING = "cancel_matchmaking"
REJOIN_GAME = "rejoin_game"
LIST_ROOMS = "list_rooms"
CREATE_ROOM = "create_room"
JOIN_ROOM = "join_room"
CANCEL_ROOM = "cancel_room"

# server -> client
GAME_START = "game_start"
MOVE_ACCEPTED = "move_accepted"
MOVE_REJECTED = "move_rejected"
JUMP_STARTED = "jump_started"
ARRIVED = "arrived"
CAPTURED = "captured"
HALTED = "halted"
PROMOTED = "promoted"
GAME_OVER = "game_over"
LOGIN_RESULT = "login_result"
MATCHMAKING_STATUS = "matchmaking_status"
OPPONENT_DISCONNECTED = "opponent_disconnected"
ROOM_LIST = "room_list"
ROOM_CREATED = "room_created"
ERROR = "error"


def encode(message: dict) -> str:
    """Stamp schema_version and serialize a message dict for the wire."""
    return json.dumps({"schema_version": SCHEMA_VERSION, **message})


def decode(text: str) -> dict:
    """Parse a wire message back into a dict.

    Raises ValueError on malformed JSON or a payload with no 'type' field -
    callers are expected to turn that into an `error` response rather than
    let it propagate as an unhandled exception.
    """
    message = json.loads(text)
    if not isinstance(message, dict) or "type" not in message:
        raise ValueError("message must be a JSON object with a 'type' field")
    return message


def position_from_wire(data: dict) -> Position:
    return Position(data["row"], data["col"])


def position_to_wire(pos: Position) -> dict:
    return {"row": pos.row, "col": pos.col}


def snapshot_to_wire(snapshot) -> dict:
    """Translate a GameSnapshot into the board-rows shape `game_start` carries."""
    board = [[snapshot.get_piece(Position(r, c)) for c in range(snapshot.cols)] for r in range(snapshot.rows)]
    return {"rows": snapshot.rows, "cols": snapshot.cols, "board": board}


def game_start(game_id: str, color: str, state_version: int, snapshot) -> dict:
    return {
        "type": GAME_START,
        "game_id": game_id,
        "color": color,
        "state_version": state_version,
        "snapshot": snapshot_to_wire(snapshot),
    }


def request_move(game_id: str, source: Position, destination: Position) -> dict:
    return {
        "type": REQUEST_MOVE,
        "game_id": game_id,
        "source": position_to_wire(source),
        "destination": position_to_wire(destination),
    }


def request_jump(game_id: str, source: Position, destination: Position) -> dict:
    return {
        "type": REQUEST_JUMP,
        "game_id": game_id,
        "source": position_to_wire(source),
        "destination": position_to_wire(destination),
    }


def jump_started(game_id: str, source: Position, destination: Position) -> dict:
    """Broadcast the instant a jump is requested - request_jump has no
    accept/reject signal from the engine (see GameEngine.request_jump), so
    unlike move_result this always fires, whether or not the engine ends up
    silently ignoring the jump (already moving, on cooldown, out of bounds)."""
    return {
        "type": JUMP_STARTED,
        "game_id": game_id,
        "source": position_to_wire(source),
        "destination": position_to_wire(destination),
    }


def move_result(game_id: str, source: Position, destination: Position, result) -> dict:
    """Build move_accepted/move_rejected from the engine's MoveResult (duck-typed
    on is_accepted/reason, so this module doesn't need to import that class)."""
    message_type = MOVE_ACCEPTED if result.is_accepted else MOVE_REJECTED
    return {
        "type": message_type,
        "game_id": game_id,
        "source": position_to_wire(source),
        "destination": position_to_wire(destination),
        "reason": result.reason,
    }


def outcome(message_type: str, game_id: str, state_version: int, engine_outcome) -> dict:
    """Build a server->client message from one of the engine's outcome
    dataclasses (Arrived/Captured/Halted/Promoted), translating its Position
    fields to wire coordinates and adding routing metadata."""
    fields = {
        key: (position_to_wire(value) if isinstance(value, Position) else value)
        for key, value in vars(engine_outcome).items()
    }
    return {"type": message_type, "game_id": game_id, "state_version": state_version, **fields}


def game_over(game_id: str, state_version: int, reason: str, winner: str | None) -> dict:
    return {
        "type": GAME_OVER,
        "game_id": game_id,
        "state_version": state_version,
        "reason": reason,
        "winner": winner,
    }


def error(code: str, message: str) -> dict:
    return {"type": ERROR, "code": code, "message": message}


def login(username: str, password: str) -> dict:
    return {"type": LOGIN, "username": username, "password": password}


def register(username: str, password: str) -> dict:
    return {"type": REGISTER, "username": username, "password": password}


def login_result(success: bool, reason: str | None, username: str | None, elo: int | None) -> dict:
    return {"type": LOGIN_RESULT, "success": success, "reason": reason, "username": username, "elo": elo}


def play() -> dict:
    return {"type": PLAY}


def cancel_matchmaking() -> dict:
    return {"type": CANCEL_MATCHMAKING}


def rejoin_game(game_id: str) -> dict:
    return {"type": REJOIN_GAME, "game_id": game_id}


def matchmaking_status(status: str) -> dict:
    return {"type": MATCHMAKING_STATUS, "status": status}


def opponent_disconnected(game_id: str, forfeit_in_ms: int) -> dict:
    return {"type": OPPONENT_DISCONNECTED, "game_id": game_id, "forfeit_in_ms": forfeit_in_ms}


def list_rooms() -> dict:
    return {"type": LIST_ROOMS}


def create_room(name: str) -> dict:
    return {"type": CREATE_ROOM, "name": name}


def join_room(room_id: str) -> dict:
    return {"type": JOIN_ROOM, "room_id": room_id}


def cancel_room(room_id: str) -> dict:
    return {"type": CANCEL_ROOM, "room_id": room_id}


def room_list(rooms: list) -> dict:
    return {"type": ROOM_LIST, "rooms": rooms}


def room_created(room_id: str) -> dict:
    return {"type": ROOM_CREATED, "room_id": room_id}
