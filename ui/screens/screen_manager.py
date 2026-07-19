"""Minimal single-slot screen switcher on top of Window: owns "the current
screen" and forwards each frame's mouse events/render call to it.

Not a full scene stack (push/pop/back) - the app only ever needs to jump
straight to a named screen (home -> game, home -> rooms -> game, ...), never
nest or automatically return to a previous one, so there's nothing here a
stack would buy that a single slot doesn't already cover.

Every screen shown through this must implement:
- tick(dt_ms) -> None: advance whatever per-frame state it owns.
- render() -> Img: compose this frame's canvas.
- handle_mouse(event, x, y, flags, param) -> None: react to a click, or do
  nothing at all (most screens only care about a subset of mouse events).
"""


class ScreenManager:
    def __init__(self, window):
        self._window = window
        self._screen = None
        window.set_mouse_callback(self._handle_mouse)

    def show(self, screen) -> None:
        """Switch the active screen, sizing the window to fit its first frame -
        screens can be very differently sized (a small home screen vs. a
        board+HUD game screen), so this happens on every switch, not just once
        at startup."""
        self._screen = screen
        screen.tick(0)
        self._window.resize_to(screen.render())

    def render_frame(self, dt_ms: int):
        """Advance and render the current screen for this frame."""
        self._screen.tick(dt_ms)
        return self._screen.render()

    def _handle_mouse(self, event, x, y, flags, param) -> None:
        if self._screen is not None:
            self._screen.handle_mouse(event, x, y, flags, param)
