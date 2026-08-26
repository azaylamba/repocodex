# Tasks: align-okf-v02-conventions

Product lock: one why file, anchors as extra keys, agent-read loop, pin check stays runtime. Do not add Attested Computation as the memory unit.

## 1. Schema and parse

- [ ] 1.1 Make `type` a string (preserve known RepoCodex values); do not reject unknown types
- [ ] 1.2 Default omitted `status` to `stable`
- [ ] 1.3 Model `sources` as a list of objects with required `resource` and optional `id` / `title` / credibility fields
- [ ] 1.4 Accept `verified` as a mapping or a list; do not require it
- [ ] 1.5 Read `okf_version` from root `index.md`; stop writing `format_version`
- [ ] 1.6 Round-trip unknown frontmatter keys including unknown `type`

## 2. Bundle layout

- [ ] 2.1 Create bundles whose root index frontmatter is only `okf_version: "0.2"`
- [ ] 2.2 Generate nested `index.md` without frontmatter, with title (and description when present) on each link
- [ ] 2.3 Write `log.md` under `## YYYY-MM-DD` headings, newest first
- [ ] 2.4 Move reverse-index generation out of `.context/`; delete `.context/reverse-index.md` from RESERVED
- [ ] 2.5 Point validate index-sync, retrieval, and the Action/hook at the new reverse-index path
- [ ] 2.6 Add a failing test that a bundle containing `.context/reverse-index.md` is non-conformant until migrated

## 3. Load vs pin policy

- [ ] 3.1 Load every typed concept, including those without `verification`
- [ ] 3.2 Keep the write gate mandatory for concepts that declare anchors
- [ ] 3.3 Do not put unanchored concepts in the reverse index
- [ ] 3.4 Add a test: Playbook with only `type` loads and is retrievable via a markdown link from a pinning concept
- [ ] 3.5 Add a test: unanchored page does not arm skipped-memory for an uncovered file

## 4. Verified vs attest

- [ ] 4.1 Stop assigning `verified` in `write_concept` on gate accept
- [ ] 4.2 Stop setting `verified` to `process:repocodex-reanchor` in `apply_anchor_patch`
- [ ] 4.3 Add a test: accepted write of a concept that omitted `verified` still omits it on disk
- [ ] 4.4 Add a test: validate does not mutate concept files
- [ ] 4.5 Keep REANCHOR path/terms updates; provenance of the *pin* stays in the verdict/patch, not in `verified`

## 5. Sources and actors

- [ ] 5.1 Emit OKF actor strings from the engine (`process:repocodex-rg`); never `agent:`
- [ ] 5.2 Map legacy `agent:` prefixes to producer/version on read
- [ ] 5.3 Write bootstrap `sources` as objects with `resource`
- [ ] 5.4 Normalize or reject scalar `sources` lists at write so the stored form is always objects
- [ ] 5.5 Update fixtures and architecture examples (actors, sources, `okf_version`, no reverse-index in the tree diagram)

## 6. Product lock and closure

- [ ] 6.1 Add a test: InvariantContract with anchors and a claim still writes as one file and still reports CLAIM_BROKEN when the literal changes
- [ ] 6.2 Confirm no task in this change requires `type: Attested Computation` for pinning
- [ ] 6.3 Confirm `openspec validate --all --strict` and the engine-package suite
- [ ] 6.4 Note in architecture §5 that `.context/` is OKF v0.2, anchors are extensions, and `verified` is not a gate receipt
