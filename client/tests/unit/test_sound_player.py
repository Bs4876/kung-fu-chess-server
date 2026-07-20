import winsound

from config import MOVE_TRAVEL_TIME_PER_CELL

import ui_config
from model.position import Position
from state.game_events import GameOver, MoveAccepted, MoveRejected, PieceCaptured, PieceHalted, Promotion
from ui_components.sound_player import SoundPlayer


def played_paths(monkeypatch):
    calls = []
    monkeypatch.setattr(winsound, "PlaySound", lambda path, flags: calls.append(path))
    return calls


def test_move_accepted_plays_the_move_sound(monkeypatch):
    calls = played_paths(monkeypatch)
    SoundPlayer().handle_event(MoveAccepted(Position(0, 0), Position(0, 1), "wP"))
    assert calls == [str(ui_config.SOUND_MOVE)]


def test_move_rejected_plays_the_illegal_move_sound(monkeypatch):
    calls = played_paths(monkeypatch)
    SoundPlayer().handle_event(MoveRejected(Position(0, 0), Position(0, 1), "not a legal move"))
    assert calls == [str(ui_config.SOUND_ILLEGAL_MOVE)]


def test_piece_captured_plays_the_capture_sound(monkeypatch):
    calls = played_paths(monkeypatch)
    SoundPlayer().handle_event(PieceCaptured(Position(0, 0), "bP", "wQ"))
    assert calls == [str(ui_config.SOUND_CAPTURE)]


def test_promotion_plays_the_promotion_sound(monkeypatch):
    calls = played_paths(monkeypatch)
    SoundPlayer().handle_event(Promotion(Position(0, 0), "wP", "wQ"))
    assert calls == [str(ui_config.SOUND_PROMOTION)]


def test_game_over_plays_the_game_over_sound(monkeypatch):
    calls = played_paths(monkeypatch)
    SoundPlayer().handle_event(GameOver())
    assert calls == [str(ui_config.SOUND_GAME_OVER)]


def test_unmapped_event_plays_nothing(monkeypatch):
    calls = played_paths(monkeypatch)
    SoundPlayer().handle_event(PieceHalted(Position(0, 0), Position(1, 1), "wB"))
    assert calls == []


def test_single_cell_move_does_not_replay_the_footstep(monkeypatch):
    calls = played_paths(monkeypatch)
    player = SoundPlayer()
    player.handle_event(MoveAccepted(Position(0, 0), Position(0, 1), "wP", duration_ms=MOVE_TRAVEL_TIME_PER_CELL))
    player.tick(MOVE_TRAVEL_TIME_PER_CELL)  # arrives - no extra footstep on the way
    assert calls == [str(ui_config.SOUND_MOVE)]


def test_three_cell_move_replays_the_footstep_once_per_cell(monkeypatch):
    calls = played_paths(monkeypatch)
    player = SoundPlayer()
    duration_ms = 3 * MOVE_TRAVEL_TIME_PER_CELL
    player.handle_event(MoveAccepted(Position(0, 0), Position(0, 3), "wQ", duration_ms=duration_ms))
    for _ in range(duration_ms // 100):
        player.tick(100)
    assert calls == [str(ui_config.SOUND_MOVE)] * 3


def test_footsteps_for_different_sources_are_tracked_independently(monkeypatch):
    calls = played_paths(monkeypatch)
    player = SoundPlayer()
    duration_ms = 2 * MOVE_TRAVEL_TIME_PER_CELL
    player.handle_event(MoveAccepted(Position(0, 0), Position(0, 2), "wQ", duration_ms=duration_ms))
    player.handle_event(MoveAccepted(Position(7, 0), Position(5, 0), "bQ", duration_ms=duration_ms))
    for _ in range(duration_ms // 100):
        player.tick(100)
    assert calls == [str(ui_config.SOUND_MOVE)] * 4  # 2 sources * (1 initial + 1 mid-flight step) each
