# enforcement Specification

## Purpose

Deny unrepaired drift and skipped memory through a pre-commit hook and a closed, deterministic required CI check. Rollout postures (`shadow` / `ratchet` / `full`) configure the same product. The human escape hatch is verifiable and cannot be self-issued.

## Requirements

### Requirement: Pre-commit deny on drift

The system SHALL install a git pre-commit hook that denies commits while any validated anchor on the diff is in unrepaired DRIFT, filtering `git commit` inside the hook body rather than relying on client-side matchers.

#### Scenario: Commit blocked until reconcile

- **GIVEN** a diff producing a DRIFT verdict
- **WHEN** the agent attempts to commit
- **THEN** the hook denies the commit and returns the RECONCILE JSON

### Requirement: Deterministic required CI check

The system SHALL provide a stateless CI check, intended for branch protection, that fails only on deterministic outcomes: unrepaired DRIFT on stable anchors, the skipped-memory ratchet, and reverse-index desync. It SHALL NOT fail because `.context/` changed, because a WEAK anchor degraded, or on any agent-judged finding.

#### Scenario: Memory update does not fail CI

- **GIVEN** a PR that edits code and updates the corresponding concept in the same change
- **WHEN** the required check runs
- **THEN** it passes

#### Scenario: Bypassed hook is caught

- **GIVEN** a commit made with `--no-verify` that leaves an anchor in DRIFT
- **WHEN** the PR's required check runs
- **THEN** the check fails until the drift is repaired

### Requirement: Skipped-memory ratchet

The system SHALL arm skipped-memory on (1) files that already contain at least one attested concept when a substantive change is not discharged, and (2) uncovered, non-excluded files that receive a substantive change (first-touch), in every posture including `shadow`. First-touch SHALL use reason `uncovered_file_without_memory`. Covered-file misses SHALL keep reason `covered_file_without_memory_update`. Uncovered files SHALL fail the check while the first-touch obligation is undischarged unless `memory-exempt` clears it.

#### Scenario: First-touch of an uncovered file requires memory

- **GIVEN** a repository with no concept pinning `src/handler.py`
- **AND** a substantive edit to `src/handler.py`
- **AND** no concept pinning that file added or modified on the run
- **WHEN** validation runs in `shadow` posture
- **THEN** `skipped_memory` contains an entry for that file with reason `uncovered_file_without_memory`
- **AND** `blocking_reasons` contains `skipped_memory`
- **AND** `blocking` is `true`

#### Scenario: Writing a pinning concept discharges first-touch

- **GIVEN** a substantive edit to an uncovered file
- **WHEN** the same change adds a gate-passing concept that pins that file
- **THEN** `skipped_memory` has no entry for that file
- **AND** the verdict is non-blocking for skipped-memory

#### Scenario: Covered file requires memory maintenance

- **GIVEN** a file carrying an attested concept
- **WHEN** a PR substantively changes that file without updating or writing memory and without a passing in-region attest
- **THEN** the required check fails

### Requirement: Rollout postures

The system SHALL ship three configuration postures of the complete product — `shadow` (report every deterministic finding; block on undischarged `skipped_memory`; do not block on drift, `CLAIM_BROKEN`, contradiction, or index desync; collect metrics), `ratchet` (also enforce DRIFT, `CLAIM_BROKEN`, contradiction, and index desync), and `full` (`ratchet` plus scheduled audits) — selected in `.repocodex.toml`, with instrumentation for false-drift rate, rejection reasons, reconcile retries, tokens per turn, and validate latency.

#### Scenario: Shadow posture still does not deny drift

- **GIVEN** a repo in `shadow` posture with drifting anchors and empty `skipped_memory`
- **WHEN** hooks and CI run
- **THEN** the drift is reported
- **AND** the verdict is non-blocking

#### Scenario: Shadow posture denies skipped memory

- **GIVEN** a repo in `shadow` posture with an undischarged skipped-memory obligation
- **WHEN** hooks and CI run with `--hook` or `--check`
- **THEN** the process is denied
- **AND** `blocking` is `true`

### Requirement: Human escape hatch

The system SHALL allow a human to merge past the required check via a `memory-exempt` override that requires review-agent acknowledgment, writes an audit entry to `log.md`, and files a follow-up repair task; and SHALL provide `repocodex repair` as a one-command human repair flow.

#### Scenario: Hotfix merges with audit trail

- **GIVEN** an incident hotfix PR failing the required check
- **WHEN** the `memory-exempt` label is applied and acknowledged
- **THEN** the merge proceeds, the bypass is logged in `log.md`, and a repair task is created for the next agent session

