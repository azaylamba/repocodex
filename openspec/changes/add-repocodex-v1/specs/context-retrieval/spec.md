# context-retrieval Spec Delta

## ADDED Requirements

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
