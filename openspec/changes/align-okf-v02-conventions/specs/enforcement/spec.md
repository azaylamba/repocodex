## ADDED Requirements

### Requirement: In-bundle reverse index is reverse-index desync

A leftover `.context/**/reverse-index.md` SHALL be reported as the existing required-check reason `index_sync`. The closed blocking set SHALL NOT gain a new member for OKF layout. When validate runs with staged or hook scope, index-sync SHALL compare the git-index copy of `.repocodex/reverse-index.md` (and shard files under `.repocodex/reverse-index/`); a generated file that exists only in the working tree SHALL count as desync.

#### Scenario: Leftover in-bundle file blocks as index_sync

- **GIVEN** a repository whose `.repocodex/reverse-index.md` matches the pins and whose `.context/reverse-index.md` still exists
- **WHEN** the required check runs
- **THEN** it is blocking
- **AND** `blocking_reasons` contains `index_sync` and does not contain a new reason name for bundle layout

#### Scenario: Unstaged generated reverse index is desync under hook scope

- **GIVEN** a write that regenerated `.repocodex/reverse-index.md` on disk
- **AND** that file is not in the git index
- **WHEN** `repocodex validate --diff --staged` (or `--hook`) runs
- **THEN** `blocking_reasons` contains `index_sync`
- **AND** a subsequent `git add` of that file clears the `index_sync` reason if pins otherwise match
