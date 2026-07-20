from config import DEFAULT_ELO
from net import protocol
from net.auth import handle_login
from net.session import Session
from persistence.db import connect
from persistence.users_repository import UsersRepository


def users_for(tmp_path) -> UsersRepository:
    return UsersRepository(connect(tmp_path / "test.db"))


def test_login_with_an_unknown_username_creates_a_new_account_and_authenticates(tmp_path):
    users = users_for(tmp_path)
    session = Session()

    response = handle_login({"username": "alice"}, session, users)

    assert response == {
        "type": protocol.LOGIN_RESULT, "success": True, "reason": None,
        "username": "alice", "elo": DEFAULT_ELO,
    }
    assert session.is_authenticated
    assert session.user.username == "alice"


def test_login_with_a_known_username_returns_its_existing_elo_unchanged(tmp_path):
    users = users_for(tmp_path)
    handle_login({"username": "alice"}, Session(), users)
    users.update_elo("alice", 1350)

    session = Session()
    response = handle_login({"username": "alice"}, session, users)

    assert response["success"] is True
    assert response["username"] == "alice"
    assert response["elo"] == 1350
    assert session.user.username == "alice"


def test_logging_in_as_the_same_username_twice_does_not_create_a_second_account(tmp_path):
    users = users_for(tmp_path)
    first_session, second_session = Session(), Session()
    handle_login({"username": "alice"}, first_session, users)
    handle_login({"username": "alice"}, second_session, users)

    assert first_session.user.id == second_session.user.id
