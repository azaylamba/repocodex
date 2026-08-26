# anchor-verification Specification

## Purpose

Pin every concept to live code with distinctive textual anchors. Accept or reject writes with ripgrep only. Classify touched anchors as LIVE, WEAK, REANCHOR, or DRIFT, and evaluate declared claim literals against the owning anchor independently of term-count classification.

## Requirements

### Requirement: Textual anchor format

The system SHALL express every concept's link to code as one or more anchors, each consisting of a pinned `path` and an `all_of` set of distinctive terms (fixed strings or ripgrep regexes), with optional `near` + `scope_lines` proximity scoping and an optional `min_match` (N-of-M) liveness threshold. Terms SHALL be matched as tokens, not exact source lines.

#### Scenario: Formatter cannot break an anchor

- **GIVEN** a live anchor whose terms co-occur in the pinned region
- **WHEN** a code formatter rewraps the region across different lines
- **THEN** the anchor still matches and the concept remains LIVE

### Requirement: Deterministic write gate

The system SHALL accept or reject every concept write using only ripgrep counts and file reads — no model, no network — failing closed with machine-readable reasons: zero hits (`no_match`), multiple disjoint in-file co-occurrence regions (`ambiguous_in_file`), no term under the repo-wide distinctiveness ceiling (`not_distinctive`), declared claim literals absent from anchor terms or matched source (`claim_not_anchored`), and pins inside excluded paths (`excluded_path`). Reject payloads SHALL include per-term repo-wide hit counts.

#### Scenario: Tautological anchor rejected

- **GIVEN** an agent proposes an anchor of a single common identifier
- **WHEN** `repocodex write` evaluates it
- **THEN** the write is rejected with `not_distinctive` and the term's repo-wide count
- **AND** the payload ranks stable-token alternatives (string literals, error messages, enums, thresholds)

#### Scenario: Invariant literal must be frozen

- **GIVEN** a concept whose prose claims a 3-cycle grace period with `claims: [{ literal: "3" }]`
- **WHEN** the proposed anchor terms do not include `3`
- **THEN** the write is rejected with `claim_not_anchored`

### Requirement: Liveness classification

The system SHALL classify every stable concept whose pinned paths intersect a diff as exactly one of: LIVE (≥ `min_match` terms hit in the pinned region; no action), WEAK (partial term loss; reported and queued, never blocking), REANCHOR (full miss with exactly one relocation found via `git diff -M` rename or `git log -S` pickaxe; anchor patch emitted for the caller to apply), or DRIFT (full miss with zero or multiple candidates; RECONCILE JSON emitted).

#### Scenario: Identifier rename degrades to WEAK

- **GIVEN** an anchor with three terms and `min_match: 2`
- **WHEN** a diff renames the identifier matching one term
- **THEN** the concept is classified WEAK, logged for opportunistic tightening, and no agent is paged

#### Scenario: File move re-anchors without paging

- **GIVEN** a pinned file is renamed 1:1 in the diff
- **WHEN** validation runs
- **THEN** the engine emits an anchor patch with the new path
- **AND** the caller applies and stages it — the engine never mutates the working tree

#### Scenario: Ambiguous relocation becomes DRIFT

- **GIVEN** a full anchor miss whose pickaxe search finds two candidate locations
- **WHEN** validation runs
- **THEN** the result is RECONCILE JSON listing both candidates and the impacted scenarios
- **AND** the repair must pass the write gate before being accepted

### Requirement: In-file uniqueness scope

The system SHALL evaluate attest-time uniqueness within claimed pinned files only, use repo-wide search solely as a post-miss relocation locator, and report term dilution caused by other code as a warning attached to the PR that introduced the duplicate — never as drift on the untouched concept.

#### Scenario: No innocent-bystander pages

- **GIVEN** an unrelated PR adds code elsewhere containing a concept's anchor terms
- **WHEN** that PR is validated
- **THEN** the concept stays LIVE and the dilution warning attaches to the new PR

### Requirement: Engine determinism and version pinning

The system SHALL produce identical verdicts for identical inputs across environments: the engine version is pinned in `.repocodex.toml`, resolved identically by hook, local CLI, and CI, and reported as `engine_version` in every JSON output.

#### Scenario: IDE and CI agree

- **GIVEN** the same diff and the same pinned engine version
- **WHEN** validation runs locally and in CI
- **THEN** the verdicts are identical

### Requirement: Optional in-code markers

The system SHALL support `// why: <concept path>` comment markers as at most one additive anchor term, verify marker-to-concept agreement in CI, and SHALL reject any anchor whose only term is a marker.

#### Scenario: Marker cannot be the sole anchor

- **GIVEN** a proposed anchor whose `all_of` contains only a marker comment
- **WHEN** the write gate evaluates it
- **THEN** the write is rejected

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

### Requirement: A claim declares the anchor that owns it

