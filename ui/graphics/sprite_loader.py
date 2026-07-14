"""Loads the board background and per-piece animated sprites out of ui/assets, via Img."""

import json

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

    def load_board(self, rows: int, cols: int) -> Img:
        """Load board.png resized to exactly fit an (rows x cols) board of cells."""
        path = self._assets_dir / "board.png"
        size = (cols * self._cell_size, rows * self._cell_size)
        return Img().read(path, size=size)

    def load_selection_highlight(self) -> Img:
        """Load the pre-baked transparent border overlay used to mark the selected cell."""
        path = self._assets_dir / "selection_highlight.png"
        return Img().read(path, size=(self._cell_size, self._cell_size))

    def load_halt_flash(self) -> Img:
        """Load the translucent red overlay marking a just-halted cell."""
        path = self._assets_dir / "halt_flash.png"
        return Img().read(path, size=(self._cell_size, self._cell_size))

    def load_panel_background(self, width: int, height: int) -> Img:
        """Load the solid-color HUD background, resized to any (width, height)."""
        path = self._assets_dir / "panel_background.png"
        return Img().read(path, size=(width, height))

    def load_cooldown_fade_frame(self, frame_index: int) -> Img:
        """Load one pre-baked cooldown-fade overlay frame (1 = just started
        cooling down/most opaque, higher index = more faded)."""
        path = self._assets_dir / "cooldown_fade" / f"{frame_index}.png"
        return Img().read(path, size=(self._cell_size, self._cell_size))

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
