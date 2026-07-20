"""The actual game view: board rendering, mouse input, HUD panels, sound -
everything client/main.py's render loop used to do inline before there was a
home screen to come from.

Parameterized by whichever facade it's given (state.game_facade.GameFacade
for local hot-seat, network.network_game_facade.NetworkGameFacade for a
networked game) - neither this class nor anything it builds needs to know or
care which, since both expose the exact same interface.
"""

import ui_config
import user_settings
from config import CELL_SIZE
from graphics.hud_renderer import HudRenderer
from graphics.renderer import BoardRenderer
from graphics.sprite_loader import SpriteLoader
from input.board_mapper import BoardMapper
from input.controller import Controller
from ui_components.cooldown_tracker import CooldownTracker
from ui_components.game_over_banner import GameOverBanner
from ui_components.halt_flash import HaltFlashTracker
from ui_components.moves_log_panel import MovesLogPanel
from ui_components.opponent_status_tracker import OpponentStatusTracker
from ui_components.player_labels import PlayerLabels
from ui_components.score_panel import ScorePanel
from ui_components.sound_player import SoundPlayer
from user_input.mouse_controller import MouseController


class GameScreen:
    def __init__(self, facade, white_name: str | None = None, black_name: str | None = None):
        self._facade = facade
        snapshot = facade.snapshot()
        self._mapper = BoardMapper(snapshot.rows, snapshot.cols, CELL_SIZE)
        self._controller = Controller(facade, self._mapper)
        self._last_snapshot = snapshot
        self._last_dt_ms = 0

        self._moves_log_panel = MovesLogPanel()
        facade.subscribe_moves(self._moves_log_panel.handle_event)
        self._score_panel = ScorePanel()
        facade.subscribe_outcomes(self._score_panel.handle_event)
        self._game_over_banner = GameOverBanner()
        facade.subscribe_game_over(self._game_over_banner.handle_event)
        self._halt_flash = HaltFlashTracker()
        facade.subscribe_outcomes(self._halt_flash.handle_event)
        self._cooldown_tracker = CooldownTracker()
        facade.subscribe_outcomes(self._cooldown_tracker.handle_event)
        self._opponent_status = OpponentStatusTracker()
        facade.subscribe_opponent_status(self._opponent_status.handle_event)
        self._sound_player = SoundPlayer()
        facade.subscribe_moves(self._sound_player.handle_event)
        facade.subscribe_outcomes(self._sound_player.handle_event)
        facade.subscribe_game_over(self._sound_player.handle_event)
        self._player_labels = PlayerLabels(
            white_name or user_settings.WHITE_NAME,
            black_name or user_settings.BLACK_NAME,
        )

        sprite_loader = SpriteLoader(ui_config.ASSETS_DIR, user_settings.SKIN, CELL_SIZE)
        self._renderer = BoardRenderer(sprite_loader, CELL_SIZE)
        self._hud = HudRenderer(sprite_loader)
        self._mouse_controller = MouseController(
            self._controller, facade, self._mapper, board_x_offset=ui_config.PANEL_WIDTH,
        )

    def handle_mouse(self, event, x, y, flags, param) -> None:
        self._mouse_controller.handle_event(event, x, y, flags, param)

    def handle_key(self, key: int | None) -> None:
        pass

    def tick(self, dt_ms: int) -> None:
        # Age existing flashes/cooldowns by dt_ms *before* facade.tick() can
        # start new ones this frame - otherwise a cooldown that only just
        # started (from an arrival inside this very facade.tick() call) would
        # immediately get the same dt_ms credited to it a second time, aging
        # it past COOLDOWN_MS before it's ever drawn even once.
        self._halt_flash.tick(dt_ms)
        self._cooldown_tracker.tick(dt_ms)
        self._opponent_status.tick(dt_ms)
        self._sound_player.tick(dt_ms)
        self._last_snapshot = self._facade.tick(dt_ms)
        self._last_dt_ms = dt_ms

    def render(self):
        selected = self._controller.selected
        legal_move_cells, legal_capture_cells = (
            self._facade.legal_destinations(selected) if selected is not None else ([], [])
        )
        board_canvas = self._renderer.render(
            self._last_snapshot,
            self._last_dt_ms,
            selected=selected,
            pending_motions=self._facade.pending_motions(),
            halted_positions=self._halt_flash.active_positions(),
            game_over=self._game_over_banner.is_game_over,
            cooldown_fade_fractions=self._cooldown_tracker.active_fade_frames(),
            legal_move_cells=legal_move_cells,
            legal_capture_cells=legal_capture_cells,
            disconnect_countdown_seconds=self._opponent_status.seconds_remaining(),
        )
        return self._hud.compose(board_canvas, self._moves_log_panel, self._score_panel, self._player_labels)
