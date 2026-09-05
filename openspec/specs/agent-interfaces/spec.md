# agent-interfaces Specification

## Purpose

Expose all engine behavior through a canonical CLI with machine-readable JSON. Skills, MCP, hooks, and CI wrap that CLI. Distribution artifacts resolve inside the packaged tree, and `repocodex repair` reports only invocations it actually performed.

## Requirements

### Requirement: Canonical CLI

The system SHALL expose all functionality through a CLI — `validate`, `write`, `relocate`, `reconcile`, `context`, `repair`, `install`, `bootstrap`, `audit` — with machine-readable JSON outputs that include `engine_version`. All other surfaces (skills, MCP, hooks, CI) SHALL wrap the CLI rather than reimplement it.

#### Scenario: One install wires the portable floor

- **GIVEN** a repository without RepoCodex
- **WHEN** `repocodex install` runs without `--mcp`
- **THEN** the pre-commit hook, GitHub Action, and agent skills are installed together
- **AND** MCP is not registered as a working surface (that requires `--mcp` and the `mcp` extra)

#### Scenario: Bootstrap seeds only attested memory

- **GIVEN** a brownfield repository
- **WHEN** `repocodex bootstrap` mines git history, comments, and docs
- **THEN** only gate-passing concepts are kept, marked `status: draft` with `stale_after` and mandatory `sources`

### Requirement: Coding-agent skill

The system SHALL ship a coding-agent skill enforcing the loop: retrieve context before editing, run the impact recipe on the diff, validate before ending the turn, apply REANCHOR patches, repair DRIFT via `reconcile`/`write` in the same change, and write gate-passing concept(s) when `result` is `WRITE` or `skipped_memory` is non-empty — with anchor-authoring guidance that prefers stable tokens over renameable identifiers. `LIVE` / `WEAK` SHALL mean proceed only when `skipped_memory` is empty.

The same skill SHALL contain a self-contained orthogonal type recipe: after a code change, check independently whether a `TechnicalDecision`, `InvariantContract`, `BusinessWorkflow`, and/or `GuardrailDecision` applies; write or update every type that applies; do not invent a type that does not apply; do not stop after the first applicable type. It SHALL state that one concept covers one why (not one file or one `skipped_memory` path), that several paths sharing one why use one page with multiple anchors, that several distinct whys (including all four types) MAY appear in the same change, and that `InvariantContract` requires `claims` with frozen literals. It SHALL require type-folder identities (`decisions/`, `invariants/`, `workflows/`, `guardrails/` as applicable) and mention `identity_prefix_mismatch` / `repocodex relocate`. It SHALL include a worked example of one change that updates all four types. It SHALL NOT tell agents to pick exactly one type per change. Packaged, plugin, and `plugin/skills` copies SHALL stay aligned.

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
- **AND** it requires type-folder identities and mentions `identity_prefix_mismatch`
- **AND** it states one concept per why
- **AND** it does not instruct the agent to pick exactly one type per change

### Requirement: Review-agent skill

The system SHALL ship a review-agent skill that runs the impact recipe on every PR, verifies each new concept's prose against the originating diff, and flags unreconciled drift, skipped recipe steps, why-changes without `supersedes`/`rationale`, weakenings, contradictions, high churn, uncovered substantive files listed in `skipped_memory` without a pinning concept, `InvariantContract` pages missing `claims`, contractual literals in a `TechnicalDecision` body without `claims`, `GuardrailDecision` pages pinned only to application source, thick single-package pages typed as `BusinessWorkflow`, multiple new pages for the same why, and new authored-type concepts missing type-folder identities (including validate `identity_prefix_warnings`) — posting all findings to the advisory check only. The skill SHALL NOT flag a PR solely because it adds more than one concept type when the bodies are distinct whys. Packaged, plugin, and `plugin/skills` copies SHALL stay aligned.

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

### Requirement: Optional MCP wrapper

