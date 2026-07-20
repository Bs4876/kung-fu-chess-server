from types import SimpleNamespace

from animation.piece_animator import PieceAnimator


def config(frames_per_sec, is_loop, next_state="idle", frame_count=5):
    return SimpleNamespace(
        frames_per_sec=frames_per_sec, is_loop=is_loop, next_state=next_state, frame_count=frame_count
    )


class FakeSpriteLoader:
    """Stands in for the real SpriteLoader: no image files, just a config
    table and a record of which (token, state, frame_index) frames were asked for."""

    def __init__(self, configs):
        self._configs = configs
        self.requested_frames = []

    def load_state_config(self, token, state):
        return self._configs[(token, state)]

    def load_frame(self, token, state, frame_index):
        self.requested_frames.append((token, state, frame_index))
        return (token, state, frame_index)


def test_starts_in_idle_state():
    animator = PieceAnimator(FakeSpriteLoader({}), "wQ")
    assert animator.state == "idle"


def test_looping_state_wraps_back_to_frame_one_after_a_full_cycle():
    sprites = FakeSpriteLoader({("wQ", "idle"): config(frames_per_sec=5, is_loop=True, frame_count=5)})
    animator = PieceAnimator(sprites, "wQ")
    animator.tick(1000)  # exactly one full 5-frame cycle at 5fps
    assert animator.current_frame() == ("wQ", "idle", 1)


def test_looping_state_never_changes_state_on_its_own():
    sprites = FakeSpriteLoader({("wQ", "idle"): config(frames_per_sec=5, is_loop=True, frame_count=5)})
    animator = PieceAnimator(sprites, "wQ")
    animator.tick(10_000)
    assert animator.state == "idle"


def test_non_looping_state_transitions_to_its_configured_next_state_when_finished():
    sprites = FakeSpriteLoader({("wQ", "jump"): config(frames_per_sec=8, is_loop=False, next_state="short_rest", frame_count=5)})
    animator = PieceAnimator(sprites, "wQ")
    animator.set_state("jump")
    animator.tick(700)  # 5 frames / 8fps = 625ms, so this finishes it
    assert animator.state == "short_rest"


def test_non_looping_state_does_not_transition_before_finishing():
    sprites = FakeSpriteLoader({("wQ", "jump"): config(frames_per_sec=8, is_loop=False, next_state="short_rest", frame_count=5)})
    animator = PieceAnimator(sprites, "wQ")
    animator.set_state("jump")
    animator.tick(100)
    assert animator.state == "jump"


def test_set_state_restarts_the_frame_timeline():
    sprites = FakeSpriteLoader({
        ("wQ", "idle"): config(frames_per_sec=5, is_loop=True, frame_count=5),
        ("wQ", "move"): config(frames_per_sec=5, is_loop=True, frame_count=5),
    })
    animator = PieceAnimator(sprites, "wQ")
    animator.tick(300)  # partway through idle
    animator.set_state("move")
    assert animator.current_frame() == ("wQ", "move", 1)


def test_set_state_to_the_same_state_does_not_reset_progress():
    sprites = FakeSpriteLoader({("wQ", "idle"): config(frames_per_sec=5, is_loop=True, frame_count=5)})
    animator = PieceAnimator(sprites, "wQ")
    animator.tick(300)
    animator.set_state("idle")  # already idle - should be a no-op
    assert animator.current_frame() == ("wQ", "idle", 2)
