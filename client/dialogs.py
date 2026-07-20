"""Native OS dialogs for the Rooms flow - a real Windows message box with a
text box and Create/Join/Cancel buttons, per the course spec ("Open a
windows message with text box and buttons: Create / Join / Cancel"),
replacing the earlier in-canvas RoomsScreen. Also used for the Play flow's
"no opponent found" popup (see client/main.py), so that's a real popup too
instead of inline screen text.
"""

import tkinter as tk
from tkinter import messagebox

from net import protocol

_POLL_INTERVAL_MS = 100


def _build_room_action_dialog(root) -> dict:
    """Builds the Create/Join/Cancel dialog's widgets onto root and returns
    handles to them - split out from prompt_room_action() so a test can
    drive it (type into the entry, .invoke() a button) without needing a
    real running mainloop."""
    result: dict = {"action": None, "text": ""}
    root.title("Room")

    tk.Label(root, text="room name / id").pack(padx=10, pady=(10, 0))
    entry = tk.Entry(root, width=30)
    entry.pack(padx=10, pady=10)
    entry.focus_set()

    def choose(action: str | None) -> None:
        result["action"] = action
        result["text"] = entry.get().strip()
        root.destroy()

    buttons = tk.Frame(root)
    buttons.pack(pady=(0, 10))
    create_button = tk.Button(buttons, text="Create", command=lambda: choose("create"))
    join_button = tk.Button(buttons, text="Join", command=lambda: choose("join"))
    cancel_button = tk.Button(buttons, text="Cancel", command=lambda: choose(None))
    create_button.pack(side="left", padx=5)
    join_button.pack(side="left", padx=5)
    cancel_button.pack(side="left", padx=5)
    root.protocol("WM_DELETE_WINDOW", lambda: choose(None))

    return {
        "result": result, "entry": entry,
        "create_button": create_button, "join_button": join_button, "cancel_button": cancel_button,
    }


def prompt_room_action() -> tuple[str, str] | None:
    """Blocks in a modal native dialog until Create, Join, or Cancel is
    clicked. Returns ("create"|"join", text) - text is the room name for
    Create, the room id for Join - or None if cancelled."""
    root = tk.Tk()
    widgets = _build_room_action_dialog(root)
    root.mainloop()
    action = widgets["result"]["action"]
    if action is None:
        return None
    return action, widgets["result"]["text"]


def show_info(title: str, message: str) -> None:
    """A literal native Windows message box."""
    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo(title, message)
    root.destroy()


def wait_for_room_match(client, room_id: str) -> dict | None:
    """A small "waiting for opponent" dialog with a Cancel button - polls
    client.recv_all() on a timer instead of blocking, so the dialog stays
    responsive to Cancel while an empty room waits (potentially
    indefinitely, unlike matchmaking's bounded wait) for a second player.
    Returns the game_start/error message once one arrives, or None if the
    user cancelled - which also sends cancel_room so the pending room
    doesn't linger server-side."""
    result: dict = {"message": None}
    root = tk.Tk()
    root.title("Room")
    tk.Label(root, text=f"Waiting for opponent...\nRoom ID: {room_id}").pack(padx=20, pady=20)

    def cancel() -> None:
        client.send(protocol.cancel_room(room_id))
        root.destroy()

    tk.Button(root, text="Cancel", command=cancel).pack(pady=(0, 10))
    root.protocol("WM_DELETE_WINDOW", cancel)

    def poll() -> None:
        for message in client.recv_all():
            if message["type"] in (protocol.GAME_START, protocol.ERROR):
                result["message"] = message
                root.destroy()
                return
        root.after(_POLL_INTERVAL_MS, poll)

    root.after(_POLL_INTERVAL_MS, poll)
    root.mainloop()
    return result["message"]
