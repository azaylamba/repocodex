# anchor-verification Spec Delta

## ADDED Requirements

### Requirement: Textual anchor format

The system SHALL express every concept's link to code as one or more anchors, each consisting of a pinned `path` and an `all_of` set of distinctive terms (fixed strings or ripgrep regexes), with optional `near` + `scope_lines` proximity scoping and an optional `min_match` (N-of-M) liveness threshold. Terms SHALL be matched as tokens, not exact source lines.

#### Scenario: Formatter cannot break an anchor

- **GIVEN** a live anchor whose terms co-occur in the pinned region
- **WHEN** a code formatter rewraps the region across different lines
- **THEN** the anchor still matches and the concept remains LIVE

### Requirement: Deterministic write gate

The system SHALL accept or reject every concept write using only ripgrep counts and file reads — no model, no network — failing closed with machine-readable reasons: zero hits (`no_match`), multiple disjoint in-file co-occurrence regions (`ambiguous_in_file`), no term under the repo-wide distinctiveness ceiling (`not_distinctive`), declared claim literals absent from anchor terms or matched source (`claim_not_anchored`), and pins inside excluded paths (`excluded_path`). Reject payloads SHALL include per-term repo-wide hit counts.

#### Scenario: Tautological anchor rejected

- **GIVEN** an agent proposes an anchor of a single common identifier
- **WHEN** `repocodex write` evaluates it
- **THEN** the write is rejected with `not_distinctive` and the term's repo-wide count
- **AND** the payload ranks stable-token alternatives (string literals, error messages, enums, thresholds)

#### Scenario: Invariant literal must be frozen

- **GIVEN** a concept whose prose claims a 3-cycle grace period with `claims: [{ literal: "3" }]`
- **WHEN** the proposed anchor terms do not include `3`
- **THEN** the write is rejected with `claim_not_anchored`

### Requirement: Liveness classification

The system SHALL classify every stable concept whose pinned paths intersect a diff as exactly one of: LIVE (≥ `min_match` terms hit in the pinned region; no action), WEAK (partial term loss; reported and queued, never blocking), REANCHOR (full miss with exactly one relocation found via `git diff -M` rename or `git log -S` pickaxe; anchor patch emitted for the caller to apply), or DRIFT (full miss with zero or multiple candidates; RECONCILE JSON emitted).

#### Scenario: Identifier rename degrades to WEAK

- **GIVEN** an anchor with three terms and `min_match: 2`
- **WHEN** a diff renames the identifier matching one term
- **THEN** the concept is classified WEAK, logged for opportunistic tightening, and no agent is paged

#### Scenario: File move re-anchors without paging

- **GIVEN** a pinned file is renamed 1:1 in the diff
- **WHEN** validation runs
- **THEN** the engine emits an anchor patch with the new path
- **AND** the caller applies and stages it — the engine never mutates the working tree

#### Scenario: Ambiguous relocation becomes DRIFT

- **GIVEN** a full anchor miss whose pickaxe search finds two candidate locations
- **WHEN** validation runs
- **THEN** the result is RECONCILE JSON listing both candidates and the impacted scenarios
- **AND** the repair must pass the write gate before being accepted

### Requirement: In-file uniqueness scope

The system SHALL evaluate attest-time uniqueness within claimed pinned files only, use repo-wide search solely as a post-miss relocation locator, and report term dilution caused by other code as a warning attached to the PR that introduced the duplicate — never as drift on the untouched concept.

#### Scenario: No innocent-bystander pages

- **GIVEN** an unrelated PR adds code elsewhere containing a concept's anchor terms
- **WHEN** that PR is validated
- **THEN** the concept stays LIVE and the dilution warning attaches to the new PR

### Requirement: Engine determinism and version pinning

The system SHALL produce identical verdicts for identical inputs across environments: the engine version is pinned in `.repocodex.toml`, resolved identically by hook, local CLI, and CI, and reported as `engine_version` in every JSON output.

#### Scenario: IDE and CI agree

- **GIVEN** the same diff and the same pinned engine version
- **WHEN** validation runs locally and in CI
- **THEN** the verdicts are identical

### Requirement: Optional in-code markers

The system SHALL support `// why: <concept path>` comment markers as at most one additive anchor term, verify marker-to-concept agreement in CI, and SHALL reject any anchor whose only term is a marker.

#### Scenario: Marker cannot be the sole anchor

- **GIVEN** a proposed anchor whose `all_of` contains only a marker comment
- **WHEN** the write gate evaluates it
- **THEN** the write is rejected
