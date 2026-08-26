# Tasks: align-okf-v02-conventions

Product lock: one why file, anchors as extra keys, agent-read loop, pin check stays runtime. Do not add Attested Computation as the memory unit.

## 1. Schema and parse

- [x] 1.1 Make `type` a string (preserve known RepoCodex values); do not reject unknown types
- [x] 1.2 Default omitted `status` to `stable`
- [x] 1.3 Model `sources` as a list of objects with required `resource` and optional `id` / `title` / credibility fields
- [x] 1.4 Accept `verified` as a mapping or a list; do not require it
- [x] 1.5 Read `okf_version` from root `index.md`; stop writing `format_version`
- [x] 1.6 Round-trip unknown frontmatter keys including unknown `type`

## 2. Bundle layout

- [x] 2.1 Create bundles whose root index frontmatter is only `okf_version: "0.2"`
- [x] 2.2 Generate nested `index.md` without frontmatter, with title (and description when present) on each link
- [x] 2.3 Write `log.md` under `## YYYY-MM-DD` headings, newest first
- [x] 2.4 Move reverse-index generation out of `.context/`; delete `.context/reverse-index.md` from RESERVED
- [x] 2.5 Point validate index-sync, retrieval, and the Action/hook at the new reverse-index path
- [x] 2.6 Add a failing test that a bundle containing `.context/reverse-index.md` is non-conformant until migrated

## 3. Load vs pin policy

- [x] 3.1 Load every typed concept, including those without `verification`
- [x] 3.2 Keep the write gate mandatory for concepts that declare anchors
- [x] 3.3 Do not put unanchored concepts in the reverse index
- [x] 3.4 Add a test: Playbook with only `type` loads and is retrievable via a markdown link from a pinning concept
- [x] 3.5 Add a test: unanchored page does not arm skipped-memory for an uncovered file

## 4. Verified vs attest

- [x] 4.1 Stop assigning `verified` in `write_concept` on gate accept
- [x] 4.2 Stop setting `verified` to `process:repocodex-reanchor` in `apply_anchor_patch`
- [x] 4.3 Add a test: accepted write of a concept that omitted `verified` still omits it on disk
- [x] 4.4 Add a test: validate does not mutate concept files
- [x] 4.5 Keep REANCHOR path/terms updates; provenance of the *pin* stays in the verdict/patch, not in `verified`

## 5. Sources and actors

- [x] 5.1 Emit OKF actor strings from the engine (`process:repocodex-rg`); never `agent:`
- [x] 5.2 Map legacy `agent:` prefixes to producer/version on read
- [x] 5.3 Write bootstrap `sources` as objects with `resource`
- [x] 5.4 Normalize or reject scalar `sources` lists at write so the stored form is always objects
- [x] 5.5 Update fixtures and architecture examples (actors, sources, `okf_version`, no reverse-index in the tree diagram)

## 6. Product lock and closure

- [x] 6.1 Add a test: InvariantContract with anchors and a claim still writes as one file and still reports CLAIM_BROKEN when the literal changes
- [x] 6.2 Confirm no task in this change requires `type: Attested Computation` for pinning
- [x] 6.3 Confirm `openspec validate --all --strict` and the engine-package suite
- [x] 6.4 Note in architecture §5 that `.context/` is OKF v0.2, anchors are extensions, and `verified` is not a gate receipt

## 7. Review follow-up (leftover path, skill, test tightness)

- [x] 7.1 Delete leftover `.context/**/reverse-index.md` when regenerating the reverse index
- [x] 7.2 Report a remaining leftover as existing `index_sync` (no new blocking reason); do not label `reverse-index.md` an OKF reserved name
- [x] 7.3 Under `--staged` / `--hook`, compare the git-index copy of `.repocodex/reverse-index.md` (missing if unstaged)
- [x] 7.4 Update coding skill and plugin copy: commit includes `.repocodex/reverse-index.md` and shard files, not only `.context/`
- [x] 7.5 Add a test: nested catalog link uses a unique frontmatter `description` that is not already in the catalog or the body
- [x] 7.6 Add a test: writing on a later UTC date places that `## YYYY-MM-DD` heading above an existing older date heading
- [x] 7.7 Stop using `verified.by: process:repocodex-rg` on sample concepts; omit `verified` or name a definition reviewer
- [x] 7.8 Confirm `openspec validate --all --strict` and the engine-package suite
