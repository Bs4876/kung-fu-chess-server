"""Loads the board background and per-piece animated sprites out of ui/assets, via Img."""

import json

import numpy as np

import ui_config
from vendor.img import Img


def token_to_sprite_code(token: str) -> str:
    """Convert a board token like "wR" to a sprite folder code like "RW".

    Board tokens are (color, kind): 'w'/'b' + an uppercase kind letter.
    Sprite folders are named (kind, COLOR): kind letter + uppercase color letter.
    """
    color, kind = token[0], token[1]
    return kind + color.upper()


class StateConfig:
    """One animation state's timing/looping rules, parsed from its config.json."""

    def __init__(self, frames_per_sec: float, is_loop: bool, next_state: str, frame_count: int):
        self.frames_per_sec = frames_per_sec
        self.is_loop = is_loop
        self.next_state = next_state
        self.frame_count = frame_count


class SpriteLoader:
    """Loads (and caches) the images and animation configs needed to draw one frame."""

    def __init__(self, assets_dir, skin: str, cell_size: int):
        self._assets_dir = assets_dir
        self._skin = skin
        self._cell_size = cell_size
        self._frame_cache: dict[tuple[str, str, int], Img] = {}
        self._config_cache: dict[tuple[str, str], StateConfig] = {}
        self._static_image_cache: dict = {}

    def _load_static(self, key, path, size) -> Img:
        """Read+resize path once per (key, size) and cache the decoded pixels;
        every call still gets its own Img wrapping a copy of that array, so a
        caller's draw_on (which mutates in place) can never corrupt the cache
        or bleed into another caller's canvas - only the disk read+decode+
        resize is shared, not the pixels themselves."""
        cache_key = (key, size)
        if cache_key not in self._static_image_cache:
            self._static_image_cache[cache_key] = Img().read(path, size=size).img
        img = Img()
        img.img = self._static_image_cache[cache_key].copy()
        return img

    def load_board(self, rows: int, cols: int) -> Img:
        """Load board.png resized to exactly fit an (rows x cols) board of cells."""
        path = self._assets_dir / "board.png"
        size = (cols * self._cell_size, rows * self._cell_size)
        return self._load_static("board", path, size)

    def load_selection_highlight(self) -> Img:
        """Load the pre-baked transparent border overlay used to mark the selected cell."""
        path = self._assets_dir / "selection_highlight.png"
        return self._load_static("selection_highlight", path, (self._cell_size, self._cell_size))

    def load_halt_flash(self) -> Img:
        """Load the translucent red overlay marking a just-halted cell."""
        path = self._assets_dir / "halt_flash.png"
        return self._load_static("halt_flash", path, (self._cell_size, self._cell_size))

    def load_panel_background(self, width: int, height: int) -> Img:
        """Load the solid-color HUD background, resized to any (width, height)."""
        path = self._assets_dir / "panel_background.png"
        return self._load_static("panel_background", path, (width, height))

    def load_cooldown_fade_frame(self, fraction: float) -> Img:
        """Generate a light-yellow bar that drains top-down as fraction goes 0->1:
        bottom-anchored, its top edge sinking toward the bottom of the cell.

        The boundary row is alpha-blended by its fractional coverage instead of
        snapping a whole pixel row at a time, so the drain reads as a smooth
        motion rather than visibly stepping row by row.
        """
        size = self._cell_size
        exact_filled = size * (1.0 - fraction)
        filled_rows = int(exact_filled)
        partial = exact_filled - filled_rows
        color = ui_config.COOLDOWN_FADE_COLOR
        alpha = ui_config.COOLDOWN_FADE_ALPHA

        overlay = np.zeros((size, size, 4), dtype=np.uint8)
        if filled_rows > 0:
            overlay[size - filled_rows:, :, 0] = color[0]
            overlay[size - filled_rows:, :, 1] = color[1]
            overlay[size - filled_rows:, :, 2] = color[2]
            overlay[size - filled_rows:, :, 3] = alpha

        boundary = size - filled_rows - 1
        if 0 <= boundary < size and partial > 0:
            overlay[boundary, :, 0] = color[0]
            overlay[boundary, :, 1] = color[1]
            overlay[boundary, :, 2] = color[2]
            overlay[boundary, :, 3] = int(alpha * partial)

        img = Img()
        img.img = overlay
        return img

    def load_legal_destination_highlight(self, is_capture: bool) -> Img:
        """A flat translucent overlay marking a square the currently-selected
        piece could legally move to - red if landing there would capture an
        enemy, green if it's just empty. Generated once per cell_size and
        cached the same way as the on-disk statics (see _load_static)."""
        cache_key = ("legal_capture" if is_capture else "legal_move", self._cell_size)
        if cache_key not in self._static_image_cache:
            size = self._cell_size
            color = ui_config.LEGAL_CAPTURE_COLOR if is_capture else ui_config.LEGAL_MOVE_COLOR
            overlay = np.zeros((size, size, 4), dtype=np.uint8)
            overlay[:, :, 0] = color[0]
            overlay[:, :, 1] = color[1]
            overlay[:, :, 2] = color[2]
            overlay[:, :, 3] = ui_config.LEGAL_DESTINATION_ALPHA
            self._static_image_cache[cache_key] = overlay
        img = Img()
        img.img = self._static_image_cache[cache_key].copy()
        return img

    def load_state_config(self, token: str, state: str) -> StateConfig:
        """Return a piece's timing/looping config for one animation state, cached."""
        key = (token, state)
        if key not in self._config_cache:
            self._config_cache[key] = self._read_state_config(token, state)
        return self._config_cache[key]

    def load_frame(self, token: str, state: str, frame_index: int) -> Img:
        """Return one 1-based numbered sprite frame, sized to one board cell, cached."""
        key = (token, state, frame_index)
        if key not in self._frame_cache:
            path = self._state_dir(token, state) / "sprites" / f"{frame_index}.png"
            size = (self._cell_size, self._cell_size)
            self._frame_cache[key] = Img().read(path, size=size)
        return self._frame_cache[key]

    def _read_state_config(self, token: str, state: str) -> StateConfig:
        state_dir = self._state_dir(token, state)
        data = json.loads((state_dir / "config.json").read_text())
        frame_count = len(list((state_dir / "sprites").glob("*.png")))
        return StateConfig(
            frames_per_sec=data["graphics"]["frames_per_sec"],
            is_loop=data["graphics"]["is_loop"],
            next_state=data["physics"]["next_state_when_finished"],
            frame_count=frame_count,
        )

    def _state_dir(self, token: str, state: str):
        code = token_to_sprite_code(token)
        return self._assets_dir / self._skin / code / "states" / state
