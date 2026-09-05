"""Retrieve ranked concepts for given paths and record a tokens-per-turn metric."""

from __future__ import annotations

from pathlib import Path

from repocodex import ENGINE_VERSION
from repocodex.metrics import record_metric
from repocodex.retrieval import retrieve
from repocodex.schema import envelope


def context_for(repo: Path, paths: list[str], *, include_drafts: bool = False) -> dict:
    """Return retrieved concepts for ``paths`` plus a tokens-per-turn estimate.

    Drafts are omitted unless ``include_drafts``. Records a ``context`` metric
    with ``tokens_per_turn`` (body chars / 4) and the requested paths.

    Returns:
        Envelope merging retrieve keys ``paths``, ``concepts``, ``related``,
        and ``catalog`` with ``tokens_per_turn`` and ``engine_version``.

    """
    payload = retrieve(repo, paths, include_drafts=include_drafts)
    chars = sum(len(item.get("body") or "") for item in payload.get("concepts") or [])
    tokens_per_turn = chars / 4.0
    record_metric(repo, "context", {"tokens_per_turn": tokens_per_turn, "paths": list(paths)})
    return envelope({**payload, "tokens_per_turn": tokens_per_turn}, engine_version=ENGINE_VERSION)
