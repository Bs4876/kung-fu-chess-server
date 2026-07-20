"""Pure login message handling: fetches an existing account by username or
creates one on the spot (no password - "just for presentation", per the
course spec), updates the connection's Session, and returns the wire
response.

No socket I/O here (see net/ws_server.py for where this gets called from a
real connection) - message-in, response-out, the same testing philosophy as
GameRoom's handle_request_move/handle_request_jump.
"""

from net import protocol
from net.session import Session
from persistence.users_repository import UsersRepository


def handle_login(message: dict, session: Session, users: UsersRepository) -> dict:
    username = message["username"]
    user = users.get_by_username(username) or users.create_user(username)
    session.user = user
    return protocol.login_result(True, None, user.username, user.elo)
