"""Non-blocking window: Img.show() is a one-shot blocking call (imshow + waitKey(0)),
which can't drive a real-time game loop. This replaces it with per-frame polling,
mouse events, and close detection, using cv2 directly instead of Img.
"""

import cv2

from ui_config import WINDOW_ESC_KEY


class Window:
    """Owns one OpenCV window and its per-frame lifecycle.

    User-resizable by dragging its edges (cv2.WINDOW_NORMAL), with
    WINDOW_KEEPRATIO so a drag never distorts the board into a non-square
    aspect ratio. This needs no extra mouse-coordinate math: cv2's own Win32
    backend already reports mouse callback (x, y) in the original image's
    pixel space, scaled back from whatever on-screen size the user dragged
    the window to.
    """

    def __init__(self, title: str):
        self._title = title
        cv2.namedWindow(title, cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)

    def show_frame(self, canvas) -> None:
        """Display one rendered Img canvas as the current frame.

        Unlike WINDOW_AUTOSIZE, a WINDOW_NORMAL window does *not* resize
        itself to fit a differently-sized image - it just scales the new
        canvas into whatever on-screen size it already has. That's exactly
        what lets the user's own drag-resize stick between frames; see
        resize_to for giving the window its initial size.
        """
        cv2.imshow(self._title, canvas.img)

    def resize_to(self, canvas) -> None:
        """Resize the OS window to exactly fit canvas.

        Called once at startup (a fresh WINDOW_NORMAL window doesn't start
        sized to the first frame shown in it) - never on every frame, since
        that would fight the user's own drag-resize by snapping the window
        back to this size on the very next tick.
        """
        height, width = canvas.img.shape[:2]
        cv2.resizeWindow(self._title, width, height)

    def poll(self) -> bool:
        """Pump this frame's window events. Returns False once the window should close
        (Esc pressed, or closed via the OS titlebar)."""
        raw_key = cv2.waitKey(1)
        # -1 means "no key this frame" - must check before masking with 0xFF,
        # since masking first would make that indistinguishable from keycode 255.
        key = None if raw_key == -1 else raw_key & 0xFF
        if key == WINDOW_ESC_KEY:
            return False
        return cv2.getWindowProperty(self._title, cv2.WND_PROP_VISIBLE) >= 1

    def set_mouse_callback(self, handler) -> None:
        """Register handler(event, x, y, flags, param) for mouse events on this window."""
        cv2.setMouseCallback(self._title, handler)

    def close(self) -> None:
        """Destroy the window, tolerating it already being gone - closing via
        the OS titlebar (not Esc) has cv2 destroy its own window handle first,
        so this later call would otherwise raise a NULL-window cv2.error."""
        try:
            cv2.destroyWindow(self._title)
        except cv2.error:
            pass
