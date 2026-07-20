"""Plays a short sound effect for each event GameFacade publishes.

winsound.PlaySound(..., SND_ASYNC) fires the clip on a background thread and
returns immediately, so this never blocks the render loop; SND_FILENAME|
SND_ASYNC together also mean a new call interrupts whatever this same process
was already playing, which is fine here since these are all short one-shots.
"""

import winsound

from config import MOVE_TRAVEL_TIME_PER_CELL

import ui_config
import user_settings
from state.game_events import GameOver, MoveAccepted, MoveRejected, PieceCaptured, Promotion

_SOUND_FOR_EVENT = {
    MoveAccepted: ui_config.SOUND_MOVE,
    MoveRejected: ui_config.SOUND_ILLEGAL_MOVE,
    PieceCaptured: ui_config.SOUND_CAPTURE,
    Promotion: ui_config.SOUND_PROMOTION,
    GameOver: ui_config.SOUND_GAME_OVER,
}


def _play(path) -> None:
    if user_settings.SOUND_ENABLED:
        winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)


class _Footsteps:
    """One multi-cell move's repeat schedule: a plain single move.wav on
    MoveAccepted reads as one flat click no matter how far the piece travels,
    so this replays it once per MOVE_TRAVEL_TIME_PER_CELL - the same per-cell
    pace the engine itself uses for the move's travel time - until arrival."""

    def __init__(self, duration_ms: int):
        self.elapsed_ms = 0
        self.duration_ms = duration_ms
        self.steps_played = 1  # the first step already played on MoveAccepted itself


class SoundPlayer:
    """Subscribe this to GameFacade's moves/outcomes/game_over channels - it
    only reacts to the event types in _SOUND_FOR_EVENT, ignoring the rest.
    Also needs tick(dt_ms) every frame to keep multi-cell moves' footsteps
    going (see _Footsteps)."""

    def __init__(self):
        self._footsteps: dict = {}

    def handle_event(self, event) -> None:
        path = _SOUND_FOR_EVENT.get(type(event))
        if path is not None:
            _play(path)
        if isinstance(event, MoveAccepted):
            self._footsteps[event.source] = _Footsteps(event.duration_ms)

    def tick(self, dt_ms: int) -> None:
        for source in list(self._footsteps):
            footsteps = self._footsteps[source]
            footsteps.elapsed_ms += dt_ms
            if footsteps.elapsed_ms >= footsteps.duration_ms:
                del self._footsteps[source]
                continue
            due_steps = footsteps.elapsed_ms // MOVE_TRAVEL_TIME_PER_CELL + 1
            if due_steps > footsteps.steps_played:
                footsteps.steps_played = due_steps
                _play(ui_config.SOUND_MOVE)
