from state.observer import Subject


def test_subscriber_receives_published_event():
    received = []
    subject = Subject()
    subject.subscribe(received.append)
    subject.publish("an event")
    assert received == ["an event"]


def test_multiple_subscribers_all_receive_the_event():
    first, second = [], []
    subject = Subject()
    subject.subscribe(first.append)
    subject.subscribe(second.append)
    subject.publish(42)
    assert first == [42]
    assert second == [42]


def test_no_subscribers_does_not_raise():
    Subject().publish("nobody is listening")


def test_subscribers_are_notified_in_subscribe_order():
    order = []
    subject = Subject()
    subject.subscribe(lambda e: order.append("first"))
    subject.subscribe(lambda e: order.append("second"))
    subject.publish(None)
    assert order == ["first", "second"]
