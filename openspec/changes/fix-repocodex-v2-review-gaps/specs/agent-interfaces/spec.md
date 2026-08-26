## ADDED Requirements

### Requirement: Repair reports only invocations it performed

`repocodex repair` SHALL report `invoked: true` only when it delivered the repair prompt to a harness and that harness ran to completion. Probing a harness — running `--help`, `--version`, or any command that does not receive the repair prompt — SHALL NOT be reported as an invocation. When a harness is present on `PATH` but the delivery fails or is not attempted, the payload SHALL report `invoked: false` with a reason, and SHALL still carry the prompt, the verdict, and the relocation candidates so a caller can drive the repair itself.

#### Scenario: Prompt delivered to an available harness

- **GIVEN** a repo in `RECONCILE` state and a harness on `PATH` that accepts the prompt
- **WHEN** `repocodex repair` runs
- **THEN** the harness receives the repair prompt
- **AND** the payload reports `invoked: true` and names the harness

#### Scenario: Probing a harness is not an invocation

- **GIVEN** a repo in `RECONCILE` state and a harness on `PATH` that the engine does not deliver the prompt to
- **WHEN** `repocodex repair` runs
- **THEN** the payload reports `invoked: false`
- **AND** the payload carries a reason distinguishing this from an absent harness

#### Scenario: Delivery failure is reported as a failure

- **GIVEN** a harness on `PATH` whose invocation exits non-zero
- **WHEN** `repocodex repair` runs
- **THEN** the payload reports `invoked: false` and `ok: false`
- **AND** the payload carries the prompt, `lost`, and `candidates`

#### Scenario: No harness available reports explicitly

- **GIVEN** a repo in `RECONCILE` state and no recognized harness on `PATH`
- **WHEN** `repocodex repair` runs
- **THEN** the payload reports `error: no_agent_harness` and `ok: false`
- **AND** the payload carries the prompt so the caller can drive the repair
