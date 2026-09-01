# user-docs Specification

## Purpose

User-facing documentation layout, README scope, and the explanations readers MUST be able to reconstruct after reading (purpose, benefit, loop, OKF, anti-regression).

## Requirements

### Requirement: README is the project front door only

`README.md` SHALL contain only what a first-time visitor needs to decide whether RepoCodex applies and to take the first step: one-paragraph purpose and benefit, a one-line positioning (git-native why next to code; pin check, not a test suite), install, the smallest command set (`install`, `context`, `validate`), engine-version pin, and links to `docs/`. It SHALL NOT duplicate architecture, CLI encyclopedias, OpenSpec, or full OKF field lists.

#### Scenario: README stays short

- **GIVEN** the project README
- **WHEN** a first-time reader opens it
- **THEN** they can state the purpose and benefit in one sentence
- **AND** they can install and run `repocodex context` / `repocodex validate --diff`
- **AND** they are pointed at named docs for how it works, how to read memory, and how agents use the loop

#### Scenario: README does not replace docs

- **GIVEN** the project README
- **WHEN** it is compared to `docs/`
- **THEN** it does not contain the full agent loop, the OKF field catalog, or the research architecture

### Requirement: README names the author without becoming a bio

`README.md` SHALL include a short author byline that names Ajay Lamba and links the GitHub user or this repository, while remaining the front door (purpose, benefit, install, three commands, links to `docs/`). It SHALL NOT add a long personal bio or duplicate architecture.

#### Scenario: Byline is present and README stays short

- **GIVEN** the project README
- **WHEN** a first-time reader opens it
- **THEN** they can see that Ajay Lamba created the project
- **AND** they can still state purpose and benefit in one sentence
- **AND** they are still pointed at named docs for how it works, memory, agents, and install

### Requirement: Each documentation file has one job

The documentation tree SHALL use these files and no extra user-facing guides unless a later spec adds them:

| File | Job |
| --- | --- |
| `README.md` | Front door: purpose, benefit, install, three commands, links |
| `docs/how-it-works.md` | Core concepts and the retrieve → read code → edit → update why → pin-check loop |
| `docs/memory.md` | How to read `.context/` (OKF v0.2): body is why, anchors pin live text, links, reverse index outside the bundle |
| `docs/agents.md` | How coding agents (and optionally humans) run that loop so a change does not detach why from code |
| `docs/install.md` | `repocodex install`, `.repocodex.toml` pin, hook, GitHub Action, optional `mcp` extra |
| `CONTRIBUTING.md` | How to contribute to the *engine* (tests, OpenSpec), not how to use memory in an application repo |
| `docs/research/architecture.md` | Canonical design; linked as further reading, not onboarding |

A file SHALL NOT repeat another file's job. Cross-links SHALL be used instead of copy.

#### Scenario: A reader looking for one topic opens one file

- **GIVEN** a reader who wants to know what lives in `.context/`
- **WHEN** they follow the README link for memory
- **THEN** they land on `docs/memory.md`
- **AND** that file does not also contain install or the full CLI reference

#### Scenario: Architecture is further reading

- **GIVEN** `docs/how-it-works.md`
- **WHEN** a reader wants engine internals
- **THEN** they are linked to `docs/research/architecture.md`
- **AND** they are not required to read it to understand purpose, benefit, and the loop

### Requirement: Readers can explain purpose, benefit, and the loop

After reading `README.md` and `docs/how-it-works.md`, a reader SHALL be able to reconstruct: RepoCodex stores *why* in an OKF bundle beside the code; agents retrieve that why and read the pinned source before editing; new work updates why in the same change, including the first substantive edit of an uncovered file; a deterministic pin check (ripgrep + git) attests that why is still attached to live text, and skipped-memory denies a change that recorded no why. The benefit is that institutional why cannot silently detach, which instruction files and tests do not guarantee.

#### Scenario: Purpose and benefit are explicit

- **GIVEN** `docs/how-it-works.md`
- **WHEN** it is read end to end
- **THEN** it states the problem (agents forget why; comments and AGENTS.md detach)
- **AND** it states the benefit (why stays git-native and pin-checked)
- **AND** it states that the required check is not a pytest suite for scenarios

#### Scenario: The loop is the product

- **GIVEN** `docs/how-it-works.md`
- **WHEN** it describes a change to a pinned file
- **THEN** the steps are: `repocodex context` (or equivalent retrieval), read returned bodies and the pinned code, edit, update or write memory if why changed, `repocodex validate --diff`
- **AND** skipped retrieval is still caught later by CLAIM_BROKEN, DRIFT, or skipped-memory on hook/CI

#### Scenario: Empty context still requires a write

- **GIVEN** `docs/how-it-works.md`
- **WHEN** it describes a substantive edit to a file with no retrieved concepts
- **THEN** it states that the agent must write a pinning concept in the same change
- **AND** that `LIVE` from validate is not success while `skipped_memory` is non-empty

