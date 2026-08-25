# Tasks: fix-repocodex-v1-review-gaps

## 1. Architecture reconciliation

- [x] 1.1 Resolve architecture §5.3 vs §6.2: define `CLAIM_BROKEN` as a classification distinct from the anchor term-count classes, and correct the liveness table
- [x] 1.2 State the required check's closed blocking set in architecture §11.3 and reconcile it with the governance CONTRADICTION rule
- [x] 1.3 Record the determinism rule in §15: verdicts depend only on tracked, non-excluded contents plus the requested diff scope
- [x] 1.4 Note in §18 that anchor terms must be dialect-portable, and that the liveness matcher and counting path must agree

## 2. Claim liveness

- [x] 2.1 Add `CLAIM_BROKEN` to the classification set with its own verdict field, reported alongside the anchor classification
- [x] 2.2 Evaluate declared literals against the anchor's matched region on every stable-concept validation
- [x] 2.3 Tighten claim matching to token equality against `all_of` terms and the matched region; remove substring satisfaction
- [x] 2.4 Remove the whole-file fallback used when no fully-matching region exists
- [x] 2.5 Make `CLAIM_BROKEN` blocking outside `shadow` and repairable only through a gate-passing write

## 3. Ratchet scoping

- [x] 3.1 Replace the global `context_touched` flag with per-file correspondence between a covered file and the concepts pinning it
- [x] 3.2 Discharge the obligation when a pinning concept is added, modified, or attests on the run
- [x] 3.3 Implement substantive-change detection (non-whitespace, non-comment-only) using the existing unused `SUBSTANTIVE_PREFIXES`, resolving ambiguity toward not arming
- [x] 3.4 Tighten agent-authorship detection for `full` posture beyond loose commit-message substring matching

## 4. Contradiction scope

- [x] 4.1 Add the optional claim subject discriminator to the schema, defaulting to no-conflict when absent
- [x] 4.2 Restrict conflict detection to same-subject differing literals and double supersede; stop flagging merely differing claim sets
- [x] 4.3 Include the conflicting subject in the CONTRADICTION payload

## 5. Determinism

- [x] 5.1 Derive the distinctiveness ceiling from tracked, non-excluded files via git instead of a filesystem walk
- [x] 5.2 Replace `hash()`-derived bootstrap identities with a stable content digest
- [x] 5.3 Thread the caller's diff scope (staged / base / working tree) through relocation, replacing the unused `diff_files` parameter
- [x] 5.4 Enforce the `.repocodex.toml` engine-version pin on every command with a machine-readable mismatch error
- [x] 5.5 Remove the `|| pip install -e .` fallback from the shipped Action so an unresolvable pin fails the job
- [x] 5.6 Reject regex anchor terms at write time when the liveness matcher and the ripgrep counting path disagree
- [x] 5.7 Fix exclusion path normalization to strip a leading `./` prefix only, preserving dotfile names

## 6. Side-effect-free attestation

- [x] 6.1 Move the metrics sink outside `.context/`, add it to `.gitignore`, and remove any committed `.context/metrics.jsonl`
- [x] 6.2 Emit escape-hatch log entries and follow-up repair tasks in the verdict instead of writing them during validation
- [x] 6.3 Add a regression test asserting the working tree is unchanged after validation in every posture
- [x] 6.4 Include relocated terms in REANCHOR patches and restamp `verified.by` as `process:repocodex-reanchor`

## 7. Posture and escape hatch

- [x] 7.1 Compute and report skipped-memory, claim breakage, drift, contradictions, and index desync in `shadow` instead of suppressing them
- [x] 7.2 Populate false-drift rate, rejection reasons, reconcile retries, tokens per turn, and latency with measured values
- [x] 7.3 Replace the unauthenticated `--review-ack` flag with verifiable acknowledgment evidence
- [x] 7.4 Wire the `memory-exempt` path end to end in the shipped Action so an acknowledged exemption clears the required check
- [x] 7.5 Enumerate the required check's blocking set in one place and assert it is closed

## 8. Store, retrieval, and impact

- [x] 8.1 Route accepted writes to the shard owning the pinned paths; keep cross-shard concepts at the root
- [x] 8.2 Resolve concept file locations shard-aware in churn inference
- [x] 8.3 Add the directory `index.md` catalog stage between reverse-index lookup and body loading
- [x] 8.4 Make the advisory CI job report agent-judged findings instead of re-running the deterministic validate

## 9. Governance surfaces

- [x] 9.1 Cite per-concept provenance in bootstrap and drop the blanket recent-commit list
- [x] 9.2 Extend bootstrap mining to git history and documentation, rejecting records with no genuine evidencing source
- [x] 9.3 Document the audit screening contract as out-of-band, and accept returned findings as CONTRADICTION proposals

## 10. Interfaces and packaging

- [x] 10.1 Make `repocodex repair` invoke an available agent harness and fail explicitly when none is available
- [x] 10.2 Ship the portable pre-commit hook inside the plugin tree so the Claude and Cursor adapters resolve
- [x] 10.3 Verify each artifact is resolvable during `repocodex install` before reporting it installed

## 11. Conformance

- [x] 11.1 Build the scenario-to-test mapping and a check that reports unmapped scenarios
- [x] 11.2 Replace disjunctive assertions in the rename REANCHOR, literal-change, and formatter-tolerance tests with exact expectations
- [x] 11.3 Assert the dilution warning is present and names the diluted terms, replacing the engine-version placeholder assertion
- [x] 11.4 Add tests for the reproduced regression: claim breakage with an unrelated `.context/` edit must block
- [x] 11.5 Add determinism tests for the derived ceiling, bootstrap identities, and cross-scope relocation
- [x] 11.6 Reconcile the `add-repocodex-v1` task list with what its tests actually verify
