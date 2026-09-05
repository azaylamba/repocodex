"""Classify each concept anchor as live, weak, reanchorable, or drifted."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from repocodex.config import RepoConfig
from repocodex.engine.match import (
    evaluate_file,
    literal_as_token,
    min_match_for,
    read_pinned,
    resolve_claim_owner,
)
from repocodex.engine.relocate import relocate_anchor
from repocodex.schema import Anchor, ConceptDocument, ConceptStatus


LIVE = "LIVE"
WEAK = "WEAK"
REANCHOR = "REANCHOR"
DRIFT = "DRIFT"
CLAIM_BROKEN = "CLAIM_BROKEN"


@dataclass
class AnchorOutcome:
    """Per-anchor liveness classification and optional reanchor patch."""

    concept: str
    anchor_index: int
    path: str
    classification: str
    reason: str
    hits: int
    required: int
    patch: dict | None = None
    candidates: list[dict] | None = None

    def to_json(self) -> dict:
        """Return this outcome as a JSON-serializable dict."""
        payload = {
            "concept": self.concept,
            "anchor": self.anchor_index,
            "path": self.path,
            "classification": self.classification,
            "reason": self.reason,
            "hits": self.hits,
            "required": self.required,
        }
        if self.patch:
            payload["patch"] = self.patch
        if self.candidates:
            payload["candidates"] = self.candidates
        return payload


@dataclass
class ClaimFinding:
    """A claim literal that is no longer present in its owning region."""

    concept: str
    literal: str
    classification: str = CLAIM_BROKEN
    anchor_classification: str | None = None
    path: str | None = None

    def to_json(self) -> dict:
        """Return this finding as a JSON-serializable dict."""
        payload = {
            "concept": self.concept,
            "literal": self.literal,
            "classification": self.classification,
        }
        if self.anchor_classification:
            payload["anchor_classification"] = self.anchor_classification
        if self.path:
            payload["path"] = self.path
        return payload


def classify_anchor(
    doc: ConceptDocument,
    index: int,
    anchor: Anchor,
    config: RepoConfig,
    *,
    staged: bool = False,
    base: str | None = None,
) -> AnchorOutcome:
    """Classify one anchor as LIVE, WEAK, REANCHOR, or DRIFT.

    LIVE meets ``min_match``; WEAK has a partial hit; REANCHOR has a unique
    relocation candidate; otherwise DRIFT with any remaining candidates.
    """
    matched = evaluate_file(anchor, config.root, default_scope=config.scope_lines)
    required = min_match_for(anchor)
    hits = matched.hits_for_best()
    if hits >= required:
        return AnchorOutcome(
            concept=doc.identity,
            anchor_index=index,
            path=anchor.path,
            classification=LIVE,
            reason="min_match",
            hits=hits,
            required=required,
        )
    if hits > 0:
        return AnchorOutcome(
            concept=doc.identity,
            anchor_index=index,
            path=anchor.path,
            classification=WEAK,
            reason="partial_term_loss",
            hits=hits,
            required=required,
        )

    relocation = relocate_anchor(anchor, config, staged=staged, base=base)
    if relocation.unique:
        candidate = relocation.candidates[0]
        return AnchorOutcome(
            concept=doc.identity,
            anchor_index=index,
            path=anchor.path,
            classification=REANCHOR,
            reason=relocation.via,
            hits=0,
            required=required,
            patch={
                "concept": doc.identity,
                "anchor_index": index,
                "op": "replace_path",
                "from": anchor.path,
                "to": candidate["path"],
                "terms": list(anchor.all_of),
                "actor": "process:repocodex-reanchor",
            },
        )
    return AnchorOutcome(
        concept=doc.identity,
        anchor_index=index,
        path=anchor.path,
        classification=DRIFT,
        reason="full_miss",
        hits=0,
        required=required,
        candidates=relocation.candidates,
    )


def evaluate_claims(
    doc: ConceptDocument,
    config: RepoConfig,
    *,
    anchor_class: str | None = None,
) -> list[ClaimFinding]:
    """Return CLAIM_BROKEN findings for stable concepts whose literals left the region.

    Draft or claim-less documents yield an empty list. ``anchor_class`` is
    copied onto each finding when provided.
    """
    if doc.status != ConceptStatus.stable or not doc.frontmatter.claims:
        return []
    findings: list[ClaimFinding] = []
    for claim in doc.frontmatter.claims:
        owner, error = resolve_claim_owner(claim, doc.anchors)
        if owner is None:
            findings.append(
                ClaimFinding(
                    concept=doc.identity,
                    literal=claim.literal,
                    anchor_classification=anchor_class,
                    path=None,
                )
            )
            continue
        anchor = doc.anchors[owner]
        text = read_pinned(config.root, anchor.path)
        if text is None:
            findings.append(
                ClaimFinding(
                    concept=doc.identity,
                    literal=claim.literal,
                    anchor_classification=anchor_class,
                    path=anchor.path,
                )
            )
            continue
        matched = evaluate_file(anchor, config.root, default_scope=config.scope_lines)
        region_text = matched.best.source(text.splitlines()) if matched.best else None
        if region_text is None or not literal_as_token(claim.literal, region_text):
            findings.append(
                ClaimFinding(
                    concept=doc.identity,
                    literal=claim.literal,
                    anchor_classification=anchor_class,
                    path=anchor.path,
                )
            )
    return findings
