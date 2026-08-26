from __future__ import annotations

from pathlib import Path

from repocodex.config import load_config
from repocodex.engine.gate import GateResult, evaluate_write
from repocodex.schema import (
    ConceptStatus,
    envelope,
    identity_from_path,
    parse_concept,
)
from repocodex.store.bundle import (
    concept_path,
    deprecate_concept,
    discover_context_roots,
    write_concept,
)
from repocodex.store.reverse_index import regenerate_all


def _context_root(repo: Path) -> Path:
    roots = discover_context_roots(repo)
    return roots[0] if roots else repo / ".context"


def _existing_concept_path(repo: Path, identity: str) -> Path | None:
    for root in discover_context_roots(repo):
        path = concept_path(root, identity)
        if path.exists():
            return path
    return None


def _why_change_rejected(existing: str | None, incoming, *, identity: str) -> str | None:
    if not existing:
        return None
    old = parse_concept(existing, identity)
    if old.status != ConceptStatus.stable:
        return None
    if incoming.frontmatter.supersedes and incoming.frontmatter.rationale:
        return None
    if old.body.strip() != incoming.body.strip() and identity == old.identity:
        if incoming.identity == old.identity and not incoming.frontmatter.supersedes:
            return "why_change_requires_supersedes"
    return None


def write_memory(
    repo: Path,
    source: Path | str,
    *,
    identity: str | None = None,
    stdin_text: str | None = None,
) -> dict:
    config = load_config(repo)
    if stdin_text is not None:
        text = stdin_text
        ident = identity or "untitled"
    else:
        path = Path(source)
        text = path.read_text(encoding="utf-8")
        if identity:
            ident = identity
        else:
            try:
                ident = identity_from_path(str(_context_root(repo)), str(path.resolve()))
            except Exception:
                ident = path.stem
    doc = parse_concept(text, ident)
    existing_path = _existing_concept_path(repo, ident)
    existing = existing_path.read_text(encoding="utf-8") if existing_path else None
    why_err = _why_change_rejected(existing, doc, identity=ident)
    if why_err:
        return envelope(
            {
                "accepted": False,
                "tighten": [why_err],
                "term_counts": {},
                "suggestions": ["supersede the predecessor and provide rationale"],
            }
        )

    if doc.frontmatter.supersedes:
        if not doc.frontmatter.rationale:
            return envelope(
                {
                    "accepted": False,
                    "tighten": ["rationale_required"],
                    "term_counts": {},
                    "suggestions": ["set rationale on why-change"],
                }
            )
        deprecate_concept(repo, doc.frontmatter.supersedes, reason=f"superseded by {ident}")

    if doc.anchors:
        gate = evaluate_write(doc, config)
    else:
        gate = GateResult(accepted=True)
    payload = envelope(gate.to_json())
    if not gate.accepted:
        return payload
    if doc.frontmatter.status == ConceptStatus.draft and not doc.frontmatter.stale_after:
        doc.frontmatter.status = ConceptStatus.stable
    shard = None
    if existing_path:
        for root in discover_context_roots(repo):
            if concept_path(root, ident) == existing_path:
                shard = root
                break
    written = write_concept(repo, doc, context_root=shard)
    regenerate_all(repo)
    payload["identity"] = ident
    payload["path"] = str(written.relative_to(repo))
    return payload
