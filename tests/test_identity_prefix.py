"""Pin write-time identity prefix rules for typed concepts.

New typed concepts must live under the matching folder. Existing flat identities
are grandfathered. Validate emits advisory prefix warnings, and relocate moves
mismatched files when the target is free.
"""

from __future__ import annotations

from repocodex.commands.relocate import relocate_memory
from repocodex.commands.validate import validate
from repocodex.commands.write import write_memory
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


def test_validate_emits_identity_prefix_warnings(repo):
    path = repo.root / ".context" / "legacy-streamer.md"
    path.write_text(STREAMER_CONCEPT, encoding="utf-8")
    payload = validate(repo.root, all_concepts=True)
    warnings = payload.get("identity_prefix_warnings") or []
    assert any(w.get("concept") == "legacy-streamer" for w in warnings)
    assert any(w.get("suggested") == "decisions/legacy-streamer" for w in warnings)
    # Prefix debt alone must not block.
    assert "identity_prefix_mismatch" not in (payload.get("blocking_reasons") or [])


def test_relocate_moves_flat_technical_decision(repo):
    path = repo.root / ".context" / "legacy-streamer.md"
    path.write_text(STREAMER_CONCEPT, encoding="utf-8")
    payload = relocate_memory(repo.root, "legacy-streamer")
    assert any(
        m["from"] == "legacy-streamer" and m["to"] == "decisions/legacy-streamer"
        for m in payload["moved"]
    )
    assert not path.exists()
    assert (repo.root / ".context" / "decisions" / "legacy-streamer.md").exists()


def test_relocate_skips_when_target_exists(repo):
    flat = repo.root / ".context" / "legacy-streamer.md"
    flat.write_text(STREAMER_CONCEPT, encoding="utf-8")
    target = repo.root / ".context" / "decisions" / "legacy-streamer.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(STREAMER_CONCEPT, encoding="utf-8")
    payload = relocate_memory(repo.root, "legacy-streamer")
    assert payload["moved"] == []
    assert any(s.get("reason") == "target_exists" for s in payload["skipped"])
    assert flat.exists()


def test_relocate_not_found(repo):
    payload = relocate_memory(repo.root, "missing-concept")
    assert payload["moved"] == []
    assert any(s.get("reason") == "not_found" for s in payload["skipped"])
