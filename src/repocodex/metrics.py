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


def read_metrics(root: Path) -> list[dict]:
    path = metrics_path(root)
    if not path.is_file():
        return []
    events: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def false_drift_rate(root: Path) -> float:
    """Share of DRIFT events later shown false by a reanchor reconcile, over the recorded window."""
    drifts = 0
    false = 0
    for event in read_metrics(root):
        if event.get("event") == "drift":
            drifts += 1
        elif event.get("event") == "reconcile" and event.get("false_drift"):
            false += 1
    if drifts == 0:
        return 0.0
    return min(1.0, false / drifts)


class Timer:
    def __init__(self) -> None:
        self.start = __import__("time").perf_counter()

    def ms(self) -> int:
        return int((__import__("time").perf_counter() - self.start) * 1000)
