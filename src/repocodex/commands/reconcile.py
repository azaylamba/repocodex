"""Reanchor drifted concepts and rewrite memory through the attested write path."""

from __future__ import annotations

from pathlib import Path

from repocodex.commands.write import write_memory
from repocodex.metrics import record_metric
from repocodex.schema import envelope, parse_concept, serialize_concept
from repocodex.store.bundle import concept_path, discover_context_roots
from repocodex.store.reverse_index import regenerate_all


def apply_anchor_patch(repo: Path, patch: dict) -> Path:
    """Apply a ``replace_path`` patch to one concept anchor and regenerate indexes.

    Looks up ``patch["concept"]`` across context roots, updates
    ``anchors[anchor_index].path`` (and optional ``terms``), writes the
    concept, and records a ``reconcile`` metric with ``false_drift`` true.

    Returns:
        Absolute path of the rewritten concept file.

    Raises:
        FileNotFoundError: If the concept identity is not on disk.
        KeyError: If required patch keys are missing.
        IndexError: If ``anchor_index`` is out of range.

    """
    identity = patch["concept"]
    roots = discover_context_roots(repo)
    path = None
    for root in roots:
        candidate = concept_path(root, identity)
        if candidate.exists():
            path = candidate
            break
    if path is None:
        raise FileNotFoundError(identity)
    doc = parse_concept(path.read_text(encoding="utf-8"), identity)
    idx = int(patch["anchor_index"])
    if patch.get("op") == "replace_path":
        doc.anchors[idx].path = patch["to"]
        if patch.get("terms"):
            doc.anchors[idx].all_of = list(patch["terms"])
    path.write_text(serialize_concept(doc), encoding="utf-8")
    regenerate_all(repo)
    if patch.get("op") == "replace_path":
        record_metric(
            repo,
            "reconcile",
            {
                "concept": identity,
                "from": patch.get("from"),
                "to": patch.get("to"),
                "outcome": "reanchor",
                "false_drift": True,
            },
        )
    return path


def reconcile_memory(repo: Path, source: Path | str, *, identity: str | None = None) -> dict:
    """Write memory via :func:`write_memory` and mark the envelope as reconcile.

    Returns:
        The write envelope with ``mode`` set to ``reconcile``.

    """
    result = write_memory(repo, source, identity=identity)
    result["mode"] = "reconcile"
    return result
