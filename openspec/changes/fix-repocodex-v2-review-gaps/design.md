# Design: fix-repocodex-v2-review-gaps

## Context

`fix-repocodex-v1-review-gaps` shipped 48 tasks against an 83-test suite that passes. The regression it targeted is genuinely closed, and the determinism, single-writer, and engine-pin requirements verify against the running engine. The findings in this change come from probing the *new* code rather than re-reading the specs, and they fall into three groups with different root causes.

The first group is a scope error the v1-review-gaps specs made and the implementation inherited faithfully. That change correctly identified that a global `context_touched` flag was too coarse, and replaced it with per-file correspondence. But one of its scenarios — "A live anchor discharges the obligation without a memory hunk" — also made an attesting anchor sufficient to discharge the obligation. Architecture §11.1 says a LIVE pass requires no `.context/` hunk, and that is true *about the region the anchor attests*. Generalized to the whole file it inverts the ratchet: appending a new function to a covered file leaves the anchors LIVE, so the obligation is discharged and the required check passes. The specification is the defect here, so this change withdraws that scenario rather than working around it.

The second group is over-tightening. The v1-review-gaps change required claims to be evaluated against the anchor's matched region rather than falling back to the whole file, which was right. The implementation put that check inside the per-anchor loop in both `evaluate_write` and `evaluate_claims`, which turned "the literal must be in a matched region" into "the literal must be in every matched region". That makes multi-anchor concepts with claims unwritable and would make committed ones permanently blocking, so the architecture's own `BusinessWorkflow` archetype cannot carry a claim.

The third group is surfaces that report more confidence than they hold: `shadow` returns an empty reason list, `false_drift_rate` returns the drift rate, `repocodex repair` returns `invoked: true` after running `--help`, the `memory-exempt` acknowledgment scan does not filter by review state or author, and the conformance map records coverage several mapped tests do not provide. Each of these passes its own test, which is the point: the tests assert the shape of the output rather than its truth.

## Goals / Non-Goals

**Goals:**

- Make claim evaluation satisfiable by a single anchor at both write time and validate time, so multi-anchor concepts can carry claims.
- Restore the ratchet's ability to fire on new behavior in covered files, and withdraw the specification that prevented it.
- Make the ratchet's verdict invariant under `git add`.
- Make `shadow` produce the measurement that justifies promotion out of `shadow`.
- Make each reporting surface state what it actually established, and remove the metric computation from the validation hot path.
- Remove the scenario-to-test table. Scenario integrity is an agent reading retrieved OKF and then the code; the required check only attests that the why is still pinned.

**Non-Goals:**

- Revisiting anything `fix-repocodex-v1-review-gaps` established and this review verified: `CLAIM_BROKEN` as a classification, the closed blocking set, the determinism-inputs rule, the single-writer rule, engine-pin enforcement, shard-local placement, subject-scoped contradiction. These are unchanged.
- Changing the anchor format, the liveness classes, the posture model, or the determinism split.
- Making the advisory check produce agent judgment. This change requires it to *report the absence* of judgment honestly; wiring an agent into that job is separate work.
- Creating RepoCodex's own `.context/` bundle. Self-hosting is a separate change; this one specifies the agent-read loop and reports the capability unsatisfied until that bundle exists.
- Using a test suite to verify that application (or engine) scenarios still hold. Engine-package tests may still pin the CLI and the attester as implementation scaffolding; they are not the product's scenario-verification path.

## Decisions

### Each claim declares the anchor that owns it

Add an optional `anchor` field to the `Claim` model holding an index into `verification.anchors`. Move the claim loop outside the per-anchor loop in both `evaluate_write` and `evaluate_claims`, and evaluate each claim against its owning anchor alone. `CLAIM_BROKEN` then names the owning anchor without inference, and anchors that were never supposed to carry a literal stop contributing findings.

*Alternative considered:* an any-anchor rule, where a claim holds if some anchor carries the literal. It needs no schema change and reaches the same verdicts for every concept writable today. Rejected because it is weaker than it looks: a concept that genuinely needs a literal at a specific site cannot say so, and a literal that survives at an incidental anchor while disappearing from the site that matters would report as intact. Explicit ownership makes the intent checkable rather than inferred.

*Migration:* none is required, and the current bug is why. Conjunctive matching means no multi-anchor concept carrying a claim can exist in any bundle, so the only concepts in the field are single-anchor. Resolution for an omitted `anchor` is therefore: the sole anchor when there is one; otherwise the single anchor whose `all_of` declares the literal; otherwise reject the write and ask the author to declare it. That is deterministic, independent of iteration order, and leaves existing bundles untouched.

