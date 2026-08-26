## MODIFIED Requirements

### Requirement: Ratchet satisfaction is per-file and evidence-based

The system SHALL discharge a covered file's skipped-memory obligation only when at least one concept pinning that specific file was added or modified in the same change, or when every substantive hunk in that file falls inside a matched region of an attesting anchor that pins it. An edit to any other part of `.context/` SHALL NOT discharge the obligation for unrelated covered files. An attesting anchor SHALL NOT by itself discharge the obligation for the whole file: attestation establishes that the pinned region's memory is intact and establishes nothing about behavior added elsewhere in the file. Where changed line ranges cannot be attributed to a region, the system SHALL leave the obligation armed.

#### Scenario: Unrelated memory edit does not clear the ratchet

- **GIVEN** a covered source file substantively changed in `ratchet` posture
- **WHEN** the same change edits an unrelated file under `.context/` and leaves the concepts pinning the covered file untouched
- **THEN** the skipped-memory obligation for that covered file is still reported and the required check fails

#### Scenario: Maintaining the covering concept clears the ratchet

- **GIVEN** a covered source file substantively changed in `ratchet` posture
- **WHEN** the same change updates a concept that pins that file
- **THEN** the obligation is discharged for that file and the required check passes

#### Scenario: New behavior added outside the matched region arms the ratchet

- **GIVEN** a covered file whose pinning concept's anchors all classify `LIVE`
- **AND** a new function appended to the file, outside every matched region
- **AND** no concept pinning that file added or modified on the run
- **WHEN** the required check runs in `ratchet` posture
- **THEN** `skipped_memory` contains an entry for that file with reason `covered_file_without_memory_update`
- **AND** `blocking_reasons` contains `skipped_memory`

#### Scenario: Substantive change inside the matched region is discharged by attestation

- **GIVEN** a covered file whose pinning anchor classifies `LIVE`
- **AND** the only substantive hunk falls inside that anchor's matched region
- **WHEN** the required check runs in `ratchet` posture
- **THEN** `skipped_memory` is empty
- **AND** no `.context/` hunk is required

#### Scenario: Unattributable hunk leaves the obligation armed

- **GIVEN** a covered file with substantive change whose line ranges cannot be attributed to any matched region
- **WHEN** the required check runs in `ratchet` posture
- **THEN** the obligation is reported rather than discharged

## ADDED Requirements

### Requirement: Substantive-change detection honors the validation's diff scope

Substantive-change detection SHALL evaluate the same content the validation's diff scope selected. In working-tree scope it SHALL compare against `HEAD` so that staged and unstaged content are both visible; in staged scope it SHALL compare the index; in base scope it SHALL compare the requested base. A verdict SHALL be invariant under `git add`.

#### Scenario: Staging does not change the verdict

- **GIVEN** a substantive change to a covered file with no corresponding memory update
- **WHEN** the required check runs in working-tree scope before `git add`
- **AND** the required check runs again in working-tree scope after `git add`
- **THEN** both runs report the same `skipped_memory` entries
- **AND** both runs report the same `blocking_reasons`

#### Scenario: Formatting-only change stays non-substantive once staged

- **GIVEN** a whitespace-only reformat of a covered file
- **WHEN** the change is staged and the required check runs in working-tree scope
- **THEN** `skipped_memory` is empty

### Requirement: Shadow posture reports the reasons it declines to enforce

In `shadow` posture the verdict SHALL carry the same `blocking_reasons` list it would carry in `ratchet` posture, and the recorded metric SHALL carry the same `rejection_reasons`. Only the `blocking` field SHALL differ. Suppressing the reason list in `shadow` withholds the measurement that posture exists to produce.

#### Scenario: Shadow carries reasons with blocking false

- **GIVEN** a change that breaks a claim in a repo configured with `posture = "shadow"`
- **WHEN** validation runs
- **THEN** `blocking` is `false`
- **AND** `blocking_reasons` contains `claim_broken`

#### Scenario: Shadow and ratchet agree on reasons

- **GIVEN** an identical change validated once under `shadow` and once under `ratchet`
- **WHEN** both verdicts are compared
- **THEN** their `blocking_reasons` lists are equal
- **AND** only `blocking` and `posture` differ

#### Scenario: Recorded metric carries the shadow reasons

- **GIVEN** the shadow run above
- **WHEN** the metrics sink is read
- **THEN** the recorded `rejection_reasons` equals the verdict's `blocking_reasons`

### Requirement: Posture metrics measure their named quantity

`false_drift_rate` SHALL report the share of `DRIFT` classifications that a relocation should have resolved — drift whose repair re-points the anchor at code equivalent to the pinned region — and SHALL NOT report the raw drift rate. Per-turn cost SHALL be measured from the context actually served to the caller. Validation SHALL NOT invoke retrieval, body loading, or per-concept churn inference for the sole purpose of computing a metric.

#### Scenario: Genuine drift does not inflate the false-drift rate

- **GIVEN** a validation in which an anchor drifts because its pinned code was deleted outright
- **WHEN** the verdict is produced
- **THEN** `false_drift_rate` is `0.0`
- **AND** the drift is still reported in `lost`

#### Scenario: Validation does not run retrieval

- **GIVEN** any validation run
- **WHEN** the calls it makes are observed
- **THEN** no concept body is loaded and no churn inference is performed for metrics
