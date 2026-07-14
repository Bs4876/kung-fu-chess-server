"""Stage 9: player names, a game-over banner, and a mid-flight-halt flash."""

import server_bridge  # noqa: F401  (must run before any server-rooted import below)

import ui_config
from animation.animation_clock import Clock
from chess_io.board_parser import BoardParser
from config import CELL_SIZE
from engine.game_engine import GameEngine
from graphics.hud_renderer import HudRenderer
from graphics.renderer import BoardRenderer
from graphics.sprite_loader import SpriteLoader
from graphics.window import Window
from input.board_mapper import BoardMapper
from input.controller import Controller
from model.starting_position import STARTING_POSITION
from state.game_facade import GameFacade
from ui_components.cooldown_tracker import CooldownTracker
from ui_components.game_over_banner import GameOverBanner
from ui_components.halt_flash import HaltFlashTracker
from ui_components.moves_log_panel import MovesLogPanel
from ui_components.player_labels import PlayerLabels
from ui_components.score_panel import ScorePanel
from user_input.mouse_controller import MouseController


def build_facade() -> GameFacade:
    """Parse the standard opening position into a real, running GameEngine,
    wrapped in a GameFacade so the UI can predict smooth in-flight motion."""
    board = BoardParser().parse(STARTING_POSITION)
    return GameFacade(GameEngine(board))


def build_mapper(facade: GameFacade) -> BoardMapper:
    snapshot = facade.snapshot()
    return BoardMapper(snapshot.rows, snapshot.cols, CELL_SIZE)


def build_controller(facade: GameFacade, mapper: BoardMapper) -> Controller:
    """Wire up server's own click-to-move Controller against this facade.

    Controller only calls request_move(...)/snapshot() on whatever it's given,
    so pointing it at GameFacade instead of the raw engine needs no changes to
    Controller itself.
    """
    return Controller(facade, mapper)


def next_fps_reading(previous_fps: float, dt_ms: int) -> float:
    """Smooth the instantaneous per-frame FPS with an exponential moving average,
    so the overlay reads steadily instead of flickering every frame."""
    if dt_ms <= 0:
        return previous_fps
    instantaneous = 1000.0 / dt_ms
    if not previous_fps:
        return instantaneous
    return previous_fps * 0.9 + instantaneous * 0.1


def draw_fps_overlay(canvas, fps: float) -> None:
    canvas.put_text(f"FPS: {fps:.0f}", 10, 30, 1.0, color=(0, 255, 0, 255))


def main() -> None:
    facade = build_facade()
    mapper = build_mapper(facade)
    controller = build_controller(facade, mapper)

    moves_log_panel = MovesLogPanel()
    facade.subscribe(moves_log_panel.handle_event)
    score_panel = ScorePanel()
    facade.subscribe(score_panel.handle_event)
    game_over_banner = GameOverBanner()
    facade.subscribe(game_over_banner.handle_event)
    halt_flash = HaltFlashTracker()
    facade.subscribe(halt_flash.handle_event)
    cooldown_tracker = CooldownTracker()
    facade.subscribe(cooldown_tracker.handle_event)
    player_labels = PlayerLabels()

    sprite_loader = SpriteLoader(ui_config.ASSETS_DIR, ui_config.SKIN, CELL_SIZE)
    renderer = BoardRenderer(sprite_loader, CELL_SIZE)
    hud = HudRenderer(sprite_loader, ui_config.SIDEBAR_WIDTH)
    window = Window(ui_config.WINDOW_TITLE)
    window.set_mouse_callback(MouseController(controller, facade, mapper).handle_event)
    clock = Clock()

    fps = 0.0
    while window.poll():
        dt_ms = clock.tick()
        # Age existing flashes/cooldowns by dt_ms *before* facade.tick() can
        # start new ones this frame - otherwise a cooldown that only just
        # started (from an arrival inside this very facade.tick() call) would
        # immediately get the same dt_ms credited to it a second time, aging
        # it past COOLDOWN_MS before it's ever drawn even once.
        halt_flash.tick(dt_ms)
        cooldown_tracker.tick(dt_ms)
        snapshot = facade.tick(dt_ms)
        fps = next_fps_reading(fps, dt_ms)

        # Controller doesn't expose selection via a public API; peeking at its
        # internal state is a pragmatic tradeoff to avoid duplicating it here.
        board_canvas = renderer.render(
            snapshot,
            dt_ms,
            selected=controller._selected,
            pending_motions=facade.pending_motions(),
            halted_positions=halt_flash.active_positions(),
            game_over=game_over_banner.is_game_over,
            cooldown_fade_frames=cooldown_tracker.active_fade_frames(),
        )
        scene = hud.compose(board_canvas, moves_log_panel, score_panel, player_labels)
        draw_fps_overlay(scene, fps)
        window.show_frame(scene)

    window.close()


if __name__ == "__main__":
    main()
