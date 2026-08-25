# memory-store Spec Delta

## ADDED Requirements

### Requirement: Accepted writes land in the owning shard

The system SHALL write each accepted concept into the `.context/` shard that owns its pinned paths — the deepest mirrored bundle whose directory contains them — rather than always into the shallowest discovered bundle, and SHALL place cross-cutting concepts whose pins span shards at the root bundle. The reverse index of the receiving shard SHALL be regenerated on acceptance.

#### Scenario: Package-local concept lands in the package shard

- **GIVEN** a monorepo with a `.context/` bundle at the root and another mirroring `packages/billing/`
- **WHEN** a concept pinning only files under `packages/billing/` is accepted
- **THEN** the concept file is written into the `packages/billing/.context/` shard
- **AND** that shard's reverse index includes the new mapping

#### Scenario: Cross-shard concept lands at the root

- **GIVEN** a `BusinessWorkflow` concept with anchors in two different shards
- **WHEN** the write is accepted
- **THEN** the concept is written to the root bundle and each affected shard's reverse index reflects its pins
