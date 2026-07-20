"""Console-only login prompt - per the course spec ("do it in a shell, not
via GUI"), replacing the earlier GUI LoginScreen. Runs before any window
exists: blocks the calling thread reading a username from stdin, then does
the login handshake (net/protocol.py's LOGIN/LOGIN_RESULT) over an
already-connected client.
"""

from net import protocol


def prompt_login(client, input_fn=input) -> tuple[str, int]:
    """client: a connected ws_client-shaped object (send(message)/
    recv_one_blocking()). input_fn: injectable for testing, defaults to the
    real builtin. Loops until a non-empty username is entered, then blocks
    for the server's login_result - handle_login always succeeds (creates
    the account on first login, per the "just for presentation" no-password
    spec), so there's no failure branch to loop on here."""
    username = ""
    while not username:
        username = input_fn("Username: ").strip()
    client.send(protocol.login(username))
    result = client.recv_one_blocking()
    return result["username"], result["elo"]
