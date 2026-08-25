# conformance Spec Delta

## ADDED Requirements

### Requirement: Every spec scenario has a falsifiable test

The system SHALL back each specification scenario with at least one automated test that fails when the described behavior regresses, and SHALL maintain a traceable mapping from scenario to test so that unmapped scenarios are detectable.

#### Scenario: Regression in a specified behavior fails the suite

- **GIVEN** a scenario stating that a renamed pinned file produces a REANCHOR patch
- **WHEN** the implementation is changed to produce DRIFT instead
- **THEN** the test suite fails

#### Scenario: Unmapped scenario is detectable

- **GIVEN** a newly added specification scenario with no corresponding test
- **WHEN** the conformance mapping is checked
- **THEN** the scenario is reported as unmapped

### Requirement: Scenario tests assert single expected outcomes

The system's scenario tests SHALL assert the one outcome the scenario specifies. A test SHALL NOT accept alternative classifications through disjunction, SHALL NOT substitute an assertion on an unrelated field for the behavior under test, and SHALL assert the presence and content of findings the scenario requires.

#### Scenario: Classification is asserted exactly

- **GIVEN** a scenario specifying the REANCHOR classification
- **WHEN** its test runs
- **THEN** the test asserts REANCHOR exactly and does not also accept DRIFT

#### Scenario: Required findings are asserted present

- **GIVEN** a scenario specifying that a dilution warning attaches to the introducing change
- **WHEN** its test runs
- **THEN** the test asserts the warning is present and names the diluted terms

#### Scenario: Placeholder assertions are not conformant

- **GIVEN** a test whose only assertion checks a field unrelated to the behavior under test, such as the engine version
- **WHEN** the conformance mapping is checked
- **THEN** the scenario is reported as unmapped
