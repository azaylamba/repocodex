# Proposal: fix-repocodex-v1-review-gaps

## Why

A review of the `add-repocodex-v1` implementation against [docs/research/architecture.md](../../../docs/research/architecture.md) and the v1 spec deltas found that the enforcement core lets through the exact regression RepoCodex exists to prevent. Reproduced against the shipped engine: an agent changes the contractual grace window from `3` to `1` in a pinned file and touches any file under `.context/` in the same change. The `InvariantContract` classifies as WEAK (2 of 3 anchor terms still hit), which architecture §6.2 defines as never blocking; the skipped-memory ratchet — the only remaining net — is cleared because a single global flag treats *any* `.context/` edit as memory maintenance for *every* covered file. The required check passes and the business rule is silently changed.

This is not one bug. It is a cluster of gaps that share a root cause: v1 specified the deterministic mechanisms but under-specified their *scope* — which region a claim must hold in, which file a memory update satisfies, which inputs may influence a verdict, and which surface may write to the tree. Two of the gaps are contradictions inside the architecture document itself (§5.3's "changing `3 → 1` breaks the match" versus §6.2's "partial term loss never blocks"; and `enforcement`'s closed list of blocking reasons versus `governance`'s requirement that CONTRADICTION block merge-completion), so implementation cannot be corrected without first resolving the source.

Alongside these, the review found determinism violations that break architecture §15's "same answer in IDE and CI by construction" (a distinctiveness ceiling derived from a live filesystem walk that includes `node_modules`, bootstrap identities built from seed-randomized `hash()`, an engine-version pin that is loaded and never enforced), engine writes to the working tree during a read-only attest, and packaging defects that make the shipped escape hatch and plugin hook adapters non-functional.

## What Changes

Close every gap the review identified, as requirements rather than patches:

- **Claim liveness becomes real enforcement.** A declared `claims[].literal` disappearing from the matched region becomes its own blocking classification, independent of the WEAK/DRIFT term count. **BREAKING** for repos in `ratchet`/`full` posture: changes that previously passed as WEAK will now block. Claim matching also tightens — token match rather than substring, evaluated against the matched region rather than falling back to the whole file.
- **Ratchet scoping becomes per-file.** A memory update satisfies the ratchet only for the covered files whose pinning concepts were actually updated, and only substantive changes (not whitespace or comment-only edits) arm it.
- **CONTRADICTION means conflict.** Differing claim sets on a shared pinned path are the normal case and stop being flagged. The blocking status of genuine contradictions is settled explicitly rather than left to disagreeing specs.
- **Verdicts stop depending on ambient state.** Derived configuration is computed from tracked, non-excluded files only; the `.repocodex.toml` engine-version pin is enforced rather than reported; relocation uses the same diff scope as the validation that invoked it; anchor terms are evaluated under one regex dialect.
- **Attestation becomes side-effect free.** `validate` no longer writes metrics, log entries, or repair tasks into the working tree, restoring architecture §15's single-writer rule. REANCHOR patches become complete — carrying relocated terms and restamping `verified.by` as `process:repocodex-reanchor`.
- **Shadow posture reports what it suppresses**, and the two measured unknowns that gate posture promotion (false-drift rate, tokens per turn) are actually populated.
- **The escape hatch becomes usable and governed.** The `memory-exempt` path works end to end in the shipped Action and requires verifiable review-agent acknowledgment rather than an unauthenticated CLI flag.
- **Packaging and surface defects are fixed.** Shard-local concept placement on write, shard-aware churn inference, the catalog stage of staged retrieval, an advisory check that carries agent-judged findings, `repocodex repair` that actually invokes an agent, plugin hook adapters that resolve to a real hook, bootstrap provenance that cites relevant sources, and an explicit contract for out-of-band audit screening.
- **A new `conformance` capability** requires every spec scenario to have a test that fails when the behavior regresses. The v1 tests pass, but the four scenarios that most needed pinning (rename REANCHOR, literal change, formatter tolerance, dilution warning) are asserted with disjunctions that cannot fail.

Explicitly **not** in this change: any revision of the determinism split, the removal of AST/SCIP, the anchor format itself, or the rollout-posture model. Those held up under review and are unchanged.

## Capabilities

### New Capabilities

- `conformance`: falsifiability requirements for the spec-scenario test suite — every scenario backed by a test that fails on regression, no disjunctive acceptance.

### Modified Capabilities

These extend the capability set introduced by `add-repocodex-v1`. That change is unarchived and `openspec/specs/` is empty, so each delta below is expressed as ADDED requirements that tighten scope rather than MODIFIED blocks; no v1 requirement is contradicted, and the two v1 specs that disagreed with each other are reconciled by a new requirement that states the resolution.

- `anchor-verification`: claim-literal liveness as a blocking class, precise claim matching, deterministic derived configuration, engine-pin enforcement, single regex dialect, diff-scope-consistent relocation, complete REANCHOR patches, side-effect-free attestation, correct exclusion-path normalization.
- `enforcement`: per-file ratchet scoping, substantive-change detection, shadow-posture reporting, populated posture metrics stored outside the bundle, a verifiable and CI-usable escape hatch, and a closed explicit blocking set for the required check.
- `governance`: contradiction requires actual conflict, accurate bootstrap provenance, deterministic bootstrap identities, explicit audit-screening contract.
- `memory-store`: shard-local concept placement on accepted writes.
- `context-retrieval`: the directory catalog stage is actually used; churn inference is shard-aware.
- `impact-analysis`: the advisory check carries agent-judged findings distinct from the required deterministic check.
- `agent-interfaces`: `repocodex repair` invokes a repair agent; distribution artifacts resolve inside the packaged tree.

## Impact

- **Affected code:** `engine/liveness.py`, `engine/gate.py`, `engine/match.py`, `engine/ratchet.py`, `engine/contradiction.py`, `engine/relocate.py`, `commands/validate.py`, `commands/write.py`, `commands/reconcile.py`, `commands/repair.py`, `commands/bootstrap.py`, `commands/audit.py`, `config.py`, `metrics.py`, `retrieval.py`, `store/bundle.py`, `data/action/repocodex.yml`, `plugin/hooks/*`, and the `tests/` suite.
- **Behavioral compatibility:** repos in `ratchet` or `full` posture will see new blocking verdicts for claim breakage and correctly-scoped skipped memory, and fewer false blocks from contradiction. `shadow` remains non-blocking by construction; the recommended rollout is to re-measure in `shadow` after this change before re-promoting.
- **Artifact compatibility:** `.context/metrics.jsonl` moves out of the committed bundle; existing bundles need no migration, but the stale file should be removed and ignored.
- **Documentation:** `docs/research/architecture.md` is updated in the same change to resolve the §5.3/§6.2 contradiction and to state the required check's blocking set, so the canonical document and the specs agree.
- **Dependencies:** unchanged — ripgrep, git, Python. No new runtime dependencies, no network access in the engine.