The system SHALL provide an optional MCP server exposing `get_context`, `get_impact`, `read_concept`, `write_memory`, `validate_diff`, and `reconcile_memory` as thin wrappers over the corresponding CLI commands, with identical verdicts. When the optional `mcp` extra is installed, `repocodex mcp` SHALL start that server over stdio using the official Python MCP SDK. When the extra is not installed, `repocodex mcp` SHALL exit with an explicit instruction to install `repocodex[mcp]` and SHALL NOT claim the server is unavailable for any other reason. A skills-only client SHALL still work. MCP SHALL NOT replace the hook or pin-check Action as enforcement.

#### Scenario: MCP and CLI agree

- **GIVEN** a build in which the MCP extra is installed
- **AND** the same diff
- **WHEN** validation runs via the MCP tool and via the CLI
- **THEN** the verdicts are identical, including `engine_version`

#### Scenario: Stdio server starts with the extra

- **GIVEN** a build with the `mcp` extra installed
- **WHEN** `repocodex mcp` runs
- **THEN** an MCP server listens on stdio
- **AND** it registers `get_context`, `get_impact`, `read_concept`, `write_memory`, `validate_diff`, and `reconcile_memory`

#### Scenario: Missing extra fails explicitly

- **GIVEN** a build without the `mcp` extra
- **WHEN** `repocodex mcp` runs
- **THEN** the process exits non-zero
- **AND** the message tells the caller to install `repocodex[mcp]`

### Requirement: install --mcp registers only a startable server

`repocodex install --mcp` SHALL merge the packaged MCP config into `.cursor/mcp.json` only when the `mcp` extra is importable. If the extra is missing, it SHALL NOT copy `mcp.json`, SHALL NOT list MCP as an installed working surface, and SHALL NOT set `ok` true solely because a config file was written.

#### Scenario: Extra present registers Cursor config

- **GIVEN** a repository and a build whose `mcp` extra imports
- **WHEN** `repocodex install --mcp` runs
- **THEN** `.cursor/mcp.json` contains the RepoCodex stdio server
- **AND** the payload lists MCP as installed
- **AND** `ok` is true if no other surfaces failed

#### Scenario: Extra missing does not copy mcp.json

- **GIVEN** a repository and a build whose `mcp` extra does not import
- **WHEN** `repocodex install --mcp` runs
- **THEN** `.cursor/mcp.json` is not created by this command
- **AND** MCP is not listed as an installed working surface
- **AND** `ok` is not true solely because an `mcp.json` was copied

### Requirement: Shipped Action installs the pinned engine

The GitHub Action that `repocodex install` writes SHALL install the engine at the `engine_version` pinned in `.repocodex.toml` and SHALL run `repocodex validate --diff --check` as the required job.

#### Scenario: Required job uses the pinned engine

- **GIVEN** a repository where `repocodex install` has written `.github/workflows/repocodex.yml` and `.repocodex.toml` with `engine_version = "0.0.1"`
- **WHEN** the required check job installs the engine
- **THEN** the installed engine version is `0.0.1`
- **AND** the job invokes `repocodex validate` with `--check`

### Requirement: Portable distribution

The system SHALL package skills and MCP configuration as an Agent Plugins 1.0 plugin (`plugin.json`, `skills/`, `mcp.json`), with the git pre-commit hook as the portable enforcement floor and per-client hook adapters (Claude/Cursor) as extras — because Agent Plugins 1.0 does not carry hooks.

#### Scenario: Skills-only client still works

- **GIVEN** an agent client that supports Agent Plugins skills but not MCP
- **WHEN** the plugin is installed
- **THEN** the skills load, the CLI remains fully usable, and enforcement still holds via hook and CI

### Requirement: `repocodex repair` invokes a repair agent

The system SHALL make `repocodex repair` invoke a repair agent against the current RECONCILE state, passing the verdict and repair prompt, and SHALL report an explicit, machine-readable failure when no agent harness is available rather than reporting success after merely writing a prompt file.

