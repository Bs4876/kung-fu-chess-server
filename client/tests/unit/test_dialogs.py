"""Covers the parts of dialogs.py that don't require a running mainloop -
Button.invoke() calls its command synchronously, so _build_room_action_dialog
can be driven directly. wait_for_room_match/show_info are thin tkinter glue
over already-tested protocol calls and are verified by manual smoke test
instead (see the plan's verification steps), not here.
"""

import tkinter as tk

import pytest

from dialogs import _build_room_action_dialog


@pytest.fixture
def root():
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"no display available for tkinter: {exc}")
    root.withdraw()
    yield root
    try:
        root.destroy()
    except tk.TclError:
        pass


def test_clicking_create_returns_create_with_the_entered_text(root):
    widgets = _build_room_action_dialog(root)
    widgets["entry"].insert(0, "My Room")

    widgets["create_button"].invoke()

    assert widgets["result"] == {"action": "create", "text": "My Room"}


def test_clicking_join_returns_join_with_the_entered_text(root):
    widgets = _build_room_action_dialog(root)
    widgets["entry"].insert(0, "abc123")

    widgets["join_button"].invoke()

    assert widgets["result"] == {"action": "join", "text": "abc123"}


def test_clicking_cancel_returns_none_action(root):
    widgets = _build_room_action_dialog(root)
    widgets["entry"].insert(0, "ignored")

    widgets["cancel_button"].invoke()

    assert widgets["result"]["action"] is None


def test_entry_text_is_stripped(root):
    widgets = _build_room_action_dialog(root)
    widgets["entry"].insert(0, "  padded  ")

    widgets["create_button"].invoke()

    assert widgets["result"]["text"] == "padded"
