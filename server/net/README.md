# Networking layer

A single-process WebSocket server that lets two real clients play a game of
Kung Fu Chess over a real network connection, instead of one process
sharing an in-process `GameEngine` directly. This is a second entrypoint
alongside `server/main.py`'s
stdin/stdout CLI mode - it doesn't replace it, and doesn't change anything
about how `GameEngine`/`RealTimeArbiter` themselves work.

## Running it

From the `server/` directory:

```bash
python -m net.ws_server
```

This starts listening on `WS_HOST:WS_PORT` (see `config.py`) and runs until
interrupted. `ui/main.py` connects to this address by default.

## Shape of the system

- **`bus/event_bus.py`** - a topic-based publish/subscribe bus every other
  piece here publishes onto (game outcomes under `"game.<id>"`), so
  cross-cutting concerns (the write-log, ELO updates) can subscribe without
  the code that publishes needing to know they exist.
- **`net/protocol.py`** - the JSON wire envelope and every message shape,
  in one place. Swapping the encoding (e.g. to msgpack) later is a one-file
  change here, not a protocol redesign.
- **`net/game_room.py`** - owns one `GameEngine` and ticks it on its own
  asyncio task, independent of whether either player is currently
  connected. Also owns the disconnect grace-then-forfeit timer and
  reconnect handling for that game.
- **`net/matchmaking.py`** / **`net/room_registry.py`** - the two ways a
  game actually gets created: automatic ELO-range pairing (giving up with an
  error if no human is found within a wait), or a manually created/joined
  room. Both terminate in an identical `GameRoom`, built from the same
  injected factory.
- **`persistence/`** - SQLite-backed accounts (username/password, hashed
  with PBKDF2-HMAC-SHA256) and ELO rating updates, reacting to the bus
  rather than being called directly by `GameRoom`.
- **`net/ws_server.py`** - wires all of the above to real WebSocket
  connections and is the only place that touches `websockets` directly.

## Testing

Most of this is tested without a real socket - the bulk of
`server/tests/unit/` calls the pure message-handling functions/classes
directly (a real `GameEngine`, a fake socket that just records what would
be sent). A handful of `server/tests/integration/` tests do open real
sockets end-to-end, including `test_full_flow.py`, which chains login,
matchmaking, disconnect/forfeit, ELO updates, a matchmaking timeout, and
rooms together against one running server instance.