*Anchor reference form:* the index, matching the `anchor_index` already used by `AnchorOutcome` and the REANCHOR patch. Referencing by path would survive reordering, but a concept may legitimately hold two anchors on one path, so the path is not a key. Since `apply_anchor_patch` mutates an anchor in place and never reorders, the index is stable in practice; the write gate rejects an out-of-range index, and re-anchoring must preserve ownership.

### Ratchet discharge is decided by hunk position relative to matched regions

Replace the `attested_identities` set with a per-file decision. For a covered file with substantive change and no pinning concept added or modified on the run, compute the changed line ranges from the same diff scope the validation used, and compare them to the matched regions of that file's pinning anchors. The obligation is discharged when every substantive hunk falls inside some matched region; otherwise it is armed.

*Alternative considered:* arm the ratchet on any substantive change to a covered file, regardless of anchor state, and rely on the memory update to clear it. That is the strictest reading of architecture §11.3 and needs no region arithmetic, but it forces a `.context/` touch for in-region edits that the anchor already attests, which is the memory churn §11.1 exists to prevent. Region comparison costs one line-range intersection per covered file against regions already computed for liveness, so the precision is nearly free.

*Ambiguity resolution:* when line ranges cannot be attributed — a file with no matched regions, or a diff the engine cannot map to line numbers — resolve toward arming. A false block is recoverable by writing memory; a false pass is the failure this project exists to prevent. This matches the direction v1-review-gaps chose for substantive-change detection, and inverts it here deliberately because the consequence is inverted.

### Substantive-change detection takes the diff scope as a parameter it already receives

`is_substantive_change` already accepts `staged` and `base`. The working-tree branch runs a bare `git diff`, which sees unstaged content only, while `changed_files` reaches the same scope through a fallback that unions staged, unstaged, and untracked. Change the working-tree branch to `git diff HEAD` so both scopes see the same content. The staged and base branches are already correct and are unchanged.

*Alternative considered:* have `changed_files` stop unioning staged content in working-tree scope, so the two agree by narrowing instead of widening. Rejected: an agent that stages part of its work and then validates should still be told about it, and the pre-commit hook depends on staged content being visible.

### Shadow differs from ratchet in one field

Compute `blocking_reasons` identically in every posture and let only `blocking` depend on posture. The current code branches earlier, producing an empty `emitted_reasons` in `shadow` that also empties the recorded `rejection_reasons`. Since `shadow` exists to measure what enforcement would cost before enabling it, the reason distribution is its primary output.

### False drift is measured at repair, not at classification

`false_drift_rate` cannot be computed from a single validation, because whether a `DRIFT` was false is only known once the anchor is re-pointed and the new region turns out to be equivalent to the pinned one. Record drift classifications and reconcile outcomes as separate metric events and derive the rate over a window at read time. The verdict field stops reporting a per-run ratio that is really the drift rate.

*Alternative considered:* rename the field to `drift_rate` and keep it. Rejected because the posture-promotion criterion in architecture §16 is specifically about *false* drift — the rate at which the engine pages a human for a rename it should have followed — and a drift rate does not answer it.

### Per-turn cost is recorded by the retrieval path, not recomputed by validation

`validate` currently calls `retrieve(..., include_bodies=True)` solely to size a metric, which runs per-concept `git log` churn inference inside the pre-commit hook and every CI run. Move the measurement to `repocodex context`, which is the surface that actually serves a turn and already has the payload in hand. Validation stops computing it.

### Repair reports invocation, and probing is not invocation

`repocodex repair` builds `REPAIR_PROMPT` and never sends it; it runs `[harness, "--help"]` and derives `invoked` from `returncode is not None`, which is always true. Deliver the prompt on the harness's documented non-interactive entry point and report `invoked` from the delivery's exit status. When the engine chooses not to deliver — no known non-interactive invocation for that harness — report `invoked: false` with a reason distinct from `no_agent_harness`, and keep carrying the prompt and candidates so the caller can drive the repair.

### Acknowledgment is an approving review by someone other than the author

Filter the Action's `listReviews` scan to `state === 'APPROVED'` and `user.login !== pull_request.user.login` before matching the acknowledgment token. On the engine side, honor `REPOCODEX_REVIEW_ACK_EVIDENCE` only when a CI runner is detected, so the variable cannot clear a check on a developer machine. The tracked committed-record path is unchanged and remains the local mechanism.

*Alternative considered:* require a signed commit or a `CODEOWNERS`-derived approver list. Rejected as disproportionate for V1; approving-review-by-another-user matches how the rest of the required check derives trust from the forge.

### Conformance is the agent-read loop; the engine only keeps why pinned

