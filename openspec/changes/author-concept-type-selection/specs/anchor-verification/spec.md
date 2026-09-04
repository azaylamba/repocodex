## MODIFIED Requirements

### Requirement: Deterministic write gate

The system SHALL accept or reject every concept write using only ripgrep counts and file reads — no model, no network — failing closed with machine-readable reasons: zero hits (`no_match`), multiple disjoint in-file co-occurrence regions (`ambiguous_in_file`), no term under the repo-wide distinctiveness ceiling (`not_distinctive`), declared claim literals absent from anchor terms or matched source (`claim_not_anchored`), `type: InvariantContract` with missing or empty `claims` (`claims_required`), and pins inside excluded paths (`excluded_path`). Reject payloads SHALL include per-term repo-wide hit counts.

#### Scenario: Tautological anchor rejected

- **GIVEN** an agent proposes an anchor of a single common identifier
- **WHEN** `repocodex write` evaluates it
- **THEN** the write is rejected with `not_distinctive` and the term's repo-wide count
- **AND** the payload ranks stable-token alternatives (string literals, error messages, enums, thresholds)

#### Scenario: Invariant literal must be frozen

- **GIVEN** a concept whose prose claims a 3-cycle grace period with `claims: [{ literal: "3" }]`
- **WHEN** the proposed anchor terms do not include `3`
- **THEN** the write is rejected with `claim_not_anchored`

#### Scenario: InvariantContract without claims is rejected

- **GIVEN** a concept with `type: InvariantContract` and no `claims` (missing or empty)
- **WHEN** `repocodex write` evaluates it
- **THEN** the write is rejected with `claims_required`
- **AND** a `TechnicalDecision` without `claims` is not rejected for that reason alone
