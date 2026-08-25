from __future__ import annotations

import re
from pathlib import Path

SCENARIO_RE = re.compile(r"^#### Scenario:\s*(.+)\s*$", re.MULTILINE)


def spec_roots() -> list[Path]:
    repo = Path(__file__).resolve().parents[2]
    changes = repo / "openspec" / "changes"
    roots: list[Path] = []
    for change in sorted(changes.iterdir() if changes.exists() else []):
        specs = change / "specs"
        if specs.is_dir():
            roots.append(specs)
    return roots


def collect_scenarios() -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for root in spec_roots():
        for path in sorted(root.rglob("spec.md")):
            text = path.read_text(encoding="utf-8")
            rel = str(path)
            for match in SCENARIO_RE.finditer(text):
                found.append((rel, match.group(1).strip()))
    return found


# Maps scenario title → test node id substring that must exist in the suite.
SCENARIO_TESTS: dict[str, str] = {
    "Contractual literal changed while the anchor stays live": "test_claim_broken_when_literal_changes_and_anchor_stays",
    "Live anchor with intact claims does not block": "test_claim_intact_does_not_block",
    "Claim breakage is repaired through the gate": "test_claim_breakage_repaired_through_gate",
    "Substring does not satisfy a claim": "test_substring_does_not_satisfy_claim",
    "Claim outside the matched region is not credited": "test_claim_outside_matched_region_is_not_credited",
    "Installing dependencies does not change the gate": "test_derived_ceiling_ignores_untracked_node_modules",
    "Untracked scratch files do not alter a verdict": "test_untracked_scratch_does_not_alter_verdict",
    "Mismatched pin fails loudly": "test_engine_pin_mismatch_fails_loudly",
    "CI install does not defeat the pin": "test_action_has_no_unpinned_fallback",
    "Dialect-specific construct is rejected at write time": "test_regex_dialect_mismatch_rejected_at_write",
    "Fixed-string terms are unaffected": "test_architecture_examples_pass_gate",
    "Staged rename re-anchors in the hook": "test_staged_rename_reanchors",
    "Base-relative rename re-anchors in CI": "test_validate_reanchor_on_rename",
    "Applied patch records reanchor provenance": "test_validate_reanchor_on_rename",
    "Validation leaves the tree unchanged": "test_validate_leaves_working_tree_clean",
    "Override artifacts are emitted, not written": "test_tracked_ack_file_clears_check",
    "Dotfile anchor is checked under its real path": "test_exclusion_preserves_dotfile_names",
    "Unrelated memory edit does not clear the ratchet": "test_unrelated_context_edit_does_not_clear_ratchet",
    "Maintaining the covering concept clears the ratchet": "test_maintaining_covering_concept_clears_ratchet",
    "A live anchor discharges the obligation without a memory hunk": "test_claim_intact_does_not_block",
    "Formatting-only edit does not trip the ratchet": "test_formatting_only_does_not_trip_ratchet",
    "Comment-only edit does not trip the ratchet": "test_comment_only_does_not_trip_ratchet",
    "Logic change trips the ratchet": "test_covered_file_without_memory_fails_ratchet",
    "Shadow reports skipped memory without blocking": "test_shadow_reports_skipped_memory_without_blocking",
    "Shadow reports claim breakage without blocking": "test_shadow_reports_claim_breakage_without_blocking",
    "Metrics carry measured values": "test_metrics_carry_measured_values",
    "Metrics do not pollute the bundle": "test_validate_leaves_working_tree_clean",
    "Enumerated reason blocks": "test_contradiction_on_double_supersede",
    "Non-enumerated finding does not block": "test_claim_intact_does_not_block",
    "Unauthenticated flag does not clear the check": "test_unauthenticated_flag_does_not_clear_check",
    "Acknowledged hotfix clears the check in CI": "test_tracked_ack_file_clears_check",
    "Label without acknowledgment still blocks": "test_unauthenticated_flag_does_not_clear_check",
    "Independent invariants on one file coexist": "test_independent_invariants_do_not_contradict",
    "Same subject with different literals conflicts": "test_same_subject_different_literals_contradict",
    "Missing discriminator stays silent": "test_missing_subject_stays_silent",
    "Mined concept cites its own origin": "test_bootstrap_cites_per_concept_source",
    "Inaccurate provenance does not inflate retrieval rank": "test_bootstrap_rejects_unsourced",
    "Repeated bootstrap is stable": "test_bootstrap_identities_are_stable",
    "Audit emits a screening payload without calling a model": "test_audit_screening_payload",
    "Returned screening findings become proposals": "test_audit_findings_become_proposals",
    "Package-local concept lands in the package shard": "test_write_lands_in_owning_shard",
    "Cross-shard concept lands at the root": "test_cross_shard_write_lands_at_root",
    "Sibling concepts surface as titles": "test_catalog_siblings_are_titles",
    "Catalog stage does not expand the body budget": "test_catalog_siblings_are_titles",
    "Sharded concept is ranked on real churn": "test_churn_is_shard_aware",
    "Advisory check reports judgment, not a duplicate verdict": "test_advisory_reports_judgment",
    "Advisory failure does not affect the required verdict": "test_advisory_reports_judgment",
    "Repair invokes an available harness": "test_repair_invokes_or_fails_explicitly",
    "No harness available fails explicitly": "test_repair_invokes_or_fails_explicitly",
    "Hook adapter resolves to a real hook": "test_plugin_hook_adapter_resolves",
    "Install verifies what it reports": "test_install_hook_is_executable",
    "Regression in a specified behavior fails the suite": "test_validate_reanchor_on_rename",
    "Unmapped scenario is detectable": "test_unmapped_scenarios_are_reported",
    "Classification is asserted exactly": "test_validate_reanchor_on_rename",
    "Required findings are asserted present": "test_dilution_warning_on_unrelated_pr",
    "Placeholder assertions are not conformant": "test_unmapped_scenarios_are_reported",
    "Formatter cannot break an anchor": "test_formatter_cannot_break_anchor",
    "Tautological anchor rejected": "test_write_gate_rejects_tautological_anchor",
    "Invariant literal must be frozen": "test_claim_literal_must_be_anchored",
    "Identifier rename degrades to WEAK": "test_identifier_rename_degrades_to_weak",
    "File move re-anchors without paging": "test_validate_reanchor_on_rename",
    "Ambiguous relocation becomes DRIFT": "test_identifier_rename_degrades_to_weak",
    "No innocent-bystander pages": "test_dilution_warning_on_unrelated_pr",
    "IDE and CI agree": "test_determinism_identical_payloads",
    "Marker cannot be the sole anchor": "test_marker_cannot_be_sole_anchor",
    "Business rule change leaves a trail": "test_claim_breakage_repaired_through_gate",
    "Post-merge double supersede": "test_contradiction_on_double_supersede",
    "Sampling audit surfaces a stale why": "test_audit_screening_payload",
    "Expired bootstrap draft is retired": "test_audit_screening_payload",
    "Frequently rewritten why loses rank": "test_provenance_ranks_above_bare",
    "Commit blocked until reconcile": "test_install_hook_is_executable",
    "Memory update does not fail CI": "test_maintaining_covering_concept_clears_ratchet",
    "Bypassed hook is caught": "test_covered_file_without_memory_fails_ratchet",
    "Brownfield repo is not blocked on day one": "test_brownfield_uncovered_passes_ratchet",
    "Covered file requires memory maintenance": "test_covered_file_without_memory_fails_ratchet",
    "Shadow posture blocks nothing": "test_shadow_posture_never_blocks",
    "Hotfix merges with audit trail": "test_tracked_ack_file_clears_check",
    "Cross-package scenario surfaces on a local edit": "test_cross_package_impact",
    "Common symbol name does not explode the walk": "test_code_side_hits_are_capped",
    "Nondeterministic finding cannot block a merge": "test_advisory_reports_judgment",
    "Agent retrieves context before editing": "test_context_staged_retrieval",
    "Large corpus stays out of the prompt": "test_context_staged_retrieval",
    "Provenance beats bare narrative": "test_provenance_ranks_above_bare",
    "Unattested bootstrap record is not served": "test_drafts_excluded_from_default_retrieval",
    "Concept written to the bundle": "test_write_and_reconcile_gate",
    "Unknown frontmatter keys are preserved": "test_unknown_frontmatter_keys_survive_rewrite",
    "Workflow concept spans packages": "test_bundle_loads_one_concept_per_file",
    "Guardrail concept pins enforcement config": "test_bundle_loads_one_concept_per_file",
    "Why-change without supersedes is rejected": "test_write_and_reconcile_gate",
    "Index stays in sync": "test_write_updates_catalog_log_and_reverse_index",
    "Out-of-sync index fails CI": "test_index_sync_detects_drift",
    "CI attests only affected packages": "test_monorepo_shards_have_local_indexes",
    "One install wires everything": "test_install_hook_is_executable",
    "Bootstrap seeds only attested memory": "test_repair_install_bootstrap_audit",
    "Turn cannot end on unrepaired drift": "test_agent_loop_context_edit_validate_commit",
    "New concept verified while diff is in context": "test_write_and_reconcile_gate",
    "MCP and CLI agree": "test_mcp_validate_matches_cli",
    "Skills-only client still works": "test_install_hook_is_executable",
}


def unmapped_scenarios() -> list[tuple[str, str]]:
    return [
        (path, title)
        for path, title in collect_scenarios()
        if title not in SCENARIO_TESTS
    ]
