# anchor-verification Spec Delta

## ADDED Requirements

### Requirement: Claim-literal liveness is a distinct blocking classification

The system SHALL evaluate every declared `claims[].literal` of a stable concept against the anchor's matched region on each validation, independently of the anchor's LIVE / WEAK / REANCHOR / DRIFT term-count classification, and SHALL classify a concept whose declared literal is absent from the matched region as `CLAIM_BROKEN`. `CLAIM_BROKEN` SHALL be a blocking outcome outside `shadow` posture, SHALL be reported alongside the anchor classification rather than replacing it, and SHALL be repairable only through a gate-passing write.

#### Scenario: Contractual literal changed while the anchor stays live

- **GIVEN** a stable `InvariantContract` with `claims: [{ literal: "3" }]` whose anchor terms are `["ENTERPRISE", "grace", "= 3"]`
- **WHEN** a diff changes `const grace = 3` to `const grace = 1` in the pinned file
- **THEN** the concept is classified `CLAIM_BROKEN` for the literal `3`
- **AND** the verdict is blocking in `ratchet` and `full` posture
- **AND** the anchor's own term-count classification is reported unchanged alongside it

#### Scenario: Live anchor with intact claims does not block

- **GIVEN** a stable concept whose declared literals all appear in the matched region
- **WHEN** an unrelated edit is made inside the same region
- **THEN** no `CLAIM_BROKEN` outcome is produced and the verdict remains non-blocking

#### Scenario: Claim breakage is repaired through the gate

- **GIVEN** a `CLAIM_BROKEN` verdict caused by an intentional business-rule change
- **WHEN** the agent supersedes the concept with `supersedes` and `rationale` and re-anchors the new literal
- **THEN** the replacement must pass the write gate before the verdict clears

### Requirement: Precise claim matching

The system SHALL match every declared `claims[].literal` as a token against the anchor's `all_of` terms and against the matched source region, SHALL NOT satisfy a claim by substring containment within a longer term or literal, and SHALL NOT fall back to scanning the whole pinned file when no fully-matching region exists.

#### Scenario: Substring does not satisfy a claim

- **GIVEN** a concept declaring `claims: [{ literal: "3" }]` and an anchor term of `"= 30"`
- **WHEN** the write gate evaluates the concept
- **THEN** the write is rejected with `claim_not_anchored`

#### Scenario: Claim outside the matched region is not credited

- **GIVEN** a pinned file where the declared literal appears only outside the anchor's matched region
- **WHEN** validation runs
- **THEN** the literal is treated as absent from the region rather than credited from elsewhere in the file

### Requirement: Verdicts depend only on committed inputs

The system SHALL derive every verdict-affecting input — including derived configuration such as the distinctiveness ceiling — from tracked, non-excluded repository contents and the explicitly requested diff scope only. Untracked files, ignored files, and excluded paths SHALL NOT influence any verdict or any derived threshold.

#### Scenario: Installing dependencies does not change the gate

- **GIVEN** a repository whose `.repocodex.toml` does not pin `distinctiveness_ceiling`
- **WHEN** the derived ceiling is computed before and after a dependency install populates `node_modules/`
- **THEN** both computations return the same ceiling

#### Scenario: Untracked scratch files do not alter a verdict

- **GIVEN** a working tree containing untracked files that match anchor terms
- **WHEN** validation runs
- **THEN** the verdict is identical to the verdict for the same tracked contents without those files

### Requirement: Engine version pin is enforced

The system SHALL compare the `engine_version` pinned in `.repocodex.toml` against the running engine on every command and SHALL fail with a machine-readable version-mismatch error rather than proceeding and reporting the running version. Installation paths used by the hook and CI SHALL NOT silently fall back to an unpinned engine when the pinned version cannot be resolved.

#### Scenario: Mismatched pin fails loudly

