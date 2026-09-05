"""Pin OKF 0.2 bundle conformance for parse, store, and validate.

Cover unknown types, sources and verified shapes, reverse-index location,
unanchored pages, leftover index desync, and generated-actor rules.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from repocodex.commands.validate import validate
from repocodex.commands.write import write_memory
from repocodex.retrieval import retrieve
from repocodex.schema import (
    parse_concept,
    parse_index,
    serialize_concept,
    serialize_index,
)
from repocodex.store.bundle import (
    ensure_bundle,
    load_concepts,
    okf_bundle_errors,
    write_concept,
)
from repocodex.store.reverse_index import merged_index, regenerate_all


PLAYBOOK = """\
---
type: Playbook
---

How to investigate billing.
"""

METRIC = """\
---
type: Metric
title: Latency
owner: billing
---

p99 under 200ms.
"""

MINIMAL_PIN = """\
---
type: TechnicalDecision
title: Keep yield
verification:
  engine: ripgrep
  anchors:
    - path: src/core/streams/CustomDataStreamer.py
      all_of: ["yield", "iter_batches"]
---

Do not listify.
"""


def test_unknown_type_is_retained_and_round_trips():
    doc = parse_concept(METRIC, identity="metrics/latency")
    assert doc.frontmatter.type == "Metric"
    rewritten = parse_concept(serialize_concept(doc), identity="metrics/latency")
    assert rewritten.frontmatter.type == "Metric"
    assert rewritten.frontmatter.model_extra["owner"] == "billing"


def test_omitted_status_is_stable():
    doc = parse_concept(MINIMAL_PIN, identity="decisions/yield")
    assert doc.status.value == "stable"


def test_sources_are_objects_with_resource():
    text = """\
---
type: TechnicalDecision
title: Sourced
sources:
  - resource: git://commit/abc123
    title: commit
    id: abc123
verification:
  engine: ripgrep
  anchors:
    - path: src/a.py
      all_of: ["yield"]
---

