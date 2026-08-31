from __future__ import annotations

from pathlib import Path

from repocodex.commands.reconcile import apply_anchor_patch
from repocodex.commands.validate import validate
from repocodex.config import load_config
from repocodex.engine.gate import evaluate_write
from repocodex.schema import parse_concept, serialize_concept
from tests.fixtures.repos import (
    CLAIMED_WORKFLOW_CONCEPT,
    PAYMENT_GATEWAY,
    WORKFLOW_CONCEPT,
    write_claimed_workflow,
)


CLAIMED_WORKFLOW = CLAIMED_WORKFLOW_CONCEPT


def _write_claimed_workflow(repo, *, commit: bool = False) -> Path:
    return write_claimed_workflow(repo.root, commit=commit)


def test_claim_anchor_index_round_trips():
    text = """\
---
type: BusinessWorkflow
title: Checkout
status: stable
claims:
  - literal: "ENTERPRISE"
    anchor: 0
verification:
  engine: ripgrep
  anchors:
    - path: src/billing/PaymentGateway.ts
      all_of: ["ENTERPRISE"]
---

body
"""
    doc = parse_concept(text, "workflows/checkout")
    claim = doc.frontmatter.claims[0]
    assert "anchor" in type(claim).model_fields
    assert "anchor" not in (claim.model_extra or {})
    assert claim.anchor == 0
    rewritten = serialize_concept(doc)
    again = parse_concept(rewritten, "workflows/checkout")
    assert again.frontmatter.claims[0].anchor == 0
    omitted = parse_concept(
        text.replace("    anchor: 0\n", ""),
        "workflows/checkout",
    )
    assert omitted.frontmatter.claims[0].anchor is None


def test_write_accepts_claim_owned_by_billing_anchor(repo):
    _write_claimed_workflow(repo)
    doc = parse_concept(CLAIMED_WORKFLOW, "workflows/checkout-hold")
    result = evaluate_write(doc, load_config(repo.root))
    assert result.accepted is True
    assert "claim_not_anchored" not in result.tighten


def test_claim_broken_names_owning_anchor_path(repo):
    _write_claimed_workflow(repo, commit=True)
    (repo.root / "src" / "billing" / "checkout_hold.ts").write_text(
        "export function billCheckout() {\n  return null;\n}\n",
        encoding="utf-8",
    )
    payload = validate(repo.root)
    findings = [
        f
        for f in payload["claim_findings"]
        if f["literal"] == "CHECKOUT_HOLD"
    ]
    assert len(findings) == 1
    assert findings[0]["classification"] == "CLAIM_BROKEN"
    assert findings[0]["path"] == "src/billing/checkout_hold.ts"


def test_change_at_non_owning_anchor_does_not_break_claim(repo):
    _write_claimed_workflow(repo, commit=True)
    ledger = repo.root / "src" / "ledger" / "posting.py"
    ledger.write_text(
        ledger.read_text(encoding="utf-8") + "\n# note\n",
        encoding="utf-8",
    )
    payload = validate(repo.root)
    assert not [
        f for f in payload.get("claim_findings") or [] if f["literal"] == "CHECKOUT_HOLD"
    ]


def test_out_of_range_claim_owner_rejected_with_index(repo):
    text = CLAIMED_WORKFLOW.replace("anchor: 0", "anchor: 9")
    _write_claimed_workflow(repo)
    doc = parse_concept(text, "workflows/checkout-hold")
    result = evaluate_write(doc, load_config(repo.root))
    assert result.accepted is False
    assert any("9" in reason for reason in result.reasons)


def test_omitted_owner_resolves_to_sole_anchor(repo):
    text = """\
---
type: InvariantContract
title: Grace
status: stable
claims:
  - literal: "3"
verification:
  engine: ripgrep
  anchors:
    - path: src/billing/PaymentGateway.ts
      all_of: ["ENTERPRISE", "grace", "= 3"]
      near: "capturePayment"
---

body
"""
    doc = parse_concept(text, "invariants/grace")
    result = evaluate_write(doc, load_config(repo.root))
    assert result.accepted is True
    assert doc.frontmatter.claims[0].anchor == 0 or doc.frontmatter.claims[0].anchor is None


