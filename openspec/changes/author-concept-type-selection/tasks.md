## 1. Write gate

- [x] 1.1 Add failing test: `InvariantContract` without `claims` is rejected with `claims_required`; `TechnicalDecision` without claims is not rejected for that reason
- [x] 1.2 In `evaluate_write`, reject `InvariantContract` with missing/empty `claims` (`claims_required`)
- [x] 1.3 Confirm fixture with claims still accepts; run targeted pytest

## 2. Coding skill

- [x] 2.1 Add failing skill-string tests for orthogonal type recipe across all three coding skill copies
- [x] 2.2 Update all three `repocodex-coding/SKILL.md` copies with independent type checks, when/how, volume, multi-type example, and clarified WRITE bullet
- [x] 2.3 Re-run skill string tests

## 3. Review skill

- [x] 3.1 Add failing skill-string tests for review type/volume flags (and multi-type-not-wrong) across all three review copies
- [x] 3.2 Update all three `repocodex-review/SKILL.md` copies
- [x] 3.3 Re-run review skill string tests

## 4. Docs and main specs

- [x] 4.1 Update architecture §5.3 (honest InvariantContract; types coexist)
- [x] 4.2 Update `docs/agents.md` and `docs/memory.md`
- [x] 4.3 Sync delta requirements into `openspec/specs/` for agent-interfaces, anchor-verification, memory-store, user-docs
- [x] 4.4 Run full pytest and `openspec validate --all --strict` if available
