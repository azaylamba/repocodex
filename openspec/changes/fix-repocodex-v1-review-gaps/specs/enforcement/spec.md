# enforcement Spec Delta

## ADDED Requirements

### Requirement: Ratchet satisfaction is per-file and evidence-based

The system SHALL discharge a covered file's skipped-memory obligation only when at least one concept pinning that specific file was added or modified in the same change, or attested on that run. An edit to any other part of `.context/` SHALL NOT discharge the obligation for unrelated covered files.

#### Scenario: Unrelated memory edit does not clear the ratchet

- **GIVEN** a covered source file substantively changed in `ratchet` posture
- **WHEN** the same change edits an unrelated file under `.context/` and leaves the concepts pinning the covered file untouched
- **THEN** the skipped-memory obligation for that covered file is still reported and the required check fails

#### Scenario: Maintaining the covering concept clears the ratchet

- **GIVEN** a covered source file substantively changed in `ratchet` posture
- **WHEN** the same change updates a concept that pins that file
- **THEN** the obligation is discharged for that file and the required check passes

#### Scenario: A live anchor discharges the obligation without a memory hunk

- **GIVEN** a covered source file changed in a way that leaves its pinning anchors attesting
- **WHEN** the required check runs
- **THEN** the obligation is discharged with no `.context/` hunk required

### Requirement: Substantive change detection arms the ratchet

The system SHALL arm the skipped-memory ratchet only for diff content that is not exclusively whitespace and not exclusively comment-only lines, determined textually without a language allowlist, and SHALL resolve ambiguity by not arming the ratchet.

#### Scenario: Formatting-only edit does not trip the ratchet

- **GIVEN** a covered file in `ratchet` posture
- **WHEN** a diff changes only indentation and line wrapping in that file
- **THEN** no skipped-memory obligation is reported

#### Scenario: Comment-only edit does not trip the ratchet

- **GIVEN** a covered file in `ratchet` posture
- **WHEN** a diff adds only comment lines to that file
- **THEN** no skipped-memory obligation is reported

#### Scenario: Logic change trips the ratchet

- **GIVEN** a covered file in `ratchet` posture
- **WHEN** a diff changes executable content in that file without maintaining its memory
- **THEN** the skipped-memory obligation is reported

### Requirement: Shadow posture reports everything it declines to block

The system SHALL compute and report every deterministic finding in `shadow` posture — including skipped-memory obligations, claim breakage, drift, contradictions, and index desync — and SHALL block on none of them. Suppressing computation of a finding in `shadow` is not conformant, because the metrics that gate posture promotion are derived from those findings.

#### Scenario: Shadow reports skipped memory without blocking

- **GIVEN** a repository in `shadow` posture with a covered file changed and no memory maintenance
- **WHEN** validation runs
- **THEN** the skipped-memory obligation appears in the verdict
- **AND** the verdict is non-blocking

#### Scenario: Shadow reports claim breakage without blocking

- **GIVEN** a repository in `shadow` posture with a broken claim literal
- **WHEN** validation runs
- **THEN** the `CLAIM_BROKEN` finding appears in the verdict and nothing is denied

### Requirement: Posture promotion metrics are populated

The system SHALL populate the metrics that gate posture promotion with measured values rather than placeholders: false-drift rate, anchor-rejection reasons, reconcile retries, tokens per turn, and validate latency. Metrics SHALL be written to a sink outside the committed `.context/` bundle.

#### Scenario: Metrics carry measured values

- **GIVEN** a sequence of validations in `shadow` posture
- **WHEN** the metrics sink is inspected
- **THEN** false-drift rate and tokens per turn hold measured values rather than null placeholders

#### Scenario: Metrics do not pollute the bundle

- **GIVEN** any number of validations
- **WHEN** the repository status is inspected
- **THEN** no metrics artifact appears inside `.context/` and none appears as an untracked change

### Requirement: The required check's blocking set is closed and enumerated

The system SHALL fail the required CI check on exactly these deterministic outcomes and no others: unrepaired DRIFT on a stable anchor, `CLAIM_BROKEN` on a stable concept, an undischarged skipped-memory obligation for the active posture, reverse-index desync, and an unresolved CONTRADICTION. Every entry SHALL be reproducible from repository contents alone, and adding an entry SHALL require a spec change.

#### Scenario: Enumerated reason blocks

- **GIVEN** a pull request with an unresolved double supersede
- **WHEN** the required check runs
- **THEN** it fails citing the CONTRADICTION reason from the enumerated set

#### Scenario: Non-enumerated finding does not block

- **GIVEN** a pull request whose only findings are a WEAK anchor, a dilution warning, and an agent-judged impact note
- **WHEN** the required check runs
- **THEN** it passes and the findings are reported without blocking

### Requirement: The escape hatch is verifiable and usable end to end

The system SHALL require verifiable evidence of review-agent acknowledgment before a `memory-exempt` override clears the required check, and SHALL NOT accept an unauthenticated caller-supplied flag as that evidence. The shipped CI workflow SHALL wire the override path end to end so that an acknowledged exemption actually clears the check.

#### Scenario: Unauthenticated flag does not clear the check

- **GIVEN** a failing required check and a caller asserting acknowledgment with no corresponding evidence
- **WHEN** validation runs
- **THEN** the override is refused and the check remains blocking

#### Scenario: Acknowledged hotfix clears the check in CI

- **GIVEN** a hotfix pull request labelled `memory-exempt` with a recorded review-agent acknowledgment
- **WHEN** the shipped workflow runs the required check
- **THEN** the check passes
- **AND** the verdict carries the audit entry and follow-up repair task for the caller to persist

#### Scenario: Label without acknowledgment still blocks

- **GIVEN** a pull request labelled `memory-exempt` with no review-agent acknowledgment
- **WHEN** the required check runs
- **THEN** the check fails citing the missing acknowledgment
