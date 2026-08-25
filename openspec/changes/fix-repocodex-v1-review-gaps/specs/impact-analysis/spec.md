# impact-analysis Spec Delta

## ADDED Requirements

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
