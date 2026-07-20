"""Owns per-piece animator lifecycle and drawing - split out of BoardRenderer
so it's independently testable without cv2/Img (see protocols.SpriteSource)."""

from animation.motion_predictor import interpolate_pixel
from animation.piece_animator import PieceAnimator
from model.board import EMPTY
from model.position import Position

_MOTION_STATES = ("move", "jump")


class PieceRenderer:
    """Keeps one PieceAnimator per occupied board cell, persisting across calls
    so each piece's animation timeline survives between frames. A cell with a
    pending motion (see GameFacade/MotionTracker) is drawn at its predicted
    in-flight pixel instead of snapped to a cell, since the engine's snapshot
    still shows it resting at its source cell until the motion actually resolves.
    """

    def __init__(self, sprite_source, cell_size: int):
        self._sprites = sprite_source
        self._cell_size = cell_size
        self._animators: dict[Position, PieceAnimator] = {}
        self._previous_motions: dict[Position, object] = {}

    def draw(self, canvas, snapshot, dt_ms: int, pending_motions: dict | None = None) -> None:
        """Draw every piece's current animation frame onto canvas, in place."""
        pending_motions = pending_motions or {}
        occupied = self._occupied_cells(snapshot)

        self._carry_over_completed_motions(occupied, pending_motions)
        self._sync_animators(occupied)
        self._sync_motion_states(pending_motions)
        self._advance_animators(dt_ms)
        self._previous_motions = pending_motions

        self._draw_pieces(canvas, pending_motions)

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
        is gone - reconciled by GameFacade, whether by arrival or otherwise.

        Also backs off once predicted travel time has fully elapsed (progress
        >= 1.0), even if GameFacade never reconciles the motion at all - e.g. a
        jump the engine silently rejected (already moving, on cooldown, out of
        bounds) never produces a resolving outcome, so without this the motion
        would sit in pending_motions forever and this loop would keep forcing
        the animator back into "jump" every time its own next_state finished,
        an animation that never ends.
        """
        for pos, animator in self._animators.items():
            motion = pending_motions.get(pos)
            if motion is not None and motion.progress < 1.0:
                desired_state = "jump" if motion.is_jump else "move"
                if animator.state not in _MOTION_STATES:
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
