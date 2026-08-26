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
   - `LIVE` / `WEAK`: proceed. WEAK is logged; optionally tighten later.
   - `REANCHOR`: apply the emitted anchor patch (engine never mutates the tree). Stage it. `repocodex reconcile --apply-patch '<json>'`.
   - `RECONCILE` / `DRIFT`: you **must** repair in this change via `repocodex write` / `repocodex reconcile`. Do not finish the turn or commit.

5. **Commit** includes `.context/` **and** `.repocodex/reverse-index.md` (plus matching files under `.repocodex/reverse-index/` when shards exist) when you wrote or reanchored memory. Committing `.context/` alone does not include the reverse index. The pre-commit hook denies unrepaired DRIFT.

## Anchor authoring

Prefer **stable tokens**: string literals, error messages, enum values, numeric thresholds. Avoid renameable identifiers as the only distinctive term. Every `claims[].literal` must appear in `all_of` and in the matched source. Markers (`// why: …`) are at most one additive term, never the sole anchor.

Why-changes **supersede** (`supersedes` + `rationale`); do not clobber a stable concept.