### Requirement: Ratchet satisfaction is per-file and evidence-based

The system SHALL discharge a covered file's skipped-memory obligation only when at least one concept pinning that specific file was added or modified in the same change, or when every substantive hunk in that file falls inside a matched region of an attesting anchor that pins it. An edit to any other part of `.context/` SHALL NOT discharge the obligation for unrelated covered files. An attesting anchor SHALL NOT by itself discharge the obligation for the whole file: attestation establishes that the pinned region's memory is intact and establishes nothing about behavior added elsewhere in the file. Where changed line ranges cannot be attributed to a region, the system SHALL leave the obligation armed.

#### Scenario: Unrelated memory edit does not clear the ratchet

- **GIVEN** a covered source file substantively changed in `ratchet` posture
- **WHEN** the same change edits an unrelated file under `.context/` and leaves the concepts pinning the covered file untouched
- **THEN** the skipped-memory obligation for that covered file is still reported and the required check fails

#### Scenario: Maintaining the covering concept clears the ratchet

- **GIVEN** a covered source file substantively changed in `ratchet` posture
- **WHEN** the same change updates a concept that pins that file
- **THEN** the obligation is discharged for that file and the required check passes

#### Scenario: New behavior added outside the matched region arms the ratchet

- **GIVEN** a covered file whose pinning concept's anchors all classify `LIVE`
- **AND** a new function appended to the file, outside every matched region
- **AND** no concept pinning that file added or modified on the run
- **WHEN** the required check runs in `ratchet` posture
- **THEN** `skipped_memory` contains an entry for that file with reason `covered_file_without_memory_update`
- **AND** `blocking_reasons` contains `skipped_memory`

#### Scenario: Substantive change inside the matched region is discharged by attestation

- **GIVEN** a covered file whose pinning anchor classifies `LIVE`
- **AND** the only substantive hunk falls inside that anchor's matched region
- **WHEN** the required check runs in `ratchet` posture
- **THEN** `skipped_memory` is empty
- **AND** no `.context/` hunk is required

#### Scenario: Unattributable hunk leaves the obligation armed

- **GIVEN** a covered file with substantive change whose line ranges cannot be attributed to any matched region
- **WHEN** the required check runs in `ratchet` posture
- **THEN** the obligation is reported rather than discharged

### Requirement: Substantive change detection arms the ratchet

The system SHALL arm the skipped-memory ratchet only for diff content that is not exclusively whitespace and not exclusively comment-only lines, determined textually without a language allowlist, and SHALL resolve ambiguity by not arming the ratchet.

#### Scenario: Formatting-only edit does not trip the ratchet

- **GIVEN** a covered file in `ratchet` posture
- **WHEN** a diff changes only indentation and line wrapping in that file
- **THEN** no skipped-memory obligation is reported

#### Scenario: Comment-only edit does not trip the ratchet

- **GIVEN** a covered file in `ratchet` posture
- **WHEN** a diff adds only comment lines to that file
- **THEN** no skipped-memory obligation is reported

#### Scenario: Logic change trips the ratchet

- **GIVEN** a covered file in `ratchet` posture
- **WHEN** a diff changes executable content in that file without maintaining its memory
- **THEN** the skipped-memory obligation is reported

### Requirement: Shadow posture reports everything it declines to block

The system SHALL compute and report every deterministic finding in `shadow` posture — including skipped-memory obligations, claim breakage, drift, contradictions, and index desync. It SHALL block on undischarged skipped-memory and SHALL NOT block on claim breakage, drift, contradiction, or index desync. Suppressing computation of a finding in `shadow` is not conformant, because the metrics that gate posture promotion are derived from those findings.

#### Scenario: Shadow reports skipped memory and blocks

- **GIVEN** a repository in `shadow` posture with a covered file changed and no memory maintenance
- **WHEN** validation runs
- **THEN** the skipped-memory obligation appears in the verdict
- **AND** the verdict is blocking

#### Scenario: Shadow reports claim breakage without blocking

- **GIVEN** a repository in `shadow` posture with a broken claim literal and empty `skipped_memory`
- **WHEN** validation runs
- **THEN** the `CLAIM_BROKEN` finding appears in the verdict and nothing is denied

### Requirement: Posture promotion metrics are populated

The system SHALL populate the metrics that gate posture promotion with measured values rather than placeholders: false-drift rate, anchor-rejection reasons, reconcile retries, tokens per turn, and validate latency. Metrics SHALL be written to a sink outside the committed `.context/` bundle.

#### Scenario: Metrics carry measured values

