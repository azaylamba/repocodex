# Agent playbook

Written for coding agents first. Humans may run the same CLI; they are not required to author or verify each concept.

The anti-regression check is this loop plus the pin check. It is not the application test suite, not human approval, and not OKF trust tiers.

## Before you edit

For every file you are about to change:

```bash
repocodex context <paths>
```

Read the returned bodies. Related pages are titles only — open a body only if the edit might touch that scenario. How to read a concept: [memory.md](memory.md).

Keep institutional why intact unless you intend a why-change (`supersedes` + `rationale`). Do not clobber a stable concept.

## Before the turn ends

```bash
repocodex validate --diff
```

| Outcome | What you do |
| --- | --- |
| `LIVE` / `WEAK` | Proceed. WEAK is logged; optionally tighten later. |
| `REANCHOR` | Apply the emitted patch (`repocodex reconcile --apply-patch '<json>'`). The engine never mutates the tree. Stage the result. |
| `RECONCILE` / `DRIFT` | Repair in this change via `repocodex write` / `repocodex reconcile`. Do not finish the turn or commit. |
| `CLAIM_BROKEN` | The declared literal no longer holds in the pinned region. Update why or restore the code. |

Unrepaired pin breakage is a failed turn. The pre-commit hook denies it.

## What to stage

When you wrote or reanchored memory, the same commit must include:

- `.context/` (the concept files, catalogs, and `log.md`)
- `.repocodex/reverse-index.md`
- matching files under `.repocodex/reverse-index/` when shards exist

Committing `.context/` alone does not include the reverse index. The required check fails on index desync.

Prefer stable tokens for new anchors: string literals, error messages, enum values, numeric thresholds. Avoid renameable identifiers as the only distinctive term.

## Humans

A human developer may run the same commands. They are optional operators, not a required reviewer of each concept.

The governed exception is `memory-exempt`: a labelled, acknowledged override for hotfixes that cannot wait for a pin repair. It is not the default path. Use `repocodex repair` when a human needs a one-command repair flow.

What the loop is for: [how-it-works.md](how-it-works.md). Install and pin: [install.md](install.md).