A `claims[]` entry SHALL carry an optional `anchor` field naming the index of the anchor within the concept's `verification.anchors` list that must carry the literal. The write gate SHALL evaluate the claim against that anchor alone, requiring the literal to appear both in that anchor's `all_of` terms and as a token in that anchor's matched region. Validation SHALL report `CLAIM_BROKEN` when the literal is absent from the owning anchor's matched region, and SHALL attribute the finding to that anchor's path. Anchors that do not own a claim SHALL NOT be evaluated against it.

This supersedes the conjunctive evaluation introduced by `fix-repocodex-v1-review-gaps`, under which every claim was required to hold in every anchor's matched region and no multi-anchor concept carrying a claim could be written.

#### Scenario: Claim evaluated only against its declared owner

- **GIVEN** a `BusinessWorkflow` with anchors on billing, ledger, and notification files
- **AND** a claim whose `anchor` names the billing anchor, whose literal is a term of that anchor and present in its matched region
- **WHEN** the concept is written
- **THEN** the write gate accepts it
- **AND** `tighten` does not contain `claim_not_anchored`

#### Scenario: Breakage at the owning anchor is reported against that anchor

- **GIVEN** the accepted concept above, committed and stable
- **WHEN** the literal is removed from the billing file
- **THEN** validation reports exactly one `CLAIM_BROKEN` finding for that literal
- **AND** the finding's `path` is the billing anchor's path

#### Scenario: Change at a non-owning anchor does not break the claim

- **GIVEN** the accepted concept above
- **WHEN** the ledger file is changed and the billing literal is untouched
- **THEN** `claim_findings` is empty

#### Scenario: Out-of-range owner is rejected at write time

- **GIVEN** a concept whose claim names an `anchor` index with no corresponding anchor
- **WHEN** the concept is written
- **THEN** the write gate rejects it with a reason naming the invalid index

### Requirement: An omitted claim owner is resolved deterministically or rejected

When a claim omits `anchor`, the engine SHALL resolve the owner without ambiguity or reject the write. The owner SHALL be the sole anchor when the concept has exactly one. When the concept has several, the owner SHALL be the single anchor whose `all_of` declares the literal. When no anchor declares it, or more than one does, the write SHALL be rejected with a reason directing the author to declare `anchor`. Resolution SHALL NOT depend on anchor iteration order.

#### Scenario: Single-anchor concept needs no declaration

- **GIVEN** an `InvariantContract` with one anchor and a claim omitting `anchor`
- **WHEN** the concept is written
- **THEN** the claim is evaluated against that anchor
- **AND** the write gate accepts it

#### Scenario: Unambiguous inference across several anchors

- **GIVEN** a multi-anchor concept and a claim omitting `anchor`
- **AND** exactly one anchor whose `all_of` declares the literal
- **WHEN** the concept is written
- **THEN** that anchor is recorded as the owner
- **AND** the write gate accepts it

#### Scenario: Ambiguous omission is rejected

- **GIVEN** a multi-anchor concept and a claim omitting `anchor`
- **AND** two anchors whose `all_of` declares the literal
- **WHEN** the concept is written
- **THEN** the write gate rejects it
- **AND** the reason directs the author to declare `anchor`

#### Scenario: Undeclared literal is rejected

- **GIVEN** a multi-anchor concept and a claim omitting `anchor`
- **AND** no anchor whose `all_of` declares the literal
- **WHEN** the concept is written
- **THEN** the write gate rejects it with `claim_not_anchored`

### Requirement: Claim ownership survives a re-anchor

Applying a REANCHOR patch SHALL preserve each claim's owning anchor. A patch that relocates an anchor SHALL NOT change which anchor a claim is evaluated against, and SHALL NOT renumber the anchors a claim refers to.

#### Scenario: Relocated owner keeps its claims

- **GIVEN** a multi-anchor concept whose claim owner is relocated by a rename
- **WHEN** the REANCHOR patch is applied
- **THEN** the claim still names the relocated anchor
- **AND** validation reports no `CLAIM_BROKEN` for a literal present at the new path

### Requirement: Regex portability is decided by matching behavior

The write gate SHALL reject a regex anchor term when the Python `re` matcher and the ripgrep counting path disagree on whether the term matches a given input, not merely when one of the two fails to compile it. The check SHALL exercise both engines against the pinned file's content and compare the resulting match decision.

#### Scenario: Construct that compiles in both but matches differently is rejected

- **GIVEN** a regex anchor term that both Python `re` and ripgrep compile without error
- **AND** the two engines reach opposite match decisions against the pinned file
- **WHEN** the concept is written
- **THEN** the write gate rejects it with `regex_dialect` in `tighten`

#### Scenario: Portable regex term is accepted

- **GIVEN** a regex anchor term that both engines compile and on which both reach the same match decision against the pinned file
- **WHEN** the concept is written
- **THEN** `regex_dialect` is absent from `tighten`
