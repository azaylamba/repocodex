# RepoCodex

This repository uses **RepoCodex executable memory**. Follow the coding-agent skill at `.claude/skills/repocodex-coding/SKILL.md` for every coding task. The skill loop is mandatory — do not skip any step:

1. Run `repocodex context <paths>` before editing any source file.
2. Edit code.
3. Run `repocodex validate --diff` before finishing the turn.
4. If `result` is `WRITE` or `skipped_memory` is non-empty, run `repocodex write` to pin the concept, then re-validate.
5. Do not finish the turn while `blocking` is true.
