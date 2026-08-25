# Design: fix-repocodex-v1-review-gaps

## Context

`add-repocodex-v1` shipped the full V1 surface: the OKF store, the ripgrep-backed gate, the LIVE/WEAK/REANCHOR/DRIFT classifier, staged retrieval, the determinism split, postures, skills, MCP, and packaging. A review against [architecture.md](../../../docs/research/architecture.md) (Revision 2) and the v1 spec deltas confirmed the shape is right — every named module exists, the CLI is canonical, judgment findings stay advisory — and found that the *scope* of several deterministic mechanisms was left implicit, which is where the guarantee leaks.

The load-bearing finding, reproduced against the shipped engine: changing a pinned contractual literal from `3` to `1` yields `classification: WEAK, hits: 2, required: 3`, and a same-change edit to any `.context/` file clears the ratchet for every covered file, producing `blocking: false`. Architecture §5.4 uses this precise scenario as its worked example of what RepoCodex prevents.

Two of the gaps cannot be fixed in code alone because the source document disagrees with itself:

- §5.3 states declared `claims` literals are "frozen into anchors so changing `3 → 1` breaks the match," while §6.2 classifies any above-zero partial term loss as WEAK and states WEAK is "never blocking." The implementation follows §6.2 and is therefore simultaneously correct and wrong.
- The `enforcement` spec closes the required check's failure set to unrepaired DRIFT, the ratchet, and index desync; the `governance` spec requires a post-merge double supersede to block merge-completion. The implementation added CONTRADICTION as a fourth blocking reason to satisfy `governance`, silently violating `enforcement`.

This change resolves both in the architecture document and the specs together, so there is one answer.

## Goals / Non-Goals

**Goals:**

- Make the claims mechanism enforce at attest time, not only at write time, so `InvariantContract` means something after the write.
- Give every deterministic mechanism an explicit scope: which region a claim holds in, which file a memory update satisfies, which inputs may influence a verdict, which surface may write to the tree.
- Restore "identical verdicts for identical inputs across environments" as a property that holds by construction rather than by assertion.
- Reduce false blocking (contradiction on merely-different claims, whitespace-only ratchet trips) at the same time as increasing true blocking, so the required check stays livable and therefore stays required.
- Make the shipped artifacts actually work: escape hatch, hook adapters, repair flow, advisory check.
- Make the spec-scenario test suite falsifiable, so this class of gap is caught next time.

**Non-Goals:**

- Revisiting the determinism split, the removal of AST/SCIP/Tree-sitter, the textual anchor format, the rollout-posture model, or the single-writer principle. All held up under review.
- Adding new runtime dependencies, network access, or an LLM anywhere in the gate, attester, or required check.
- Retrofitting existing bundles. No concept file needs migration; only the stray `.context/metrics.jsonl` is relocated.
- Achieving structural (AST-grade) claims. Claims remain textual literals near a pinned region; this change makes them *enforced*, not more expressive.

## Decisions

### 1. A lost claim literal is its own blocking class, not a term-count outcome

`claims` and `all_of` answer different questions. `all_of` asks "is this concept still about this code?" — a fuzzy, rename-tolerant question where WEAK is the correct, deliberately forgiving answer. `claims` asks "is the specific fact this prose asserts still true in the code?" — a binary question where forgiveness is the bug. Collapsing the second into the first is what produced the reproduction above.

So a stable concept whose declared literal is absent from the matched region classifies as `CLAIM_BROKEN`: blocking outside `shadow`, repaired through the normal gate-passing supersede path, and reported alongside (not instead of) the anchor's LIVE/WEAK/REANCHOR/DRIFT classification. The anchor may be perfectly LIVE while the claim is broken — that combination is precisely the silent business-rule change, and it must be nameable.

*Alternatives considered.* Forcing `min_match` to all terms whenever `claims` are present would reuse existing machinery, but it couples two independent concerns: an unrelated identifier rename in a claims-bearing concept would then hard-DRIFT, reintroducing the rename drift-storm that `min_match` exists to prevent (architecture §17 row 2). Leaving §6.2 as written and correcting §5.3 instead was rejected because it would make `InvariantContract` a write-time-only construct, which removes the reason the type exists.

