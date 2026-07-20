from bus.event_bus import EventBus
from net.game_room import GameEnded
from persistence.db import connect
from persistence.elo import update_ratings
from persistence.elo_updater import EloUpdater
from persistence.users_repository import UsersRepository


def users_for(tmp_path) -> UsersRepository:
    return UsersRepository(connect(tmp_path / "test.db"))


def test_updates_both_players_elo_when_the_game_had_a_winner(tmp_path):
    users = users_for(tmp_path)
    white = users.create_user("alice")
    black = users.create_user("bob")
    bus = EventBus()
    bus.subscribe_all(EloUpdater(users))

    bus.publish("game.1", GameEnded(game_id="1", white_player=white, black_player=black, winner="white"))

    expected_white, expected_black = update_ratings(white.elo, black.elo, score_a=1.0)
    assert users.get_by_username("alice").elo == expected_white
    assert users.get_by_username("bob").elo == expected_black


def test_ignores_events_that_are_not_game_ended(tmp_path):
    users = users_for(tmp_path)
    white = users.create_user("alice")
    bus = EventBus()
    bus.subscribe_all(EloUpdater(users))

    bus.publish("game.1", "not a GameEnded event")

    assert users.get_by_username("alice").elo == white.elo


def test_ignores_a_game_where_one_side_had_no_authenticated_player(tmp_path):
    users = users_for(tmp_path)
    white = users.create_user("alice")
    bus = EventBus()
    bus.subscribe_all(EloUpdater(users))

    bus.publish("game.1", GameEnded(game_id="1", white_player=white, black_player=None, winner="white"))

    assert users.get_by_username("alice").elo == white.elo


def test_a_draw_moves_both_toward_each_other_via_the_0_5_score(tmp_path):
    users = users_for(tmp_path)
    white = users.create_user("alice")  # DEFAULT_ELO
    black = users.create_user("bob")
    users.update_elo("bob", black.elo + 200)
    black.elo += 200
    bus = EventBus()
    bus.subscribe_all(EloUpdater(users))

    bus.publish("game.1", GameEnded(game_id="1", white_player=white, black_player=black, winner=None))

    expected_white, expected_black = update_ratings(white.elo, black.elo, score_a=0.5)
    assert users.get_by_username("alice").elo == expected_white
    assert users.get_by_username("bob").elo == expected_black
