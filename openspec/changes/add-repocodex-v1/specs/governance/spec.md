# governance Spec Delta

## ADDED Requirements

### Requirement: Supersede chain on why-change

The system SHALL require why-changes to supersede the predecessor concept (`status: deprecated`, `supersedes` + `rationale`) rather than clobber it, so the next agent sees that and why the why changed.

#### Scenario: Business rule change leaves a trail

- **GIVEN** a stable `InvariantContract` whose business rule is being changed intentionally
- **WHEN** the agent writes the replacement concept
- **THEN** the old concept is deprecated with the new one recording `supersedes` and `rationale`, and both remain in git history

### Requirement: Contradiction handling

The system SHALL flag CONTRADICTION when overlapping pinned regions carry conflicting claims, or when a merge leaves two concepts superseding the same predecessor, and SHALL require the current agent to resolve by superseding one — the engine never picks a winner.

#### Scenario: Post-merge double supersede

- **GIVEN** two branches that each superseded the same concept
- **WHEN** the first validate after the merge runs
- **THEN** a CONTRADICTION is raised and merge-completion is blocked until an agent resolves it through the gate

### Requirement: Anti-poisoning controls

The system SHALL treat attested-but-wrong memory as a first-class threat: the review agent verifies new concepts' prose against the originating diff at write time; bootstrap-mined concepts require `sources` and expire via `stale_after` unless re-attested; retrieval is provenance-weighted; and `repocodex audit` periodically samples stable concepts plus their pinned code for model-based contradiction screening whose findings become CONTRADICTION flags — proposals only, resolved through the normal attested-write path, never in the hot path or required check.

#### Scenario: Sampling audit surfaces a stale why

- **GIVEN** a stable concept whose narrative no longer matches its pinned code's behavior
- **WHEN** a scheduled `repocodex audit` samples it
- **THEN** a CONTRADICTION flag is raised for an agent to resolve, and no automatic edit occurs

### Requirement: Garbage collection

The system SHALL deprecate — never delete — unmatched drafts, records past `stale_after`, and orphaned pages (no inbound OKF links and no live anchors), keeping one concept per why and updating in place when the why is unchanged.

#### Scenario: Expired bootstrap draft is retired

- **GIVEN** a `draft` bootstrap concept past its `stale_after` without a passing attest
- **WHEN** GC runs
- **THEN** the concept is marked `deprecated` and remains retrievable from git history

### Requirement: Churn-based down-ranking

The system SHALL infer concept churn from git history and down-rank high-churn concepts in retrieval, without storing any score in the bundle.

#### Scenario: Frequently rewritten why loses rank

- **GIVEN** a concept superseded three times in a month
- **WHEN** context is retrieved for its pinned file
- **THEN** it ranks below stable, sourced concepts pinning the same file