### Requirement: Memory docs teach how to read OKF, not how to reimplement it

`docs/memory.md` SHALL explain enough of OKF v0.2 for a consumer of `.context/`: reserved `index.md` / `log.md`; concept files with `type`; body = why; `verification.anchors` and `claims` as RepoCodex extensions on the same file; markdown links for related why; reverse index at `.repocodex/reverse-index.md` (not inside the bundle); `verified` is definition review, not a gate stamp. It SHALL link the official OKF spec for field catalogs. It SHALL NOT require `type: Attested Computation` as the memory unit.

#### Scenario: An agent can open a concept file usefully

- **GIVEN** `docs/memory.md`
- **WHEN** an agent (or human) opens a concept under `.context/`
- **THEN** they know to read the body as why, follow anchors to code, and follow markdown links for related why
- **AND** they know not to treat the reverse index as a concept

#### Scenario: Trust is not the pin check

- **GIVEN** `docs/memory.md`
- **WHEN** it mentions `verified` or trust
- **THEN** it states that missing `verified` does not fail CI
- **AND** that a passing pin check does not write `verified`

### Requirement: Agent and optional-human docs describe anti-regression as the read loop plus pin check

`docs/agents.md` SHALL be written for coding agents first. It SHALL tell them to retrieve context before edit, keep why intact unless they intend a why-change (`supersedes` + `rationale`), write a pinning concept when context was empty and the edit is substantive, commit `.context/` and `.repocodex/reverse-index.md` (and shards) with the code, treat `WRITE` / non-empty `skipped_memory` as an unfinished turn, and treat hook/CI failure as unrepaired pin breakage or skipped memory. Humans MAY follow the same CLI; they are not required in the hot path. The document SHALL NOT present tests, human approval, or OKF trust tiers as the regression check.

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

### Requirement: Install docs cover the mechanical floor only

`docs/install.md` SHALL cover installing the CLI, `repocodex install` (hook, Action, skills), the `.repocodex.toml` engine pin, and that hook and CI wrap `repocodex validate`. Optional MCP belongs in this file as a separate step (`mcp` extra then `repocodex install --mcp`), not as part of the required floor. It SHALL NOT explain OKF or the agent loop.

#### Scenario: Install is enough to get a blocking check

- **GIVEN** `docs/install.md`
- **WHEN** a maintainer follows it in an application repo
- **THEN** they can install, pin the engine, and enable hook plus required CI
- **AND** they are linked to `docs/how-it-works.md` for what the check means

### Requirement: Install docs include optional MCP extra

`docs/install.md` SHALL document installing the optional `mcp` extra (`pip install 'repocodex[mcp]'` or `pip install -e '.[mcp]'`) and then `repocodex install --mcp` as a working setup step for hosts that speak MCP over stdio. That step SHALL remain optional. The README SHALL remain the front door and SHALL NOT require MCP to complete the first install.

#### Scenario: Maintainer can wire MCP from install.md

- **GIVEN** `docs/install.md`
- **WHEN** a maintainer wants Cursor (or another stdio host) to call RepoCodex tools
- **THEN** they are instructed to install the `mcp` extra and run `repocodex install --mcp`
- **AND** they can still complete CLI, hook, and Action setup without that step

#### Scenario: README stays the front door

- **GIVEN** the project README
- **WHEN** a first-time reader follows the install snippet
- **THEN** they can install from git or a clone and run `repocodex install`, `context`, and `validate --diff`
- **AND** they are not required to install MCP to finish that path

### Requirement: Install docs do not assume PyPI

`README.md` and `docs/install.md` SHALL tell a first-time visitor how to install from the public git tag on `azaylamba/repocodex` (or an equivalent local editable install). They SHALL NOT present `pip install repocodex` from PyPI as the install path until a later change adds a published package. They SHALL state that the first public release is experimental (`0.0.1`).

#### Scenario: README install works without PyPI

- **GIVEN** the project README
- **WHEN** a first-time reader follows the install snippet
- **THEN** the commands do not require a PyPI project named `repocodex`
- **AND** they can reach `repocodex context` / `repocodex validate --diff` after install from git or from a clone

#### Scenario: Install doc matches the shipped Action

- **GIVEN** `docs/install.md`
- **WHEN** it describes how CI gets the engine
- **THEN** it describes git-tag install matching `engine_version`
- **AND** it does not say the Action runs `pip install repocodex==` against PyPI

### Requirement: Install docs state default shadow still denies skipped memory

`docs/install.md` SHALL state that default `posture = "shadow"` reports pin-check findings without denying drift or `CLAIM_BROKEN`, and SHALL state that undischarged skipped-memory (including first-touch of uncovered source) is blocking in `shadow` so hook and `--check` deny a change that recorded no why.

#### Scenario: Maintainer is not told shadow never blocks

- **GIVEN** `docs/install.md`
- **WHEN** it describes `posture`
- **THEN** it does not claim that shadow blocks nothing
- **AND** it names skipped-memory as blocking on the default install