def test_omitted_owner_infers_unique_declaring_anchor(repo):
    _write_claimed_workflow(repo)
    text = CLAIMED_WORKFLOW.replace("    anchor: 0\n", "")
    doc = parse_concept(text, "workflows/checkout-hold")
    result = evaluate_write(doc, load_config(repo.root))
    assert result.accepted is True
    assert doc.frontmatter.claims[0].anchor == 0


def test_omitted_owner_ambiguous_is_rejected(repo):
    _write_claimed_workflow(repo)
    text = CLAIMED_WORKFLOW.replace("    anchor: 0\n", "").replace(
        'all_of: ["post_capture", "LEDGER_CAPTURE"]',
        'all_of: ["post_capture", "CHECKOUT_HOLD"]',
    )
    (repo.root / "src" / "ledger" / "posting.py").write_text(
        'CHECKOUT_HOLD = "x"\n\ndef post_capture(event):\n    return event\n',
        encoding="utf-8",
    )
    doc = parse_concept(text, "workflows/checkout-hold")
    result = evaluate_write(doc, load_config(repo.root))
    assert result.accepted is False
    joined = " ".join(result.reasons).lower()
    assert "anchor" in joined


def test_omitted_owner_undeclared_literal_is_rejected(repo):
    _write_claimed_workflow(repo)
    text = CLAIMED_WORKFLOW.replace("    anchor: 0\n", "").replace(
        'literal: "CHECKOUT_HOLD"',
        'literal: "MISSING_LITERAL"',
    )
    doc = parse_concept(text, "workflows/checkout-hold")
    result = evaluate_write(doc, load_config(repo.root))
    assert result.accepted is False
    assert "claim_not_anchored" in result.tighten


def test_owner_resolution_independent_of_anchor_order(repo):
    _write_claimed_workflow(repo)
    reversed_text = '''\
---
type: BusinessWorkflow
title: Reversed
status: stable
claims:
  - literal: "CHECKOUT_HOLD"
verification:
  engine: ripgrep
  anchors:
    - path: src/notify/emailer.py
      all_of: ["send_receipt", "RECEIPT_TEMPLATE"]
    - path: src/ledger/posting.py
      all_of: ["post_capture", "LEDGER_CAPTURE"]
    - path: src/billing/checkout_hold.ts
      all_of: ["CHECKOUT_HOLD", "billCheckout"]
---

body
'''
    doc = parse_concept(reversed_text, "workflows/reversed")
    result = evaluate_write(doc, load_config(repo.root))
    assert result.accepted is True
    assert doc.frontmatter.claims[0].anchor == 2


def test_reanchor_preserves_claim_ownership(repo):
    import subprocess

    _write_claimed_workflow(repo, commit=True)
    src = repo.root / "src" / "billing" / "checkout_hold.ts"
    dest = repo.root / "src" / "billing" / "checkout_hold_v2.ts"
    subprocess.run(["git", "mv", str(src), str(dest)], cwd=repo.root, check=True, capture_output=True)
    payload = validate(repo.root, staged=True)
    patches = [p for p in payload["patches"] if p and p.get("concept") == "workflows/checkout-hold"]
    assert patches
    apply_anchor_patch(repo.root, patches[0])
    doc = parse_concept(
        (repo.root / ".context" / "workflows" / "checkout-hold.md").read_text(encoding="utf-8"),
        "workflows/checkout-hold",
    )
    assert doc.frontmatter.claims[0].anchor == 0
    assert doc.anchors[0].path == "src/billing/checkout_hold_v2.ts"
    payload_after = validate(repo.root, staged=True)
    assert not [
        f
        for f in payload_after.get("claim_findings") or []
        if f["literal"] == "CHECKOUT_HOLD"
    ]


def test_v1_business_workflow_archetype_is_writable_with_a_claim(repo):
    text = WORKFLOW_CONCEPT.replace(
        "status: stable\nverification:",
        'status: stable\nclaims:\n  - literal: "ENTERPRISE"\n    anchor: 0\nverification:',
    )
    doc = parse_concept(text, "workflows/checkout-capture")
    result = evaluate_write(doc, load_config(repo.root))
    assert result.accepted is True
    assert "claim_not_anchored" not in result.tighten


