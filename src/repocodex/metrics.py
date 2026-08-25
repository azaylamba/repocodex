from __future__ import annotations

import json
import os
from pathlib import Path

from repocodex.schema import utc_now


DEFAULT_METRICS_REL = ".repocodex/metrics.jsonl"


def metrics_path(root: Path) -> Path:
    override = os.environ.get("REPOCODEX_METRICS_SINK")
    if override:
        path = Path(override)
        if not path.is_absolute():
            path = root / path
    else:
        path = root / DEFAULT_METRICS_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def record_metric(root: Path, event: str, payload: dict) -> None:
    line = {"event": event, "at": utc_now(), **payload}
    with metrics_path(root).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(line) + "\n")


class Timer:
    def __init__(self) -> None:
        self.start = __import__("time").perf_counter()

    def ms(self) -> int:
        return int((__import__("time").perf_counter() - self.start) * 1000)