Delete `src/repocodex/conformance.py` and its scenario-to-test table. The why of a change or implementation is an OKF concept; a multi-file scenario is links between concepts; the reverse index is how an agent finds them from a path. Before editing, the agent retrieves those pages and reads the pinned code. That read is how it knows not to break an existing scenario. After editing, it writes or updates the why in the same change, which the ratchet already makes unskippable.

The required check does not run tests and does not fail because an agent judged a scenario broken. It fails when the why has detached from live text — drift, a broken claim literal, skipped memory, index desync, contradiction. Those are pin checks, not behavior tests.

This is the architecture’s existing split (deterministic pin vs advisory judgment). The table was a third path invented during review, and it contradicted the product: humans maintaining a map, tests standing in for reading why.

*What this deliberately does not catch:* an agent that retrieves the why and then ignores it. The skills and the review-agent advisory job are the pressure on that path. Adding pytest would not make a careless agent more careful; it would recreate a parallel verification system the product exists to avoid.

*Dependency:* applying the same loop to RepoCodex itself needs a `.context/` bundle that does not exist. This change specifies the loop and reports the capability unsatisfied until that bundle exists. It does not invent tests to fill the gap.

## Risks / Trade-offs

- **Arming the ratchet on out-of-region change will block work that is currently passing.** → The change is behavioral for `ratchet` and `full` postures only. Recommend re-measuring in `shadow` — which after this change reports its reasons — before re-promoting, and land the ratchet change with the shadow-reporting change so the measurement is available.
- **Region-position arithmetic can misattribute hunks in files with overlapping or merged matched regions.** → Regions are already merged by the matcher before liveness classification, so comparison uses the merged set. Ambiguity resolves toward arming, and the false-block path is recoverable by writing memory.
- **A claim can name only one anchor.** → A rule that must hold at several sites needs one claim per site, which is more verbose than a set-valued owner. Accepted for now because the verbosity is honest — each site is separately checkable and separately reported — and a list-valued `anchor` remains a compatible extension if it turns out to be needed.
- **Ownership is positional, so reordering anchors silently re-points a claim.** → The write gate rejects an out-of-range index, re-anchoring must preserve ownership, and `apply_anchor_patch` mutates in place rather than reordering. Reordering is only reachable by hand-editing a concept, which the gate re-evaluates on the next write.
- **Deriving false drift over a window means the metric is unavailable on a single run.** → Acceptable: it is a promotion criterion evaluated over a shadow period, not a per-verdict field.
- **OKF conformance cannot start on RepoCodex itself until it has a bundle.** → The capability reports unsatisfied rather than silently passing. The table is deleted rather than left as a fallback, because a fallback would keep tests as the scenario check.
- **An agent can retrieve the why and ignore it.** → Skills and the advisory review job are the pressure. A test suite is not added to compensate; that would be a second product.
- **Filtering acknowledgment to approving reviews assumes the review agent can approve.** → A bot without approval rights cannot acknowledge an exemption. This is intended: the override should require an actor trusted enough to approve the pull request.

## Migration Plan

1. Land the claims fix first. It only relaxes verdicts, so it cannot introduce a new block, and it unblocks writing the multi-anchor fixtures the later tests need.
2. Land shadow reason reporting before the ratchet change, so operators can measure the new ratchet's cost in `shadow` before it can block.
3. Land the ratchet scoping and diff-scope fixes together — separately, the diff-scope fix alone would arm the ratchet on staged changes while the discharge rule is still too permissive, producing a confusing intermediate state.
4. Land the reporting-honesty fixes (repair, advisory, metrics, acknowledgment) in any order; they are independent.
5. Delete the conformance table last. Until the self-hosting change seeds a bundle, the capability reports unsatisfied. Do not leave pytest as a stand-in for scenario integrity.

**Rollback:** each group is independently revertable. The ratchet change is the only one that can newly block a merge; reverting it or setting `posture = "shadow"` restores the prior behavior without touching stored memory. No `.context/` bundle migration is required by any part of this change.

## Open Questions

- Should the withdrawn scenario's replacement also discharge on a *deleted* pinning concept, or does removing memory for a still-covered file deserve its own reason? Current plan treats deletion as a modification, which discharges; that may be too permissive.
- Which non-interactive entry points should `repocodex repair` target for each harness, and should an unknown harness on `PATH` be probed at all or simply reported as undeliverable?
- Does per-turn cost belong on `repocodex context` alone, or should the code-side impact walk in the advisory job contribute to it as architecture §16 suggests?
- When RepoCodex hosts its own bundle, is one concept per why (architecture §14) enough, with OKF links covering related scenarios, rather than one concept per OpenSpec scenario title?
