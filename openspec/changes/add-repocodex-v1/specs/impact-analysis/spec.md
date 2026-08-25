# impact-analysis Spec Delta

## ADDED Requirements

### Requirement: Deterministic intent-side impact

The system SHALL compute intent-side impact deterministically — changed files → reverse index → concepts → OKF markdown links → other pinned paths — and include the resulting `impacted_scenarios` in every validate output.

#### Scenario: Cross-package scenario surfaces on a local edit

- **GIVEN** a `BusinessWorkflow` concept pinning sites in `billing`, `ledger`, and `notify`
- **WHEN** a diff touches only the `ledger` site
- **THEN** validate output lists the workflow among `impacted_scenarios`, exposing the downstream ordering constraint

### Requirement: Bounded agentic code-side impact

The coding and review skills SHALL run a bounded code-side impact recipe on every diff — grep changed symbol names, rank hits by path proximity and test-file status, read plausible callers within a per-walk file cap, respect exclusion lists — and treat a skipped recipe step as a review-agent finding.

#### Scenario: Common symbol name does not explode the walk

- **GIVEN** a changed symbol whose name greps to hundreds of hits in a monorepo
- **WHEN** the impact recipe runs
- **THEN** hits are ranked and reads stop at the configured cap

### Requirement: Advisory-only enforcement of judgment findings

The system SHALL NOT gate the required CI check on any agent-judged impact finding. Code-side impact results, "scenarios not considered" flags, and similar judgments post only to the separate advisory review check.

#### Scenario: Nondeterministic finding cannot block a merge

- **GIVEN** a review-agent impact finding produced by model judgment
- **WHEN** checks are reported on the PR
- **THEN** the finding appears in the advisory check and the required check's verdict is unaffected
