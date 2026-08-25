from __future__ import annotations

from pathlib import Path

from repocodex import ENGINE_VERSION
from repocodex.retrieval import retrieve
from repocodex.schema import envelope


def context_for(repo: Path, paths: list[str], *, include_drafts: bool = False) -> dict:
    payload = retrieve(repo, paths, include_drafts=include_drafts)
    return envelope(payload, engine_version=ENGINE_VERSION)
