# context-retrieval Specification

## Purpose

Answer which whys apply to files about to be edited, in stages: reverse-index lookup, directory catalogs, then bodies on demand. Rank by provenance and inferred churn; exclude unattested drafts from production reads by default.

## Requirements

### Requirement: Staged retrieval

The system SHALL answer "which whys apply to these files" in stages — reverse-index lookup first, directory `index.md` catalogs second, full concept bodies on demand — and SHALL never emit the whole `.context/` corpus in one response.

#### Scenario: Agent retrieves context before editing

- **GIVEN** an agent about to edit two source files
- **WHEN** it runs `repocodex context <paths>`
- **THEN** it receives the concepts pinning those paths with bodies, plus one link-hop of related pages as titles only

#### Scenario: Large corpus stays out of the prompt

- **GIVEN** a repository with thousands of stable concepts
- **WHEN** context is retrieved for a typical edit
- **THEN** only the concepts pinned to the files in play (typically 2–5 bodies) are returned

### Requirement: Ranked ordering

The system SHALL order retrieved concepts by provenance weight — attested concepts citing `sources` before bare narrative — and SHALL down-rank high-churn concepts using churn inferred from git history, never a stored score.

#### Scenario: Provenance beats bare narrative

- **GIVEN** two concepts pinning the same file, one citing a source PR and one without sources
- **WHEN** context is retrieved
- **THEN** the sourced concept ranks first

### Requirement: Draft concepts excluded from production reads

The system SHALL default production retrieval to `status: stable` concepts; `draft` (unattested bootstrap) concepts are excluded unless explicitly requested.

#### Scenario: Unattested bootstrap record is not served

- **GIVEN** a bootstrap-mined concept still in `status: draft`
- **WHEN** an agent retrieves context for its pinned file
- **THEN** the draft is omitted from the default result

### Requirement: The catalog stage is used

The system SHALL consult directory `index.md` catalogs as the middle stage of staged retrieval, between the reverse-index lookup and the loading of concept bodies, so that sibling concepts in a relevant directory are surfaced as titles without their bodies being read.

#### Scenario: Sibling concepts surface as titles

- **GIVEN** a directory containing several concepts, one of which pins a file being edited
- **WHEN** context is retrieved for that file
- **THEN** the pinning concept's body is returned
- **AND** its directory catalog siblings are offered as titles without bodies

#### Scenario: Catalog stage does not expand the body budget

- **GIVEN** a directory containing many concepts
- **WHEN** context is retrieved for one pinned file in it
- **THEN** only the pinned concepts' bodies are returned, and the catalog contributes titles only

### Requirement: Churn inference is shard-aware

The system SHALL infer concept churn from the git history of each concept's actual file location, resolving the owning `.context/` shard rather than assuming a root-relative path, so that concepts stored in sharded bundles are ranked on real churn.

#### Scenario: Sharded concept is ranked on real churn

- **GIVEN** a frequently rewritten concept stored in a `packages/billing/.context/` shard
- **WHEN** context is retrieved for its pinned file
- **THEN** its churn is computed from that file's history and it is down-ranked accordingly, not treated as zero-churn

### Requirement: Retrieval serves the bundle, not only pinned concepts

`repocodex context` SHALL return concepts that the reverse index or directory catalog associates with the requested paths, including linked neighbors that have no anchors. Reserved files (`index.md`, `log.md`) are catalogs, not concept bodies. Unanchored pages are for the agent to read as why; they SHALL NOT by themselves arm skipped-memory.

#### Scenario: Linked unanchored page is reachable

- **GIVEN** a pinning concept that markdown-links to an unanchored Playbook in the same bundle
- **WHEN** context is requested for the pinned source path
- **THEN** the Playbook appears as a linked title or one-hop body
- **AND** no test runner is invoked

#### Scenario: Unanchored page does not trip the ratchet

- **GIVEN** only an unanchored concept in `.context/` and a source file with no pinning concept
- **WHEN** that source file changes substantively
- **THEN** skipped-memory is not reported for that file by reason of the unanchored page