- **GIVEN** a sequence of validations in `shadow` posture
- **WHEN** the metrics sink is inspected
- **THEN** false-drift rate and tokens per turn hold measured values rather than null placeholders

#### Scenario: Metrics do not pollute the bundle

- **GIVEN** any number of validations
- **WHEN** the repository status is inspected
- **THEN** no metrics artifact appears inside `.context/` and none appears as an untracked change

### Requirement: The required check's blocking set is closed and enumerated

The system SHALL fail the required CI check on exactly these deterministic outcomes and no others: unrepaired DRIFT on a stable anchor (except in `shadow`), `CLAIM_BROKEN` on a stable concept (except in `shadow`), an undischarged skipped-memory obligation in every posture including `shadow`, reverse-index desync (except in `shadow`), and an unresolved CONTRADICTION (except in `shadow`). Every entry SHALL be reproducible from repository contents alone, and adding an entry SHALL require a spec change.

#### Scenario: Enumerated reason blocks

- **GIVEN** a pull request with an unresolved double supersede
- **WHEN** the required check runs outside `shadow` posture
- **THEN** it fails citing the CONTRADICTION reason from the enumerated set

#### Scenario: Non-enumerated finding does not block

- **GIVEN** a pull request whose only findings are a WEAK anchor, a dilution warning, and an agent-judged impact note
- **WHEN** the required check runs
- **THEN** it passes and the findings are reported without blocking

#### Scenario: Skipped memory blocks the required check in shadow

- **GIVEN** a pull request with an undischarged first-touch skipped-memory obligation
- **AND** `posture = "shadow"`
- **WHEN** the required check runs
- **THEN** it fails citing `skipped_memory`

### Requirement: The escape hatch is verifiable and usable end to end

The system SHALL require verifiable evidence of review-agent acknowledgment before a `memory-exempt` override clears the required check, and SHALL NOT accept an unauthenticated caller-supplied flag as that evidence. The shipped CI workflow SHALL wire the override path end to end so that an acknowledged exemption actually clears the check.

#### Scenario: Unauthenticated flag does not clear the check

- **GIVEN** a failing required check and a caller asserting acknowledgment with no corresponding evidence
- **WHEN** validation runs
- **THEN** the override is refused and the check remains blocking

#### Scenario: Acknowledged hotfix clears the check in CI

- **GIVEN** a hotfix pull request labelled `memory-exempt` with a recorded review-agent acknowledgment
- **WHEN** the shipped workflow runs the required check
- **THEN** the check passes
- **AND** the verdict carries the audit entry and follow-up repair task for the caller to persist

#### Scenario: Label without acknowledgment still blocks

- **GIVEN** a pull request labelled `memory-exempt` with no review-agent acknowledgment
- **WHEN** the required check runs
- **THEN** the check fails citing the missing acknowledgment

### Requirement: Substantive-change detection honors the validation's diff scope

Substantive-change detection SHALL evaluate the same content the validation's diff scope selected. In working-tree scope it SHALL compare against `HEAD` so that staged and unstaged content are both visible; in staged scope it SHALL compare the index; in base scope it SHALL compare the requested base. A verdict SHALL be invariant under `git add`.

#### Scenario: Staging does not change the verdict

- **GIVEN** a substantive change to a covered file with no corresponding memory update
- **WHEN** the required check runs in working-tree scope before `git add`
- **AND** the required check runs again in working-tree scope after `git add`
- **THEN** both runs report the same `skipped_memory` entries
- **AND** both runs report the same `blocking_reasons`

#### Scenario: Formatting-only change stays non-substantive once staged

- **GIVEN** a whitespace-only reformat of a covered file
- **WHEN** the change is staged and the required check runs in working-tree scope
- **THEN** `skipped_memory` is empty

### Requirement: Shadow posture reports the reasons it declines to enforce

In `shadow` posture the verdict SHALL carry the same `blocking_reasons` list it would carry in `ratchet` posture, and the recorded metric SHALL carry the same `rejection_reasons`. For reasons other than `skipped_memory`, only the `blocking` field SHALL differ. When `skipped_memory` is present, `blocking` SHALL be `true` in `shadow` as in `ratchet`. Suppressing the reason list in `shadow` withholds the measurement that posture exists to produce.

#### Scenario: Shadow carries reasons with blocking false for claim breakage

- **GIVEN** a change that breaks a claim in a repo configured with `posture = "shadow"`
- **AND** `skipped_memory` is empty
- **WHEN** validation runs
- **THEN** `blocking` is `false`
- **AND** `blocking_reasons` contains `claim_broken`

#### Scenario: Shadow and ratchet agree on reasons

