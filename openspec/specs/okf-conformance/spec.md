# okf-conformance Specification

## Purpose

Keep `.context/` a conformant OKF v0.2 bundle: every non-reserved markdown file is a typed concept, reserved names are only `index.md` and `log.md`, and runtime artifacts live outside the bundle. The product loop is unchanged: the body is the why; agents retrieve it and read pinned code; the required check attests pins.

## Requirements

### Requirement: The context tree is a conformant OKF v0.2 bundle

The directory that holds RepoCodex memory SHALL satisfy OKF v0.2 conformance: every non-reserved `.md` file has a parseable YAML frontmatter block and a non-empty `type`; reserved filenames at any level are only `index.md` and `log.md`; a missing optional family SHALL NOT cause a concept to be rejected. The product loop is unchanged: the body is the why; agents retrieve it and read pinned code; the required check attests pins, it does not run tests.

#### Scenario: A concept with only type is loadable

- **GIVEN** a `.md` file under `.context/` whose frontmatter is solely `type: Playbook`
- **WHEN** the bundle is loaded
- **THEN** the document is present as a concept
- **AND** it is not rejected for missing `verification`, `claims`, or `status`

#### Scenario: Unknown type is a generic concept

- **GIVEN** a concept with `type: Metric`
- **WHEN** the bundle is loaded
- **THEN** it is retained
- **AND** round-trip serialization preserves `type: Metric`

#### Scenario: Non-reserved markdown without type is not a concept

- **GIVEN** a `.md` file under `.context/` that is not `index.md` or `log.md` and has no `type`
- **WHEN** conformance of the bundle is checked
- **THEN** the bundle is reported non-conformant

### Requirement: Runtime artifacts do not occupy reserved or concept paths

Generated indexes that are not OKF concepts SHALL NOT live in the bundle under a reserved name OKF does not define. The reverse index SHALL be written outside `.context/`. `index.md` and `log.md` keep their OKF meanings. Regenerating the reverse index SHALL delete leftover `.context/**/reverse-index.md`. A leftover file is an illegal extra file, not an OKF reserved name.

#### Scenario: Reverse index is outside the bundle

- **GIVEN** an accepted write that pins a source file
- **WHEN** the reverse index is regenerated
- **THEN** no `reverse-index.md` exists under `.context/`
- **AND** the mapping is still readable by validate and context retrieval

#### Scenario: Leftover in-bundle reverse index is removed

- **GIVEN** a bundle that still contains `.context/reverse-index.md`
- **WHEN** the reverse index is regenerated
- **THEN** that file no longer exists under `.context/`
- **AND** `.repocodex/reverse-index.md` (or the shard file) holds the mapping

#### Scenario: Leftover is not reported as a reserved name

- **GIVEN** a bundle that still contains `.context/reverse-index.md`
- **WHEN** bundle conformance or index-sync is reported
- **THEN** the finding does not name `reverse-index.md` as an OKF reserved filename
- **AND** reserved names remain only `index.md` and `log.md`

#### Scenario: Root index declares okf_version

- **GIVEN** a newly created bundle
- **WHEN** the root `index.md` is read
- **THEN** its only frontmatter key is `okf_version` with value `"0.2"`
- **AND** it does not contain `format_version`

#### Scenario: Nested index has no frontmatter

- **GIVEN** a concept written under `invariants/`
- **WHEN** `invariants/index.md` is generated
- **THEN** the file has no YAML frontmatter
- **AND** the body lists the concept as a markdown link with title and description when present

#### Scenario: Catalog description comes from frontmatter

- **GIVEN** a concept whose frontmatter `description` is a unique string that does not already appear in the nested catalog
- **AND** whose body contains different prose
- **WHEN** the nested `index.md` is generated
- **THEN** the new catalog link includes that `description`
- **AND** the catalog does not use the body prose as the description

### Requirement: Log files follow OKF date grouping

`log.md` SHALL group entries under ISO 8601 `YYYY-MM-DD` headings, newest day first. Entries MAY keep a bold lead word. Engine writes SHALL append to today's heading rather than a flat timestamp list.

#### Scenario: A write appears under today's date heading

- **GIVEN** an accepted concept write
- **WHEN** the bundle `log.md` is read
- **THEN** the newest heading is `## YYYY-MM-DD` for the write's UTC date
- **AND** an entry names the concept identity

#### Scenario: Newer day sorts above older day

- **GIVEN** a `log.md` that already contains a `## 2020-01-01` heading with an entry
- **WHEN** a concept is written on a later UTC date
- **THEN** the later `## YYYY-MM-DD` heading appears before `## 2020-01-01`
- **AND** today's entry is under the later heading
