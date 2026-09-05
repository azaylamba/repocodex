"""Sample stable concepts for out-of-band screening and retire orphan or expired drafts."""

from __future__ import annotations

import json
import random
from datetime import date, datetime, timezone
from pathlib import Path

from repocodex.config import load_config
from repocodex.engine.contradiction import contradiction_flags
from repocodex.engine.gate import _term_count
from repocodex.engine.match import evaluate_file, read_pinned
from repocodex.schema import ConceptStatus, envelope, utc_now
from repocodex.store.bundle import deprecate_concept, load_concepts
from repocodex.store.reverse_index import merged_index


def _expired(stale_after: str | None) -> bool:
    """Return True when ``stale_after`` parses as a UTC date already past."""
    if not stale_after:
        return False
    try:
        return date.fromisoformat(stale_after[:10]) < datetime.now(timezone.utc).date()
    except ValueError:
        return False


def gc(repo: Path) -> list[str]:
    """Deprecate orphan concepts and expired drafts.

    A concept is retired when nothing inbound-links it and no anchor still
    matches, or when it is a draft past ``stale_after``. Deprecation uses
    reason ``gc``.

    Returns:
        Identities that were deprecated.

    """
    retired: list[str] = []
    concepts = load_concepts(repo)
    inbound: set[str] = set()
    from repocodex.engine.impact import linked_identities

    for doc in concepts:
        inbound.update(linked_identities(doc))
    for doc in concepts:
        live_anchor = False
        for anchor in doc.anchors:
            matched = evaluate_file(anchor, repo)
            if matched.hits_for_best() > 0:
                live_anchor = True
                break
        orphan = doc.identity not in inbound and not live_anchor
        expired_draft = doc.status == ConceptStatus.draft and _expired(doc.frontmatter.stale_after)
        if orphan or expired_draft:
            deprecate_concept(repo, doc.identity, reason="gc")
            retired.append(doc.identity)
    return retired


def audit(
    repo: Path,
    *,
    sample_size: int | None = None,
    seed: int = 0,
    findings_path: Path | None = None,
) -> dict:
    """Emit a screening payload for out-of-band review; never invoke a model.

    Samples stable concepts (all of them when the set is at most ``n``),
    scores term distinctiveness, flags contradictions, and runs :func:`gc`.
    Optional ``findings_path`` JSON (a list, or ``findings`` / ``results``)
    becomes ``CONTRADICTION`` proposals for the attested-write path.

    Returns:
        Envelope with ``sampled``, ``distinctiveness``, ``weak_anchors``,
        ``contradictions``, ``contradiction_proposals``, ``gc_deprecated``,
        ``screening``, ``model_invoked`` always ``False``, ``note``, and
        ``at``.

    """
    config = load_config(repo)
    concepts = [doc for doc in load_concepts(repo) if doc.status == ConceptStatus.stable]
    n = sample_size or config.audit_sample_size
    rng = random.Random(seed)
    sample = concepts if len(concepts) <= n else rng.sample(concepts, n)
    scored = []
    weak = []
    screening = []
    for doc in sample:
        term_counts: dict[str, int] = {}
        for anchor in doc.anchors:
            for term in anchor.all_of:
                term_counts[term] = _term_count(term, config)
            distinctive = any(
                count < config.distinctiveness_ceiling for count in term_counts.values()
            )
            if not distinctive:
                weak.append(doc.identity)
            region = ""
            text = read_pinned(repo, anchor.path)
            if text:
                matched = evaluate_file(anchor, repo, default_scope=config.scope_lines)
                if matched.best:
                    region = matched.best.source(text.splitlines())
            screening.append(
                {
                    "identity": doc.identity,
                    "title": doc.frontmatter.title,
                    "body": doc.body,
                    "pinned_region": region,
                    "term_counts": term_counts,
                }
            )
        scored.append({"identity": doc.identity, "term_counts": term_counts})
    contradictions = contradiction_flags(load_concepts(repo), repo)
    retired = gc(repo)
    proposals: list[dict] = []
    if findings_path:
        data = json.loads(Path(findings_path).read_text(encoding="utf-8"))
        items = data if isinstance(data, list) else data.get("findings") or data.get("results") or []
        for item in items:
            identity = item.get("identity") or item.get("concept")
            if not identity:
                continue
            proposals.append(
                {
                    "kind": "CONTRADICTION",
                    "reason": "audit_screening",
                    "concept": identity,
                    "proposal": True,
                    "detail": item,
                }
            )
    return envelope(
        {
            "sampled": [doc.identity for doc in sample],
            "distinctiveness": scored,
            "weak_anchors": weak,
            "contradictions": contradictions,
            "contradiction_proposals": proposals,
            "gc_deprecated": retired,
            "screening": screening,
            "model_invoked": False,
            "note": (
                "repocodex audit emits a screening payload for out-of-band model review; "
                "no model is invoked inside the engine. Returned findings become CONTRADICTION "
                "proposals resolved through the attested-write path, never automatic edits."
            ),
            "at": utc_now(),
        }
    )
