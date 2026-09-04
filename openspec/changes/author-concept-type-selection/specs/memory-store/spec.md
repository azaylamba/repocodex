## MODIFIED Requirements

### Requirement: Concept types

The system SHALL author `TechnicalDecision`, `InvariantContract`, `BusinessWorkflow`, and `GuardrailDecision`. These types are orthogonal: a single change MAY add or update more than one type when each page is a distinct why. `InvariantContract` SHALL mean a must-hold token contract whose declared `claims` literals are re-checked as `CLAIM_BROKEN`; it SHALL NOT mean a general structural invariant. An `InvariantContract` write SHALL include at least one claim. The schema SHALL NOT enumerate OKF types as a closed set that rejects the document. A consumer load SHALL keep unknown `type` values. A concept that pins code SHALL pass the write gate; an unanchored typed page SHALL be loadable and SHALL NOT be reverse-indexed.

#### Scenario: Workflow concept spans packages

- **GIVEN** a business flow touching `api`, `billing`, `ledger`, and `notify` packages
- **WHEN** an agent writes a `BusinessWorkflow` concept
- **THEN** the concept carries one anchor per participating site, each attesting independently

#### Scenario: Guardrail concept pins enforcement config

- **GIVEN** a negative architectural rule enforced by import-linter
- **WHEN** an agent writes a `GuardrailDecision` concept
- **THEN** the concept anchors the enforcing tool's config file, so weakening the rule drifts the anchor
- **AND** anchors are stored as extra keys on that file

#### Scenario: Types coexist on one change

- **GIVEN** a change that introduces a construct why, a frozen contractual token, a cross-package flow, and a negative guardrail
- **WHEN** an agent authors memory for that change
- **THEN** the agent MAY write four concepts (one per type) in the same change
- **AND** the engine does not require exactly one type per change
