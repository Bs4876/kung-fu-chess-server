from bus.event_bus import EventBus


def test_topic_subscriber_receives_only_that_topics_events():
    received = []
    bus = EventBus()
    bus.subscribe("game.1", received.append)
    bus.publish("game.1", "arrived")
    bus.publish("game.2", "ignored")
    assert received == ["arrived"]


def test_wildcard_subscriber_receives_every_topics_events():
    received = []
    bus = EventBus()
    bus.subscribe_all(received.append)
    bus.publish("system", "login")
    bus.publish("game.1", "arrived")
    assert received == [("system", "login"), ("game.1", "arrived")]


def test_topic_and_wildcard_subscribers_both_fire_for_the_same_event():
    topic_received, wildcard_received = [], []
    bus = EventBus()
    bus.subscribe("game.1", topic_received.append)
    bus.subscribe_all(wildcard_received.append)
    bus.publish("game.1", "arrived")
    assert topic_received == ["arrived"]
    assert wildcard_received == [("game.1", "arrived")]


def test_publishing_to_a_topic_with_no_subscribers_does_not_raise():
    EventBus().publish("game.1", "arrived")


def test_subscribers_are_notified_in_subscribe_order():
    order = []
    bus = EventBus()
    bus.subscribe("game.1", lambda e: order.append("first"))
    bus.subscribe("game.1", lambda e: order.append("second"))
    bus.publish("game.1", None)
    assert order == ["first", "second"]
