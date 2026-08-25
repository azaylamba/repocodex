# Architecture delta: original PDF vs Revision 1 (DEPRECATED)

**Status:** Deprecated / historical — do not implement against this document.
**Superseded by:** [architecture.md](architecture.md) (Revision 2, 25 Aug 2026) — the canonical architecture.
**Scope of this file:** Diff of the original PDF draft vs **Revision 1 only** (24 Aug 2026). It does **not** describe Revision 2.

**Original PDF:** [Architecture (System Design) Repo Codex.pdf](Architecture%20(System%20Design)%20Repo%20Codex.pdf)
**Revision 1 (superseded):** retrievable from git history of `architecture.md` at 24 Aug 2026.

Kept for provenance only: what the PDF got wrong, what Revision 1 corrected, and what Revision 1 still claimed (AST/SCIP code graph, ast-grep witnesses, Layer 1/2 bipartite store). Revision 2 removed the AST/SCIP linking layer and replaced it with ripgrep-attested textual anchors plus agentic retrieval/impact. See [architecture.md](architecture.md) §4.4 and §21 for that change.

Audience assumption that drove Revision 1 (still true in Revision 2): **autonomous coding agents write and maintain memory. Developers do not author or approve each contract.**

---

## Summary (PDF → Revision 1)

Columns below mean **PDF draft** vs **Revision 1**. They are not the current design.

| Area | Original (PDF) | Revision 1 (deprecated) |
| --- | --- | --- |
| Who writes memory | Developers and agents | Agents only (engine may heal cosmetics) |
| Who approves mutations | Human PR reviewer / `[Y]` prompt | Nobody human. Attester + coding agent + review agent + required CI |
| Witness / ast-grep | Required on invariants; optional on Technical Decisions | Mandatory on every concept (the proof) |
| Code graph / SCIP | Named in Layer 1, not operationalized | First-class V1, Tree-sitter always, SCIP best-effort with `precision` |
| Impact analysis | 1st/2nd-degree OKF neighbors of files | `get_impact`: impacted code **and** impacted business scenarios |
| Validate | PASS / FAIL | PASS / COSMETIC_HEAL / REANCHOR / RECONCILE (agent must repair) |
| OKF schema | Custom `id`, `lifecycle.state`, `PROPOSED_BY_AGENT` | OKF v0.2 (`status`, `generated`, `verified`) plus extensions |
| LangGraph | CLI orchestrator in the hot path | After a deterministic verdict only (draft why, review commentary) |
| Agent Plugins 1.0 | Assumed to include PreToolUse hooks | Skills + MCP only; hooks are per-client adapters |
| Unskippable memory | Skill + optional hook | Engine re-attest + Stop/commit hook + **required CI** |

---

## What was incorrect in the original document

> Throughout this file, “current,” “replace with,” and “added” refer to **Revision 1**, not Revision 2.

These are not taste changes. They are claims that conflict with how the named technologies work, or with the agent-only audience.

### 1. Humans are in the memory loop

**Original:** Developers author `.context/` alongside agents. `PROPOSED_BY_AGENT` defers approval to a human PR reviewer. Workflow B prompts a human `[Y]` after breaking an invariant.

**Why incorrect:** The product exists so developers (and later agents) do not have to remember or ratify why a block was written. Code is often produced by other agents or other developers. Per-contract human review will not happen and cannot be load-bearing.

**Replace with:** Agents write memory. Humans are out of the hot path.

### 2. Technical Decisions had no proof

**Original:** Invariants carry an ast-grep rule. Technical Decisions are markdown plus `entry_points` only — “vital reading material,” not executable.

**Why incorrect:** Path-only anchors rot on the first rename/split, and an agent can write a story about the wrong code. Without a witness, Layer 2 is not actually linked to Layer 1.

**Replace with:** Every concept, including Technical Decisions, must present a witness that matches live AST before write. The witness proves *anchoring*, not that the narrative is true.

### 3. OKF schema is a parallel dialect, not OKF

**Original:** `id: INV-802`, `lifecycle.state: ACTIVE | ORPHANED | PROPOSED_BY_AGENT`, `provenance.author: "@human-dev"`.

**Why incorrect:** OKF v0.2 identity is the **file path**. Lifecycle is `status: draft | stable | deprecated` plus `stale_after`. Provenance is `generated` / `verified` / `sources` with actor strings (`human:…`, `agent:…`, `process:…`). Custom keys are allowed; replacing the reserved vocabulary is not conformance.

