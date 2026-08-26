## ADDED Requirements

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
