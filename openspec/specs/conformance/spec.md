# conformance Specification

## Purpose

Keep the why of a change in linked OKF concepts served to agents. Scenario integrity is judged by reading that why and the pinned code. The required check remains a pin check; this capability does not add blocking reasons or a scenario-to-test table.

## Requirements

### Requirement: Why is stored as linked OKF and served to agents

The why of a change or of an implementation SHALL live in an OKF concept — business, technical, or both. A scenario that spans files SHALL be expressed by linking concepts, not by a side table. Correspondence from a code path to the concepts that describe it SHALL be the reverse index, regenerated on accepted writes. An agent about to edit SHALL retrieve those concepts and their linked neighbors through the existing context recipe. No hand-maintained mapping from scenarios to tests SHALL exist, and no human SHALL be required to keep the graph in sync.

Creating RepoCodex’s own bundle is a separate change. Until that bundle exists, this capability applied to RepoCodex itself SHALL report unsatisfied rather than falling back to a table.

#### Scenario: Agent finds why from the path it is about to edit

- **GIVEN** a concept whose anchors pin a source file and whose body states why that code exists
- **WHEN** an agent requests context for that path
- **THEN** the concept is returned
- **AND** linked concepts for a multi-file scenario are reachable as titles or one-hop bodies
- **AND** no scenario-to-test table is consulted

#### Scenario: Multi-file scenario is a link, not a second index

- **GIVEN** a workflow whose steps live in billing, ledger, and notification files
- **AND** concepts for those steps linked to each other
- **WHEN** one of the pinned files changes
- **THEN** impact lists the linked concepts
- **AND** the agent can follow the links without a human pointing at them

#### Scenario: New why is written in the same change

- **GIVEN** an agent adding or changing an implementation
- **WHEN** the change is completed
- **THEN** the why is captured in a concept in the same change
- **AND** the skipped-memory ratchet reports the file if that write did not happen

#### Scenario: Bundle absent reports unsatisfied, not a table fallback

- **GIVEN** a repository with no OKF bundle of its own
- **WHEN** this capability is checked against that repository
- **THEN** it is reported unsatisfied
- **AND** no scenario-to-test table is used

### Requirement: Scenario integrity is judged by reading why and code

Whether a change breaks an existing scenario SHALL be decided by an agent that has retrieved the relevant concepts and read the code they pin. That judgment SHALL NOT be performed by running a test suite. The required check SHALL NOT fail because an agent judged a scenario broken; it SHALL fail only when memory is no longer pinned to live text — unreconciled drift, a broken claim literal, skipped memory, index desync, or unresolved contradiction.

#### Scenario: Agent verifies by reading, not by running tests

- **GIVEN** a diff that touches a pinned file
- **WHEN** the coding or review agent runs the context and impact recipes
- **THEN** it receives the why for that file and the linked scenario
- **AND** it judges the scenario against the code by reading
- **AND** no test runner is invoked for that judgment

#### Scenario: Required check stays a pin check

- **GIVEN** an agent that judged a scenario weakened but left every anchor and claim literal intact
- **WHEN** the required check runs
- **THEN** it does not block on that judgment
- **AND** the judgment appears only on the advisory surface

#### Scenario: Detached memory still blocks

- **GIVEN** a change that removes the pinned text a concept’s anchors require, with no reconcile
- **WHEN** the required check runs
- **THEN** the verdict blocks
- **AND** the reason is drawn from the existing closed blocking set

### Requirement: The required check does not grow a parallel conformance path

Conformance SHALL not introduce blocking reasons, a scenario-to-test table, or a test runner in the required job. When RepoCodex later hosts its own bundle, the same split SHALL apply to it: the engine attests that its why is still pinned; agents read that why and the engine source to judge whether a change breaks a described scenario.

#### Scenario: No new blocking reason

- **GIVEN** any validation run
- **WHEN** blocking reasons are enumerated
- **THEN** they are a subset of the existing closed set
- **AND** no reason named `conformance` or `unmapped_scenario` is present

#### Scenario: Table is gone

- **GIVEN** the codebase after this change
- **WHEN** a caller looks up a scenario by name
- **THEN** `src/repocodex/conformance.py` does not exist
- **AND** no dictionary maps scenario titles to test function names
