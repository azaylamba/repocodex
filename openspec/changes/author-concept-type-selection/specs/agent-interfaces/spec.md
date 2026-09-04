## MODIFIED Requirements

### Requirement: Coding-agent skill

The system SHALL ship a coding-agent skill enforcing the loop: retrieve context before editing, run the impact recipe on the diff, validate before ending the turn, apply REANCHOR patches, repair DRIFT via `reconcile`/`write` in the same change, and write gate-passing concept(s) when `result` is `WRITE` or `skipped_memory` is non-empty — with anchor-authoring guidance that prefers stable tokens over renameable identifiers. `LIVE` / `WEAK` SHALL mean proceed only when `skipped_memory` is empty.

The same skill SHALL contain a self-contained orthogonal type recipe: after a code change, check independently whether a `TechnicalDecision`, `InvariantContract`, `BusinessWorkflow`, and/or `GuardrailDecision` applies; write or update every type that applies; do not invent a type that does not apply; do not stop after the first applicable type. It SHALL state that one concept covers one why (not one file or one `skipped_memory` path), that several paths sharing one why use one page with multiple anchors, that several distinct whys (including all four types) MAY appear in the same change, and that `InvariantContract` requires `claims` with frozen literals. It SHALL include a worked example of one change that updates all four types. It SHALL NOT tell agents to pick exactly one type per change. Packaged, plugin, and `plugin/skills` copies SHALL stay aligned.

#### Scenario: Turn cannot end on unrepaired drift

- **GIVEN** a coding agent whose diff produced DRIFT
- **WHEN** the agent attempts to finish its turn or commit
- **THEN** the skill and hook require a gate-passing repair first

#### Scenario: Turn cannot end on WRITE

- **GIVEN** a coding agent whose validate payload has `result` `WRITE` or non-empty `skipped_memory`
- **WHEN** the agent attempts to finish its turn or commit
- **THEN** the skill requires gate-passing `repocodex write` of concept(s) that together pin each listed path, then re-validate
- **AND** the skill allows one concept with multiple anchors when those paths share one why
- **AND** the hook denies the commit while `blocking` is true

#### Scenario: Skill teaches orthogonal types

- **GIVEN** the installed coding-agent skill text (packaged, plugin, and `plugin/skills` copies)
- **WHEN** an agent must write memory
- **THEN** the skill names `TechnicalDecision`, `InvariantContract`, `BusinessWorkflow`, and `GuardrailDecision`
- **AND** it states types are independent and may coexist in one change
- **AND** it requires `claims` on `InvariantContract`
- **AND** it states one concept per why
- **AND** it does not instruct the agent to pick exactly one type per change

### Requirement: Review-agent skill

The system SHALL ship a review-agent skill that runs the impact recipe on every PR, verifies each new concept's prose against the originating diff, and flags unreconciled drift, skipped recipe steps, why-changes without `supersedes`/`rationale`, weakenings, contradictions, high churn, uncovered substantive files listed in `skipped_memory` without a pinning concept, `InvariantContract` pages missing `claims`, contractual literals in a `TechnicalDecision` body without `claims`, `GuardrailDecision` pages pinned only to application source, thick single-package pages typed as `BusinessWorkflow`, and multiple new pages for the same why — posting all findings to the advisory check only. The skill SHALL NOT flag a PR solely because it adds more than one concept type when the bodies are distinct whys. Packaged, plugin, and `plugin/skills` copies SHALL stay aligned.

#### Scenario: New concept verified while diff is in context

- **GIVEN** a PR that adds a new concept alongside code
- **WHEN** the review agent runs
- **THEN** it checks the concept's narrative against the diff and flags mismatches as advisory findings

#### Scenario: Missing first-touch concept is advisory

- **GIVEN** a PR whose required check reports `uncovered_file_without_memory`
- **WHEN** the review agent runs
- **THEN** it flags the missing pinning concept as an advisory finding

#### Scenario: Multi-type PR is not wrong by itself

- **GIVEN** a PR that adds a `TechnicalDecision` and an `InvariantContract` with distinct whys
- **WHEN** the review agent runs
- **THEN** it does not flag the presence of multiple types as a finding
- **AND** it still flags an `InvariantContract` that lacks `claims`
