import json
from datetime import date

from src.models import PostResult
from src.run_log import RunLogger


def test_record_run_writes_jsonl_entry_per_result(tmp_path):
    log_path = tmp_path / "run_log.jsonl"
    logger = RunLogger(log_path)
    result = PostResult(
        product_id="p1", language="ja", board_id="b1", pin_id="pin1", status="posted", detail="ok"
    )
    logger.record_run(date(2026, 9, 10), [result])

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["product_id"] == "p1"
    assert entry["date"] == "2026-09-10"
    assert entry["status"] == "posted"


def test_record_run_appends_across_calls(tmp_path):
    log_path = tmp_path / "run_log.jsonl"
    logger = RunLogger(log_path)
    result = PostResult(
        product_id="p1", language="ja", board_id="b1", pin_id="pin1", status="posted", detail="ok"
    )
    logger.record_run(date(2026, 9, 10), [result])
    logger.record_run(date(2026, 9, 11), [result])
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
