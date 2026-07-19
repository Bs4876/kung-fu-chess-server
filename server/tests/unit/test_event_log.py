import json
from dataclasses import dataclass

from persistence.event_log import EventLogWriter


class FakePosition:
    def __init__(self, row, col):
        self.row = row
        self.col = col


@dataclass
class FakeArrived:
    source: FakePosition
    token: str


def test_writes_one_json_line_per_event(tmp_path):
    writer = EventLogWriter(tmp_path)
    writer(("game.1", FakeArrived(FakePosition(0, 2), "wR")))

    lines = (tmp_path / "1.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record == {
        "topic": "game.1",
        "event_type": "FakeArrived",
        "event": {"source": {"row": 0, "col": 2}, "token": "wR"},
    }


def test_appends_across_multiple_events_instead_of_overwriting(tmp_path):
    writer = EventLogWriter(tmp_path)
    writer(("game.1", "first"))
    writer(("game.1", "second"))

    lines = (tmp_path / "1.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2


def test_non_game_topic_logs_under_its_own_name_with_no_prefix_stripped(tmp_path):
    writer = EventLogWriter(tmp_path)
    writer(("system", "login"))

    assert (tmp_path / "system.jsonl").exists()


def test_creates_log_dir_if_missing(tmp_path):
    log_dir = tmp_path / "nested" / "logs"
    EventLogWriter(log_dir)
    assert log_dir.is_dir()