**Replace with:** OKF v0.2 frontmatter. Extensions: `entry_points`, `verification`, `evidence`, `supersedes`. Machine-confirmed trust is `verified.by: process:repocodex-ast-grep`, not a human click.

### 4. Diff-driven parsing of “modified lines”

**Original:** “Never parse the full repository… running Tree-sitter only on the uncommitted diff.” Performance scales with PR size.

**Why incorrect:** Tree-sitter incrementally reparses **files**, not hunks. Cross-file edges and SCIP symbols cannot be made correct from changed lines alone. Production Tree-sitter+SCIP pipelines skip SCIP on incremental sync and do a periodic full index.

**Replace with:** Re-parse whole changed files with Tree-sitter on every edit. Refresh SCIP on commit/CI/schedule. Expose `index_sha` and `scip_fresh` to agents. Targeted validation of *contracts whose nodes sit in the diff* remains valid.

### 5. 2–5 ms / 100 ms as if measured

**Original:** SQLite neighbor lookup ~2–5 ms. Local validation ~100 ms. Python CLI + `ast-grep-cli` subprocess.

**Why incorrect:** Those numbers are claims. Python process start plus an ast-grep subprocess routinely blows a 100 ms budget (Claude Code guidance: Python hooks often ~200 ms vs ~15 ms Node).

**Replace with:** Long-lived MCP server, in-process `ast-grep-py`. Measure before advertising SLOs.

### 6. Agent Plugins 1.0 includes PreToolUse

**Original:** Distributed as an Agent Plugin 1.0 manifest; Workflow B intercepts via PreToolUse.

**Why incorrect:** Agent Plugins 1.0 (Aug 2026) standardizes **skills + `mcp.json` only**. Hooks, commands, and git interception are not portable. Claude Code still uses its own hook format. `Bash(git commit*)` matchers have known bugs; filter inside the hook script.

**Replace with:** Portable package = plugin + MCP + skill. Git pre-commit as the portable floor. Claude/Cursor hooks as adapters.

### 7. LangGraph as the CLI/hot-path orchestrator

**Original:** “CLI & Orchestrator: Python (typer, LangGraph) for Git hook injection, state management, and terminal UX.”

**Why incorrect:** Validate is a mechanical AST match. An LLM graph is slow, non-deterministic, needs an API key, and can talk a broken witness into PASS (self-serving mutation inside the checker).

**Replace with:** Deterministic engine decides PASS / heal / RECONCILE. LangGraph (or any LLM workflow) drafts why, proposes repairs, and writes review commentary *after* that verdict. Typer remains the CLI wrapper.

### 8. Silent 1:N AST self-heal

**Original:** On file split, run the rule on new files; if it matches, silently update YAML.

**Why incorrect:** A pattern can match coincidentally in an unrelated new file. Silent YAML mutation dirty-commits memory the agent did not intend. Ambiguous multi-match must not guess.

**Replace with:** Unique match may re-anchor. Multiple matches → RECONCILE JSON to the coding agent. Never a human TTY prompt.

### 9. Ambiguous deletion prompts a human

**Original:** “Humans receive a terminal prompt; Agents receive a system directive.”

**Why incorrect:** Humans are not operators of this loop. A TTY `[Y]` will be skipped or `--no-verify`’d.

**Replace with:** Engine heals cosmetics. Agent receives RECONCILE and cannot end the turn / merge until repaired. CI is the backstop.

### 10. `git diff -M` is “semantic re-anchoring”

**Original:** Section 5 titles file-path rename detection as semantic re-anchoring.

**Why incorrect:** `git diff -M` is file-level similarity. Function moves, identifier renames, and equivalent refactors are not file renames. Variable rename would break a raw source hash even when the business scenario did not change.

**Replace with:** Three classes — LIVE (unique witness match, including variable rename; no git write), REANCHOR (unique match in a new location; update `entry_points` only), DRIFT (zero or ambiguous matches; agent repairs). Hashes are cache-only and never block.

### 11. Bi-partite graph is named but not specified as a store

**Original:** Layer 1 is Tree-sitter + SCIP. SQLite “indexes virtual edges.” `get_context` returns 1st/2nd-degree OKF neighbors of **files**.

**Why incorrect as specified:** If SQLite only stores path → contract, there is no code graph. You cannot find callers, implementations, tests, or other code pinned by the same business scenario. SCIP is listed but never given an incremental/failure story.

**Replace with:** Persist a real Layer 1 (Tree-sitter always; SCIP when it runs). Virtual edges exist only after a passing witness. `get_impact` walks code neighbors **and** intent neighbors. Label `precision: scip | heuristic`. SCIP failure is not downtime.

