"""Durable audit trail: one JSONL file per topic, appended to as events arrive."""

import json
from pathlib import Path

from config import GAME_LOG_DIR


class EventLogWriter:
    """A bus wildcard subscriber (see EventBus.subscribe_all) that appends every
    (topic, event) it receives as one JSON line, flushing immediately so a
    crash mid-game never loses an already-published event."""

    def __init__(self, log_dir: Path = GAME_LOG_DIR):
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)

    def __call__(self, topic_and_event: tuple) -> None:
        topic, event = topic_and_event
        record = {"topic": topic, "event_type": type(event).__name__, "event": self._serialize(event)}
        with self._log_path(topic).open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    def _log_path(self, topic: str) -> Path:
        # "game.<id>" logs to "<id>.jsonl"; anything else (e.g. "system") logs as-is.
        game_id = topic.removeprefix("game.")
        return self._log_dir / f"{game_id}.jsonl"

    @classmethod
    def _serialize(cls, value):
        """Recursively turn dataclasses/position-like objects into JSON-safe values."""
        if isinstance(value, dict):
            return {key: cls._serialize(val) for key, val in value.items()}
        if isinstance(value, (list, tuple)):
            return [cls._serialize(val) for val in value]
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if hasattr(value, "row") and hasattr(value, "col"):
            return {"row": value.row, "col": value.col}
        if hasattr(value, "__dict__"):
            return {key: cls._serialize(val) for key, val in vars(value).items()}
        return str(value)
