from net import protocol
from shell_login import prompt_login


class FakeClient:
    def __init__(self):
        self.sent = []
        self._queue = []

    def send(self, message: dict) -> None:
        self.sent.append(message)

    def queue(self, message: dict) -> None:
        self._queue.append(message)

    def recv_one_blocking(self, timeout: float = 5.0) -> dict:
        return self._queue.pop(0)


def _input_fn(*answers):
    remaining = list(answers)

    def input_fn(_prompt: str) -> str:
        return remaining.pop(0)

    return input_fn


def test_sends_login_with_the_entered_username():
    client = FakeClient()
    client.queue(protocol.login_result(True, None, "alice", 1200))

    prompt_login(client, input_fn=_input_fn("alice"))

    assert client.sent == [protocol.login("alice")]


def test_returns_username_and_elo_from_the_login_result():
    client = FakeClient()
    client.queue(protocol.login_result(True, None, "alice", 1200))

    username, elo = prompt_login(client, input_fn=_input_fn("alice"))

    assert (username, elo) == ("alice", 1200)


def test_reprompts_until_a_non_empty_username_is_entered():
    client = FakeClient()
    client.queue(protocol.login_result(True, None, "bob", 1000))

    prompt_login(client, input_fn=_input_fn("", "   ", "bob"))

    assert client.sent == [protocol.login("bob")]
