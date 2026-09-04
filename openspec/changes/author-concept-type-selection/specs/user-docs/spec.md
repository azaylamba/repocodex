## MODIFIED Requirements

### Requirement: Agent and optional-human docs describe anti-regression as the read loop plus pin check

`docs/agents.md` SHALL be written for coding agents first. It SHALL tell them to retrieve context before edit, keep why intact unless they intend a why-change (`supersedes` + `rationale`), write a pinning concept when context was empty and the edit is substantive, commit `.context/` and `.repocodex/reverse-index.md` (and shards) with the code, treat `WRITE` / non-empty `skipped_memory` as an unfinished turn, and treat hook/CI failure as unrepaired pin breakage or skipped memory. It SHALL include a short orthogonal summary of the four authored types and one-concept-per-why volume, and SHALL state that the full when/how recipe lives in the installed coding skill. Humans MAY follow the same CLI; they are not required in the hot path. The document SHALL NOT present tests, human approval, or OKF trust tiers as the regression check.

#### Scenario: Agent path is complete

- **GIVEN** `docs/agents.md`
- **WHEN** an agent is about to change a covered file
- **THEN** the doc names `repocodex context <paths>` as the first step
- **AND** names validate before the turn ends
- **AND** names what to stage when memory was written or reanchored

#### Scenario: Uncovered file path is complete

- **GIVEN** `docs/agents.md`
- **WHEN** `repocodex context` returns no concepts for the files to edit
- **THEN** the doc tells the agent to write a pinning concept after the edit
- **AND** not to treat `result` `LIVE` as done if `skipped_memory` is populated

#### Scenario: Humans are optional

- **GIVEN** `docs/agents.md` or `docs/how-it-works.md`
- **WHEN** a human developer is described
- **THEN** they may run the same CLI and the `memory-exempt` escape hatch is mentioned only as an exception
- **AND** the doc does not require a human to author or verify each concept

#### Scenario: Type summary points at the skill

- **GIVEN** `docs/agents.md`
- **WHEN** an agent needs to choose concept type or count
- **THEN** the doc summarizes the four orthogonal types and one-concept-per-why
- **AND** it states that the installed coding skill is the full recipe

## ADDED Requirements

### Requirement: Memory docs state type intent and claims

`docs/memory.md` SHALL state that `type` is author intent (catalog), that the four authored types may coexist on one change when they are distinct whys, and that `claims` are the binary token check (`CLAIM_BROKEN`) — with `InvariantContract` requiring claims as a must-hold token contract, not a general structural invariant.

#### Scenario: Reader understands type vs claims

- **GIVEN** `docs/memory.md`
- **WHEN** a reader opens a concept
- **THEN** they know `type` is author intent
- **AND** they know `claims` freeze checkable literals for `CLAIM_BROKEN`
- **AND** they know types are not mutually exclusive per change
