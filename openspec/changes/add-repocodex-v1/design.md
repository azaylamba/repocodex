# Design: add-repocodex-v1

Authoritative source: [docs/research/architecture.md](../../../docs/research/architecture.md) (Revision 2). This file records the decisions that shape implementation; the architecture document holds the full reasoning and the self-validation table (§17).

## Key decisions

### 1. Determinism split is the load-bearing invariant

Liveness (is this memory still about live code?) is never delegated to a model — an LLM asked "is this still valid?" will say yes so the task can proceed. Everything the required CI check evaluates must be reproducible: ripgrep anchor attest, the file-level skipped-memory ratchet, reverse-index sync. All agent-judged findings (code-side impact, weakenings, truth checks) post to a separate advisory check.

### 2. Textual anchors instead of AST witnesses

Revision 1's ast-grep/Tree-sitter/SCIP layer was removed after self-validation: agents could not reliably author relational AST rules (the spec's own examples failed to match), the toolchain imposed a language allowlist, and its impact precision was name-based heuristics in practice. Anchors are distinctive term sets checked by `rg` — deterministic, language-agnostic (anything grep-able, including config/SQL/IaC), and easy for agents to author honestly. `verification.engine` stays extensible as a schema property, but no AST engine is part of this design.

### 3. Engine emits patches; callers apply them (single-writer rule)

REANCHOR produces an anchor patch in the JSON verdict. The agent, hook, or CI job applies and stages it. The engine never mutates the working tree, avoiding races with staged hunks, other hooks, and worktrees.

### 4. Uniqueness is scoped in-file

Attest-time uniqueness is evaluated within claimed pinned files only. Repo-wide search runs solely as a relocation locator after a full miss. Term dilution caused by unrelated code warns the PR that introduced the duplicate — never the concept owner. This removes the innocent-bystander failure mode by definition.

### 5. Rollout postures, not product versions

`shadow` (report only, collect metrics) → `ratchet` (enforce DRIFT + covered-file skipped-memory) → `full` (extend to agent-authored commits repo-wide, schedule audits). Posture is a `.repocodex.toml` flag on the complete product. Promotion between postures is gated by measured metrics: false-drift rate, anchor-rejection reasons, reconcile retries, tokens per turn, validate latency.

### 6. Humans get a governed edge, not a hot path

`memory-exempt` PR label bypasses the required check with review-agent acknowledgment, a `log.md` audit entry, and a self-healing follow-up repair task. `repocodex repair` gives humans a one-command agent-invoking repair flow.

### 7. Stack

Python + Typer CLI orchestrating `rg` and `git` subprocesses; Pydantic models over OKF v0.2 + extensions; no compiled extensions beyond ripgrep itself. Engine version pinned in `.repocodex.toml`; `engine_version` in every JSON output; CI runs the pinned version so IDE and CI agree by construction.

## Alternatives considered

- **Full AST/SCIP code graph (Revision 1):** rejected — witness-authoring ergonomics, operational surface, language allowlist. See architecture §4.4 and the Revision 1 → 2 history in §21.
- **Pure agentic linking (no stored anchors):** rejected — self-serving validation; degenerates into `AGENTS.md` + grep with no liveness guarantee.
- **Comment markers as the primary link:** rejected as load-bearing (comments get deleted and drift); kept as optional additive anchor terms.

## Open questions (measured, not guessed)

- Acceptable false-drift threshold before `ratchet` promotion — decided per repo from shadow metrics.
- Default distinctiveness ceiling and `scope_lines` — start at repo-size-relative defaults, tune from shadow data.
