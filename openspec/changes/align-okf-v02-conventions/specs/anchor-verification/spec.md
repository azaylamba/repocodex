## ADDED Requirements

### Requirement: Stored verified is definition review, not a pin receipt

OKF `verified` records who confirmed the concept's *definition* against its sources. A successful ripgrep match, write-gate accept, or REANCHOR SHALL NOT replace or append `verified` by itself. Pin liveness remains a runtime attest: LIVE, WEAK, REANCHOR, DRIFT, CLAIM_BROKEN in the validate verdict. That verdict is not written into the concept. The product goal is unchanged: agents read why then code; the required check still blocks when pins break.

#### Scenario: Gate pass leaves verified unchanged

- **GIVEN** a stable concept with no `verified` key
- **WHEN** `repocodex write` accepts it because anchors match
- **THEN** the stored file still has no `verified` key
- **AND** the write payload reports accepted

#### Scenario: Validate does not stamp verified

- **GIVEN** a concept whose anchors still match
- **WHEN** `repocodex validate` runs
- **THEN** the working tree's concept files are byte-identical to before
- **AND** the verdict may include LIVE or CLAIM_BROKEN without writing `verified`

#### Scenario: Reanchor does not pretend to be definition review

- **GIVEN** a unique rename producing a REANCHOR patch
- **WHEN** the patch is applied
- **THEN** the concept's `path` is updated
- **AND** `verified` is not set to `process:repocodex-reanchor` unless a separate definition review occurred

### Requirement: Anchors remain extra keys on the why document

A concept that pins code SHALL keep `verification.anchors` (and `claims` when used) on that same file. The engine SHALL NOT require a sibling `type: Attested Computation` concept in order to attest. Optional `resource` MAY duplicate the primary pinned path as a URI for OKF consumers; retrieval and the pin check still use anchors.

#### Scenario: One file is enough for an invariant

- **GIVEN** an InvariantContract whose body states the why and whose frontmatter carries anchors and a claim
- **WHEN** it is written and later validated
- **THEN** no second Attested Computation file is required
- **AND** changing the claimed literal in the pinned file still reports CLAIM_BROKEN

#### Scenario: Optional resource does not replace anchors

- **GIVEN** a concept with `resource` set to a file URI and with anchors
- **WHEN** the pin check runs
- **THEN** liveness is decided from `verification.anchors`
- **AND** `resource` alone is not treated as an anchor
