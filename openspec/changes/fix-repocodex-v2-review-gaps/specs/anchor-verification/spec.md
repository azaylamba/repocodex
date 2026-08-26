## ADDED Requirements

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
