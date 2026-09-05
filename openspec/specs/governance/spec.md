# governance Specification

## Purpose

Keep why-changes as supersede chains, raise CONTRADICTION only on genuine conflicts, contain attested-but-wrong memory, and retire unused pages without deleting history. The engine never picks a winner.

## Requirements

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

### Requirement: Attested-but-wrong memory is contained

The system SHALL contain attested-but-wrong memory in the engine path: bootstrap-mined concepts require `sources` and expire via `stale_after` unless re-attested; retrieval is provenance-weighted; and `repocodex audit` emits a screening payload of sampled stable concepts plus their pinned regions. Findings supplied back SHALL become CONTRADICTION proposals resolved through the attested-write path. The engine SHALL NOT invoke a model, auto-edit concepts, or put audit findings in the required check.

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

### Requirement: A memory-exempt acknowledgment cannot be issued by the author

Acknowledgment evidence for the `memory-exempt` override SHALL come from a reviewer other than the pull request author. The shipped Action SHALL accept only an approving review whose author differs from the pull request author; a comment review, a pending review, or any review authored by the pull request author SHALL NOT constitute evidence. An override without qualifying evidence SHALL leave the required check blocking and SHALL report `exemption_refused`.

#### Scenario: Author's own acknowledgment does not clear the check

- **GIVEN** a pull request carrying the `memory-exempt` label and a blocking reason
- **AND** the only review containing the acknowledgment token was authored by the pull request author
- **WHEN** the required check runs
- **THEN** `memory_exempt` is `false`
- **AND** `exemption_refused` is reported
- **AND** the check fails

#### Scenario: Comment review does not clear the check

- **GIVEN** a pull request carrying the `memory-exempt` label and a blocking reason
- **AND** the acknowledgment token appears only in a non-approving comment review by another user
- **WHEN** the required check runs
- **THEN** `memory_exempt` is `false`
- **AND** the check fails

#### Scenario: Approving review from another user clears the check

- **GIVEN** a pull request carrying the `memory-exempt` label and a blocking reason
- **AND** an approving review by a user other than the author containing the acknowledgment token
- **WHEN** the required check runs
- **THEN** `memory_exempt` is `true`
- **AND** the verdict emits the audit entry and the follow-up repair task

### Requirement: Environment-supplied acknowledgment evidence is confined to CI

The engine SHALL honor acknowledgment evidence supplied through the environment only when it is running in a recognized CI runner. Outside CI the engine SHALL ignore that channel and fall back to the tracked, committed acknowledgment record, so that setting an environment variable on a developer machine cannot clear a required check.

#### Scenario: Environment evidence is ignored on a developer machine

- **GIVEN** a blocking verdict and no tracked acknowledgment record
- **AND** the acknowledgment evidence environment variable set to an arbitrary value
- **AND** no CI runner environment present
- **WHEN** validation runs with the override requested
- **THEN** `memory_exempt` is `false`
- **AND** `exemption_refused` is reported

#### Scenario: Environment evidence is honored in CI

- **GIVEN** the same blocking verdict and evidence variable
- **AND** a recognized CI runner environment
- **WHEN** validation runs with the override requested
- **THEN** `memory_exempt` is `true`
