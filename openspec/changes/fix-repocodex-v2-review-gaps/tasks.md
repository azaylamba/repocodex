# Tasks: fix-repocodex-v2-review-gaps

Ordered by the migration plan in `design.md`: claims first (relaxes only), then shadow reporting, then the ratchet change it lets operators measure, then the independent reporting fixes, then conformance.

## 1. Claims declare their owning anchor

- [ ] 1.1 Add an optional `anchor` index to the `Claim` model in `schema.py` and confirm it round-trips through serialization
- [ ] 1.2 Add a failing test: a three-anchor concept whose claim names the billing anchor, with the literal in that anchor's terms and matched region, is accepted by the write gate
- [ ] 1.3 Add a failing test: removing the literal from the owning anchor produces exactly one `CLAIM_BROKEN` finding naming that anchor's path
- [ ] 1.4 Add a failing test: changing a non-owning anchor's file leaves `claim_findings` empty
- [ ] 1.5 Add a failing test: an out-of-range `anchor` index is rejected at write time with a reason naming the index
- [ ] 1.6 Lift the claim loop in `evaluate_write` out of the per-anchor loop and evaluate each claim against its owning anchor alone
- [ ] 1.7 Lift the claim loop in `evaluate_claims` the same way, attributing the finding to the owning anchor
- [ ] 1.8 Implement owner resolution for an omitted `anchor`: sole anchor, else the single anchor whose `all_of` declares the literal, else reject — with a test per branch including the ambiguous and undeclared rejections
- [ ] 1.9 Assert owner resolution is independent of anchor iteration order
- [ ] 1.10 Preserve claim ownership in `apply_anchor_patch` so a REANCHOR does not re-point or renumber a claim, with a test
- [ ] 1.11 Add a multi-anchor claim-carrying fixture to `tests/fixtures/repos.py` so later groups can reuse it
- [ ] 1.12 Confirm the `add-repocodex-v1` `BusinessWorkflow` archetype example is writable with a claim
- [ ] 1.13 Document the `anchor` field in architecture §5.3 alongside `literal` and `subject`

## 2. Shadow reports its reasons

- [ ] 2.1 Add a failing test: a shadow-posture verdict on a claim-breaking change carries `claim_broken` in `blocking_reasons` with `blocking` false
- [ ] 2.2 Add a failing test: shadow and ratchet verdicts on an identical change have equal `blocking_reasons` and differ only in `blocking` and `posture`
- [ ] 2.3 Add a failing test: the recorded metric's `rejection_reasons` equals the shadow verdict's `blocking_reasons`
- [ ] 2.4 Compute `blocking_reasons` identically in every posture in `commands/validate.py`; make only `blocking` posture-dependent
- [ ] 2.5 Record `rejection_reasons` from the computed list rather than the posture-filtered one

## 3. Ratchet discharge scoped to the attested region

- [ ] 3.1 Add a failing test: a new function appended outside every matched region of a covered file arms the ratchet even though all anchors classify `LIVE`
- [ ] 3.2 Add a failing test: a substantive hunk falling inside the matched region leaves `skipped_memory` empty
- [ ] 3.3 Add a failing test: modifying a pinning concept discharges the obligation regardless of hunk position
- [ ] 3.4 Add a helper that returns changed line ranges for a path under the caller's diff scope
- [ ] 3.5 Replace the `attested_identities` discharge in `commands/validate.py` with per-file hunk-versus-region comparison against the merged matched regions
- [ ] 3.6 Resolve unattributable line ranges toward arming, and cover that path with a test
- [ ] 3.7 Remove the `attested_identities` parameter from `skipped_memory` once no caller supplies it

## 4. Substantive-change detection honors the diff scope

- [ ] 4.1 Add a failing test: the same substantive change to a covered file yields identical `skipped_memory` and `blocking_reasons` before and after `git add`
- [ ] 4.2 Add a failing test: a whitespace-only reformat stays non-substantive once staged
- [ ] 4.3 Change the working-tree branch of `is_substantive_change` to diff against `HEAD`
- [ ] 4.4 Verify the staged and base branches are unaffected, with a test per scope

## 5. Metrics measure their named quantity

- [ ] 5.1 Add a failing test: a validation whose anchor drifts because its pinned code was deleted reports `false_drift_rate` as `0.0` while still reporting the drift in `lost`
- [ ] 5.2 Add a failing test: a validation run performs no concept-body load and no churn inference
- [ ] 5.3 Record drift classifications and reconcile outcomes as separate metric events and derive false drift over a window at read time
- [ ] 5.4 Remove the per-run `false_drift_rate` ratio that reports the raw drift rate
- [ ] 5.5 Remove the `retrieve(..., include_bodies=True)` call from `commands/validate.py`
- [ ] 5.6 Record per-turn cost from `repocodex context`, which already holds the served payload
- [ ] 5.7 Replace the `is not None` assertions in `test_metrics_carry_measured_values` with exact expectations

