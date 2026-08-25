# enforcement Spec Delta

## ADDED Requirements

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

The system SHALL scope skipped-memory enforcement to files that already contain at least one attested concept (file-level), extending repo-wide only for agent-authored commits in the `full` posture. Uncovered files SHALL never fail the check in `shadow` or `ratchet`.

#### Scenario: Brownfield repo is not blocked on day one

- **GIVEN** a repository with zero memory coverage in `ratchet` posture
- **WHEN** PRs touch uncovered files
- **THEN** the required check passes

#### Scenario: Covered file requires memory maintenance

- **GIVEN** a file carrying an attested concept, in `ratchet` posture
- **WHEN** a PR substantively changes that file without updating or writing memory and without a passing attest
- **THEN** the required check fails

### Requirement: Rollout postures

The system SHALL ship three configuration postures of the complete product — `shadow` (report everything, block nothing, collect metrics), `ratchet` (enforce DRIFT + covered-file skipped-memory), and `full` (extend enforcement to agent-authored commits, schedule audits) — selected in `.repocodex.toml`, with instrumentation for false-drift rate, rejection reasons, reconcile retries, tokens per turn, and validate latency.

#### Scenario: Shadow posture blocks nothing

- **GIVEN** a repo in `shadow` posture with drifting anchors
- **WHEN** hooks and CI run
- **THEN** all verdicts are reported and recorded, and nothing is denied

### Requirement: Human escape hatch

The system SHALL allow a human to merge past the required check via a `memory-exempt` override that requires review-agent acknowledgment, writes an audit entry to `log.md`, and files a follow-up repair task; and SHALL provide `repocodex repair` as a one-command human repair flow.

#### Scenario: Hotfix merges with audit trail

- **GIVEN** an incident hotfix PR failing the required check
- **WHEN** the `memory-exempt` label is applied and acknowledged
- **THEN** the merge proceeds, the bypass is logged in `log.md`, and a repair task is created for the next agent session
