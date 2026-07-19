import asyncio

from net.matchmaking import Matchmaking


class FakeUser:
    def __init__(self, username: str, elo: int):
        self.username = username
        self.elo = elo


class FakeSocket:
    async def send(self, text: str) -> None:
        pass


class FakeRoom:
    """Records join() calls in order - first is "white", second is "black",
    matching the real GameRoom's own convention closely enough for these
    pure queue/timing tests, without needing a real GameRoom."""

    def __init__(self):
        self.joined: list[tuple] = []

    def join(self, websocket, player=None) -> str:
        color = "white" if not self.joined else "black"
        self.joined.append((websocket, player))
        return color


class FakeClock:
    """A manually-advanced clock - lets a test simulate wait_ms elapsing
    without actually waiting real seconds for it."""

    def __init__(self, start: float = 0.0):
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def matchmaking_for(clock=None, elo_range: int = 100, tick_ms: int = 10, wait_ms: int = 1000):
    rooms: list[FakeRoom] = []

    def new_room() -> FakeRoom:
        room = FakeRoom()
        rooms.append(room)
        return room

    matchmaking = Matchmaking(
        new_room, clock=clock or FakeClock(),
        elo_range=elo_range, tick_ms=tick_ms, wait_ms=wait_ms,
    )
    return matchmaking, rooms


async def test_two_users_within_range_are_matched_into_the_same_room():
    matchmaking, rooms = matchmaking_for(tick_ms=10)
    matchmaking.start()
    try:
        alice, bob = FakeUser("alice", 1200), FakeUser("bob", 1250)
        alice_task = asyncio.create_task(matchmaking.play(FakeSocket(), alice))
        bob_task = asyncio.create_task(matchmaking.play(FakeSocket(), bob))

        alice_room = await asyncio.wait_for(alice_task, timeout=1)
        bob_room = await asyncio.wait_for(bob_task, timeout=1)

        assert alice_room is bob_room
        assert len(rooms) == 1
    finally:
        matchmaking.stop()


async def test_users_outside_range_are_not_matched_to_each_other():
    matchmaking, rooms = matchmaking_for(elo_range=100, tick_ms=10, wait_ms=10_000)
    matchmaking.start()
    try:
        alice, bob = FakeUser("alice", 1000), FakeUser("bob", 1500)
        alice_task = asyncio.create_task(matchmaking.play(FakeSocket(), alice))
        bob_task = asyncio.create_task(matchmaking.play(FakeSocket(), bob))
        await asyncio.sleep(0.05)  # let several ticks run

        assert not alice_task.done()
        assert not bob_task.done()
        assert rooms == []

        alice_task.cancel()
        bob_task.cancel()
    finally:
        matchmaking.stop()


async def test_a_lone_waiting_user_resolves_to_none_after_wait_ms_elapses():
    clock = FakeClock()
    matchmaking, rooms = matchmaking_for(clock=clock, tick_ms=10, wait_ms=1000)
    matchmaking.start()
    try:
        alice = FakeUser("alice", 1200)
        socket = FakeSocket()
        task = asyncio.create_task(matchmaking.play(socket, alice))
        await asyncio.sleep(0.02)  # let it register as waiting
        clock.advance(2)  # jump past wait_ms

        result = await asyncio.wait_for(task, timeout=1)

        assert result is None
        assert rooms == []
    finally:
        matchmaking.stop()


async def test_timeout_does_not_fire_before_wait_ms_elapses():
    clock = FakeClock()
    matchmaking, rooms = matchmaking_for(clock=clock, tick_ms=10, wait_ms=1000)
    matchmaking.start()
    try:
        task = asyncio.create_task(matchmaking.play(FakeSocket(), FakeUser("alice", 1200)))
        await asyncio.sleep(0.03)
        clock.advance(0.5)  # short of wait_ms(1000ms) = 1s
        await asyncio.sleep(0.03)

        assert not task.done()
        assert rooms == []
        task.cancel()
    finally:
        matchmaking.stop()


async def test_cancel_removes_a_still_waiting_entry():
    matchmaking, rooms = matchmaking_for(tick_ms=10, wait_ms=10_000)
    matchmaking.start()
    try:
        socket = FakeSocket()
        task = asyncio.create_task(matchmaking.play(socket, FakeUser("alice", 1200)))
        await asyncio.sleep(0.02)

        matchmaking.cancel(socket)
        await asyncio.sleep(0.05)

        assert not task.done()
        assert rooms == []
        task.cancel()
    finally:
        matchmaking.stop()