- **GIVEN** an identical change validated once under `shadow` and once under `ratchet`
- **WHEN** both verdicts are compared
- **THEN** their `blocking_reasons` lists are equal

#### Scenario: Recorded metric carries the shadow reasons

- **GIVEN** the shadow run above
- **WHEN** the metrics sink is read
- **THEN** the recorded `rejection_reasons` equals the verdict's `blocking_reasons`

### Requirement: Posture metrics measure their named quantity

`false_drift_rate` SHALL report the share of `DRIFT` classifications that a relocation should have resolved — drift whose repair re-points the anchor at code equivalent to the pinned region — and SHALL NOT report the raw drift rate. Per-turn cost SHALL be measured from the context actually served to the caller. Validation SHALL NOT invoke retrieval, body loading, or per-concept churn inference for the sole purpose of computing a metric.

#### Scenario: Genuine drift does not inflate the false-drift rate

- **GIVEN** a validation in which an anchor drifts because its pinned code was deleted outright
- **WHEN** the verdict is produced
- **THEN** `false_drift_rate` is `0.0`
- **AND** the drift is still reported in `lost`

#### Scenario: Validation does not run retrieval

- **GIVEN** any validation run
- **WHEN** the calls it makes are observed
- **THEN** no concept body is loaded and no churn inference is performed for metrics

### Requirement: In-bundle reverse index is reverse-index desync

A leftover `.context/**/reverse-index.md` SHALL be reported as the existing required-check reason `index_sync`. The closed blocking set SHALL NOT gain a new member for OKF layout. When validate runs with staged or hook scope, index-sync SHALL compare the git-index copy of `.repocodex/reverse-index.md` (and shard files under `.repocodex/reverse-index/`); a generated file that exists only in the working tree SHALL count as desync.

#### Scenario: Leftover in-bundle file blocks as index_sync

- **GIVEN** a repository whose `.repocodex/reverse-index.md` matches the pins and whose `.context/reverse-index.md` still exists
- **WHEN** the required check runs
- **THEN** it is blocking
- **AND** `blocking_reasons` contains `index_sync` and does not contain a new reason name for bundle layout

#### Scenario: Unstaged generated reverse index is desync under hook scope

- **GIVEN** a write that regenerated `.repocodex/reverse-index.md` on disk
- **AND** that file is not in the git index
- **WHEN** `repocodex validate --diff --staged` (or `--hook`) runs
- **THEN** `blocking_reasons` contains `index_sync`
- **AND** a subsequent `git add` of that file clears the `index_sync` reason if pins otherwise match

### Requirement: First-touch skip list does not arm skipped memory

The system SHALL NOT arm first-touch skipped-memory on paths that are excluded (`path_excluded`), under `.context/` or the reverse-index tree, or whose basename is one of: `.gitignore`, `.gitattributes`, `.repocodex.toml`, `.repocodexignore`, `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `npm-shrinkwrap.json`, `uv.lock`, `Cargo.lock`, `poetry.lock`, `Pipfile.lock`, `composer.lock`, `Gemfile.lock`, `go.sum`. Application source and dependency manifests not in that basename set remain in scope.

#### Scenario: Lockfile-only change does not require a concept

- **GIVEN** a repository with zero coverage
- **WHEN** the only changed file is `uv.lock`
- **THEN** `skipped_memory` is empty
- **AND** `blocking` is `false`

#### Scenario: Gitignore alongside source still requires memory for source

- **GIVEN** a substantive edit to `src/handler.py` and a change to `.gitignore`
- **AND** no pinning concept for `src/handler.py`
- **WHEN** validation runs
- **THEN** `skipped_memory` contains `src/handler.py` with reason `uncovered_file_without_memory`
- **AND** does not contain `.gitignore`

### Requirement: Undischarged skipped memory is not a LIVE result

When `skipped_memory` is non-empty and the pin-check result would otherwise be `LIVE` or `WEAK`, the verdict `result` SHALL be `WRITE`. `REANCHOR`, `RECONCILE`, `CLAIM_BROKEN`, and `CONTRADICTION` SHALL remain the result when those pin-check outcomes apply; `skipped_memory` SHALL still appear on the payload.

#### Scenario: Uncovered substantive edit is WRITE

- **GIVEN** a first-touch obligation and no drifting anchors
- **WHEN** validation runs
- **THEN** `result` is `WRITE`
- **AND** `blocking` is `true`

#### Scenario: Drift still reports RECONCILE

- **GIVEN** unrepaired DRIFT and an undischarged skipped-memory obligation
- **WHEN** validation runs
- **THEN** `result` is `RECONCILE`
- **AND** `skipped_memory` is still populated
