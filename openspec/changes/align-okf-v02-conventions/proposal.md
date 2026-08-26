# Proposal: align-okf-v02-conventions

## Why

`.context/` is meant to be an [OKF v0.2](https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/main/SPEC.md) knowledge bundle: why of a change or implementation, written by agents, read by agents, linked across files. The product loop does not change — retrieve the why, read the pinned code, write or update why in the same change; the required check only attests that why is still attached to live text.

The current store is a private dialect in an OKF-shaped directory. A v0.2 consumer cannot load it (`reverse-index.md` has no `type`; `format_version` is not `okf_version`; `sources` are bare strings; actors use `agent:`). Our parser cannot load a normal OKF document (unknown `type` rejected; concepts without `verification` skipped). `verified` is stamped on every gate pass, which OKF reserves for definition review, not for a per-run attest.

Align the bundle with the spec so the why remains portable knowledge. Do not replace the product with Attested Computation as the unit of memory, and do not introduce a test suite as scenario verification.

## What Changes

- **The bundle becomes OKF-conformant.** Every non-reserved `.md` file has frontmatter and `type`. Reserved names stay `index.md` and `log.md` only. Root `index.md` declares `okf_version: "0.2"`. Nested indexes have no frontmatter. `log.md` uses date headings. **BREAKING** for existing bundles: `format_version` is replaced; generated reverse indexes move out of the bundle.
- **Runtime artifacts leave the bundle.** The reverse index is written outside `.context/` (same family as metrics). CI still verifies it is in sync. It is not an OKF concept and not a reserved OKF filename.
- **Standard fields use OKF shapes.** `sources` are objects with `resource` (and optional `id` for footnotes). Actors are `<producer>/<version>`, `human:<id>`, or `process:<id>`. Absent `status` means `stable`. Unknown frontmatter keys still round-trip.
- **`verified` is not a gate receipt.** A successful ripgrep attest does not overwrite `verified`. Attestation remains a runtime verdict (LIVE / CLAIM_BROKEN / …), not stored in the concept. `verified` is written only when a reviewer or process confirms the *definition* (the why) against its sources.
- **Parser is an OKF consumer.** Unknown `type` values are tolerated as generic concepts. Concepts without `verification.anchors` remain in the bundle and in retrieval. The write gate and the required pin check still apply only to concepts that pin code — that is RepoCodex policy, not an OKF requirement.
- **Anchors stay a producer extension.** `verification.anchors` and `claims` remain extra keys on the same why document. We do **not** split every invariant into a narrative concept plus `type: Attested Computation`. Splitting would add a file the agent must maintain per why and would fight “one concept per why.” Optional `resource` on a pinning concept MAY name the primary pinned path as a URI; it does not replace anchors.

Explicitly **not** in this change: the agent-read scenario loop, CLAIM_BROKEN, owned claims, the scoped ratchet, the closed blocking set, or making pytest the scenario check. Those stay as specified in `fix-repocodex-v2-review-gaps`.

## Capabilities

### New Capabilities

- `okf-conformance`: the `.context/` tree is a conformant OKF v0.2 bundle — reserved files, version key, parse rules, and what must not live in the tree.

### Modified Capabilities

- `memory-store`: sources objects, actor strings, status default, reverse-index location, catalog/log conventions, unknown types preserved.
- `anchor-verification`: distinguish stored `verified` (definition) from runtime attest (pin check); do not stamp `verified` on gate pass.
- `context-retrieval`: serve any concept in the bundle, including those without anchors; skip only reserved files.

## Impact

- **Affected code:** `schema.py`, `store/bundle.py`, `store/reverse_index.py`, `commands/write.py`, `commands/bootstrap.py`, `commands/validate.py`, `retrieval.py`, fixtures, architecture §5.
- **Existing bundles:** one-time rewrite of root index key and reverse-index path; `sources: ["commit:…"]` becomes `{ resource: … }`; `agent:` actors become `producer/version`. Concepts keep their identities and anchors.
- **Product behavior:** agents still retrieve why and read code. The required check still blocks on detached pins, not on missing `verified`. Unanchored OKF pages can live in `.context/` for narrative; they do not arm the ratchet until they pin files.
- **Dependencies:** none. Still git + ripgrep + Python. No OKF runtime or attester ABI (OKF defers that).
