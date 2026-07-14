"""Composes one frame: the board background plus every animated piece on it."""

from animation.motion_predictor import interpolate_pixel
from animation.piece_animator import PieceAnimator
from model.board import EMPTY
from model.position import Position

_MOTION_STATES = ("move", "jump")


class BoardRenderer:
    """Draws a GameSnapshot onto a fresh canvas each call, animating each piece.

    A fresh board.png copy is loaded every frame (via sprite_loader) rather than
    reused, because Img.draw_on mutates pixels in place with no way to undo a draw.

    Keeps one PieceAnimator per occupied board cell, persisting across calls so
    each piece's animation timeline survives between frames. A cell with a
    pending motion (see GameFacade) is drawn at its predicted in-flight pixel
    instead of snapped to a cell, since the engine's snapshot still shows it
    resting at its source cell until the motion actually resolves.
    """

    def __init__(self, sprite_loader, cell_size: int):
        self._sprites = sprite_loader
        self._cell_size = cell_size
        self._animators: dict[Position, PieceAnimator] = {}
        self._previous_motions: dict[Position, object] = {}

    def render(self, snapshot, dt_ms: int = 0, selected: Position | None = None,
               pending_motions: dict | None = None, halted_positions: list | None = None,
               game_over: bool = False, cooldown_fade_frames: dict | None = None):
        """Return a new Img with the board, every piece's current frame, a
        highlight border around the selected cell (if given), a brief red
        flash over any just-halted cells (if given), a fading yellow overlay
        over any cooling-down cells (if given), and a game-over banner (if the
        game has ended), all drawn on it."""
        pending_motions = pending_motions or {}
        occupied = self._occupied_cells(snapshot)

        self._carry_over_completed_motions(occupied, pending_motions)
        self._sync_animators(occupied)
        self._sync_motion_states(pending_motions)
        self._advance_animators(dt_ms)
        self._previous_motions = pending_motions

        canvas = self._sprites.load_board(snapshot.rows, snapshot.cols)
        self._draw_pieces(canvas, pending_motions)
        if selected is not None:
            self._draw_selection(canvas, selected)
        for pos in halted_positions or []:
            self._draw_halt_flash(canvas, pos)
        for pos, frame_index in (cooldown_fade_frames or {}).items():
            self._draw_cooldown_fade(canvas, pos, frame_index)
        if game_over:
            self._draw_game_over_banner(canvas)
        return canvas

    def _occupied_cells(self, snapshot) -> dict[Position, str]:
        occupied = {}
        for row in range(snapshot.rows):
            for col in range(snapshot.cols):
                pos = Position(row, col)
                token = snapshot.get_piece(pos)
                if token != EMPTY:
                    occupied[pos] = token
        return occupied

    def _carry_over_completed_motions(self, occupied: dict, pending_motions: dict) -> None:
        """A motion pending last frame but gone this frame just resolved somehow.

        If the piece is now resting exactly at that motion's intended
        destination, it was a clean arrival: move its existing animator there
        instead of letting _sync_animators create a fresh 'idle' one, so it
        plays the move/jump state's next_state_when_finished (e.g. long_rest)
        instead of skipping straight to idle. Any other outcome (stale-target
        cancellation, a mid-flight halt short of the destination, a mid-flight
        kill) is deliberately left for _sync_animators' plain create/drop logic,
        since those all *should* snap rather than carry an animation over.
        """
        for source, motion in self._previous_motions.items():
            if source in pending_motions or source not in self._animators:
                continue
            destination = motion.destination
            if occupied.get(destination) == motion.token:
                self._animators[destination] = self._animators.pop(source)

    def _sync_animators(self, occupied: dict) -> None:
        """Create an animator for each occupied cell (or replace it if the piece
        there changed, e.g. after a capture), and drop animators for empty cells.

        Keying animators by the board's own resting position - re-derived fresh
        from the snapshot every frame - is what makes reconciliation automatic:
        a piece that never left its source, one that ended up somewhere other
        than its intended destination, and one that vanished entirely all just
        fall out of this create/drop logic without special-casing any of them.
        """
        for pos, token in occupied.items():
            existing = self._animators.get(pos)
            if existing is None or existing.token != token:
                self._animators[pos] = PieceAnimator(self._sprites, token)

        for pos in list(self._animators):
            if pos not in occupied:
                del self._animators[pos]

    def _sync_motion_states(self, pending_motions: dict) -> None:
        """Switch an animator into move/jump when its motion starts, and back off
        it (into whatever that state's config says comes next) once the motion
        is gone - reconciled by GameFacade, whether by arrival or otherwise."""
        for pos, animator in self._animators.items():
            motion = pending_motions.get(pos)
            if motion is not None:
                desired_state = "jump" if motion.is_jump else "move"
                animator.set_state(desired_state)
            elif animator.state in _MOTION_STATES:
                finished_config = self._sprites.load_state_config(animator.token, animator.state)
                animator.set_state(finished_config.next_state)

    def _advance_animators(self, dt_ms: int) -> None:
        for animator in self._animators.values():
            animator.tick(dt_ms)

    def _draw_pieces(self, canvas, pending_motions: dict) -> None:
        for pos, animator in self._animators.items():
            sprite = animator.current_frame()
            x, y = self._pixel_position(pos, pending_motions.get(pos))
            sprite.draw_on(canvas, x, y)

    def _pixel_position(self, pos: Position, motion) -> tuple[int, int]:
        if motion is None:
            return pos.col * self._cell_size, pos.row * self._cell_size
        x, y = interpolate_pixel(motion.source, motion.destination, motion.progress, self._cell_size)
        return int(x), int(y)

    def _draw_selection(self, canvas, selected: Position) -> None:
        highlight = self._sprites.load_selection_highlight()
        highlight.draw_on(canvas, selected.col * self._cell_size, selected.row * self._cell_size)

    def _draw_halt_flash(self, canvas, position: Position) -> None:
        flash = self._sprites.load_halt_flash()
        flash.draw_on(canvas, position.col * self._cell_size, position.row * self._cell_size)

    def _draw_cooldown_fade(self, canvas, position: Position, frame_index: int) -> None:
        fade = self._sprites.load_cooldown_fade_frame(frame_index)
        fade.draw_on(canvas, position.col * self._cell_size, position.row * self._cell_size)

    def _draw_game_over_banner(self, canvas) -> None:
        board_height = canvas.img.shape[0]
        canvas.put_text("GAME OVER", self._cell_size, board_height // 2, 1.6, color=(0, 0, 255, 255), thickness=3)