## 6. Repair reports invocation truthfully

- [ ] 6.1 Add a failing test: a harness that receives the prompt yields `invoked: true`; a harness that is only probed yields `invoked: false` with a distinguishing reason
- [ ] 6.2 Add a failing test: a harness whose invocation exits non-zero yields `invoked: false`, `ok: false`, and still carries the prompt, `lost`, and `candidates`
- [ ] 6.3 Deliver `REPAIR_PROMPT` on each supported harness's non-interactive entry point and derive `invoked` from that delivery's exit status
- [ ] 6.4 Remove the `returncode is not None` expression that makes `invoked` unconditionally true
- [ ] 6.5 Report an undeliverable harness with a reason distinct from `no_agent_harness`, keeping the existing absent-harness test passing

## 7. Escape hatch cannot be self-issued

- [ ] 7.1 Add a failing test: acknowledgment evidence attributable to the pull request author does not clear the check and reports `exemption_refused`
- [ ] 7.2 Add a failing test: a non-approving comment review carrying the token does not clear the check
- [ ] 7.3 Add a failing test: an approving review by another user clears the check and emits the audit entry and repair task
- [ ] 7.4 Filter the Action's review scan to approving reviews whose author differs from the pull request author
- [ ] 7.5 Add a failing test: the acknowledgment environment variable is ignored with no CI runner present and honored with one
- [ ] 7.6 Gate the `REPOCODEX_REVIEW_ACK_EVIDENCE` path in `_ack_evidence` on CI-runner detection
- [ ] 7.7 Confirm the tracked committed-record path still clears the check locally

## 8. Advisory distinguishes absent judgment from clean

- [ ] 8.1 Add a failing test: a category with no agent judgment is marked not evaluated rather than reported as an empty finding list
- [ ] 8.2 Add a failing test: a produced judgment carries the concept, path, and discrepancy
- [ ] 8.3 Replace the hardcoded empty `skipped_recipe_steps` and `churn_flags` with per-category evaluation status
- [ ] 8.4 Remove the fixed prose-versus-diff note that is emitted as though it were a finding
- [ ] 8.5 Keep and re-assert the existing guarantee that the advisory payload never affects the required verdict

## 9. Conformance is the agent-read loop

- [ ] 9.1 Delete `src/repocodex/conformance.py` and `tests/test_conformance.py`, including the scenario-to-test table
- [ ] 9.2 Confirm no dictionary or check maps scenario titles to test function names remains in the tree
- [ ] 9.3 Report this capability unsatisfied when no OKF bundle is present, with no table fallback
- [ ] 9.4 Confirm `repocodex context` and impact return linked concepts for a multi-file scenario so an agent can read why then code
- [ ] 9.5 Confirm the required check's blocking set is unchanged and contains no conformance or unmapped-scenario reason
- [ ] 9.6 Confirm the advisory surface is where scenario-integrity judgment is reported, and that it does not invoke a test runner
- [ ] 9.7 Record the requirements the separate self-hosting change must satisfy (same loop, applied to this repo)

## 10. Reconcile the superseded specification

- [ ] 10.1 Confirm the `fix-repocodex-v1-review-gaps` enforcement requirement is reconciled with its MODIFIED replacement, and that the withdrawn scenario appears nowhere in the suite
- [ ] 10.2 Confirm both removed pytest-based `conformance` requirements leave no residue in code, specs, or task lists

## 11. Documentation and closure

- [ ] 11.1 Clarify architecture §11.1 so "a LIVE pass requires no `.context/` hunk" is scoped to the region the anchor attests
- [ ] 11.2 Make architecture §16's false-drift and per-turn-cost definitions precise, and note where each is measured
- [ ] 11.3 Record claim ownership in architecture §5.3 alongside the `CLAIM_BROKEN` description
- [ ] 11.4 Add a §17.1 row for each blocking finding in this review
- [ ] 11.5 Note in architecture §2/§8 that scenario integrity is the agent reading retrieved why and then code, not a test suite
- [ ] 11.6 Run the engine-package suite and `openspec validate --all --strict`
- [ ] 11.7 Re-run the review probes and confirm the original `3 → 1` reproduction still blocks
