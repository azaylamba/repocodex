# agent-interfaces Spec Delta

## ADDED Requirements

### Requirement: Canonical CLI

The system SHALL expose all functionality through a CLI — `validate`, `write`, `reconcile`, `context`, `repair`, `install`, `bootstrap`, `audit` — with machine-readable JSON outputs that include `engine_version`. All other surfaces (skills, MCP, hooks, CI) SHALL wrap the CLI rather than reimplement it.

#### Scenario: One install wires everything

- **GIVEN** a repository without RepoCodex
- **WHEN** `repocodex install` runs
- **THEN** the pre-commit hook, GitHub Action, agent skills, and optional MCP registration are installed together

#### Scenario: Bootstrap seeds only attested memory

- **GIVEN** a brownfield repository
- **WHEN** `repocodex bootstrap` mines git history, comments, and docs
- **THEN** only gate-passing concepts are kept, marked `status: draft` with `stale_after` and mandatory `sources`

### Requirement: Coding-agent skill

The system SHALL ship a coding-agent skill enforcing the loop: retrieve context before editing, run the impact recipe on the diff, validate before ending the turn, apply REANCHOR patches, and repair DRIFT via `reconcile`/`write` in the same change — with anchor-authoring guidance that prefers stable tokens over renameable identifiers.

#### Scenario: Turn cannot end on unrepaired drift

- **GIVEN** a coding agent whose diff produced DRIFT
- **WHEN** the agent attempts to finish its turn or commit
- **THEN** the skill and hook require a gate-passing repair first

### Requirement: Review-agent skill

The system SHALL ship a review-agent skill that runs the impact recipe on every PR, verifies each new concept's prose against the originating diff, and flags unreconciled drift, skipped recipe steps, why-changes without `supersedes`/`rationale`, weakenings, contradictions, and high churn — posting all findings to the advisory check only.

#### Scenario: New concept verified while diff is in context

- **GIVEN** a PR that adds a new concept alongside code
- **WHEN** the review agent runs
- **THEN** it checks the concept's narrative against the diff and flags mismatches as advisory findings

### Requirement: Optional MCP wrapper

The system SHALL provide an optional MCP server exposing `get_context`, `get_impact`, `read_concept`, `write_memory`, `validate_diff`, and `reconcile_memory` as thin wrappers over the corresponding CLI commands, with identical verdicts.

#### Scenario: MCP and CLI agree

- **GIVEN** the same diff
- **WHEN** validation runs via the MCP tool and via the CLI
- **THEN** the verdicts are identical, including `engine_version`

### Requirement: Portable distribution

The system SHALL package skills and MCP configuration as an Agent Plugins 1.0 plugin (`plugin.json`, `skills/`, `mcp.json`), with the git pre-commit hook as the portable enforcement floor and per-client hook adapters (Claude/Cursor) as extras — because Agent Plugins 1.0 does not carry hooks.

#### Scenario: Skills-only client still works

- **GIVEN** an agent client that supports Agent Plugins skills but not MCP
- **WHEN** the plugin is installed
- **THEN** the skills load, the CLI remains fully usable, and enforcement still holds via hook and CI
