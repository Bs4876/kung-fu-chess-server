# Kung-Fu Chess Client

A graphical client for the [`server/`](../server/README.md) game engine, built
entirely on the course-provided `Img` class (vendored in `client/vendor/img.py`) -
no PyGame/SFML/LWJGL anywhere.

## Running it

From the repository root:

```bash
uv run python client/main.py
```

A window opens with the opening position. Click a piece, then click a
destination square to move it. To jump instead (bypassing normal move
legality), left-click to select a piece, then **right-click** the
destination. The window can be resized by dragging its edges (both
dimensions scale together, so the board is never distorted). Esc or the
window's close button quits.

## What it does

- Board and pieces rendered from `client/assets/` (course-provided sprites),
  animated per-piece (idle/move/jump/short_rest/long_rest) from each state's
  own `config.json`.
- Pieces glide smoothly between cells in real time instead of snapping on
  arrival, predicted client-side and reconciled against the engine's actual
  outcome every frame (see `client/state/game_facade.py`).
- Click-to-move via server's own `Controller`/`BoardMapper`, unmodified.
- Two side panels (White on the left, Black on the right) show each
  player's name, a running score, and that side's own move-by-move log, all
  updated via an Observer/event stream published by `GameFacade` - see
  `client/state/game_events.py` and `client/graphics/hud_renderer.py`.
- Score is the sum of the piece values of everything that side has captured
  (`PIECE_VALUES` in `server/model/piece_values.py`), not a raw capture count.
- The moves log records each accepted move as `<piece> <from>-<to> [<time>]`
  on the mover's own panel; it does not currently list captures, promotions,
  game-over, or rejected moves.
- A red flash marks a piece that halted mid-flight (same-color collision); a
  "GAME OVER" banner appears once a king is captured.
- A piece must rest after landing before it can be commanded again -
  `MOVE_COOLDOWN_MS` (5s) after a move, the shorter `JUMP_COOLDOWN_MS` (2s)
  after a jump (both in `server/config.py`). Trying to move it again too soon
  is silently rejected, same as any other illegal move. A fading yellow
  overlay on the cooling-down cell mirrors the same duration client-side
  (`client/ui_components/cooldown_tracker.py`).

## Testing

Pure-logic pieces (animation state machine, motion interpolation, the
snapshot-diffing that drives events, the log/score panels) have real unit
tests:

```bash
uv run python -m pytest client/tests/unit -v
```

Rendering, animation feel, and click responsiveness aren't practically
automatable - run the app and actually play it. A reasonable manual pass
covers: a plain move, a capture, a pawn promoting on the last row, two pieces
moving at once, a same-color collision (one halts before reaching the other),
trying to move a piece again immediately after it arrives (should be rejected
by cooldown) and again after its cooldown elapses (~5s after a move, ~2s
after a jump - should work), and capturing a king (game over banner + no
further moves accepted).
