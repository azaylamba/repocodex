## Why

Installed coding skills tell agents to write a gate-passing pinning concept but never when to use which type or how many files. Agents default to `TechnicalDecision`, skip `claims` on contractual tokens, and invent one page per `skipped_memory` path. `InvariantContract` over-promises general invariants while the engine only polices verbatim tokens — and accepts that type with no `claims`, leaving the type decorative.

## What Changes

- Redefine `InvariantContract` in architecture and memory-store as a rare **claims-bearing token contract** (name stays); types remain orthogonal — one change MAY write or update all four when they are distinct whys.
- Write gate **rejects** `InvariantContract` with missing or empty `claims` (`claims_required`).
- Coding skill (all install/plugin copies) becomes a self-contained when/how recipe: independent type checks, paths, `claims`, volume (one concept per why), multi-type same-change example.
- Review skill gains advisory flags for type/volume misuse; MUST NOT flag multiple types in one PR when whys differ.
- User docs (`agents.md`, `memory.md`) summarize; skill remains the agent source of truth.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `agent-interfaces`: coding skill SHALL include orthogonal type recipe, one-concept-per-why, multi-type same-change example; review skill SHALL flag type/volume misuse without treating multiple types as wrong.
- `anchor-verification`: write gate SHALL reject `InvariantContract` without `claims` (`claims_required`).
- `memory-store`: concept type definitions — `InvariantContract` requires `claims`; types coexist on one change.
- `user-docs`: `agents.md` / `memory.md` describe orthogonal types and point at the installed coding skill for the full recipe.

## Impact

- Engine: `src/repocodex/engine/gate.py` (+ tests).
- Skills: three copies each of `repocodex-coding` and `repocodex-review` under `src/repocodex/data/skills/`, `src/repocodex/data/plugin/skills/`, `plugin/skills/`.
- Docs: `docs/research/architecture.md` §5.3, `docs/agents.md`, `docs/memory.md`.
- Specs: deltas under this change; no API or CLI surface change beyond reject reason.