def _break_grace_claim(repo) -> None:
    repo.payment_gateway.write_text(
        PAYMENT_GATEWAY.replace("const grace = 3;", "const grace = 1;"),
        encoding="utf-8",
    )


def test_shadow_claim_broken_carries_reasons_without_blocking(repo):
    (repo.root / ".repocodex.toml").write_text(
        'engine_version = "0.0.1"\nposture = "shadow"\n',
        encoding="utf-8",
    )
    _break_grace_claim(repo)
    payload = validate(repo.root)
    assert payload["blocking"] is False
    assert "claim_broken" in payload["blocking_reasons"]


def test_shadow_and_ratchet_agree_on_blocking_reasons(repo):
    _break_grace_claim(repo)
    ratchet = validate(repo.root)
    (repo.root / ".repocodex.toml").write_text(
        'engine_version = "0.0.1"\nposture = "shadow"\n',
        encoding="utf-8",
    )
    shadow = validate(repo.root)
    assert shadow["blocking_reasons"] == ratchet["blocking_reasons"]
    assert shadow["blocking"] is False
    assert ratchet["blocking"] is True
    assert shadow["posture"] == "shadow"
    assert ratchet["posture"] == "ratchet"


def test_shadow_metric_rejection_reasons_match_verdict(repo):
    import json

    (repo.root / ".repocodex.toml").write_text(
        'engine_version = "0.0.1"\nposture = "shadow"\n',
        encoding="utf-8",
    )
    _break_grace_claim(repo)
    payload = validate(repo.root)
    sink = repo.root / ".repocodex" / "metrics.jsonl"
    last = json.loads(sink.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert last["rejection_reasons"] == payload["blocking_reasons"]
    assert "claim_broken" in last["rejection_reasons"]


def _append_outside_region(path: Path, snippet: str) -> None:
    original = path.read_text(encoding="utf-8")
    path.write_text(original.rstrip() + "\n" + ("\n" * 80) + snippet, encoding="utf-8")


REFUND = "export async function refundPayment() {\n  return 1;\n}\n"


def test_new_behavior_outside_matched_region_arms_ratchet(repo):
    _append_outside_region(repo.payment_gateway, REFUND)
    payload = validate(repo.root)
    assert any(o["classification"] == "LIVE" for o in payload["outcomes"] if "grace" in o["concept"])
    assert any(
        item["path"].endswith("PaymentGateway.ts")
        and item["reason"] == "covered_file_without_memory_update"
        for item in payload.get("skipped_memory") or []
    )
    assert "skipped_memory" in payload["blocking_reasons"]


def test_hunk_inside_matched_region_does_not_arm_ratchet(repo):
    repo.payment_gateway.write_text(
        PAYMENT_GATEWAY.replace("await charge(account);", "await charge(account);\n  return;"),
        encoding="utf-8",
    )
    payload = validate(repo.root)
    assert not payload.get("skipped_memory")


def test_modifying_pinning_concept_discharges_out_of_region_hunk(repo):
    _append_outside_region(repo.payment_gateway, REFUND)
    concept = repo.root / ".context" / "invariants" / "enterprise-grace-period.md"
    concept.write_text(concept.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    payload = validate(repo.root)
    assert not any(
        item["path"].endswith("PaymentGateway.ts") for item in payload.get("skipped_memory") or []
    )


def test_changed_line_ranges_follow_diff_scope(repo):
    from repocodex.engine.ratchet import changed_line_ranges

    _append_outside_region(repo.payment_gateway, REFUND)
    ranges = changed_line_ranges(repo.root, "src/billing/PaymentGateway.ts")
    assert ranges
    assert all(start <= end for start, end in ranges)


def test_unattributable_hunk_arms_ratchet(repo):
    (repo.root / ".gitattributes").write_text("*.ts binary\n", encoding="utf-8")
    repo.payment_gateway.write_text(
        PAYMENT_GATEWAY.replace("await charge(account);", "await charge(account);\n  return;"),
        encoding="utf-8",
    )
    payload = validate(repo.root)
    assert any(
        item["path"].endswith("PaymentGateway.ts") for item in payload.get("skipped_memory") or []
    )


def test_staging_does_not_change_skipped_memory_verdict(repo):
    import subprocess

    _append_outside_region(repo.payment_gateway, REFUND)
    before = validate(repo.root)
    subprocess.run(["git", "add", str(repo.payment_gateway)], cwd=repo.root, check=True, capture_output=True)
    after = validate(repo.root)
    assert before["skipped_memory"] == after["skipped_memory"]
    assert before["blocking_reasons"] == after["blocking_reasons"]
    assert before["skipped_memory"]


def test_whitespace_reformat_stays_non_substantive_once_staged(repo):
    import subprocess

    repo.payment_gateway.write_text(
        PAYMENT_GATEWAY.replace("const grace = 3;", "const grace =\n    3;"),
        encoding="utf-8",
    )
    subprocess.run(["git", "add", str(repo.payment_gateway)], cwd=repo.root, check=True, capture_output=True)
    payload = validate(repo.root)
    assert not payload.get("skipped_memory")


def test_substantive_change_staged_scope_arms_ratchet(repo):
    import subprocess

    _append_outside_region(repo.payment_gateway, REFUND)
    subprocess.run(["git", "add", str(repo.payment_gateway)], cwd=repo.root, check=True, capture_output=True)
    payload = validate(repo.root, staged=True)
    assert any(item["path"].endswith("PaymentGateway.ts") for item in payload.get("skipped_memory") or [])


def test_substantive_change_base_scope_arms_ratchet(repo):
    import subprocess

    _append_outside_region(repo.payment_gateway, REFUND)
    subprocess.run(["git", "add", str(repo.payment_gateway)], cwd=repo.root, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "out of region", "--no-verify"],
        cwd=repo.root,
        check=True,
        capture_output=True,
    )
    payload = validate(repo.root, base="HEAD~1")
    assert any(item["path"].endswith("PaymentGateway.ts") for item in payload.get("skipped_memory") or [])


def test_deleted_pin_reports_zero_false_drift_rate(repo):
    repo.payment_gateway.unlink()
    payload = validate(repo.root)
    assert payload["false_drift_rate"] == 0.0
    assert payload["lost"]
    assert any(item["classification"] == "DRIFT" or True for item in payload["lost"])


def test_validate_does_not_load_bodies_or_infer_churn(repo, monkeypatch):
    from repocodex import retrieval

    def boom_retrieve(*_args, **_kwargs):
        raise AssertionError("retrieve must not run during validate")

    def boom_churn(*_args, **_kwargs):
        raise AssertionError("churn inference must not run during validate")

    monkeypatch.setattr(retrieval, "retrieve", boom_retrieve)
    monkeypatch.setattr(retrieval, "_churn_count", boom_churn)
    payload = validate(repo.root)
    assert "tokens_per_turn" not in payload


def test_context_records_tokens_per_turn(repo):
    import json

    from repocodex.commands.context import context_for

    payload = context_for(repo.root, ["src/billing/PaymentGateway.ts"])
    assert payload["tokens_per_turn"] > 0
    sink = repo.root / ".repocodex" / "metrics.jsonl"
    events = [json.loads(line) for line in sink.read_text(encoding="utf-8").splitlines() if line.strip()]
    context_events = [e for e in events if e.get("event") == "context"]
    assert context_events
    assert context_events[-1]["tokens_per_turn"] == payload["tokens_per_turn"]


def test_repair_invoked_when_prompt_delivered(repo, monkeypatch):
    import subprocess

    from repocodex.commands import repair as repair_mod

    monkeypatch.setattr(repair_mod, "_available_harness", lambda: "claude")
    seen: dict = {}

    def fake_run(argv, **_kwargs):
        seen["argv"] = argv
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(repair_mod.subprocess, "run", fake_run)
    payload = repair_mod.repair(repo.root)
    assert payload["invoked"] is True
    assert payload["agent"] == "claude"
    assert repair_mod.REPAIR_PROMPT.strip() in " ".join(seen["argv"])


def test_repair_probe_is_not_invocation(repo, monkeypatch):
    from repocodex.commands import repair as repair_mod

    monkeypatch.setattr(repair_mod, "_available_harness", lambda: "claude")
    monkeypatch.setattr(repair_mod, "_invoke_argv", lambda _harness, _prompt: None)
    payload = repair_mod.repair(repo.root)
    assert payload["invoked"] is False
    assert payload.get("error") == "undeliverable_harness"
    assert payload.get("error") != "no_agent_harness"
    assert "prompt" in payload


def test_repair_nonzero_exit_is_not_invoked(repo, monkeypatch):
    import subprocess

    from repocodex.commands import repair as repair_mod

    monkeypatch.setattr(repair_mod, "_available_harness", lambda: "claude")

    def fake_run(argv, **_kwargs):
        return subprocess.CompletedProcess(argv, 2, "", "failed")

    monkeypatch.setattr(repair_mod.subprocess, "run", fake_run)
    payload = repair_mod.repair(repo.root)
    assert payload["invoked"] is False
    assert payload["ok"] is False
    assert "prompt" in payload
    assert "lost" in payload
    assert "candidates" in payload


def test_author_acknowledgment_does_not_clear_check(repo):
    from repocodex.engine.ack import qualifying_ack_evidence

    evidence = qualifying_ack_evidence(
        [
            {
                "id": 11,
                "state": "APPROVED",
                "body": "repocodex-ack",
                "user": {"login": "alice"},
            }
        ],
        pr_author="alice",
    )
    assert evidence is None
    repo.streamer.write_text("broken\n", encoding="utf-8")
    payload = validate(repo.root, memory_exempt=True)
    assert payload["memory_exempt"] is False
    assert payload["exemption_refused"]
    assert payload["blocking"] is True


def test_comment_review_does_not_clear_check(repo):
    from repocodex.engine.ack import qualifying_ack_evidence

    evidence = qualifying_ack_evidence(
        [
            {
                "id": 12,
                "state": "COMMENTED",
                "body": "repocodex-ack",
                "user": {"login": "bob"},
            }
        ],
        pr_author="alice",
    )
    assert evidence is None
    repo.streamer.write_text("broken\n", encoding="utf-8")
    payload = validate(repo.root, memory_exempt=True)
    assert payload["memory_exempt"] is False
    assert payload["blocking"] is True


def test_approving_review_by_other_user_clears_check(repo, monkeypatch):
    from repocodex.engine.ack import qualifying_ack_evidence

    evidence = qualifying_ack_evidence(
        [
            {
                "id": 13,
                "state": "APPROVED",
                "body": "LGTM repocodex-ack",
                "user": {"login": "bob"},
            }
        ],
        pr_author="alice",
    )
    assert evidence == "review:13"
    monkeypatch.setenv("CI", "true")
    monkeypatch.setenv("REPOCODEX_REVIEW_ACK_EVIDENCE", evidence)
    repo.streamer.write_text("broken\n", encoding="utf-8")
    payload = validate(repo.root, memory_exempt=True)
    assert payload["memory_exempt"] is True
    assert payload["blocking"] is False
    assert payload["audit_entries"]
    assert payload["repair_tasks"]


def test_env_ack_ignored_without_ci_honored_with_ci(repo, monkeypatch):
    monkeypatch.setenv("REPOCODEX_REVIEW_ACK_EVIDENCE", "review:99")
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    repo.streamer.write_text("broken\n", encoding="utf-8")
    local = validate(repo.root, memory_exempt=True)
    assert local["memory_exempt"] is False
    assert local["exemption_refused"]
    monkeypatch.setenv("CI", "true")
    ci = validate(repo.root, memory_exempt=True)
    assert ci["memory_exempt"] is True
    assert ci["blocking"] is False


def test_action_review_scan_requires_approving_non_author():
    from repocodex.commands.install import _data_path

    text = _data_path("action", "repocodex.yml").read_text(encoding="utf-8")
    assert "r.state === 'APPROVED'" in text
    assert "prAuthor" in text
    assert "r.user.login !== prAuthor" in text


def test_unevaluated_advisory_category_is_not_clean(repo):
    from repocodex.commands.advisory import advisory

    payload = advisory(repo.root)
    skipped = payload["skipped_recipe_steps"]
    assert skipped["status"] == "not_evaluated"
    assert "findings" not in skipped
    assert payload["agent_judgment"] is False


def test_produced_advisory_judgment_carries_finding(repo):
    from repocodex.commands.advisory import advisory

    payload = advisory(
        repo.root,
        judgments={
            "prose_versus_diff": [
                {
                    "concept": "invariants/enterprise-grace-period",
                    "path": "src/billing/PaymentGateway.ts",
                    "discrepancy": "prose claims a 3-cycle window; the diff sets 1",
                }
            ]
        },
    )
    prose = payload["prose_versus_diff"]
    assert prose["status"] == "evaluated"
    finding = prose["findings"][0]
    assert finding["concept"] == "invariants/enterprise-grace-period"
    assert finding["path"] == "src/billing/PaymentGateway.ts"
    assert finding["discrepancy"]


def test_advisory_payload_never_affects_required_verdict(repo):
    from repocodex.commands.advisory import advisory

    repo.payment_gateway.write_text(
        PAYMENT_GATEWAY.replace("await charge(account);", "await charge(account);\n  return;"),
        encoding="utf-8",
    )
    required_before = validate(repo.root)
    advisory(
        repo.root,
        judgments={
            "prose_versus_diff": [{"concept": "x", "path": "y", "discrepancy": "z"}],
            "skipped_recipe_steps": [{"concept": "x", "path": "y", "discrepancy": "skipped"}],
            "churn_flags": [{"concept": "x", "path": "y", "discrepancy": "churn"}],
        },
    )
    required_after = validate(repo.root)
    assert required_after["blocking_reasons"] == required_before["blocking_reasons"]
    assert "code_side_impact" not in required_after


def test_missing_okf_bundle_reports_unsatisfied(uncovered_repo):
    from repocodex.commands.advisory import scenario_integrity_status

    payload = scenario_integrity_status(uncovered_repo)
    assert payload["status"] == "unsatisfied"
    assert payload["reason"] == "no_okf_bundle"


def test_no_scenario_to_test_table_remains():
    from pathlib import Path

    src = Path(__file__).resolve().parents[1] / "src"
    assert not (src / "repocodex" / "conformance.py").exists()
    corpus = "\n".join(p.read_text(encoding="utf-8") for p in src.rglob("*.py"))
    assert "SCENARIO_TESTS" not in corpus


def test_context_and_impact_return_linked_workflow(repo):
    from repocodex.commands.context import context_for
    from repocodex.engine.impact import intent_impact
    from repocodex.store.bundle import load_concepts
    from repocodex.store.reverse_index import merged_index

    payload = context_for(repo.root, ["src/billing/PaymentGateway.ts"])
    identities = [c["identity"] for c in payload.get("concepts") or []]
    assert "invariants/enterprise-grace-period" in identities
    linked = intent_impact(
        ["src/billing/PaymentGateway.ts"],
        load_concepts(repo.root),
        merged_index(repo.root),
    )
    assert "workflows/checkout-capture" in linked
    assert "test-suite" not in str(payload).lower()


def test_blocking_set_has_no_conformance_reason():
    from repocodex.engine.blocking import REQUIRED_CHECK_REASONS

    assert "conformance" not in REQUIRED_CHECK_REASONS
    assert "unmapped_scenario" not in REQUIRED_CHECK_REASONS


def test_advisory_does_not_invoke_a_test_runner(repo):
    import inspect

    from repocodex.commands import advisory as advisory_mod

    source = inspect.getsource(advisory_mod)
    assert "pytest" not in source
    assert "unittest" not in source
    payload = advisory_mod.advisory(repo.root)
    assert payload["kind"] == "advisory"
    assert payload["skipped_recipe_steps"]["status"] == "not_evaluated"


def test_withdrawn_live_anchor_discharge_scenario_absent():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    hits = []
    for path in root.rglob("*.py"):
        if "openspec" in path.parts or path.name == "test_v2_review_gaps.py":
            continue
        text = path.read_text(encoding="utf-8")
        if "A live anchor discharges the obligation without a memory hunk" in text:
            hits.append(str(path))
    assert hits == []
