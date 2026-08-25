# Proposal: add-repocodex-v1

## Why

Autonomous coding agents write syntax well and forget institutional context. Repositories have instruction files (`AGENTS.md`, `.cursor/rules`) and code-search indexes, but no git-native, code-anchored memory that agents write as they work, that later agents can query for blast radius, and that cannot silently detach from the code it describes. The result is regressions: an agent optimizes a generator into a list comprehension and reintroduces a memory leak, or changes a grace-period constant without knowing it is a contractual business rule.

The architecture for solving this is settled in [docs/research/architecture.md](../../../docs/research/architecture.md) (Revision 2, 25 Aug 2026). This change implements it as V1. Nothing in the architecture is deferred; rollout postures (`shadow` / `ratchet` / `full`) are configuration of the complete product.

## What Changes

Build RepoCodex V1: a repository-native executable memory framework consisting of

- **Memory store** — an OKF v0.2 bundle in `.context/` (one markdown concept per file; prose why as the payload; machine-checkable frontmatter), with a generated, committed reverse index (`source path → concepts`).
- **Anchor verification** — every concept pins code locations with distinctive textual terms; a deterministic write gate (ripgrep counts) rejects loose anchors; a deterministic liveness engine classifies every touched anchor as LIVE / WEAK / REANCHOR / DRIFT using ripgrep and git pickaxe. No LLM anywhere in the gate or attester.
- **Context retrieval** — staged, token-cheap reads: reverse index → catalogs → bodies on demand; provenance-weighted, churn-down-ranked ordering.
- **Impact analysis** — deterministic intent-side impact (`impacted_scenarios`) in every validate output; bounded agentic code-side impact as a skill recipe; judgment findings are advisory only.
- **Enforcement** — pre-commit deny on DRIFT, a required CI check that contains only deterministic outcomes, rollout postures, and a governed human escape hatch (`memory-exempt` + `repocodex repair`).
- **Agent interfaces** — a canonical CLI (`validate`, `write`, `reconcile`, `context`, `repair`, `install`, `bootstrap`, `audit`), coding/review agent skills, and an optional MCP wrapper, distributed as an Agent Plugins 1.0 package with a git pre-commit portable floor.
- **Governance** — supersede chains, CONTRADICTION handling, anti-poisoning (write-time prose-vs-diff review, mandatory `sources` on bootstrap, provenance ranking, scheduled sampling audits), and GC of orphaned pages.

Explicitly **not** in this change (removed by design in Revision 2, not postponed): persisted code graph, Tree-sitter/SCIP/ast-grep in any required path, LLM-decided liveness, human approval queues, silent multi-candidate healing, nondeterministic findings in the required CI check.

## Impact

- **Affected specs:** all new — `memory-store`, `anchor-verification`, `context-retrieval`, `impact-analysis`, `enforcement`, `agent-interfaces`, `governance`.
- **Affected code:** new Python package (Typer CLI over ripgrep + git), Pydantic schema layer, git pre-commit hook, GitHub Action, agent skills, optional MCP server, Agent Plugins 1.0 packaging.
- **Runtime dependencies:** ripgrep, git, Python. No native parser toolchains, no API keys, no network access in the engine.
- **Risk posture:** the two measured unknowns (false-drift rate from renames, tokens per agent turn) are quantified in the `shadow` posture before any gate is enforced; see `design.md` and architecture §17.