### 12. CI only blocks “code vs invariant without `.context/` mutation”

**Original:** Hard-block if code violates an invariant and `.context/` was not mutated. Mutations marked `PROPOSED_BY_AGENT` wait for humans.

**Why incorrect for agent-only:** Intent change *should* mutate memory in the same change. Blocking “any mutation without human verify” fights the product. Allowing mutation without attestation lets agents rubber-stamp FAIL → rewrite rule → PASS. Also, `--no-verify` bypasses hooks; CI must be required, not optional.

**Replace with:** Fail **unreconciled drift** (witness lost and not healed/repaired). Do not fail because memory was updated. Require attestation of the new witness and a `supersedes` + rationale on why-changes.

### 13. MCP-only will keep agents honest

**Original:** Agent calls `get_context` / `validate_diff` / `propose_mutation` as a loop.

**Why incorrect:** Agents skip tools. `git commit --no-verify` exists. MCP cannot force a call.

**Replace with:** Engine re-attests the diff (cosmetics cannot be skipped) + Stop/commit deny on DRIFT + branch-protected GitHub Check. Install is `repocodex install` of all three.

---

## What is added (not in the original)

- **Agent-only authoring as the product constraint.** Write-on-edit memory; no human ratification.
- **Mandatory witness on all concepts**, including Technical Decisions. `write_memory` rejects non-matching rules.
- **Evidence model:** unique ast-grep match is liveness. Structural hashes optional in `.cache.sqlite` only; they never fail CI or rewrite why. Grep/glob fill `candidates[]` after a miss.
- **`write_memory` tightness:** reject file-level / name-only / whole-function-`$$$` / high-fanout pins; InvariantContract claims (`3`, `ENTERPRISE`) must be pattern literals; TechnicalDecision must pin a distinctive construct. Impact is `get_impact` from the owning symbol, not witness miss.
- **Change classes:** COSMETIC / REANCHOR / DRIFT. Cosmetic must not page the agent or rewrite the why.
- **OKF v0.2 alignment:** `index.md` page catalog, `log.md`, `status`, `generated`, `verified`, `stale_after`, `sources`. Trust inferred, not a portable score.
- **`supersedes` chain.** Mutations deprecate the old concept instead of clobbering it. Next agent sees that the why changed.
- **Churn / tautology controls.** Down-rank high-rewrite concepts. Reject witnesses that only match a file-level node or match too many nodes.
- **Contradiction handling.** Overlapping entry points with conflicting claims → CONTRADICTION flag; current agent must supersede one. Engine does not pick a winner.
- **`get_impact` (V1).** Blast radius: all impacted code (callers, impls, tests) and all impacted business/technical scenarios.
- **`read_concept`.** Progressive disclosure: neighborhood returns titles first; bodies on demand. Do not dump `.context/`.
- **Code-review agents in V1.** Same MCP. Review skill uses `get_impact` + `validate_diff`. Second machine, not a human stand-in.
- **RECONCILE as a first-class outcome.** JSON to the coding agent (lost nodes, candidates, impacted scenarios). Three-tier resolver: engine → coding agent same turn → CI/repair agent.
- **Precision labels** on graph edges (`scip` vs `heuristic`). `index_sha`, `scip_fresh` in MCP.
- **SCIP operational policy.** Not on every keystroke. Full/refresh on commit/CI. Tree-sitter fallback; never pretend SCIP ran.
- **Unskippable loop:** engine heal on diff, Stop/PreToolUse/pre-commit deny, required Checks API, review agent skip-detection.
- **`repocodex install`** as one package: MCP + skill + hook + CI workflow.
- **Bootstrap job.** Mine git history / comments / existing docs; keep only attested hits; short `stale_after`.
- **Worktree / cache rules.** `.cache.sqlite` gitignored, keyed by HEAD + dirty tree. CI rebuilds from source.
- **Language allowlist.** Unsupported files error instead of fake anchors.
- **Split of LLM vs engine.** Engine attests; model narrates and repairs.

New MCP surface vs original three tools:

| Tool | Role |
| --- | --- |
| `get_context` | 1st/2nd-degree intent for files about to be edited (kept, now graph-backed) |
| `get_impact` | **New.** Impacted code + impacted scenarios for a diff/PR |
| `read_concept` | **New.** Fetch one OKF page by path |
| `write_memory` | **Replaces** `propose_mutation` as the primary write |
| `validate_diff` | Kept, outcomes expanded (heal vs reconcile) |
| `reconcile_memory` | **New.** Repair path for DRIFT |

---

## What is removed or demoted

