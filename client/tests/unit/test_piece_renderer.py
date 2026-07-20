from types import SimpleNamespace

from graphics.piece_renderer import PieceRenderer
from model.board import EMPTY
from model.position import Position


def config(frames_per_sec=5, is_loop=True, next_state="idle", frame_count=5):
    return SimpleNamespace(
        frames_per_sec=frames_per_sec, is_loop=is_loop, next_state=next_state, frame_count=frame_count
    )


class FakeSprite:
    """Stands in for an Img frame: just records where it was drawn."""

    def __init__(self, token, state, frame_index):
        self.token = token
        self.state = state
        self.frame_index = frame_index

    def draw_on(self, canvas, x, y):
        canvas.draws.append((self.token, self.state, self.frame_index, x, y))


class FakeSpriteSource:
    def __init__(self, configs):
        self._configs = configs

    def load_state_config(self, token, state):
        return self._configs.get((token, state), config())

    def load_frame(self, token, state, frame_index):
        return FakeSprite(token, state, frame_index)


class FakeCanvas:
    def __init__(self):
        self.draws = []


class FakeSnapshot:
    def __init__(self, tokens: dict, rows=3, cols=3):
        self._tokens = tokens
        self.rows = rows
        self.cols = cols

    def get_piece(self, pos):
        return self._tokens.get(pos, EMPTY)


class FakeMotion:
    def __init__(self, source, destination, progress, is_jump=False, token="wR"):
        self.source = source
        self.destination = destination
        self.progress = progress
        self.is_jump = is_jump
        self.token = token


def test_a_resting_piece_is_drawn_at_its_cell_s_top_left_pixel():
    renderer = PieceRenderer(FakeSpriteSource({}), cell_size=100)
    canvas = FakeCanvas()
    snapshot = FakeSnapshot({Position(1, 2): "wR"})
    renderer.draw(canvas, snapshot, dt_ms=16)
    assert canvas.draws == [("wR", "idle", 1, 200, 100)]


def test_a_moving_piece_is_drawn_at_its_interpolated_pixel_not_its_resting_cell():
    renderer = PieceRenderer(FakeSpriteSource({}), cell_size=100)
    canvas = FakeCanvas()
    snapshot = FakeSnapshot({Position(0, 0): "wR"})
    motion = FakeMotion(Position(0, 0), Position(0, 2), progress=0.5)
    renderer.draw(canvas, snapshot, dt_ms=16, pending_motions={Position(0, 0): motion})
    (_, _, _, x, y) = canvas.draws[0]
    assert (x, y) == (100, 0)  # halfway from col 0 to col 2 at cell_size 100


def test_animator_switches_to_move_state_when_a_motion_starts():
    renderer = PieceRenderer(FakeSpriteSource({("wR", "move"): config(is_loop=True)}), cell_size=100)
    canvas = FakeCanvas()
    snapshot = FakeSnapshot({Position(0, 0): "wR"})
    motion = FakeMotion(Position(0, 0), Position(0, 2), progress=0.1)
    renderer.draw(canvas, snapshot, dt_ms=16, pending_motions={Position(0, 0): motion})
    assert canvas.draws[0][1] == "move"


def test_capture_drops_the_animator_for_the_vacated_cell():
    renderer = PieceRenderer(FakeSpriteSource({}), cell_size=100)
    renderer.draw(FakeCanvas(), FakeSnapshot({Position(0, 0): "wR"}), dt_ms=16)
    canvas = FakeCanvas()
    renderer.draw(canvas, FakeSnapshot({}), dt_ms=16)
    assert canvas.draws == []


def test_token_change_at_the_same_cell_replaces_the_animator():
    renderer = PieceRenderer(FakeSpriteSource({}), cell_size=100)
    renderer.draw(FakeCanvas(), FakeSnapshot({Position(0, 0): "wR"}), dt_ms=16)
    canvas = FakeCanvas()
    renderer.draw(canvas, FakeSnapshot({Position(0, 0): "wQ"}), dt_ms=16)
    assert canvas.draws == [("wQ", "idle", 1, 0, 0)]


def test_a_motion_never_reconciled_by_the_facade_still_exits_its_move_state_once_progress_completes():
    # e.g. a rejected jump: GameFacade optimistically starts the pending motion
    # before the engine confirms it, and a silent rejection (already moving, on
    # cooldown, out of bounds) never produces a resolving outcome from wait() -
    # so pending_motions keeps reporting this motion forever. Without capping on
    # progress, the animator would be forced back into "jump" every time its own
    # config finishes it, looping that state indefinitely.
    sprites = FakeSpriteSource({("wR", "jump"): config(is_loop=False, frame_count=1, next_state="short_rest")})
    renderer = PieceRenderer(sprites, cell_size=100)
    snapshot = FakeSnapshot({Position(0, 0): "wR"})
    stuck_motion = FakeMotion(Position(0, 0), Position(0, 2), progress=1.0, is_jump=True)

    for _ in range(3):
        canvas = FakeCanvas()
        renderer.draw(canvas, snapshot, dt_ms=16, pending_motions={Position(0, 0): stuck_motion})

    assert canvas.draws[0][1] != "jump"


def test_completed_motion_carries_the_animator_to_its_destination_instead_of_resetting_it():
    # "move"'s configured next_state is "long_rest", not "idle" - carrying the
    # existing animator over means it plays THAT, distinguishing it from
    # _sync_animators' plain create-fresh-idle-animator path (which a lost
    # carry-over would fall through to instead).
    sprites = FakeSpriteSource({("wR", "move"): config(is_loop=True, frame_count=5, next_state="long_rest")})
    renderer = PieceRenderer(sprites, cell_size=100)
    motion = FakeMotion(Position(0, 0), Position(0, 2), progress=0.9)
    renderer.draw(FakeCanvas(), FakeSnapshot({Position(0, 0): "wR"}), dt_ms=16,
                   pending_motions={Position(0, 0): motion})

    # motion resolved: piece now rests at its intended destination, no longer pending
    canvas = FakeCanvas()
    renderer.draw(canvas, FakeSnapshot({Position(0, 2): "wR"}), dt_ms=16)
    assert canvas.draws[0][1] == "long_rest"
