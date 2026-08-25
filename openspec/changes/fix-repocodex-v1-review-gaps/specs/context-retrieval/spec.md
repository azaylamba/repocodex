# context-retrieval Spec Delta

## ADDED Requirements

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
