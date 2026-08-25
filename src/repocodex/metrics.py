from __future__ import annotations

import json
import time
from pathlib import Path

from repocodex.schema import utc_now


def metrics_path(root: Path) -> Path:
    path = root / ".context" / "metrics.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def record_metric(root: Path, event: str, payload: dict) -> None:
    line = {"event": event, "at": utc_now(), **payload}
    with metrics_path(root).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(line) + "\n")


class Timer:
    def __init__(self) -> None:
        self.start = time.perf_counter()

    def ms(self) -> int:
        return int((time.perf_counter() - self.start) * 1000)
