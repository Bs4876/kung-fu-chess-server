from unittest.mock import MagicMock

import cv2

from model.position import Position
from user_input.mouse_controller import MouseController


def build(selected=None):
    controller = MagicMock()
    controller.selected = selected
    facade = MagicMock()
    mapper = MagicMock()
    return MouseController(controller, facade, mapper), controller, facade, mapper


def test_left_click_is_forwarded_to_controller():
    mc, controller, facade, mapper = build()
    mc.handle_event(cv2.EVENT_LBUTTONDOWN, 50, 50, 0, None)
    controller.click.assert_called_once_with(50, 50)
    facade.request_jump.assert_not_called()


def test_right_click_with_no_selection_does_nothing():
    mc, controller, facade, mapper = build(selected=None)
    mc.handle_event(cv2.EVENT_RBUTTONDOWN, 150, 50, 0, None)
    facade.request_jump.assert_not_called()


def test_right_click_with_a_selected_piece_requests_a_jump():
    mc, controller, facade, mapper = build(selected=Position(0, 0))
    mapper.pixel_to_cell.return_value = Position(0, 2)
    mc.handle_event(cv2.EVENT_RBUTTONDOWN, 250, 50, 0, None)
    facade.request_jump.assert_called_once_with(Position(0, 0), Position(0, 2))


def test_right_click_clears_the_selection_afterward():
    mc, controller, facade, mapper = build(selected=Position(0, 0))
    mapper.pixel_to_cell.return_value = Position(0, 2)
    mc.handle_event(cv2.EVENT_RBUTTONDOWN, 250, 50, 0, None)
    controller.deselect.assert_called_once()


def test_right_click_outside_the_board_does_not_request_a_jump():
    mc, controller, facade, mapper = build(selected=Position(0, 0))
    mapper.pixel_to_cell.return_value = None
    mc.handle_event(cv2.EVENT_RBUTTONDOWN, 9999, 9999, 0, None)
    facade.request_jump.assert_not_called()


def test_left_clicking_the_already_selected_square_again_jumps_in_place():
    mc, controller, facade, mapper = build(selected=Position(0, 0))
    mapper.pixel_to_cell.return_value = Position(0, 0)  # same square clicked again
    mc.handle_event(cv2.EVENT_LBUTTONDOWN, 50, 50, 0, None)
    facade.request_jump.assert_called_once_with(Position(0, 0), Position(0, 0))
    controller.click.assert_not_called()


def test_left_clicking_the_same_square_again_clears_the_selection_afterward():
    mc, controller, facade, mapper = build(selected=Position(0, 0))
    mapper.pixel_to_cell.return_value = Position(0, 0)
    mc.handle_event(cv2.EVENT_LBUTTONDOWN, 50, 50, 0, None)
    controller.deselect.assert_called_once()


def test_left_clicking_a_different_square_while_selected_still_goes_through_controller():
    mc, controller, facade, mapper = build(selected=Position(0, 0))
    mapper.pixel_to_cell.return_value = Position(0, 2)  # a different square
    mc.handle_event(cv2.EVENT_LBUTTONDOWN, 250, 50, 0, None)
    controller.click.assert_called_once_with(250, 50)
    facade.request_jump.assert_not_called()


def test_board_x_offset_is_subtracted_before_forwarding_a_left_click():
    controller = MagicMock()
    controller.selected = None
    facade = MagicMock()
    mapper = MagicMock()
    mc = MouseController(controller, facade, mapper, board_x_offset=220)
    mc.handle_event(cv2.EVENT_LBUTTONDOWN, 270, 50, 0, None)
    controller.click.assert_called_once_with(50, 50)


def test_board_x_offset_is_subtracted_before_mapping_a_right_click():
    controller = MagicMock()
    controller.selected = Position(0, 0)
    facade = MagicMock()
    mapper = MagicMock()
    mapper.pixel_to_cell.return_value = Position(0, 2)
    mc = MouseController(controller, facade, mapper, board_x_offset=220)
    mc.handle_event(cv2.EVENT_RBUTTONDOWN, 470, 50, 0, None)
    mapper.pixel_to_cell.assert_called_once_with(250, 50)
    facade.request_jump.assert_called_once_with(Position(0, 0), Position(0, 2))
