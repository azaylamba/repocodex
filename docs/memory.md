# How to read `.context/`

RepoCodex memory is an [OKF v0.2](https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/main/SPEC.md) knowledge bundle at `.context/`. This page is a consumer guide: enough to open a concept usefully. Field catalogs live in the OKF spec; do not treat this file as a schema.

## What lives in the bundle

| Path | Role |
| --- | --- |
| `.context/index.md` | Root catalog. Frontmatter is `okf_version: "0.2"` only. |
| `.context/log.md` | Chronological writes, grouped under `## YYYY-MM-DD`. |
| Nested `index.md` | Directory catalogs (title — description links). Not concepts. |
| Every other `.md` | A concept. Identity is the path relative to `.context/` without `.md`. |

Reserved filenames at any level are only `index.md` and `log.md`. Everything else with a `type` is a concept.

The reverse index is **not** a concept and is **not** in the bundle. It is generated at `.repocodex/reverse-index.md` (shards: `.repocodex/reverse-index/<escaped-context-parent>.md`). Do not look for `reverse-index.md` under `.context/`.

## Opening a concept

1. **Read the body as why.** The markdown after the frontmatter is the payload: why this decision, invariant, workflow, or guardrail exists.
2. **Note `type`.** RepoCodex authors `TechnicalDecision`, `InvariantContract`, `BusinessWorkflow`, and `GuardrailDecision`. Unknown types are still concepts; they load. Unanchored pages (no `verification`) are valid knowledge; they are not reverse-indexed and do not arm the pin check.
3. **Follow anchors to code.** When the concept pins live text, `verification.anchors` lists paths and distinctive terms. Open those files. `claims` (when present) are checkable literals that must appear in the owning anchor's matched region.
4. **Follow markdown links for related why.** Links between concept files are the graph. Retrieval returns one hop of titles; open a linked body only if the edit might touch that scenario.

`verification.anchors` and `claims` are RepoCodex extensions on the same why document. The memory unit is not `type: Attested Computation`.

For OKF families (`title`, `description`, `tags`, `generated`, `status`, `sources`, and the rest), use the [OKF v0.2 spec](https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/main/SPEC.md).

## `verified` is not a gate stamp

OKF `verified` records definition review against `sources` (a reviewer confirming the *why*). It is optional.

- Missing `verified` does **not** fail CI.
- A passing pin check does **not** write `verified`.

Trust tiers inferred from actor prefixes (`human:…` vs producer/version) also do not affect the required pin check. Liveness is a runtime verdict (`LIVE`, `CLAIM_BROKEN`, `DRIFT`, …), not a field on the concept.

## Next

How agents retrieve and maintain this: [agents.md](agents.md). What the loop is for: [how-it-works.md](how-it-works.md).
