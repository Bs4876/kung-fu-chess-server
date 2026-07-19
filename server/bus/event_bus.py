"""Topic-based publish/subscribe bus, built on the generic Subject primitive."""

from engine.observer import Subject


class EventBus:
    """Routes each published event to that topic's subscribers, plus every
    wildcard subscriber (subscribe_all) regardless of topic - e.g. a single
    durable write-log that records everything without knowing every topic."""

    def __init__(self):
        self._topics: dict[str, Subject] = {}
        self._wildcard = Subject()

    def subscribe(self, topic: str, callback) -> None:
        self._topic(topic).subscribe(callback)

    def subscribe_all(self, callback) -> None:
        self._wildcard.subscribe(callback)

    def publish(self, topic: str, event) -> None:
        self._topic(topic).publish(event)
        self._wildcard.publish((topic, event))

    def _topic(self, topic: str) -> Subject:
        return self._topics.setdefault(topic, Subject())
