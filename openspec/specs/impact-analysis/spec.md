# impact-analysis Specification

## Purpose

Compute intent-side blast radius deterministically from the reverse index and OKF links, run bounded code-side impact as a skill recipe, and keep every agent-judged finding on an advisory surface that cannot change the required check.

## Requirements

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

### Requirement: The advisory check carries agent-judged findings

The system SHALL make the advisory check a distinct surface that reports agent-judged findings — code-side impact results, prose-versus-diff verification, weakenings, skipped recipe steps, and churn flags — rather than re-reporting the deterministic verdict the required check already produces. The advisory check SHALL never affect the required check's verdict.

#### Scenario: Advisory check reports judgment, not a duplicate verdict

- **GIVEN** a pull request that changes code covered by memory
- **WHEN** both checks run
- **THEN** the advisory check reports code-side impact and prose-versus-diff findings
- **AND** it does not merely restate the required check's deterministic outcome

#### Scenario: Advisory failure does not affect the required verdict

- **GIVEN** an advisory check reporting several judgment findings
- **WHEN** the required check evaluates the same pull request
- **THEN** the required verdict is unchanged by those findings

### Requirement: The advisory check distinguishes an absent judgment from a clean one

The advisory payload SHALL report, per finding category, whether a judgment was produced. A category the engine cannot judge without an agent SHALL be reported as not evaluated, not as an empty finding list. A fixed note instructing a reader to perform the judgment SHALL NOT be reported as a finding. When no agent judgment is available for any category, the payload SHALL say so plainly so that a green advisory job is not mistaken for a reviewed change.

#### Scenario: Unevaluated category is not reported as clean

- **GIVEN** an advisory run with no agent judgment available for skipped recipe steps
- **WHEN** the payload is produced
- **THEN** the skipped-recipe-steps category is marked not evaluated
- **AND** it is not reported as an empty list of findings

#### Scenario: Produced judgment carries its finding

- **GIVEN** an advisory run in which an agent judged a concept's prose to disagree with the diff
- **WHEN** the payload is produced
- **THEN** the prose-versus-diff category is marked evaluated
- **AND** it carries the concept, the path, and the judged discrepancy

#### Scenario: Advisory payload never affects the required verdict

- **GIVEN** an advisory payload reporting findings in every category
- **WHEN** the required check runs on the same change
- **THEN** the required verdict's `blocking_reasons` is unaffected by the advisory payload

### Requirement: Impact hands the agent the why so it can read the scenario

The impact and context recipes SHALL give a coding or review agent the concepts (and their OKF links) that a diff touches, so the agent can read the why and then read the pinned code. That read is how existing scenarios are checked. The recipes SHALL NOT invoke a test runner, and SHALL NOT substitute a test result for the retrieved concepts.

#### Scenario: Diff surfaces linked why, not a test report

- **GIVEN** a change to a file pinned by a workflow concept that links to two other concepts
- **WHEN** impact runs
- **THEN** `impacted_scenarios` includes that workflow and the linked concepts
- **AND** the payload does not include a test-suite result standing in for those concepts

#### Scenario: Review agent judges the scenario from why plus the diff

- **GIVEN** the retrieved concepts and the diff
- **WHEN** the review agent evaluates whether the scenario still holds
- **THEN** the finding is posted on the advisory check
- **AND** the required check is unchanged by that finding
