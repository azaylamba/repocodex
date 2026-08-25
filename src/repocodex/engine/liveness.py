from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from repocodex.config import RepoConfig
from repocodex.engine.match import evaluate_file, min_match_for
from repocodex.engine.relocate import relocate_anchor
from repocodex.schema import Anchor, ConceptDocument


LIVE = "LIVE"
WEAK = "WEAK"
REANCHOR = "REANCHOR"
DRIFT = "DRIFT"


@dataclass
class AnchorOutcome:
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


def classify_anchor(
    doc: ConceptDocument,
    index: int,
    anchor: Anchor,
    config: RepoConfig,
    *,
    diff_files: list[str] | None = None,
) -> AnchorOutcome:
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

    relocation = relocate_anchor(anchor, config, diff_files=diff_files)
    if relocation.unique:
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
                "to": relocation.candidates[0]["path"],
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
