"""Per-piece animation state machine: which sprite state/frame to draw right now.

One state per sprite folder (idle/move/jump/short_rest/long_rest). Looping states
cycle their frames forever; non-looping states play once and then transition to
whatever their config.json's next_state_when_finished says (e.g. jump -> short_rest).
"""

DEFAULT_STATE = "idle"


class PieceAnimator:
    """Tracks one piece's current animation state and elapsed time within it."""

    def __init__(self, sprite_loader, token: str):
        self._sprites = sprite_loader
        self.token = token
        self._state = DEFAULT_STATE
        self._elapsed_ms = 0.0

    @property
    def state(self) -> str:
        return self._state

    def set_state(self, state: str) -> None:
        """Switch to a new animation state, restarting its frame timeline."""
        if state != self._state:
            self._state = state
            self._elapsed_ms = 0.0

    def tick(self, dt_ms: int) -> None:
        """Advance the current state's animation by dt_ms.

        A looping state just wraps its elapsed time; a finished non-looping state
        transitions to its configured next state instead of freezing on frame 1.
        """
        self._elapsed_ms += dt_ms
        config = self._sprites.load_state_config(self.token, self._state)
        total_duration_ms = self._total_duration_ms(config)

        if config.is_loop:
            self._elapsed_ms %= total_duration_ms
        elif self._elapsed_ms >= total_duration_ms:
            self.set_state(config.next_state)

    def current_frame(self):
        """Return the Img to draw for this piece right now."""
        config = self._sprites.load_state_config(self.token, self._state)
        frame_duration_ms = 1000.0 / config.frames_per_sec
        frame_index = int(self._elapsed_ms // frame_duration_ms) % config.frame_count
        return self._sprites.load_frame(self.token, self._state, frame_index + 1)

    @staticmethod
    def _total_duration_ms(config) -> float:
        return (1000.0 / config.frames_per_sec) * config.frame_count
