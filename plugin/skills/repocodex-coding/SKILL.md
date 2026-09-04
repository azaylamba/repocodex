---
name: repocodex-coding
description: Retrieve RepoCodex context before editing, run impact on the diff, validate before ending the turn, and repair DRIFT in the same change.
---

# RepoCodex coding-agent skill

You are working in a repository that uses RepoCodex executable memory.

## Loop (do not skip)

1. **Context before edit.** For every file you are about to change, run:

   `repocodex context <paths>`

   Read returned concept bodies. Related pages are titles only — open a body only if the edit might touch that scenario.

2. **Code-side impact recipe (bounded).** On the diff:
   - Grep changed symbol names (exclude vendored / generated / `.repocodexignore` paths).
   - Rank hits by path proximity to the edit, then test-file status (prefer `**/test*` after same-package callers).
   - Read plausible callers until the read cap (default 12 files). Stop at the cap; do not explode on common names.
   - Treat a skipped step as a defect you must note.

3. **Edit code.** Keep institutional why intact unless you intend a why-change.

4. **Validate before the turn ends.**

   `repocodex validate --diff`

   Outcomes:
   - `LIVE` / `WEAK`: proceed only if `skipped_memory` is empty. WEAK is logged; optionally tighten later.
   - `WRITE` or non-empty `skipped_memory`: **before** `repocodex write`, run **all four** type checks in [Choose type](#choose-type-types-are-independent) — write or update every type that applies (not only one `TechnicalDecision`). Then `repocodex write` gate-passing concept(s) that **together** pin each listed path, then re-validate. One concept with multiple anchors may cover several paths that share one why — do not invent one page per path. Do not treat `LIVE` as done while `skipped_memory` is populated. Do not finish the turn or commit while `blocking` is true.
   - `REANCHOR`: apply the emitted anchor patch (engine never mutates the tree). Stage it. `repocodex reconcile --apply-patch '<json>'`.
   - `RECONCILE` / `DRIFT`: you **must** repair in this change via `repocodex write` / `repocodex reconcile`. Do not finish the turn or commit.
   - `CLAIM_BROKEN`: restore the literal or supersede the concept with `rationale`.
   - Do not finish the turn while `blocking` is true.

5. **Commit** includes `.context/` **and** `.repocodex/reverse-index.md` (plus matching files under `.repocodex/reverse-index/` when shards exist) when you wrote or reanchored memory. Committing `.context/` alone does not include the reverse index. The pre-commit hook denies unrepaired DRIFT and undischarged skipped-memory.

## Choose type (types are independent)

After the code change, run **all four** checks. Write or update **every** type that applies. Do not stop at the first match. Do not invent a type that does not apply. One change MAY update all four when they are distinct whys. Prefer update-in-place or `supersedes` + `rationale` if a matching page already exists.

| When this is true | Type | How |
| --- | --- | --- |
| Why this **construct** exists (shape, API, generator vs list, …) | `TechnicalDecision` | Pin a distinctive construct from the why (`yield`, error string), not the function name alone. **Identity MUST be under `decisions/`** (or the package shard's `decisions/`). Default **coverage** type when first-touch needs a pin and nothing else applies. |
| A **verbatim token** must not change silently (threshold, enum, contract error string) — losing it should `CLAIM_BROKEN`, not WEAK | `InvariantContract` | **Requires `claims`** with frozen literals; each literal in owning anchor `all_of` and matched region. Not for structural shape. **Identity MUST be under `invariants/`**. |
| **Cross-package flow** (order, boundaries) | `BusinessWorkflow` | Thin page: ordering, boundaries, links to step pages. One anchor per participating site. **Identity MUST be under `workflows/`**. |
| Global **do-not** / layering rule with an enforcement tool | `GuardrailDecision` | Pin the **enforcement config** (linter, import-linter, CI), not a complying app file. **Identity MUST be under `decisions/` or `guardrails/`**. |

`repocodex write --identity` for those four types is rejected with `identity_prefix_mismatch` when the identity lacks the type folder (e.g. use `--identity decisions/custom-data-streamer`, not `custom-data-streamer`). Existing flat files may still be updated (suggestion only); clear debt with `repocodex relocate <identity>` or `repocodex relocate --mismatched`. Validate lists remaining debt in non-blocking `identity_prefix_warnings`.

Do not relabel an `InvariantContract` as `TechnicalDecision` to dodge `claims`. Unanchored narrative pages do not discharge `skipped_memory`.

## How many files

- **One concept per why** — not per file, not per `skipped_memory` path.
- Several paths sharing one why → one page, multiple anchors.
- Several distinct whys (including all four types) → several pages in the same commit.
- If retrieved context already covers a why, do not duplicate.

## Example (one change, four types)

A checkout feature may write in the same change: `decisions/…` (why capture streams), `invariants/…` (grace `"3"` + `ENTERPRISE` with `claims`), `workflows/…` (api → billing → ledger), `decisions/…` or `guardrails/…` (domain must not import infra, pin `.importlinter`). Four files because four whys — not because every change must fill every type.

## Anchor authoring

Prefer **stable tokens**: string literals, error messages, enum values, numeric thresholds. Avoid renameable identifiers as the only distinctive term. Every `claims[].literal` must appear in `all_of` and in the matched source. Markers (`// why: …`) are at most one additive term, never the sole anchor.

Why-changes **supersede** (`supersedes` + `rationale`); do not clobber a stable concept.
