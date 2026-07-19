import asyncio

from bus.event_bus import EventBus
from model.board import Board
from net.anonymous_lobby import AnonymousLobby


class FakeSocket:
    def __init__(self):
        self.sent = []

    async def send(self, text):
        self.sent.append(text)


def make_board():
    return Board([["wR", "."], [".", "bK"]])


async def test_first_connection_waits_until_a_second_one_arrives():
    lobby = AnonymousLobby(EventBus(), make_board)
    first_task = asyncio.create_task(lobby.join(FakeSocket()))
    await asyncio.sleep(0)  # let first_task actually start waiting on its future
    assert not first_task.done()

    room = await lobby.join(FakeSocket())
    assert await first_task is room


async def test_paired_sockets_get_different_colors_in_the_same_room():
    lobby = AnonymousLobby(EventBus(), make_board)
    first_socket, second_socket = FakeSocket(), FakeSocket()
    first_task = asyncio.create_task(lobby.join(first_socket))
    await asyncio.sleep(0)
    room = await lobby.join(second_socket)
    await first_task

    assert {room.color_of(first_socket), room.color_of(second_socket)} == {"white", "black"}


async def test_a_third_and_fourth_connection_form_a_separate_room():
    lobby = AnonymousLobby(EventBus(), make_board)
    first_task = asyncio.create_task(lobby.join(FakeSocket()))
    await asyncio.sleep(0)
    first_room = await lobby.join(FakeSocket())
    await first_task

    third_task = asyncio.create_task(lobby.join(FakeSocket()))
    await asyncio.sleep(0)
    second_room = await lobby.join(FakeSocket())
    await third_task

    assert first_room.game_id != second_room.game_id
    first_room.stop()
    second_room.stop()


async def test_room_is_already_ticking_once_a_pair_completes():
    lobby = AnonymousLobby(EventBus(), make_board)
    first_task = asyncio.create_task(lobby.join(FakeSocket()))
    await asyncio.sleep(0)
    room = await lobby.join(FakeSocket())
    await first_task

    assert room._tick_task is not None
    room.stop()
