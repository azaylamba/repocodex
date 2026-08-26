from __future__ import annotations

from pathlib import Path

from repocodex.commands.write import write_memory
from repocodex.metrics import record_metric
from repocodex.schema import envelope, parse_concept, serialize_concept, stamp
from repocodex.store.bundle import concept_path, discover_context_roots
from repocodex.store.reverse_index import regenerate_all


def apply_anchor_patch(repo: Path, patch: dict) -> Path:
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
        doc.frontmatter.verified = stamp("process:repocodex-reanchor")
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
    result = write_memory(repo, source, identity=identity)
    result["mode"] = "reconcile"
    return result
