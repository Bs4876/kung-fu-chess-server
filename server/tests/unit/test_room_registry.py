import asyncio

from net.room_registry import RoomRegistry


class FakeSocket:
    async def send(self, text: str) -> None:
        pass


class FakeUser:
    def __init__(self, username: str):
        self.username = username


class FakeRoom:
    def __init__(self):
        self.joined: list[tuple] = []

    def join(self, websocket, player=None) -> str:
        color = "white" if not self.joined else "black"
        self.joined.append((websocket, player))
        return color


def registry_for():
    rooms: list[FakeRoom] = []

    def new_room() -> FakeRoom:
        room = FakeRoom()
        rooms.append(room)
        return room

    return RoomRegistry(new_room), rooms


async def test_create_room_lists_it_with_one_occupant():
    registry, _rooms = registry_for()
    room_id = registry.create_room("Alice's room", FakeSocket(), FakeUser("alice"))
    assert registry.list_rooms() == [{"id": room_id, "name": "Alice's room", "occupants": 1, "capacity": 2}]


async def test_join_room_seats_the_second_occupant_and_starts_a_game_room():
    registry, rooms = registry_for()
    creator_socket, joiner_socket = FakeSocket(), FakeSocket()
    alice, bob = FakeUser("alice"), FakeUser("bob")
    room_id = registry.create_room("Alice's room", creator_socket, alice)

    game_room = registry.join_room(room_id, joiner_socket, bob)

    assert game_room is rooms[0]
    assert game_room.joined == [(creator_socket, alice), (joiner_socket, bob)]


async def test_joined_room_no_longer_appears_in_the_list():
    registry, _rooms = registry_for()
    room_id = registry.create_room("Alice's room", FakeSocket(), FakeUser("alice"))
    registry.join_room(room_id, FakeSocket(), FakeUser("bob"))
    assert registry.list_rooms() == []


async def test_join_room_with_an_unknown_id_returns_none():
    registry, _rooms = registry_for()
    assert registry.join_room("no-such-room", FakeSocket(), FakeUser("bob")) is None


async def test_join_room_resolves_await_join_with_the_same_game_room():
    registry, _rooms = registry_for()
    room_id = registry.create_room("Alice's room", FakeSocket(), FakeUser("alice"))
    wait_task = asyncio.create_task(registry.await_join(room_id))
    await asyncio.sleep(0)  # let wait_task start awaiting the future

    game_room = registry.join_room(room_id, FakeSocket(), FakeUser("bob"))
    resolved = await asyncio.wait_for(wait_task, timeout=1)

    assert resolved is game_room


async def test_cancel_room_by_its_creator_removes_it():
    registry, _rooms = registry_for()
    creator_socket = FakeSocket()
    room_id = registry.create_room("Alice's room", creator_socket, FakeUser("alice"))

    assert registry.cancel_room(room_id, creator_socket) is True
    assert registry.list_rooms() == []


async def test_cancel_room_by_someone_else_does_nothing():
    registry, _rooms = registry_for()
    room_id = registry.create_room("Alice's room", FakeSocket(), FakeUser("alice"))

    assert registry.cancel_room(room_id, FakeSocket()) is False
    assert len(registry.list_rooms()) == 1


def test_cancel_room_with_an_unknown_id_returns_false():
    registry, _rooms = registry_for()
    assert registry.cancel_room("no-such-room", FakeSocket()) is False


async def test_room_ids_are_unique_across_creations():
    registry, _rooms = registry_for()
    first = registry.create_room("Room A", FakeSocket(), FakeUser("alice"))
    second = registry.create_room("Room B", FakeSocket(), FakeUser("bob"))
    assert first != second
