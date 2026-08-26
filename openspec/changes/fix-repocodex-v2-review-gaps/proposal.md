# Proposal: fix-repocodex-v2-review-gaps

## Why

`fix-repocodex-v1-review-gaps` closed the regression it was written for. Reproduced against the current engine: changing the contractual grace window from `3` to `1` while touching an unrelated file under `.context/` now returns `CLAIM_BROKEN` with `blocking: true`. Derived configuration, bootstrap identities, and the engine-version pin are deterministic, and validation leaves the tracked tree byte-identical. Those requirements hold.

A review of that implementation found that three of its mechanisms are now wrong in a way the green test suite does not catch, and that one of them is wrong because the v1-review-gaps spec asked for the wrong thing:

- **Claims are conjunctive across anchors.** Both the write gate and the validate-time claim evaluator require every declared literal to appear in *every* anchor's matched region. A three-anchor `BusinessWorkflow` whose `ENTERPRISE` claim legitimately lives only at the billing site is rejected at write with `claim_not_anchored`, and would report `CLAIM_BROKEN` against the unrelated anchors forever. Multi-anchor concepts carrying claims are currently unwritable — the architecture's own `BusinessWorkflow` archetype cannot be expressed.
- **The skipped-memory ratchet no longer fires for the case it exists for.** `validate` discharges the obligation for any covered file whose pinning concepts have a `LIVE` anchor. Appending an entire new `refundPayment` function to a covered file leaves both anchors `LIVE`, so `skipped_memory` is empty and nothing blocks. This follows the v1-review-gaps scenario "A live anchor discharges the obligation without a memory hunk" exactly; that scenario over-generalized architecture §11.1. A live anchor proves the *existing* memory is intact — it says nothing about whether *new* behavior in that file is covered, which is the ratchet's entire purpose.
- **Staging a change hides it from the ratchet.** `changed_files` reaches its working-tree scope through a fallback that unions staged, unstaged, and untracked paths, but `is_substantive_change` runs a plain `git diff` that sees only unstaged content. The same edit reports substantive before `git add` and non-substantive after. The pre-commit hook (`--staged`) and CI (`--base`) are unaffected; an agent that stages before running `repocodex validate` gets a false pass.

Below the blocking tier, the review found surfaces that satisfy the letter of their v1-review-gaps requirement while reporting more confidence than they earned: `shadow` posture suppresses the rejection reasons it exists to collect, `false_drift_rate` reports the raw drift rate, `repocodex repair` reports `invoked: true` after running the harness's `--help`, the `memory-exempt` acknowledgment can be self-issued by the pull request author, and the conformance map records coverage that several of its mapped tests do not provide.

## What Changes

- **Each claim declares the anchor that owns it.** An optional `anchor` index on a claim names the anchor that must carry the literal, and the claim is evaluated against that anchor alone. Omitting it resolves to the sole anchor, or to the single anchor whose terms declare the literal, and is rejected when ambiguous. **BREAKING** relative to `fix-repocodex-v1-review-gaps` — concepts rejected under conjunctive matching become writable, and spurious `CLAIM_BROKEN` verdicts on multi-anchor concepts disappear. No bundle migration is needed, because conjunctive matching means no multi-anchor concept carrying a claim can exist today.
- **Ratchet discharge narrows.** A live anchor alone stops discharging the obligation. It is discharged when a pinning concept is added or modified on the run, or when the anchor attests *and* the file's substantive hunks fall inside its matched regions. **BREAKING** — this modifies the v1-review-gaps requirement "Ratchet satisfaction is per-file and evidence-based", dropping its scenario "A live anchor discharges the obligation without a memory hunk". Repos in `ratchet` or `full` posture will see the ratchet fire on new behavior added to covered files.
- **Substantive-change detection uses the validation's own scope.** Working-tree scope compares against `HEAD` so staged and unstaged content are both visible, and the verdict is invariant under `git add`.
- **Shadow reports its reasons.** The reason list and the recorded `rejection_reasons` metric are populated in `shadow` exactly as they would be under `ratchet`; only `blocking` differs.
- **Metrics measure what they are named.** False drift is distinguished from drift, per-turn cost is measured from what the caller was actually served, and `validate` stops performing a full body-loading retrieval — with its per-concept churn inference — inside the pre-commit and CI hot path solely to compute a metric.
- **`repocodex repair` reports only invocations it performed.** It delivers the repair prompt to the harness or reports that it did not; probing a harness's `--help` is not an invocation.
- **The escape hatch cannot be self-issued.** Acknowledgment requires an approving review from someone other than the pull request author, and the environment-supplied evidence path is honored only in a recognized CI runner.
- **Conformance is the product loop, not a test suite.** The scenario-to-test table is deleted. Why lives in OKF, multi-file scenarios are OKF links, and agents retrieve those concepts then read the code — that is how “no existing scenario is broken” is checked. The required check stays a pin check (anchors, claims, ratchet). It does not run tests and does not fail on agent judgment. **BREAKING** — `src/repocodex/conformance.py` and its table are removed. RepoCodex’s own bundle is still a separate change; until it exists this capability reports unsatisfied rather than falling back to a table.
- **The advisory check carries judgment or reports that it has none**, instead of emitting a fixed note beside permanently empty finding lists.