#### Scenario: Repair invokes an available harness

- **GIVEN** a repository in a RECONCILE state with an agent harness available
- **WHEN** a human runs `repocodex repair`
- **THEN** the harness is invoked with the verdict and repair prompt
- **AND** the result reports the invocation outcome

#### Scenario: No harness available fails explicitly

- **GIVEN** a repository in a RECONCILE state with no agent harness available
- **WHEN** a human runs `repocodex repair`
- **THEN** the command reports an explicit unavailable-harness failure with the repair prompt for manual use
- **AND** it does not report success

### Requirement: Distribution artifacts resolve within the packaged tree

The system SHALL ensure every installed artifact resolves the files it references from within the tree that was installed — per-client hook adapters SHALL resolve to a hook script present in the same distribution, and installation SHALL verify each artifact is resolvable before reporting it installed.

#### Scenario: Hook adapter resolves to a real hook

- **GIVEN** a repository where `repocodex install` has placed the plugin and its hook adapters
- **WHEN** a per-client hook adapter is executed
- **THEN** it resolves and runs the portable pre-commit hook from the installed tree

#### Scenario: Install verifies what it reports

- **GIVEN** an installation in which a referenced artifact is missing from the distribution
- **WHEN** `repocodex install` runs
- **THEN** it reports the failure rather than listing the artifact as installed

### Requirement: Repair reports only invocations it performed

`repocodex repair` SHALL report `invoked: true` only when it delivered the repair prompt to a harness and that harness ran to completion. Probing a harness — running `--help`, `--version`, or any command that does not receive the repair prompt — SHALL NOT be reported as an invocation. When a harness is present on `PATH` but the delivery fails or is not attempted, the payload SHALL report `invoked: false` with a reason, and SHALL still carry the prompt, the verdict, and the relocation candidates so a caller can drive the repair itself.

#### Scenario: Prompt delivered to an available harness

- **GIVEN** a repo in `RECONCILE` state and a harness on `PATH` that accepts the prompt
- **WHEN** `repocodex repair` runs
- **THEN** the harness receives the repair prompt
- **AND** the payload reports `invoked: true` and names the harness

#### Scenario: Probing a harness is not an invocation

- **GIVEN** a repo in `RECONCILE` state and a harness on `PATH` that the engine does not deliver the prompt to
- **WHEN** `repocodex repair` runs
- **THEN** the payload reports `invoked: false`
- **AND** the payload carries a reason distinguishing this from an absent harness

#### Scenario: Delivery failure is reported as a failure

- **GIVEN** a harness on `PATH` whose invocation exits non-zero
- **WHEN** `repocodex repair` runs
- **THEN** the payload reports `invoked: false` and `ok: false`
- **AND** the payload carries the prompt, `lost`, and `candidates`

#### Scenario: No harness available reports explicitly

- **GIVEN** a repo in `RECONCILE` state and no recognized harness on `PATH`
- **WHEN** `repocodex repair` runs
- **THEN** the payload reports `error: no_agent_harness` and `ok: false`
- **AND** the payload carries the prompt so the caller can drive the repair

### Requirement: Coding skill commits the reverse index beside metrics

The coding-agent skill, including the copy shipped inside the Agent Plugins tree, SHALL tell the agent that an accepted write or reanchor regenerates the reverse index outside `.context/` and that the same commit MUST include `.repocodex/reverse-index.md` and, when shards exist, the matching files under `.repocodex/reverse-index/`. Instructing the agent to commit `.context/` alone SHALL NOT be sufficient.

#### Scenario: Skill names the reverse-index commit path

- **GIVEN** the installed coding-agent skill text
- **WHEN** it describes what to stage after writing or reanchoring memory
- **THEN** it names `.repocodex/reverse-index.md` (and shard files under `.repocodex/reverse-index/` when applicable)
- **AND** it does not imply that committing `.context/` alone includes the reverse index
