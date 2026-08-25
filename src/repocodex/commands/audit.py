from __future__ import annotations

import random
from datetime import date, datetime, timezone
from pathlib import Path

from repocodex.config import load_config
from repocodex.engine.contradiction import contradiction_flags
from repocodex.engine.gate import _term_count
from repocodex.engine.match import evaluate_file, read_pinned
from repocodex.schema import ConceptStatus, envelope, utc_now
from repocodex.store.bundle import append_log, deprecate_concept, discover_context_roots, load_concepts
from repocodex.store.reverse_index import merged_index


def _expired(stale_after: str | None) -> bool:
    if not stale_after:
        return False
    try:
        return date.fromisoformat(stale_after[:10]) < datetime.now(timezone.utc).date()
    except ValueError:
        return False


def gc(repo: Path) -> list[str]:
    retired: list[str] = []
    concepts = load_concepts(repo)
    index = merged_index(repo)
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


def audit(repo: Path, *, sample_size: int | None = None, seed: int = 0) -> dict:
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
    roots = discover_context_roots(repo)
    if roots:
        append_log(roots[0], f"audit sampled {len(sample)} concepts")
    return envelope(
        {
            "sampled": [doc.identity for doc in sample],
            "distinctiveness": scored,
            "weak_anchors": weak,
            "contradictions": contradictions,
            "gc_deprecated": retired,
            "screening": screening,
            "note": "model screening is advisory; findings become CONTRADICTION proposals only",
            "at": utc_now(),
        }
    )
