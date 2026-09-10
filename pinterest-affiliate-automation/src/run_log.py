import json
from dataclasses import asdict
from datetime import date
from pathlib import Path

from src.models import PostResult


class RunLogger:
    def __init__(self, log_path: str | Path):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def record_run(self, run_date: date, results: list[PostResult]) -> None:
        with open(self.log_path, "a", encoding="utf-8") as f:
            for result in results:
                entry = {"date": run_date.isoformat(), **asdict(result)}
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