Explicitly **not** in this change: the `CLAIM_BROKEN` classification, the closed blocking set, the determinism inputs rule, the single-writer rule, shard-local placement, or the engine-pin enforcement. Those were introduced by `fix-repocodex-v1-review-gaps`, were verified against the running engine, and are unchanged.

## Capabilities

### New Capabilities

<!-- None. Every finding tightens a capability introduced by add-repocodex-v1 or fix-repocodex-v1-review-gaps. -->

### Modified Capabilities

`openspec/specs/` is empty and both prior changes are unarchived, so deltas below are expressed as ADDED requirements except where a v1-review-gaps requirement is corrected rather than extended. The one such case is `enforcement`'s ratchet requirement, carried as a MODIFIED block with its full updated content.

- `anchor-verification`: a claim declares and is evaluated against its owning anchor rather than every anchor; the regex portability check compares matching behavior rather than compilability alone.
- `enforcement`: **MODIFIED** — ratchet discharge requires the change to fall inside a region the anchor attests, replacing whole-file discharge on attestation. **ADDED** — substantive-change detection honors the validation's diff scope; `shadow` reports its reasons; posture metrics measure their named quantity and are not computed by re-running retrieval.
- `governance`: `memory-exempt` acknowledgment must come from a reviewer other than the author, and environment-supplied evidence is confined to CI.
- `agent-interfaces`: `repocodex repair` reports invocation truthfully.
- `impact-analysis`: the advisory check distinguishes an absent judgment from a clean one; the recipes hand the agent the linked why for a diff so it can read the scenario, and never substitute a test result.

## Impact

- **Affected code:** `schema.py`, `engine/gate.py`, `engine/liveness.py`, `engine/ratchet.py`, `commands/validate.py`, `commands/reconcile.py`, `commands/repair.py`, `commands/advisory.py`, `metrics.py`, `data/action/repocodex.yml`, and the `tests/` suite. `conformance.py` and `tests/test_conformance.py` are deleted.
- **Superseded specification:** the `enforcement` requirement "Ratchet satisfaction is per-file and evidence-based" from `fix-repocodex-v1-review-gaps` is modified, dropping its scenario "A live anchor discharges the obligation without a memory hunk". Both `conformance` requirements from that change are removed.
- **Dependent change:** applying this loop to RepoCodex itself requires a `.context/` bundle that does not exist. Creating it is a separate change; this one specifies the loop and reports the capability unsatisfied until that bundle exists.
- **Behavioral compatibility:** repos in `ratchet` or `full` posture will see new blocking verdicts where new behavior is added to covered files without memory, and will stop seeing spurious `CLAIM_BROKEN` on multi-anchor concepts. `shadow` remains non-blocking; its output gains the reason list. Verdicts already produced under `--staged` or `--base` are unchanged.
- **Documentation:** `docs/research/architecture.md` §11.1 is clarified so that "a LIVE pass requires no `.context/` hunk" is scoped to the region the anchor attests, and §16's metric definitions are made precise.
- **Dependencies:** unchanged — ripgrep, git, Python. No new runtime dependencies, no network access in the engine.
