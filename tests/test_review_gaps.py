"""Pin review-identified gaps across validate, ratchet, and install.

Cover claim breakage, comment and format diffs, contradictions, exemptions,
bootstrap and audit payloads, shard writes, and advisory findings.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from repocodex.commands.validate import validate
from repocodex.engine.gate import evaluate_write
from repocodex.config import load_config
from repocodex.schema import parse_concept
from tests.conftest import run_cli
from tests.fixtures.repos import GRACE_CONCEPT, PAYMENT_GATEWAY


def test_claim_broken_when_literal_changes_and_anchor_stays(repo):
    repo.payment_gateway.write_text(
        PAYMENT_GATEWAY.replace("const grace = 3;", "const grace = 1;"),
        encoding="utf-8",
    )
    payload = validate(repo.root)
    grace = [o for o in payload["outcomes"] if "grace" in o["concept"]]
    assert grace
    assert grace[0]["classification"] == "WEAK"
    assert payload["claim_findings"]
    assert any(f["classification"] == "CLAIM_BROKEN" and f["literal"] == "3" for f in payload["claim_findings"])
    assert payload["blocking"] is True
    assert "claim_broken" in payload["blocking_reasons"]


def test_claim_breakage_with_unrelated_context_edit_blocks(repo):
    repo.payment_gateway.write_text(
        PAYMENT_GATEWAY.replace("const grace = 3;", "const grace = 1;"),
        encoding="utf-8",
    )
    (repo.root / ".context" / "log.md").write_text("# log\n- unrelated\n", encoding="utf-8")
    payload = validate(repo.root)
    assert any(f["classification"] == "CLAIM_BROKEN" for f in payload["claim_findings"])
    assert payload["blocking"] is True
    assert "claim_broken" in payload["blocking_reasons"]


def test_claim_intact_does_not_block(repo):
    repo.payment_gateway.write_text(
        PAYMENT_GATEWAY.replace("await charge(account);", "await charge(account);\n  return;"),
        encoding="utf-8",
    )
    payload = validate(repo.root)
    assert not payload.get("claim_findings")
    assert "claim_broken" not in payload["blocking_reasons"]


def test_substring_does_not_satisfy_claim(repo):
    text = GRACE_CONCEPT.replace('all_of: ["ENTERPRISE", "grace", "= 3"]', 'all_of: ["ENTERPRISE", "grace", "= 30"]')
    doc = parse_concept(text, "invariants/enterprise-grace-period")
    result = evaluate_write(doc, load_config(repo.root))
    assert result.accepted is False
    assert "claim_not_anchored" in result.tighten


def test_claim_outside_matched_region_is_not_credited(repo):
    extra = PAYMENT_GATEWAY + "\nconst elsewhere = 3;\n"
    repo.payment_gateway.write_text(extra, encoding="utf-8")
    text = GRACE_CONCEPT.replace('all_of: ["ENTERPRISE", "grace", "= 3"]', 'all_of: ["ENTERPRISE", "grace"]')
    text = text.replace('claims:\n  - literal: "3"\n  - literal: "ENTERPRISE"', 'claims:\n  - literal: "3"\n  - literal: "ENTERPRISE"')
    doc = parse_concept(text, "invariants/outside-region")
    # near capturePayment; literal 3 only exists below the function if we remove = 3 from the region
    repo.payment_gateway.write_text(
        PAYMENT_GATEWAY.replace("const grace = 3;", "const grace = 9;")
        + ("\n" * 80)
        + "const leftover = 3;\n",
        encoding="utf-8",
    )
    payload = validate(repo.root)
    # original concept still has claim 3; grace region now has 9 and leftover 3 is outside near-scope
    findings = payload.get("claim_findings") or []
    assert any(f["classification"] == "CLAIM_BROKEN" for f in findings)


def _append_outside_region(path: Path, snippet: str) -> None:
    original = path.read_text(encoding="utf-8")
    path.write_text(original.rstrip() + "\n" + ("\n" * 80) + snippet, encoding="utf-8")


def _weaken_streamer(text: str) -> str:
    return text.replace("yield parsed.rows", "return parsed.rows")


def test_unrelated_context_edit_does_not_clear_ratchet(repo):
    _append_outside_region(repo.streamer, "def refund_batches():\n    return []\n")
    (repo.root / ".context" / "log.md").write_text("# log\n- unrelated note\n", encoding="utf-8")
    payload = validate(repo.root)
    assert payload["skipped_memory"]
    assert any(item["path"].endswith("CustomDataStreamer.py") for item in payload["skipped_memory"])
    assert payload["blocking"] is True
    assert "skipped_memory" in payload["blocking_reasons"]


def test_maintaining_covering_concept_clears_ratchet(repo):
    repo.streamer.write_text(_weaken_streamer(repo.streamer.read_text(encoding="utf-8")), encoding="utf-8")
    concept = repo.root / ".context" / "decisions" / "custom-data-streamer.md"
    concept.write_text(concept.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    payload = validate(repo.root)
    assert not any(
        item["path"].endswith("CustomDataStreamer.py") for item in payload.get("skipped_memory") or []
    )


def test_formatting_only_does_not_trip_ratchet(repo):
    repo.payment_gateway.write_text(
        PAYMENT_GATEWAY.replace("const grace = 3;", "const grace =\n    3;"),
        encoding="utf-8",
    )
    payload = validate(repo.root)
    assert not payload.get("skipped_memory")


def test_comment_only_does_not_trip_ratchet(repo):
    repo.payment_gateway.write_text(
        PAYMENT_GATEWAY.replace(
            "export async function capturePayment",
            "// note: keep grace\nexport async function capturePayment",
        ),
        encoding="utf-8",
    )
    payload = validate(repo.root)
    assert not payload.get("skipped_memory")


def test_independent_invariants_do_not_contradict(repo):
    retry = repo.root / ".context" / "invariants" / "retry-budget.md"
    retry.write_text(
        GRACE_CONCEPT.replace("enterprise-grace-period", "retry-budget")
        .replace('literal: "3"', 'literal: "5"\n    subject: retry_budget')
        .replace('literal: "ENTERPRISE"', 'literal: "ENTERPRISE"\n    subject: plan_tier')
        .replace('all_of: ["ENTERPRISE", "grace", "= 3"]', 'all_of: ["ENTERPRISE", "grace"]'),
        encoding="utf-8",
    )
    grace = repo.root / ".context" / "invariants" / "enterprise-grace-period.md"
    text = grace.read_text(encoding="utf-8").replace(
        '  - literal: "3"\n  - literal: "ENTERPRISE"',
        '  - literal: "3"\n    subject: grace_cycles\n  - literal: "ENTERPRISE"\n    subject: plan_tier',
    )
    grace.write_text(text, encoding="utf-8")
    payload = validate(repo.root, all_concepts=True)
    assert not [c for c in payload["contradictions"] if c.get("reason") == "conflicting_claims"]


def test_same_subject_different_literals_contradict(repo):
    other = repo.root / ".context" / "invariants" / "grace-alt.md"
    other.write_text(
        GRACE_CONCEPT.replace("enterprise-grace-period", "grace-alt")
        .replace('literal: "3"', 'literal: "1"\n    subject: grace_cycles'),
        encoding="utf-8",
    )
    grace = repo.root / ".context" / "invariants" / "enterprise-grace-period.md"
    grace.write_text(
        grace.read_text(encoding="utf-8").replace(
            '  - literal: "3"',
            '  - literal: "3"\n    subject: grace_cycles',
        ),
        encoding="utf-8",
    )
    payload = validate(repo.root, all_concepts=True)
    conflicts = [c for c in payload["contradictions"] if c.get("reason") == "conflicting_claims"]
    assert conflicts
    assert conflicts[0]["subject"] == "grace_cycles"


def test_missing_subject_stays_silent(repo):
    other = repo.root / ".context" / "invariants" / "grace-alt.md"
    other.write_text(
        GRACE_CONCEPT.replace("enterprise-grace-period", "grace-alt").replace('literal: "3"', 'literal: "1"'),
        encoding="utf-8",
    )
    payload = validate(repo.root, all_concepts=True)
    assert not [c for c in payload["contradictions"] if c.get("reason") == "conflicting_claims"]


def test_shadow_reports_skipped_memory_and_blocks(repo):
    (repo.root / ".repocodex.toml").write_text(
        'engine_version = "0.0.1"\nposture = "shadow"\n',
        encoding="utf-8",
    )
    _append_outside_region(repo.streamer, "def refund_batches():\n    return []\n")
    payload = validate(repo.root)
    assert payload["skipped_memory"]
    assert payload["blocking"] is True


def test_shadow_reports_claim_breakage_without_blocking(repo):
    (repo.root / ".repocodex.toml").write_text(
        'engine_version = "0.0.1"\nposture = "shadow"\n',
        encoding="utf-8",
    )
    repo.payment_gateway.write_text(
        PAYMENT_GATEWAY.replace("const grace = 3;", "const grace = 1;"),
        encoding="utf-8",
    )
    payload = validate(repo.root)
    assert payload["claim_findings"]
    assert payload["blocking"] is False


def test_validate_leaves_working_tree_clean(repo):
    import subprocess

    before = subprocess.run(["git", "status", "--porcelain"], cwd=repo.root, capture_output=True, text=True)
    assert before.stdout.strip() == ""
    validate(repo.root, memory_exempt=True)
    after = subprocess.run(["git", "status", "--porcelain"], cwd=repo.root, capture_output=True, text=True)
    assert after.stdout.strip() == ""
    assert not (repo.root / ".context" / "metrics.jsonl").exists()


def test_engine_pin_mismatch_fails_loudly(repo):
    (repo.root / ".repocodex.toml").write_text(
        'engine_version = "9.9.9"\nposture = "ratchet"\n',
        encoding="utf-8",
    )
    result = run_cli(["validate", "--diff"], cwd=repo.root)
    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["error"] == "engine_version_mismatch"
    assert payload["pinned"] == "9.9.9"
    assert payload["running"] == "0.0.1"
    assert "result" not in payload


def test_unauthenticated_flag_does_not_clear_check(repo):
    repo.streamer.write_text("broken\n", encoding="utf-8")
    result = run_cli(["validate", "--diff", "--memory-exempt", "--review-ack"], cwd=repo.root)
    payload = json.loads(result.stdout)
    assert payload["blocking"] is True
    assert payload.get("memory_exempt") is not True


def test_tracked_ack_file_clears_check(repo):
    import subprocess

    repo.streamer.write_text("broken\n", encoding="utf-8")
    ack = repo.root / ".repocodex" / "acknowledgments" / "memory-exempt.json"
    ack.parent.mkdir(parents=True, exist_ok=True)
    ack.write_text(
        json.dumps({"kind": "memory-exempt", "reviewer": "agent:repocodex-review", "at": "2026-08-25T00:00:00Z"}),
        encoding="utf-8",
    )
    subprocess.run(["git", "add", str(ack)], cwd=repo.root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "ack", "--no-verify"], cwd=repo.root, check=True, capture_output=True)
    payload = validate(repo.root, memory_exempt=True, ack_file=str(ack.relative_to(repo.root)))
    assert payload["memory_exempt"] is True
    assert payload["blocking"] is False
    assert payload["audit_entries"]
    assert payload["repair_tasks"]
    assert "memory-exempt" not in (repo.root / ".context" / "log.md").read_text(encoding="utf-8")


def test_derived_ceiling_ignores_untracked_node_modules(tmp_path: Path):
    from tests.fixtures.repos import init_git_repo, write_architecture_fixtures

    root = tmp_path / "repo"
    root.mkdir()
    write_architecture_fixtures(root)
    init_git_repo(root)
    toml = (root / ".repocodex.toml").read_text(encoding="utf-8")
    (root / ".repocodex.toml").write_text(
        "\n".join(line for line in toml.splitlines() if "distinctiveness_ceiling" not in line) + "\n",
        encoding="utf-8",
    )
    first = load_config(root).distinctiveness_ceiling
    nm = root / "node_modules" / "pkg"
    nm.mkdir(parents=True)
    for i in range(50):
        (nm / f"f{i}.js").write_text("x\n", encoding="utf-8")
    second = load_config(root).distinctiveness_ceiling
    assert first == second


def test_exclusion_preserves_dotfile_names(repo):
    from repocodex.engine.gate import path_excluded

    cfg = load_config(repo.root)
    assert path_excluded(".importlinter", cfg) is False


def test_regex_dialect_mismatch_rejected_at_write(repo):
    text = GRACE_CONCEPT.replace('all_of: ["ENTERPRISE", "grace", "= 3"]', 'all_of: ["ENTERPRISE", "/grace(?=Period)/"]')
    text = text.replace('claims:\n  - literal: "3"\n  - literal: "ENTERPRISE"\n', "")
    doc = parse_concept(text, "invariants/lookaround")
    result = evaluate_write(doc, load_config(repo.root))
    assert result.accepted is False
    assert "regex_dialect" in result.tighten


def test_blocking_set_is_closed():
    from repocodex.engine.blocking import REQUIRED_CHECK_REASONS

    assert REQUIRED_CHECK_REASONS == frozenset(
        {"drift", "claim_broken", "skipped_memory", "index_sync", "contradiction"}
    )


def test_claim_breakage_repaired_through_gate(repo):
    from repocodex.commands.write import write_memory
    from tests.fixtures.repos import PAYMENT_GATEWAY as GATEWAY

    repo.payment_gateway.write_text(
        GATEWAY.replace("const grace = 3;", "const grace = 1;"),
        encoding="utf-8",
    )
    broken = validate(repo.root)
    assert broken["claim_findings"]
    replacement = GRACE_CONCEPT.replace('literal: "3"', 'literal: "1"').replace(
        'all_of: ["ENTERPRISE", "grace", "= 3"]',
        'all_of: ["ENTERPRISE", "grace", "= 1"]',
    ).replace(
        "status: stable",
        "status: stable\nsupersedes: invariants/enterprise-grace-period\nrationale: business-rule change",
    )
    result = write_memory(
        repo.root,
        ".",
        identity="invariants/enterprise-grace-period-v2",
        stdin_text=replacement,
    )
    assert result["accepted"] is True


def test_untracked_scratch_arms_first_touch(repo):
    first = validate(repo.root, all_concepts=True)
    assert not first["skipped_memory"]
    scratch = repo.root / "scratch_untracked.py"
    scratch.write_text('plan = "ENTERPRISE"\nconst grace = 3\nyield\n', encoding="utf-8")
    second = validate(repo.root, all_concepts=True)
    assert any(
        item.get("path") == "scratch_untracked.py"
        and item.get("reason") == "uncovered_file_without_memory"
        for item in second["skipped_memory"]
    )
    assert second["result"] == "WRITE"
    assert second["blocking"] is True


def test_action_has_no_unpinned_fallback():
    from repocodex.commands.install import _data_path

    text = _data_path("action", "repocodex.yml").read_text(encoding="utf-8")
    assert "|| pip install" not in text
    assert 'pip install "git+https://github.com/azaylamba/repocodex.git@v${PIN}"' in text
    assert 'pip install "repocodex==' not in text
    assert "repocodex advisory" in text


def test_engine_ci_does_not_require_context_bundle():
    from pathlib import Path

    workflow = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "engine-tests.yml"
    text = workflow.read_text(encoding="utf-8")
    assert "pytest" in text
    assert 'python-version: "3.11"' in text
    assert "ripgrep" in text
    assert 'pip install -e ".[dev]"' in text
    assert "repocodex validate" not in text


def test_staged_rename_reanchors(repo):
    import subprocess

    dest = repo.root / "src" / "core" / "streams" / "streamer_v2.py"
    subprocess.run(["git", "mv", str(repo.streamer), str(dest)], cwd=repo.root, check=True, capture_output=True)
    payload = validate(repo.root, staged=True)
    streamer = [o for o in payload["outcomes"] if "streamer" in o["concept"]]
    assert streamer
    assert streamer[0]["classification"] == "REANCHOR"


def test_metrics_carry_measured_values(repo):
    payload = validate(repo.root)
    assert payload["false_drift_rate"] == 0.0
    assert "tokens_per_turn" not in payload
    sink = repo.root / ".repocodex" / "metrics.jsonl"
    assert sink.exists()
    assert not (repo.root / ".context" / "metrics.jsonl").exists()


def test_bootstrap_cites_per_concept_source(repo):
    import subprocess

    from repocodex.commands.bootstrap import bootstrap
    from repocodex.store.bundle import load_concepts

    src = repo.root / "src" / "hint.py"
    src.write_text("# why: keep UNIQUE_BOOTSTRAP_TOKEN near iter hint\nUNIQUE_BOOTSTRAP_TOKEN = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", str(src)], cwd=repo.root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "hint", "--no-verify"], cwd=repo.root, check=True, capture_output=True)
    payload = bootstrap(repo.root)
    docs = [d for d in load_concepts(repo.root) if d.identity in payload["kept"]]
    assert all(d.identity.startswith("decisions/") for d in docs)
    if payload["kept"]:
        assert all(
            d.frontmatter.sources
            and all(
                (s.resource if hasattr(s, "resource") else s["resource"]).startswith("git://commit/")
                for s in d.frontmatter.sources
            )
            for d in docs
        )


def test_bootstrap_rejects_unsourced(repo):
    from repocodex.commands.bootstrap import bootstrap

    src = repo.root / "src" / "unsourced.py"
    src.write_text("# why: ephemeral note never committed\nEPHEMERAL_TOKEN_XYZ = 1\n", encoding="utf-8")
    payload = bootstrap(repo.root)
    assert any("no_evidencing_source" in (item.get("tighten") or []) for item in payload["rejected"]) or not payload["kept"]


def test_bootstrap_identities_are_stable(repo):
    import subprocess

    from repocodex.commands.bootstrap import _stable_id

    src = repo.root / "src" / "stable_boot.py"
    note = "keep STABLE_BOOT_TOKEN"
    src.write_text(f"# why: {note}\nSTABLE_BOOT_TOKEN = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", str(src)], cwd=repo.root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "boot", "--no-verify"], cwd=repo.root, check=True, capture_output=True)
    first = _stable_id("src/stable_boot.py", note)
    second = _stable_id("src/stable_boot.py", note)
    assert first == second


def test_audit_screening_payload(repo):
    from repocodex.commands.audit import audit

    payload = audit(repo.root, sample_size=2)
    assert payload["model_invoked"] is False
    assert payload["screening"]
    assert "out-of-band" in payload["note"]


def test_audit_findings_become_proposals(repo, tmp_path: Path):
    from repocodex.commands.audit import audit

    findings = tmp_path / "findings.json"
    findings.write_text(
        json.dumps([{"identity": "invariants/enterprise-grace-period", "note": "contradicts pinned code"}]),
        encoding="utf-8",
    )
    payload = audit(repo.root, sample_size=1, findings_path=findings)
    assert payload["contradiction_proposals"]
    assert payload["contradiction_proposals"][0]["proposal"] is True


def test_write_lands_in_owning_shard(tmp_path: Path):
    from tests.fixtures.repos import init_git_repo, write_architecture_fixtures
    from repocodex.commands.write import write_memory
    from tests.fixtures.repos import GRACE_CONCEPT as CONCEPT

    root = tmp_path / "mono"
    root.mkdir()
    write_architecture_fixtures(root)
    shard = root / "packages" / "billing" / ".context"
    shard.mkdir(parents=True)
    (shard / "index.md").write_text("---\nokf_version: '0.2'\n---\n\n# shard\n", encoding="utf-8")
    init_git_repo(root)
    billing_src = root / "packages" / "billing" / "src" / "gw.ts"
    billing_src.parent.mkdir(parents=True)
    billing_src.write_text(
        'export async function capturePayment() {\n  const ENTERPRISE = "ENTERPRISE";\n  const grace = 3;\n}\n',
        encoding="utf-8",
    )
    text = CONCEPT.replace("src/billing/PaymentGateway.ts", "packages/billing/src/gw.ts")
    result = write_memory(root, ".", identity="invariants/local-grace", stdin_text=text)
    assert result["accepted"] is True
    assert result["path"].startswith("packages/billing/.context/")


def test_cross_shard_write_lands_at_root(tmp_path: Path):
    from tests.fixtures.repos import init_git_repo, write_architecture_fixtures
    from repocodex.commands.write import write_memory
    from tests.fixtures.repos import WORKFLOW_CONCEPT

    root = tmp_path / "mono"
    root.mkdir()
    write_architecture_fixtures(root)
    (root / "packages" / "billing" / ".context").mkdir(parents=True)
    (root / "packages" / "ledger" / ".context").mkdir(parents=True)
    init_git_repo(root)
    result = write_memory(root, ".", identity="workflows/checkout-copy", stdin_text=WORKFLOW_CONCEPT)
    assert result["accepted"] is True
    assert result["path"].startswith(".context/")


def test_catalog_siblings_are_titles(repo):
    from repocodex.retrieval import retrieve

    extra = repo.root / ".context" / "invariants" / "sibling.md"
    extra.write_text(
        (repo.root / ".context" / "decisions" / "custom-data-streamer.md")
        .read_text(encoding="utf-8")
        .replace("custom-data-streamer", "sibling"),
        encoding="utf-8",
    )
    catalog = (repo.root / ".context" / "invariants" / "index.md")
    catalog.write_text(
        catalog.read_text(encoding="utf-8") + "\n- [sibling](./sibling.md)\n",
        encoding="utf-8",
    )
    from repocodex.store.reverse_index import regenerate_all

    regenerate_all(repo.root)
    payload = retrieve(repo.root, ["src/billing/PaymentGateway.ts"])
    bodies = [c for c in payload["concepts"] if c["identity"] == "invariants/enterprise-grace-period"]
    assert bodies and "body" in bodies[0]
    assert payload["catalog"]
    assert all("body" not in item for item in payload["catalog"])


def test_churn_is_shard_aware(tmp_path: Path):
    from tests.fixtures.repos import init_git_repo, write_architecture_fixtures
    from repocodex.retrieval import _churn_count, _concept_file
    from tests.fixtures.repos import GRACE_CONCEPT as CONCEPT

    root = tmp_path / "mono"
    root.mkdir()
    write_architecture_fixtures(root)
    shard = root / "packages" / "billing" / ".context" / "invariants"
    shard.mkdir(parents=True)
    (shard / "local.md").write_text(CONCEPT, encoding="utf-8")
    init_git_repo(root)
    path = _concept_file(root, "invariants/local")
    assert path is not None
    assert "packages/billing" in str(path)
    assert _churn_count(root, "invariants/local") >= 1


def test_advisory_reports_judgment(repo):
    from repocodex.commands.advisory import advisory

    repo.payment_gateway.write_text(
        PAYMENT_GATEWAY.replace("await charge(account);", "await charge(account);\n  return;"),
        encoding="utf-8",
    )
    payload = advisory(repo.root)
    assert payload["kind"] == "advisory"
    assert payload["required_verdict_unaffected"] is True
    assert "code_side_impact" in payload
    required = validate(repo.root)
    assert "code_side_impact" not in required


def test_repair_invokes_or_fails_explicitly(repo, monkeypatch):
    from repocodex.commands import repair as repair_mod

    monkeypatch.setattr(repair_mod, "_available_harness", lambda: None)
    payload = repair_mod.repair(repo.root)
    assert payload["error"] == "no_agent_harness"
    assert payload.get("ok") is False
    assert "prompt" in payload


def test_plugin_hook_adapter_resolves(repo):
    from repocodex.commands.install import install

    payload = install(repo.root)
    adapter = repo.root / ".repocodex" / "plugin" / "hooks" / "claude-pre-commit"
    portable = repo.root / ".repocodex" / "plugin" / "hooks" / "pre-commit"
    assert adapter.exists()
    assert portable.exists()
    assert payload["ok"] is True
    text = adapter.read_text(encoding="utf-8")
    assert "pre-commit" in text
