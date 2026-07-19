import server_bridge  # noqa: F401  (must run before any server-rooted import below)

import ui_config
import user_settings
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
from ui_components.sound_player import SoundPlayer
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


def build_render_stack() -> tuple[BoardRenderer, HudRenderer]:
    """Build both renderers, sharing one sprite loader sized to CELL_SIZE."""
    sprite_loader = SpriteLoader(ui_config.ASSETS_DIR, user_settings.SKIN, CELL_SIZE)
    renderer = BoardRenderer(sprite_loader, CELL_SIZE)
    hud = HudRenderer(sprite_loader)
    return renderer, hud


def main() -> None:
    facade = build_facade()

    mapper = build_mapper(facade)
    controller = build_controller(facade, mapper)

    moves_log_panel = MovesLogPanel()
    facade.subscribe_moves(moves_log_panel.handle_event)
    score_panel = ScorePanel()
    facade.subscribe_outcomes(score_panel.handle_event)
    game_over_banner = GameOverBanner()
    facade.subscribe_game_over(game_over_banner.handle_event)
    halt_flash = HaltFlashTracker()
    facade.subscribe_outcomes(halt_flash.handle_event)
    cooldown_tracker = CooldownTracker()
    facade.subscribe_outcomes(cooldown_tracker.handle_event)
    sound_player = SoundPlayer()
    facade.subscribe_moves(sound_player.handle_event)
    facade.subscribe_outcomes(sound_player.handle_event)
    facade.subscribe_game_over(sound_player.handle_event)
    player_labels = PlayerLabels(user_settings.WHITE_NAME, user_settings.BLACK_NAME)

    renderer, hud = build_render_stack()
    window = Window(ui_config.WINDOW_TITLE)
    mouse_controller = MouseController(controller, facade, mapper, board_x_offset=ui_config.PANEL_WIDTH)
    window.set_mouse_callback(mouse_controller.handle_event)
    clock = Clock()

    initial_canvas = renderer.render(facade.snapshot(), 0)
    window.resize_to(hud.compose(initial_canvas, moves_log_panel, score_panel, player_labels))

    while window.poll():
        window.maintain_aspect_ratio()
        dt_ms = clock.tick()
        # Age existing flashes/cooldowns by dt_ms *before* facade.tick() can
        # start new ones this frame - otherwise a cooldown that only just
        # started (from an arrival inside this very facade.tick() call) would
        # immediately get the same dt_ms credited to it a second time, aging
        # it past COOLDOWN_MS before it's ever drawn even once.
        halt_flash.tick(dt_ms)
        cooldown_tracker.tick(dt_ms)
        sound_player.tick(dt_ms)
        snapshot = facade.tick(dt_ms)

        selected = controller.selected
        legal_move_cells, legal_capture_cells = (
            facade.legal_destinations(selected) if selected is not None else ([], [])
        )
        board_canvas = renderer.render(
            snapshot,
            dt_ms,
            selected=selected,
            pending_motions=facade.pending_motions(),
            halted_positions=halt_flash.active_positions(),
            game_over=game_over_banner.is_game_over,
            cooldown_fade_fractions=cooldown_tracker.active_fade_frames(),
            legal_move_cells=legal_move_cells,
            legal_capture_cells=legal_capture_cells,
        )
        scene = hud.compose(board_canvas, moves_log_panel, score_panel, player_labels)
        window.show_frame(scene)

    window.close()


if __name__ == "__main__":
    main()
