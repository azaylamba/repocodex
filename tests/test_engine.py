from __future__ import annotations

from pathlib import Path

from repocodex.config import load_config
from repocodex.engine.gate import evaluate_write
from repocodex.engine.liveness import classify_anchor
from repocodex.engine.match import match_anchor
from repocodex.schema import Anchor, ConceptDocument, ConceptFrontmatter, ConceptType, Verification, parse_concept
from tests.fixtures.repos import GRACE_CONCEPT, PAYMENT_GATEWAY, STREAMER


def test_formatter_cannot_break_anchor():
    wrapped = PAYMENT_GATEWAY.replace(
        'const grace = 3;',
        "const grace =\n      3;",
    )
    anchor = Anchor(
        path="src/billing/PaymentGateway.ts",
        all_of=["ENTERPRISE", "grace", "= 3"],
        near="capturePayment",
    )
    matched = match_anchor(anchor, wrapped)
    assert matched.hits_for_best() == 3


def test_write_gate_rejects_tautological_anchor(repo):
    cfg = load_config(repo.root)
    cfg.distinctiveness_ceiling = 1
    filler = repo.root / "src" / "common.py"
    filler.write_text("id\n" * 5, encoding="utf-8")
    doc = ConceptDocument(
        identity="decisions/weak",
        frontmatter=ConceptFrontmatter(
            type=ConceptType.TechnicalDecision,
            title="weak",
            verification=Verification(
                engine="ripgrep",
                anchors=[Anchor(path="src/common.py", all_of=["id"])],
            ),
        ),
        body="because",
    )
    result = evaluate_write(doc, cfg)
    assert result.accepted is False
    assert "not_distinctive" in result.tighten
    assert "id" in result.term_counts
    assert result.suggestions


def test_claim_literal_must_be_anchored(repo):
    text = GRACE_CONCEPT.replace('all_of: ["ENTERPRISE", "grace", "= 3"]', 'all_of: ["ENTERPRISE", "grace"]')
    doc = parse_concept(text, "invariants/enterprise-grace-period")
    result = evaluate_write(doc, load_config(repo.root))
    assert result.accepted is False
    assert "claim_not_anchored" in result.tighten


def test_marker_cannot_be_sole_anchor(repo):
    doc = ConceptDocument(
        identity="decisions/mark",
        frontmatter=ConceptFrontmatter(
            type=ConceptType.TechnicalDecision,
            title="mark",
            verification=Verification(
                engine="ripgrep",
                anchors=[
                    Anchor(
                        path="src/billing/PaymentGateway.ts",
                        all_of=['// why: .context/decisions/mark.md'],
                    )
                ],
            ),
        ),
        body="x",
    )
    result = evaluate_write(doc, load_config(repo.root))
    assert result.accepted is False


def test_identifier_rename_degrades_to_weak(repo):
    doc = parse_concept(
        """\
---
type: TechnicalDecision
title: n of m
status: stable
verification:
  engine: ripgrep
  anchors:
    - path: src/core/streams/CustomDataStreamer.py
      all_of: ["yield", "iter_batches", "CustomDataStreamer"]
---

body
""",
        "decisions/n-of-m",
    )
    streamer = repo.root / "src" / "core" / "streams" / "CustomDataStreamer.py"
    streamer.write_text(STREAMER.replace("iter_batches", "iter_chunks", 1).replace("def iter_chunks", "def iter_batches"), encoding="utf-8")
    # rename only the identifier in the yield path keep two terms
    streamer.write_text(
        "class CustomDataStreamer:\n    def iter_chunks(self, source):\n        for chunk in source:\n            parsed = parse_xml(chunk)\n            yield parsed.rows\n",
        encoding="utf-8",
    )
    outcome = classify_anchor(doc, 0, doc.anchors[0], load_config(repo.root))
    assert outcome.classification == "WEAK"


def test_architecture_examples_pass_gate(repo):
    docs = {
        path.name: parse_concept(path.read_text(encoding="utf-8"), "x")
        for path in (repo.root / ".context").rglob("*.md")
        if path.name not in {"index.md", "log.md", "reverse-index.md"}
    }
    cfg = load_config(repo.root)
    grace = parse_concept(
        (repo.root / ".context" / "invariants" / "enterprise-grace-period.md").read_text(encoding="utf-8"),
        "invariants/enterprise-grace-period",
    )
    streamer = parse_concept(
        (repo.root / ".context" / "decisions" / "custom-data-streamer.md").read_text(encoding="utf-8"),
        "decisions/custom-data-streamer",
    )
    assert evaluate_write(grace, cfg).accepted
    assert evaluate_write(streamer, cfg).accepted