*Consequence.* This is the one behavioral break in the change. Repos already in `ratchet` or `full` will see new blocking verdicts on claim breakage. The migration plan below handles it via a shadow re-measurement pass.

### 2. Ratchet satisfaction is per-file and evidence-based

The v1 ratchet asks a global question ("did this diff touch `.context/`?") to answer a per-file one ("was the memory covering *this* file maintained?"). The fix is to require correspondence: a covered file's ratchet obligation is discharged only when at least one concept pinning *that file* was added or modified in the same change, or its anchors attested on this run. Determining that is pure file reads over the diff and the reverse index — no judgment, so it stays in the required check.

Arming the ratchet also requires a substantive change. `SUBSTANTIVE_PREFIXES` already exists in the code and is unused; the definition adopted here is diff-hunk content that is not exclusively whitespace, and not exclusively lines that are comment-only in the pinned file's existing comment style, detected textually. Getting this wrong in the lenient direction is safe (a missed ratchet is a WEAK-grade miss); getting it wrong in the strict direction is what makes required checks get unrequired, so ambiguity resolves toward not firing.

### 3. Contradiction requires actual conflict

The v1 implementation flags any two live concepts sharing a pinned path whose claim sets differ. Differing claims on a shared file is the ordinary case — a grace-period invariant and a retry-budget invariant legitimately coexist in one payment gateway — and flagging it produced a blocking false positive in review. A contradiction requires a shared *subject*, not merely a shared file: two concepts asserting different literals for the same claim key, or two live concepts superseding the same predecessor. Claims therefore gain an optional subject discriminator so the comparison has something to key on, defaulting to no-conflict when absent. Silence beats a false page.

### 4. CONTRADICTION blocks, and the required check's blocking set becomes closed and enumerated

Resolving the `enforcement`/`governance` disagreement in favor of blocking: a double supersede is deterministic (a frontmatter comparison, no model), and an unresolved one leaves the memory graph genuinely ambiguous about which why is current. What made this a defect was not the blocking, it was that the set of blocking reasons was stated in one spec as closed and then extended in code without the spec following.

The fix is structural rather than a one-line addition: the required check's blocking reasons become an explicitly enumerated, closed set — unrepaired DRIFT on stable anchors, broken claims, correctly-scoped skipped memory, reverse-index desync, and unresolved CONTRADICTION — and any future addition is a spec change. Every entry must be reproducible from the repository contents alone.

### 5. Determinism means the verdict depends only on committed inputs

Three v1 verdict inputs vary with ambient state: the distinctiveness ceiling is derived from a live `rglob` that counts `node_modules` and `.venv` (measured: 54 on a clean checkout, 204 after adding 300 files under `node_modules`), bootstrap identities come from seed-randomized `hash()` (measured: different identities across two processes on identical input), and relocation always runs a bare `git diff -M` regardless of the `--staged`/`--base` scope it was invoked under, so rename-driven REANCHOR behaves differently in the hook and CI than locally.

The unifying rule adopted: a verdict may depend only on tracked, non-excluded repository contents and the explicitly requested diff scope. Derived configuration counts tracked non-excluded files via git rather than walking the filesystem; generated identities use a stable content digest; relocation inherits its caller's diff scope. The engine-version pin gains teeth — a mismatch between `.repocodex.toml` and the running engine fails loudly instead of being reported as whatever happens to be installed, and the CI installer loses the silent `|| pip install -e .` fallback that defeats the pin.

The regex-dialect split is the subtler case. Anchor terms are evaluated for liveness by Python's `re` and counted for distinctiveness by ripgrep's Rust regex, so one `verification.engine: ripgrep` field is served by two dialects that disagree on constructs like lookaround. Rather than reimplement matching over `rg` subprocesses (a large change to the hot path for a small correctness gain), the gate validates at write time that every regex term compiles under both dialects and rejects those that do not. The declared engine then means what it says for every term that exists in a bundle.

