"""Adapts OpenCV's mouse-callback signature to server input.

Left-click reuses server's own Controller for select-then-move, with one
addition Controller doesn't know about: clicking the *same* already-selected
square again triggers an in-place jump (a "dodge") instead of Controller's
normal reselect-same-square no-op. Right-click does a full jump instead: it
takes whatever piece is currently selected as the source and jumps it to the
clicked cell, bypassing normal move legality - the Controller has no concept
of jumps, so both talk to the facade directly.

board_x_offset accounts for the board no longer starting at the window's own
pixel (0, 0): HudRenderer draws a side panel to the board's left, so every
raw mouse coordinate needs that panel's width subtracted before it means
anything to server's Controller/BoardMapper, which only ever think in
board-local pixels and have no idea the HUD exists.
"""

import cv2


class MouseController:
    def __init__(self, controller, facade, mapper, board_x_offset: int = 0):
        self._controller = controller
        self._facade = facade
        self._mapper = mapper
        self._board_x_offset = board_x_offset

    def handle_event(self, event, x, y, flags, param) -> None:
        x -= self._board_x_offset
        if event == cv2.EVENT_LBUTTONDOWN:
            self._handle_left_click(x, y)
        elif event == cv2.EVENT_RBUTTONDOWN:
            self._handle_jump(x, y)

    def _handle_left_click(self, x, y) -> None:
        selected = self._controller.selected
        if selected is not None and self._mapper.pixel_to_cell(x, y) == selected:
            self._facade.request_jump(selected, selected)
            self._controller.deselect()
            return
        self._controller.click(x, y)

    def _handle_jump(self, x, y) -> None:
        source = self._controller.selected
        if source is None:
            return
        destination = self._mapper.pixel_to_cell(x, y)
        if destination is not None:
            self._facade.request_jump(source, destination)
        self._controller.deselect()
