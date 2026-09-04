from __future__ import annotations

from pathlib import Path

from repocodex.commands.validate import validate
from repocodex.commands.write import write_memory
from repocodex.store.bundle import ensure_bundle, write_concept
from repocodex.schema import (
    Anchor,
    ConceptDocument,
    ConceptFrontmatter,
    ConceptType,
    Verification,
    parse_concept,
)
from tests.fixtures.repos import STREAMER_CONCEPT


def test_new_flat_technical_decision_rejected(repo):
    payload = write_memory(
        repo.root,
        "stdin",
        identity="flat-streamer",
        stdin_text=STREAMER_CONCEPT,
    )
    assert payload["accepted"] is False
    assert "identity_prefix_mismatch" in payload["tighten"]
    assert any("decisions/" in s for s in payload.get("suggestions", []))
    assert not (repo.root / ".context" / "flat-streamer.md").exists()


def test_prefixed_technical_decision_accepted(repo):
    payload = write_memory(
        repo.root,
        "stdin",
        identity="decisions/extra-streamer",
        stdin_text=STREAMER_CONCEPT,
    )
    assert payload["accepted"] is True
    assert (repo.root / ".context" / "decisions" / "extra-streamer.md").exists()


def test_existing_flat_identity_update_accepted_with_suggestion(repo):
    ctx = repo.root / ".context"
    path = ctx / "legacy-streamer.md"
    path.write_text(STREAMER_CONCEPT, encoding="utf-8")
    payload = write_memory(
        repo.root,
        "stdin",
        identity="legacy-streamer",
        stdin_text=STREAMER_CONCEPT,
    )
    assert payload["accepted"] is True
    assert any("decisions/" in s for s in payload.get("suggestions", []))
    assert path.exists()


def test_guardrail_under_guardrails_accepted(repo):
    text = """\
---
type: GuardrailDecision
title: Domain must not import infra
status: stable
verification:
  engine: ripgrep
  anchors:
    - path: .importlinter
      all_of: ["ForbiddenContract", "domain", "infra"]
---

Pin the linter config.
"""
    (repo.root / ".importlinter").write_text(
        "[importlinter]\nroot_package = app\n\n[importlinter:contract:1]\nname = ForbiddenContract\nsource_modules = domain\nforbidden_modules = infra\n",
        encoding="utf-8",
    )
    payload = write_memory(
        repo.root,
        "stdin",
        identity="guardrails/no-domain-infra",
        stdin_text=text,
    )
    assert payload["accepted"] is True


def test_unknown_type_at_root_accepted(repo):
    text = """\
---
type: Playbook
title: Ops notes
status: stable
---

Narrative only.
"""
    payload = write_memory(
        repo.root,
        "stdin",
        identity="ops-notes",
        stdin_text=text,
    )
    assert payload["accepted"] is True
    assert (repo.root / ".context" / "ops-notes.md").exists()