Body
"""
    doc = parse_concept(text, identity="decisions/sourced")
    assert doc.frontmatter.sources
    first = doc.frontmatter.sources[0]
    resource = first.resource if hasattr(first, "resource") else first["resource"]
    assert resource == "git://commit/abc123"


def test_verified_accepts_mapping_or_list_and_is_optional():
    mapping = parse_concept(
        MINIMAL_PIN.replace(
            "title: Keep yield\n",
            "title: Keep yield\nverified: { by: human:reviewer, at: 2026-08-25T12:00:00Z }\n",
        ),
        identity="decisions/yield",
    )
    assert mapping.frontmatter.verified
    listed = parse_concept(
        MINIMAL_PIN.replace(
            "title: Keep yield\n",
            "title: Keep yield\nverified:\n  - { by: human:reviewer, at: 2026-08-25T12:00:00Z }\n",
        ),
        identity="decisions/yield",
    )
    assert isinstance(listed.frontmatter.verified, list)
    omitted = parse_concept(MINIMAL_PIN, identity="decisions/yield")
    assert omitted.frontmatter.verified is None


def test_root_index_uses_okf_version_not_format_version():
    index = parse_index('---\nokf_version: "0.2"\n---\n\n# catalog\n')
    assert index.okf_version == "0.2"
    dumped = serialize_index(index)
    assert "okf_version" in dumped
    assert "format_version" not in dumped


def test_legacy_agent_prefix_maps_on_read():
    text = MINIMAL_PIN.replace(
        "title: Keep yield\n",
        "title: Keep yield\ngenerated: { by: agent:cursor/grok-4.6, at: 2026-08-25T12:00:00Z }\n",
    )
    doc = parse_concept(text, identity="decisions/yield")
    by = doc.frontmatter.generated.by if hasattr(doc.frontmatter.generated, "by") else doc.frontmatter.generated["by"]
    assert by == "cursor/grok-4.6"
    assert not by.startswith("agent:")


def test_playbook_with_only_type_loads(repo):
    path = repo.root / ".context" / "playbooks" / "billing.md"
    path.parent.mkdir(parents=True)
    path.write_text(PLAYBOOK, encoding="utf-8")
    docs = load_concepts(repo.root)
    identities = {doc.identity for doc in docs}
    assert "playbooks/billing" in identities


def test_ensure_bundle_writes_okf_version_only(tmp_path: Path):
    root = tmp_path / ".context"
    ensure_bundle(root)
    text = (root / "index.md").read_text(encoding="utf-8")
    assert 'okf_version: "0.2"' in text
    assert "format_version" not in text
    assert not (root / "reverse-index.md").exists()


def test_reverse_index_lives_outside_context(repo):
    regenerate_all(repo.root)
    assert not (repo.root / ".context" / "reverse-index.md").exists()
    assert (repo.root / ".repocodex" / "reverse-index.md").exists()
    mapping = merged_index(repo.root)
    assert "src/billing/PaymentGateway.ts" in mapping


def test_legacy_context_reverse_index_is_nonconformant(repo):
    (repo.root / ".context" / "reverse-index.md").write_text("# reverse-index\n", encoding="utf-8")
    errors = okf_bundle_errors(repo.root)
    assert errors
    assert all(err.get("reason") != "reserved_name" for err in errors)
    blob = str(errors).lower()
    assert "reserved" not in blob


def test_markdown_without_type_is_nonconformant(repo):
    (repo.root / ".context" / "notes.md").write_text("# just notes\n", encoding="utf-8")
    errors = okf_bundle_errors(repo.root)
    assert errors


def test_unanchored_playbook_is_retrievable_via_link(repo):
    playbook = repo.root / ".context" / "playbooks" / "billing.md"
    playbook.parent.mkdir(parents=True)
    playbook.write_text(PLAYBOOK, encoding="utf-8")
    grace = repo.root / ".context" / "invariants" / "enterprise-grace-period.md"
    text = grace.read_text(encoding="utf-8")
    grace.write_text(text.rstrip() + "\nSee [billing playbook](../playbooks/billing.md).\n", encoding="utf-8")
    payload = retrieve(repo.root, ["src/billing/PaymentGateway.ts"])
    related_ids = [item["identity"] for item in payload["related"]]
    concept_ids = [item["identity"] for item in payload["concepts"]]
    assert "playbooks/billing" in related_ids or "playbooks/billing" in concept_ids


def test_unanchored_page_does_not_arm_skipped_memory(repo):
    playbook = repo.root / ".context" / "playbooks" / "orphan.md"
    playbook.parent.mkdir(parents=True)
    playbook.write_text(PLAYBOOK, encoding="utf-8")
    uncovered = repo.root / "src" / "uncovered.py"
    uncovered.write_text("print('new')\n", encoding="utf-8")
    payload = validate(repo.root)
    skipped = payload.get("skipped_memory") or []
    assert not any(str(item.get("path", "")).endswith("orphan.md") for item in skipped)
    assert any(
        item.get("path") == "src/uncovered.py"
        and item.get("reason") == "uncovered_file_without_memory"
        for item in skipped
    )


def test_write_of_unverified_concept_omits_verified(repo):
    result = write_memory(repo.root, ".", identity="decisions/no-verified", stdin_text=MINIMAL_PIN)
    assert result["accepted"] is True
    stored = (repo.root / ".context" / "decisions" / "no-verified.md").read_text(encoding="utf-8")
    assert "verified:" not in stored


def test_validate_does_not_mutate_concept_files(repo):
    path = repo.root / ".context" / "invariants" / "enterprise-grace-period.md"
    before = path.read_text(encoding="utf-8")
    validate(repo.root, all_concepts=True)
    assert path.read_text(encoding="utf-8") == before


def test_reanchor_updates_path_not_verified(repo):
    from repocodex.commands.reconcile import apply_anchor_patch

    dest = repo.root / "src" / "core" / "streams" / "streamer_v2.py"
    repo.streamer.rename(dest)
    payload = validate(repo.root)
    streamer = [o for o in payload["outcomes"] if "streamer" in o["concept"]]
    assert streamer and streamer[0]["classification"] == "REANCHOR"
    patch = streamer[0]["patch"]
    assert "verified" not in patch
    apply_anchor_patch(repo.root, patch)
    stored = (repo.root / ".context" / "decisions" / "custom-data-streamer.md").read_text(
        encoding="utf-8"
    )
    assert "streamer_v2.py" in stored
    assert "process:repocodex-reanchor" not in stored


def test_scalar_sources_are_rewritten_to_objects_on_write(repo):
    text = MINIMAL_PIN.replace(
        "title: Keep yield\n",
        'title: Keep yield\nsources: ["commit:abc123def"]\n',
    )
    result = write_memory(repo.root, ".", identity="decisions/sourced-write", stdin_text=text)
    assert result["accepted"] is True
    stored = (repo.root / ".context" / "decisions" / "sourced-write.md").read_text(encoding="utf-8")
    assert "resource:" in stored
    assert "- commit:abc123def" not in stored


def test_generated_actor_is_not_agent_prefixed(repo):
    text = MINIMAL_PIN.replace(
        "title: Keep yield\n",
        "title: Keep yield\ngenerated: { by: agent:cursor/grok-4.6, at: 2026-08-25T12:00:00Z }\n",
    )
    result = write_memory(repo.root, ".", identity="decisions/actor", stdin_text=text)
    assert result["accepted"] is True
    stored = (repo.root / ".context" / "decisions" / "actor.md").read_text(encoding="utf-8")
    assert "agent:" not in stored
    assert "cursor/grok-4.6" in stored


def test_invariant_stays_one_file_and_claim_broken(repo):
    from tests.fixtures.repos import PAYMENT_GATEWAY

    written = list((repo.root / ".context").rglob("*Attested*"))
    assert written == []
    repo.payment_gateway.write_text(
        PAYMENT_GATEWAY.replace("const grace = 3;", "const grace = 1;"),
        encoding="utf-8",
    )
    payload = validate(repo.root)
    assert any(f["classification"] == "CLAIM_BROKEN" and f["literal"] == "3" for f in payload["claim_findings"])


def test_write_gate_still_required_when_anchors_declared(repo):
    text = MINIMAL_PIN.replace('all_of: ["yield", "iter_batches"]', 'all_of: ["missing_token_xyz"]')
    result = write_memory(repo.root, ".", identity="decisions/bad-pin", stdin_text=text)
    assert result["accepted"] is False
    assert result["tighten"]


def test_unanchored_concepts_are_absent_from_reverse_index(repo):
    path = repo.root / ".context" / "playbooks" / "billing.md"
    path.parent.mkdir(parents=True)
    path.write_text(PLAYBOOK, encoding="utf-8")
    regenerate_all(repo.root)
    mapping = merged_index(repo.root)
    identities = [ident for ids in mapping.values() for ident in ids]
    assert "playbooks/billing" not in identities


UNIQUE_CATALOG_DESC = "UNIQUE_CATALOG_DESC_ZX9"


def test_regenerate_deletes_leftover_context_reverse_index(repo):
    leftover = repo.root / ".context" / "reverse-index.md"
    leftover.write_text("# reverse-index\n", encoding="utf-8")
    nested = repo.root / ".context" / "decisions" / "reverse-index.md"
    nested.write_text("# reverse-index\n", encoding="utf-8")
    regenerate_all(repo.root)
    assert not leftover.exists()
    assert not nested.exists()
    assert (repo.root / ".repocodex" / "reverse-index.md").exists()


def test_leftover_in_bundle_reverse_index_is_index_sync(repo):
    leftover = repo.root / ".context" / "reverse-index.md"
    leftover.write_text("# reverse-index\n", encoding="utf-8")
    payload = validate(repo.root)
    assert payload["blocking"] is True
    assert "index_sync" in payload["blocking_reasons"]
    assert set(payload["blocking_reasons"]) <= {
        "drift",
        "claim_broken",
        "skipped_memory",
        "index_sync",
        "contradiction",
    }
    blob = str(payload.get("index_sync")).lower() + str(okf_bundle_errors(repo.root)).lower()
    assert "reserved_name" not in blob
    assert "reserved filename" not in blob


def test_unstaged_generated_reverse_index_is_desync_under_staged(repo):
    import subprocess

    from tests.fixtures.repos import STREAMER_CONCEPT

    text = STREAMER_CONCEPT.replace("custom-data-streamer", "copy-unstaged")
    result = write_memory(repo.root, ".", identity="decisions/copy-unstaged", stdin_text=text)
    assert result["accepted"] is True
    generated = repo.root / ".repocodex" / "reverse-index.md"
    assert generated.exists()
    payload = validate(repo.root, staged=True)
    assert "index_sync" in payload["blocking_reasons"]
    subprocess.run(["git", "add", str(generated)], cwd=repo.root, check=True, capture_output=True)
    after = validate(repo.root, staged=True)
    assert "index_sync" not in after["blocking_reasons"]


def test_unstaged_deletion_of_leftover_is_desync_under_staged(repo):
    import subprocess

    leftover = repo.root / ".context" / "reverse-index.md"
    leftover.write_text("# reverse-index\n", encoding="utf-8")
    subprocess.run(["git", "add", str(leftover)], cwd=repo.root, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "track leftover reverse-index", "--no-verify"],
        cwd=repo.root,
        check=True,
        capture_output=True,
    )
    regenerate_all(repo.root)
    assert not leftover.exists()
    payload = validate(repo.root, staged=True)
    assert "index_sync" in payload["blocking_reasons"]
    subprocess.run(
        ["git", "add", "-u", "--", ".context/reverse-index.md"],
        cwd=repo.root,
        check=True,
        capture_output=True,
    )
    after = validate(repo.root, staged=True)
    assert "index_sync" not in after["blocking_reasons"]


def test_hook_alone_uses_git_index_for_leftover(repo):
    import subprocess

    from tests.conftest import run_cli

    leftover = repo.root / ".context" / "reverse-index.md"
    leftover.write_text("# reverse-index\n", encoding="utf-8")
    subprocess.run(["git", "add", str(leftover)], cwd=repo.root, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "track leftover reverse-index", "--no-verify"],
        cwd=repo.root,
        check=True,
        capture_output=True,
    )
    regenerate_all(repo.root)
    result = run_cli(["validate", "--diff", "--hook"], cwd=repo.root)
    assert result.returncode != 0
    assert "index_sync" in result.stdout


def test_coding_skill_names_reverse_index_commit_path():
    roots = [
        Path("src/repocodex/data/skills/repocodex-coding/SKILL.md"),
        Path("src/repocodex/data/plugin/skills/repocodex-coding/SKILL.md"),
        Path("plugin/skills/repocodex-coding/SKILL.md"),
    ]
    for path in roots:
        text = path.read_text(encoding="utf-8")
        assert ".repocodex/reverse-index.md" in text
        assert ".repocodex/reverse-index/" in text
        commit_lines = [line for line in text.splitlines() if "commit" in line.lower() or "stage" in line.lower()]
        joined = "\n".join(commit_lines).lower()
        assert ".context/" not in joined or ".repocodex/reverse-index" in joined


def test_nested_catalog_link_uses_unique_frontmatter_description(repo):
    from tests.fixtures.repos import STREAMER_CONCEPT

    catalog_path = repo.root / ".context" / "decisions" / "index.md"
    catalog_before = catalog_path.read_text(encoding="utf-8")
    assert UNIQUE_CATALOG_DESC not in catalog_before
    doc = parse_concept(
        STREAMER_CONCEPT.replace("custom-data-streamer", "unique-desc"),
        "decisions/unique-desc",
    )
    doc.frontmatter.title = "Unique desc concept"
    doc.frontmatter.description = UNIQUE_CATALOG_DESC
    assert UNIQUE_CATALOG_DESC not in doc.body
    write_concept(repo.root, doc)
    catalog = catalog_path.read_text(encoding="utf-8")
    link_line = next(line for line in catalog.splitlines() if "unique-desc.md" in line)
    assert UNIQUE_CATALOG_DESC in link_line
    assert "Do not optimize" not in link_line


def test_later_date_heading_sorts_above_older(repo):
    from tests.fixtures.repos import STREAMER_CONCEPT

    log = repo.root / ".context" / "log.md"
    log.write_text("# log\n\n## 2020-01-01\n\n- **wrote** old-entry\n", encoding="utf-8")
    doc = parse_concept(
        STREAMER_CONCEPT.replace("custom-data-streamer", "dated"),
        "decisions/dated",
    )
    write_concept(repo.root, doc)
    text = log.read_text(encoding="utf-8")
    today = datetime.now(timezone.utc).date().isoformat()
    assert text.find(f"## {today}") < text.find("## 2020-01-01")
    assert "dated" in text[text.find(f"## {today}") : text.find("## 2020-01-01")]


def test_sample_concepts_do_not_teach_pin_check_as_verified():
    from tests.fixtures import repos as fixtures

    for name in (
        "GRACE_CONCEPT",
        "STREAMER_CONCEPT",
        "WORKFLOW_CONCEPT",
        "CLAIMED_WORKFLOW_CONCEPT",
        "GUARDRAIL_CONCEPT",
    ):
        text = getattr(fixtures, name)
        if "verified:" not in text:
            continue
        doc = parse_concept(text, identity=name.lower())
        stamps = doc.frontmatter.verified
        if stamps is None:
            continue
        items = stamps if isinstance(stamps, list) else [stamps]
        for stamp in items:
            by = stamp.by if hasattr(stamp, "by") else stamp["by"]
            assert by != "process:repocodex-rg"
            assert by.startswith("human:") or "/" in by
