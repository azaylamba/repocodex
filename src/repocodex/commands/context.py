from __future__ import annotations

from pathlib import Path

from repocodex import ENGINE_VERSION
from repocodex.metrics import record_metric
from repocodex.retrieval import retrieve
from repocodex.schema import envelope


def context_for(repo: Path, paths: list[str], *, include_drafts: bool = False) -> dict:
    payload = retrieve(repo, paths, include_drafts=include_drafts)
    chars = sum(len(item.get("body") or "") for item in payload.get("concepts") or [])
    tokens_per_turn = chars / 4.0
    record_metric(repo, "context", {"tokens_per_turn": tokens_per_turn, "paths": list(paths)})
    return envelope({**payload, "tokens_per_turn": tokens_per_turn}, engine_version=ENGINE_VERSION)
