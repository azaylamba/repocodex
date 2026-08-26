## ADDED Requirements

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