| Original item | Fate | Reason |
| --- | --- | --- |
| Human authoring of `.context/` | Removed from design | Audience is agents |
| Workflow B (human IDE `[Y]` gate, LLM proposer to the user) | Removed | Humans are not in the loop |
| `lifecycle.state: PROPOSED_BY_AGENT` as a review queue | Removed | OKF `status` + `generated` + attester `verified` |
| `lifecycle.state: ORPHANED` | Demoted | Use `deprecated` after unmatched reconcile timeout; history stays in git / `log.md` |
| Custom `id: INV-802` as identity | Removed as identity | OKF path is identity; display id may remain as an optional field |
| Narrative-only Technical Decisions (no witness) | Removed | Mandatory proof |
| LangGraph in git-hook / validate hot path | Removed from hot path | Kept only after deterministic verdict |
| `ast-grep-cli` subprocess as the V1 engine | Demoted | Prefer in-process `ast-grep-py` |
| Silent 1:N heal on any match | Removed | Unique match only; else RECONCILE |
| Human terminal prompt on broken edges | Removed | Agent RECONCILE + CI |
| Agent Plugins 1.0 as a portable hook bus | Removed as a claim | Skills + MCP only |
| “Parse only git diff lines” | Removed | Parse changed files; SCIP on a slower cadence |
| Treating `get_context` file-path joins as a bi-partite graph | Removed as sufficient | Real Layer 1 store required in V1 |
| Human PR reviewer as the mutation backstop | Removed | Review **agent** + required CI |
| Blocking CI because memory mutated | Removed | Block unreconciled drift only |
| 5,000-rule framing as if humans will author a rule farm | Demoted | Agents write locally; GC, `stale_after`, scoped retrieval contain volume |

Kept from the original (still correct):

- Bi-partite idea: syntax isolated from intent, linked by virtual edges
- Git-native `.context/` that branches and merges with code
- ast-grep + Tree-sitter as deterministic attesters (not as the whole product)
- SQLite as an ephemeral cache, not the source of truth
- Targeted validation (only contracts on the touched subgraph)
- 1:1 file rename via `git diff -M` as *one* heal, not the whole heal story
- MCP as the agent interface
- CI as a hard gate so drift does not reach main
- Pydantic + Typer + Python orchestration over compiled analysis tools
- Scoped context so agents do not ingest the whole memory corpus

---

## Original workflows → Revision 1 workflows

**Workflow A (agent loop)** — kept, rewired.

1. `get_context` / `get_impact` before edit
2. Edit code
3. Engine re-attests the diff (cosmetics healed without asking)
4. If DRIFT: `reconcile_memory` / `write_memory` with a new passing witness and `supersedes` if the why changed
5. Stop/commit denied until `validate_diff` is PASS
6. Required CI repeats the attester; review agent runs `get_impact`

There is no `PROPOSED_BY_AGENT` deferral to a human.

**Workflow B (human `[Y]`)** — removed.

**Workflow C (CI)** — kept, semantics changed: fail unreconciled drift and skipped memory, not “mutation without human approval.”

---

## Open risks the original did not name (as of Revision 1)

These were open when Revision 1 was written. Several were later addressed by Revision 2 (see [architecture.md](architecture.md) §17); others remain in different form.

- A matching witness is not proof the story is true (tautological `def foo` pins). → Revision 2: textual distinctiveness gate + structured `claims` + anti-poisoning audits.
- Agents can still weaken a why on DRIFT; `supersedes` + churn + review agent only contain it. → Still true in substance; Revision 2 keeps the same containment set.
- SCIP compile environments will fail in real monorepos; heuristic impact will be wrong sometimes and must be labeled. → Revision 2: SCIP removed; impact is agentic and advisory.
- Mandatory witnesses exclude config/SQL/unsupported languages unless V1 explicitly errors. → Revision 2: anything grep-able is in scope; no language allowlist.
- “Never skip” is false without a required CI check. → Still true; Revision 2 adds rollout postures and a human escape hatch so the required check stays livable.

---

## Supersession note

This delta and the “fold into the PDF” rewrite path below are **obsolete**.

**Do not implement Revision 1.** Implement [architecture.md](architecture.md) Revision 2.

Revision 2 kept from Revision 1: OKF v0.2 store, agent-only authoring, deterministic attester (no LLM in the gate), unskippable loop (engine + hook + required CI), review agent, containment (`supersedes`, churn, CONTRADICTION).

Revision 2 dropped from Revision 1: persisted code graph, Tree-sitter/SCIP, ast-grep witnesses, Layer 1/2 numbering, language allowlist, SQLite as a required edge store.
