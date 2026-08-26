from __future__ import annotations

from repocodex.schema import (
    ConceptFrontmatter,
    ConceptType,
    parse_concept,
    serialize_concept,
)


def test_parses_okf_frontmatter_and_extensions():
    text = """\
---
type: InvariantContract
title: Grace
status: stable
custom_producer_key: keep-me
claims:
  - literal: "3"
    subject: grace_cycles
verification:
  engine: ripgrep
  anchors:
    - path: src/a.ts
      all_of: ["ENTERPRISE", "grace"]
      near: capturePayment
      min_match: 2
supersedes: invariants/old
rationale: business change
---

The why.
"""
    doc = parse_concept(text, identity="invariants/grace")
    assert doc.frontmatter.type == ConceptType.InvariantContract
    assert doc.frontmatter.claims[0].literal == "3"
    assert doc.frontmatter.claims[0].subject == "grace_cycles"
    assert doc.frontmatter.verification.anchors[0].all_of == ["ENTERPRISE", "grace"]
    assert doc.frontmatter.supersedes == "invariants/old"
    assert doc.body.strip() == "The why."
    assert doc.frontmatter.model_extra["custom_producer_key"] == "keep-me"


def test_unknown_frontmatter_keys_survive_rewrite():
    text = """\
---
type: TechnicalDecision
title: Keep extras
status: stable
vendor_field: { nested: true }
verification:
  engine: ripgrep
  anchors:
    - path: src/a.py
      all_of: ["yield"]
---

Body
"""
    doc = parse_concept(text, identity="decisions/keep")
    rewritten = serialize_concept(doc)
    again = parse_concept(rewritten, identity="decisions/keep")
    assert again.frontmatter.model_extra["vendor_field"] == {"nested": True}


def test_okf_version_is_bundle_level_field():
    text = """\
---
okf_version: "0.2"
---

# catalog
"""
    from repocodex.schema import parse_index

    index = parse_index(text)
    assert index.okf_version == "0.2"
