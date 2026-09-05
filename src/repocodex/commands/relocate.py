"""Move concepts whose identity prefix does not match their authored type."""

from __future__ import annotations

from pathlib import Path

from repocodex.engine.gate import (
    identity_prefix_ok,
    suggested_identity,
)
from repocodex.schema import envelope, parse_concept, type_str
from repocodex.store.bundle import (
    append_log,
    concept_path,
    discover_context_roots,
    load_concepts,
    update_catalog,
)
from repocodex.store.reverse_index import regenerate_all


def _find_concept(repo: Path, identity: str) -> tuple[Path, Path] | None:
    """Return (context_root, file_path) for identity, if present."""
    for root in discover_context_roots(repo):
        path = concept_path(root, identity)
        if path.exists():
            return root, path
    return None


def _remove_catalog_link(context_root: Path, identity: str) -> None:
    """Drop the old catalog index line that pointed at this identity."""
    directory = (context_root / identity).parent
    index_path = directory / "index.md"
    if not index_path.exists():
        return
    leaf = Path(identity).name
    lines = index_path.read_text(encoding="utf-8").splitlines(keepends=True)
    kept = [line for line in lines if f"](./{leaf}.md)" not in line and f"]({leaf}.md)" not in line]
    if kept != lines:
        index_path.write_text("".join(kept), encoding="utf-8")


def relocate_memory(
    repo: Path,
    identity: str | None = None,
    *,
    mismatched: bool = False,
) -> dict:
    """Move one concept, or every prefix-mismatched concept, to the typed prefix.

    Requires ``mismatched`` or a specific ``identity``. Already-correct
    prefixes, unknown types, missing files, and occupied targets are skipped.
    Successful moves update the catalog, append a relocate log line, and
    regenerate the reverse index.

    Returns:
        Envelope with ``moved`` (``from``, ``to``, ``path``) and ``skipped``
        (``identity``, ``reason``). Skip reasons include ``not_found``,
        ``identity_or_mismatched_required``, ``not_mismatched``,
        ``unknown_type``, and ``target_exists``.

    """
    moved: list[dict] = []
    skipped: list[dict] = []

    if mismatched:
        targets = [
            doc
            for doc in load_concepts(repo)
            if not identity_prefix_ok(doc.frontmatter.type, doc.identity)
        ]
    elif identity:
        found = _find_concept(repo, identity)
        if found is None:
            return envelope(
                {
                    "moved": [],
                    "skipped": [{"identity": identity, "reason": "not_found"}],
                }
            )
        root, path = found
        doc = parse_concept(path.read_text(encoding="utf-8"), identity)
        targets = [doc]
    else:
        return envelope(
            {
                "moved": [],
                "skipped": [{"identity": None, "reason": "identity_or_mismatched_required"}],
            }
        )

    for doc in targets:
        if identity_prefix_ok(doc.frontmatter.type, doc.identity):
            skipped.append({"identity": doc.identity, "reason": "not_mismatched"})
            continue
        suggested = suggested_identity(doc.frontmatter.type, doc.identity)
        if suggested is None:
            skipped.append({"identity": doc.identity, "reason": "unknown_type"})
            continue
        located = _find_concept(repo, doc.identity)
        if located is None:
            skipped.append({"identity": doc.identity, "reason": "not_found"})
            continue
        root, src = located
        dest = concept_path(root, suggested)
        if dest.exists():
            skipped.append({"identity": doc.identity, "reason": "target_exists"})
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        text = src.read_text(encoding="utf-8")
        src.unlink()
        _remove_catalog_link(root, doc.identity)
        dest.write_text(text, encoding="utf-8")
        relocated = parse_concept(text, suggested)
        update_catalog(root, relocated)
        append_log(
            root,
            f"relocated {doc.identity} -> {suggested} ({type_str(doc.frontmatter.type)})",
        )
        moved.append(
            {
                "from": doc.identity,
                "to": suggested,
                "path": str(dest.relative_to(repo)),
            }
        )

    if moved:
        regenerate_all(repo)
    return envelope({"moved": moved, "skipped": skipped})
