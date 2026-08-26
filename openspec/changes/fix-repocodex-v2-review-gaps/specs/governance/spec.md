## ADDED Requirements

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
