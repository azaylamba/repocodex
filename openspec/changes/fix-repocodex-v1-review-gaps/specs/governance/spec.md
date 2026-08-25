# governance Spec Delta

## ADDED Requirements

### Requirement: Contradiction requires an actual conflict

The system SHALL raise CONTRADICTION only when two live concepts genuinely conflict — asserting different literals for the same claim subject, or superseding the same predecessor — and SHALL NOT raise it merely because two concepts pin a shared path with differing claim sets. Claims MAY carry an optional subject discriminator; when a discriminator is absent, the comparison SHALL default to no conflict.

#### Scenario: Independent invariants on one file coexist

- **GIVEN** a grace-period invariant claiming `3` and a retry-budget invariant claiming `5`, both pinning the same source file
- **WHEN** validation runs
- **THEN** no CONTRADICTION is raised and the required check passes

#### Scenario: Same subject with different literals conflicts

- **GIVEN** two live concepts asserting different literals for the same claim subject on a shared pinned path
- **WHEN** validation runs
- **THEN** a CONTRADICTION is raised naming both concepts and the shared subject

#### Scenario: Missing discriminator stays silent

- **GIVEN** two live concepts with differing claims and no subject discriminators
- **WHEN** validation runs
- **THEN** no CONTRADICTION is raised

### Requirement: Bootstrap provenance is accurate per concept

The system SHALL cite, in each bootstrap-mined concept's `sources`, only provenance actually evidencing that concept — the commit, pull request, incident, or document the why was mined from — and SHALL NOT attach an unrelated blanket list of recent commits to every mined record. Bootstrap SHALL mine git history and documentation in addition to in-code comments.

#### Scenario: Mined concept cites its own origin

- **GIVEN** a why mined from a specific commit
- **WHEN** the bootstrap concept is written
- **THEN** its `sources` cite that commit and no unrelated commits

#### Scenario: Inaccurate provenance does not inflate retrieval rank

- **GIVEN** a bootstrap draft with no genuine evidencing source
- **WHEN** the concept is written
- **THEN** it is rejected rather than written with placeholder sources that would outrank genuinely sourced concepts

### Requirement: Generated concept identities are deterministic

The system SHALL derive every generated concept identity from a stable content digest, so that bootstrapping identical repository contents produces identical identities across processes, machines, and runs.

#### Scenario: Repeated bootstrap is stable

- **GIVEN** a repository bootstrapped twice in separate processes
- **WHEN** the resulting concept identities are compared
- **THEN** they are identical

### Requirement: Audit screening has an explicit out-of-band contract

The system SHALL define `repocodex audit` as emitting a screening payload for out-of-band model review and SHALL state that no model is invoked inside the engine. When a screening result is supplied back to the system, its findings SHALL become CONTRADICTION proposals resolved through the normal attested-write path, never automatic edits.

#### Scenario: Audit emits a screening payload without calling a model

- **GIVEN** a scheduled audit over stable concepts
- **WHEN** it runs
- **THEN** it emits sampled concepts with their pinned regions for review and makes no model call
- **AND** the payload states that findings are advisory proposals

#### Scenario: Returned screening findings become proposals

- **GIVEN** an out-of-band screening result asserting a concept contradicts its pinned code
- **WHEN** the result is supplied to the system
- **THEN** a CONTRADICTION proposal is raised for an agent to resolve and no concept is edited automatically
