"""Structural types (typing.Protocol) for the rendering layer.

Letting PieceRenderer/OverlayRenderer/HudRenderer depend on these instead of
concrete SpriteLoader/BoardRenderer classes means a test double only needs to
match the shape, not subclass anything real - no cv2/Img/disk access needed
to unit test drawing logic. pyright picks these up too (see pyproject.toml's
extraPaths), so they're statically checked, not just documentation.
"""

from typing import Protocol

from graphics.sprite_loader import StateConfig
from vendor.img import Img


class SpriteSource(Protocol):
    """Everything the rendering layer needs from a sprite provider - matches
    SpriteLoader's public surface exactly (see graphics/sprite_loader.py)."""

    def load_board(self, rows: int, cols: int) -> Img: ...
    def load_selection_highlight(self) -> Img: ...
    def load_halt_flash(self) -> Img: ...
    def load_panel_background(self, width: int, height: int) -> Img: ...
    def load_cooldown_fade_frame(self, fraction: float) -> Img: ...
    def load_legal_destination_highlight(self, is_capture: bool) -> Img: ...
    def load_state_config(self, token: str, state: str) -> StateConfig: ...
    def load_frame(self, token: str, state: str, frame_index: int) -> Img: ...


class Renderer(Protocol):
    """Matches BoardRenderer.render(...)'s signature."""

    def render(self, snapshot, dt_ms: int = 0, selected=None, pending_motions: dict | None = None,
               halted_positions: list | None = None, game_over: bool = False,
               cooldown_fade_frames: dict | None = None, legal_move_cells: list | None = None,
               legal_capture_cells: list | None = None) -> Img: ...
