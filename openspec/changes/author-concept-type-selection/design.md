## Context

Agents in application repos only see what `repocodex install` copies. The coding skill today forces a write on `WRITE` / `skipped_memory` but does not teach type or volume. `InvariantContract` is accepted without `claims`, so the type that exists for `CLAIM_BROKEN` can be decorative. Types are independent catalog labels; one change can need all four.

## Goals / Non-Goals

**Goals:**

- Orthogonal type recipe in the install-copied coding skill (when, how, paths, claims, volume, multi-type example).
- Write-gate reject `InvariantContract` with no `claims` (`claims_required`).
- Review skill flags misuse without treating multiple types in one PR as wrong.
- Docs and architecture §5.3 match the honest token-contract definition.

**Non-Goals:**

- Renaming or dropping `InvariantContract`.
- Engine auto-classification of type.
- Bootstrap emitting invariants.
- Required CI failing on wrong type or missing sibling types.
- A third skill file.

## Decisions

1. **Keep the type name; redefine meaning.** Renaming breaks existing bundles for little gain. Honest docs + required `claims` fix the decorative case.
2. **Orthogonal checks, not first-match exclusive.** One change may write all four when they are distinct whys. Default coverage type remains `TechnicalDecision` only when nothing else applies.
3. **Extend existing skills, not a new skill.** Install already points Cursor/Claude at `repocodex-coding`; a third skill would be skipped.
4. **Gate only `claims_required` on InvariantContract.** Other types may omit claims; wrong-type judgment stays advisory.
5. **Three copies stay byte-aligned** for coding and review skills (packaged, plugin data, plugin tree) — same pattern as first-touch skill tests.

## Risks / Trade-offs

- [Agents ignore the skill] → Hook still blocks skipped-memory; review flags misuse; no CI type oracle (accepted).
- [Agents invent four types for one why] → Skill + review stress one-concept-per-why.
- [Existing InvariantContract drafts without claims] → Gate rejects new writes; stable concepts without claims remain loadable until next write (no migration sweep).
- [Skill length] → Keep recipe tight but self-contained; pointers stay one paragraph.

## Migration Plan

Ship in one change. No bundle migration. Re-run `repocodex install` in app repos to refresh skill copies. Rollback: revert gate check and skill text.

## Open Questions

None — defaults from the approved plan.
