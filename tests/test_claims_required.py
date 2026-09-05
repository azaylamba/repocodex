"""Pin write-gate claims requirements by concept type.

InvariantContract must declare claims, including unanchored invariants.
TechnicalDecision may omit claims and still pass the gate.
"""

from __future__ import annotations

from repocodex.commands.write import write_memory
from repocodex.config import load_config
from repocodex.engine.gate import evaluate_write
from repocodex.schema import parse_concept
from tests.fixtures.repos import GRACE_CONCEPT, STREAMER_CONCEPT


def test_invariant_without_claims_rejected(repo):
    text = GRACE_CONCEPT.replace(
        "claims:\n  - literal: \"3\"\n  - literal: \"ENTERPRISE\"\n",
        "",
    )
    doc = parse_concept(text, "invariants/enterprise-grace-period")
    assert not doc.frontmatter.claims
    result = evaluate_write(doc, load_config(repo.root))
    assert result.accepted is False
    assert "claims_required" in result.tighten


def test_invariant_with_empty_claims_rejected(repo):
    text = GRACE_CONCEPT.replace(
        "claims:\n  - literal: \"3\"\n  - literal: \"ENTERPRISE\"\n",
        "claims: []\n",
    )
    doc = parse_concept(text, "invariants/enterprise-grace-period")
    result = evaluate_write(doc, load_config(repo.root))
    assert result.accepted is False
    assert "claims_required" in result.tighten


def test_technical_decision_without_claims_still_ok(repo):
    doc = parse_concept(STREAMER_CONCEPT, "decisions/custom-data-streamer")
    assert not doc.frontmatter.claims
    result = evaluate_write(doc, load_config(repo.root))
    assert result.accepted is True
    assert "claims_required" not in result.tighten


def test_invariant_with_claims_still_accepted(repo):
    doc = parse_concept(GRACE_CONCEPT, "invariants/enterprise-grace-period")
    result = evaluate_write(doc, load_config(repo.root))
    assert result.accepted is True


def test_unanchored_invariant_without_claims_rejected_by_write(repo):
    text = """\
---
type: InvariantContract
title: Decorative without claims
status: stable
---

Must hold something, but no claims and no anchors.
"""
    payload = write_memory(
        repo.root,
        "stdin",
        identity="invariants/decorative",
        stdin_text=text,
    )
    assert payload["accepted"] is False
    assert "claims_required" in payload["tighten"]