### 6. Attestation is side-effect free

Architecture §15's single-writer rule exists so that hooks, CI, agents, and worktrees never race on the tree. V1's `validate` breaks it three ways: `record_metric` appends `.context/metrics.jsonl` on every run into the committed bundle, and the `memory-exempt` path appends to `log.md` and creates `repair-tasks/*.md` mid-verdict. Validation becomes read-only: metrics go to a gitignored, non-bundle location (or a caller-specified sink), and the audit artifacts the escape hatch owes are emitted *in the verdict* for the caller to persist — the same engine-emits/caller-applies pattern REANCHOR already uses.

### 7. Review acknowledgment must be evidence, not a flag

`--review-ack` is currently an unauthenticated boolean, and the shipped Action never passes it, so the escape hatch is simultaneously ungoverned locally and unusable in CI. Acknowledgment becomes a verifiable artifact — a review-agent acknowledgment recorded on the PR (checked via the CI context) or a signed/committed acknowledgment record — and the Action wires the path end to end. The engine still never decides; it checks for the presence of evidence a human and a review agent produced.

## Risks / Trade-offs

- **New blocking verdicts land on repos already in `ratchet`, and a check that suddenly goes red gets unrequired** (architecture §17 row 11) → Ship behind the posture model rather than as a flag day: the migration plan below re-measures in `shadow` first, and the same change removes two sources of false blocking (contradiction on differing claims, whitespace-only ratchet trips) so net noise should fall.
- **Per-file ratchet correspondence is stricter and could annoy legitimate cross-cutting edits** → Correspondence is satisfied by an attesting anchor as well as an edited concept, so a change that keeps memory genuinely live needs no `.context/` hunk. Ambiguity resolves toward not firing.
- **`CLAIM_BROKEN` invites agents to drop `claims` from frontmatter to dodge the gate** → Claims are already required whenever prose states checkable literals, and removing them from a stable concept is a why-change requiring `supersedes` + `rationale`. The review agent flags claim removal as a weakening; this is the same containment posture as architecture §14.1, not a new hole.
- **Rejecting regex terms that disagree across dialects narrows what authors may write** → The rejected set is small (dialect-specific constructs), the gate reports it at write time with the term, and fixed-string terms — the stable-token preference the gate already ranks first — are unaffected.
- **Subject discriminators on claims add schema surface** → Optional and backward compatible; absent discriminators mean "no conflict," so existing bundles get quieter, never louder.
- **Moving metrics out of `.context/` loses the committed audit trail some teams may want** → `log.md` remains the committed audit trail for memory events; metrics are operational telemetry for posture promotion, not memory, and were never specified as bundle content.

## Migration Plan

1. Land the engine changes with no posture change. `shadow` repos are unaffected by construction.
2. For repos in `ratchet`/`full`: temporarily return to `shadow` and re-measure. The new `CLAIM_BROKEN` rate and the corrected skipped-memory rate are exactly the metrics the posture ladder is supposed to gate on, and until this change they were not being collected (`skipped_memory` returned empty in `shadow`, and `false_drift_rate`/`tokens_per_turn` were written as `None`).
3. Repair whatever the shadow pass surfaces through the normal gate-passing path, then re-promote.
4. Delete any committed `.context/metrics.jsonl` and confirm the new metrics location is ignored.
5. Rollback is a version pin revert — now meaningful, since the pin is enforced.

## Open Questions

- The exact evidence format for review acknowledgment on non-GitHub forges. GitHub is wired first; the requirement is stated in terms of verifiable evidence so other forges can supply their own adapter.
- Whether `CLAIM_BROKEN` should also fire for `draft` concepts once they attest, or remain `stable`-only as the liveness rule is today. Starting `stable`-only, consistent with §6.2's scoping.
- Whether substantive-change detection should eventually consult language-aware comment syntax rather than textual heuristics. Deliberately deferred — it would reintroduce a language allowlist, which Revision 2 removed by design.
