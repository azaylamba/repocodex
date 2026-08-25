# agent-interfaces Spec Delta

## ADDED Requirements

### Requirement: `repocodex repair` invokes a repair agent

The system SHALL make `repocodex repair` invoke a repair agent against the current RECONCILE state, passing the verdict and repair prompt, and SHALL report an explicit, machine-readable failure when no agent harness is available rather than reporting success after merely writing a prompt file.

#### Scenario: Repair invokes an available harness

- **GIVEN** a repository in a RECONCILE state with an agent harness available
- **WHEN** a human runs `repocodex repair`
- **THEN** the harness is invoked with the verdict and repair prompt
- **AND** the result reports the invocation outcome

#### Scenario: No harness available fails explicitly

- **GIVEN** a repository in a RECONCILE state with no agent harness available
- **WHEN** a human runs `repocodex repair`
- **THEN** the command reports an explicit unavailable-harness failure with the repair prompt for manual use
- **AND** it does not report success

### Requirement: Distribution artifacts resolve within the packaged tree

The system SHALL ensure every installed artifact resolves the files it references from within the tree that was installed — per-client hook adapters SHALL resolve to a hook script present in the same distribution, and installation SHALL verify each artifact is resolvable before reporting it installed.

#### Scenario: Hook adapter resolves to a real hook

- **GIVEN** a repository where `repocodex install` has placed the plugin and its hook adapters
- **WHEN** a per-client hook adapter is executed
- **THEN** it resolves and runs the portable pre-commit hook from the installed tree

#### Scenario: Install verifies what it reports

- **GIVEN** an installation in which a referenced artifact is missing from the distribution
- **WHEN** `repocodex install` runs
- **THEN** it reports the failure rather than listing the artifact as installed