- **GIVEN** a repository pinning `engine_version = "9.9.9"` and an installed engine at `1.0.0`
- **WHEN** any command runs
- **THEN** the command fails with a version-mismatch error naming both versions
- **AND** no verdict is emitted

#### Scenario: CI install does not defeat the pin

- **GIVEN** a CI job resolving the pinned engine version
- **WHEN** the pinned version cannot be installed
- **THEN** the job fails rather than installing the working-tree or latest version

### Requirement: Single regex dialect for anchor terms

The system SHALL guarantee that every anchor term stored in a bundle evaluates identically under every engine the system uses for that term. The write gate SHALL reject any regex term that does not compile with identical semantics under both the liveness matcher and the ripgrep counting path, reporting the term and the incompatibility.

#### Scenario: Dialect-specific construct is rejected at write time

- **GIVEN** an anchor term using a regex construct supported by one matcher but not the other
- **WHEN** `repocodex write` evaluates the concept
- **THEN** the write is rejected with the offending term and the dialect incompatibility
- **AND** the reject payload suggests a fixed-string stable-token alternative

#### Scenario: Fixed-string terms are unaffected

- **GIVEN** an anchor whose terms are all fixed strings
- **WHEN** the write gate evaluates it
- **THEN** no dialect check rejection occurs

### Requirement: Relocation uses the caller's diff scope

The system SHALL perform rename detection and pickaxe relocation against the same diff scope the validation was invoked with — staged, base-relative, or working tree — so that a given repository state and scope produce the same relocation outcome in the pre-commit hook, the local CLI, and CI.

#### Scenario: Staged rename re-anchors in the hook

- **GIVEN** a pinned file renamed 1:1 and staged for commit
- **WHEN** the pre-commit hook runs validation with staged scope
- **THEN** the rename is detected and a REANCHOR patch is emitted, matching the working-tree result for the same rename

#### Scenario: Base-relative rename re-anchors in CI

- **GIVEN** a pull request whose diff against the base renames a pinned file
- **WHEN** the required check validates against that base
- **THEN** the rename is detected rather than falling through to a pickaxe search

### Requirement: REANCHOR patches are complete

The system SHALL emit REANCHOR patches carrying every field the relocation changed — the pinned `path` and any relocated terms — together with an updated `verified` stamp of `{ by: process:repocodex-reanchor }`, so that a caller applying the patch verbatim produces a concept that attests and correctly records its provenance.

#### Scenario: Applied patch records reanchor provenance

- **GIVEN** a REANCHOR verdict for a renamed pinned file
- **WHEN** the caller applies the emitted patch
- **THEN** the concept's `verified.by` is `process:repocodex-reanchor`
- **AND** re-running validation classifies the concept LIVE with no further patch

### Requirement: Attestation is side-effect free

The system SHALL NOT modify the working tree during validation. Metrics, audit entries, and follow-up repair tasks SHALL be emitted in the verdict for the caller to persist, and any metrics sink SHALL live outside the committed `.context/` bundle and be ignored by git.

#### Scenario: Validation leaves the tree unchanged

- **GIVEN** a clean working tree
- **WHEN** validation runs in any posture, including a verdict that would record metrics or an override
- **THEN** the working tree remains clean

#### Scenario: Override artifacts are emitted, not written

- **GIVEN** an acknowledged `memory-exempt` override
- **WHEN** validation runs
- **THEN** the log entry and follow-up repair task appear in the verdict payload for the caller to apply

### Requirement: Exclusion path normalization is correct

The system SHALL normalize anchor paths for exclusion checking by removing a leading `./` prefix only, preserving leading dots in dotfile names, so that dotfile anchors such as enforcement-tool configs are checked against the paths they actually name.

#### Scenario: Dotfile anchor is checked under its real path

- **GIVEN** a `GuardrailDecision` anchoring `.importlinter`
- **WHEN** the write gate evaluates exclusions
- **THEN** the ignore check is performed against `.importlinter` rather than a name with the leading dot stripped
