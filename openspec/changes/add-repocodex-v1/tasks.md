# Tasks: add-repocodex-v1

## 1. Foundation

- [x] 1.1 Scaffold Python package (Typer CLI entry point, `pyproject.toml`, test harness)
- [x] 1.2 Pydantic schema for OKF v0.2 frontmatter + extensions (`verification`, `claims`, `supersedes`, `rationale`, `format_version`)
- [x] 1.3 `.repocodex.toml` config loader (engine version pin, posture, distinctiveness ceilings, `scope_lines` default, exclusion globs) and `.repocodexignore` support
- [x] 1.4 ripgrep + git subprocess wrappers with structured results and version reporting

## 2. Memory store

- [x] 2.1 `.context/` bundle reader/writer: one concept per file, path identity, `index.md` catalogs, `log.md` appends
- [x] 2.2 Concept types: TechnicalDecision, InvariantContract, BusinessWorkflow (multi-anchor), GuardrailDecision
- [x] 2.3 Reverse-index generator (`reverse-index.md`), regenerated on accepted write/reanchor; sync verifier for CI
- [x] 2.4 Monorepo sharding: per-directory `.context/` mirroring and per-shard reverse indexes

## 3. Anchor engine

- [x] 3.1 Anchor evaluator: `all_of` terms/regex, `near` + `scope_lines`, `min_match` (N-of-M), multi-anchor concepts
- [x] 3.2 Write gate: zero-hit reject, in-file uniqueness, distinctiveness ceilings with reported term counts, claims-anchored check, exclusion enforcement; JSON reject payloads with tighten reasons and suggestions
- [x] 3.3 Liveness classifier: LIVE / WEAK / REANCHOR / DRIFT per touched anchor, diff-scoped via reverse index
- [x] 3.4 Relocation: `git diff -M` rename detection + `git log -S` pickaxe candidate search; unique candidate → anchor patch emission (caller applies)
- [x] 3.5 RECONCILE JSON: lost anchors, candidates, `impacted_scenarios`, `engine_version`
- [x] 3.6 Dilution warnings attached to the PR introducing duplicate terms

## 4. CLI

- [x] 4.1 `repocodex validate --diff` (all outcomes, JSON)
- [x] 4.2 `repocodex write` / `repocodex reconcile` (gate-enforced)
- [x] 4.3 `repocodex context <paths>` (staged retrieval, machine-readable)
- [x] 4.4 `repocodex repair` (invoke repair agent on current RECONCILE state)
- [x] 4.5 `repocodex install` (pre-commit hook + GitHub Action + skills + optional MCP registration)
- [x] 4.6 `repocodex bootstrap` (mine history/comments/docs; gate-passing only; `status: draft`, `stale_after`, mandatory `sources`)
- [x] 4.7 `repocodex audit` (sampling truth audit + distinctiveness re-scoring)

## 5. Retrieval and impact

- [x] 5.1 Staged retrieval: reverse index → catalogs → bodies on demand; 1 link-hop titles
- [x] 5.2 Ranking: provenance-weighted, churn down-ranked (inferred from git history)
- [x] 5.3 Intent-side impact walk (deterministic): changed files → concepts → OKF links → other pinned paths; included in validate output
- [x] 5.4 Code-side impact recipe in skills: bounded grep/read walk (hit ranking, read caps, exclusions)

## 6. Enforcement

- [x] 6.1 Git pre-commit hook: deny commit on DRIFT; filter `git commit` inside hook body
- [x] 6.2 GitHub Action (required check): DRIFT, ratcheted skipped-memory, index sync — deterministic only
- [x] 6.3 Rollout postures `shadow` / `ratchet` / `full` with metrics instrumentation (false-drift rate, rejection reasons, reconcile retries, tokens per turn, latency)
- [x] 6.4 `memory-exempt` escape hatch: review-agent acknowledgment, `log.md` audit entry, follow-up repair task
- [x] 6.5 Post-merge re-attest and CONTRADICTION on conflicting supersedes

## 7. Agent surfaces

- [x] 7.1 Coding-agent skill: context before edit, impact on diff, reconcile handling, anchor-authoring guidance (stable-token preference)
- [x] 7.2 Review-agent skill: impact recipe, prose-vs-diff verification for new concepts, weakening/contradiction/churn flags; advisory check output
- [x] 7.3 Optional MCP server wrapping the CLI (`get_context`, `get_impact`, `read_concept`, `write_memory`, `validate_diff`, `reconcile_memory`)
- [x] 7.4 Agent Plugins 1.0 packaging (`plugin.json`, `mcp.json`, `skills/`) + Claude/Cursor hook adapters

## 8. Verification

- [x] 8.1 Attest fixtures: architecture §5.4/§5.5 examples must pass the gate and classify correctly under formatting, rename, move, and literal-change edits
- [x] 8.2 Determinism test: identical verdicts across two environments at the pinned engine version
- [x] 8.3 Brownfield simulation: zero-coverage repo passes `ratchet`; covered-file edits enforce correctly
- [x] 8.4 End-to-end: agent loop (context → edit → validate → reconcile → commit) against a sample repo

## Verification notes (reconciled with tests)

The boxes above record that a test existed, not that it asserted the scenario exactly. Review of the v1 suite found:

- 8.1 rename REANCHOR, literal-change, and formatter-tolerance tests accepted alternative classifications (`REANCHOR|DRIFT`, `WEAK|DRIFT`, `LIVE|WEAK`). Tightened in `fix-repocodex-v1-review-gaps`.
- 8.1 dilution warning was asserted only via `engine_version` presence. The warning content is now asserted.
- 8.3 covered-file ratchet was cleared by any `.context/` edit; per-file correspondence is now tested.
- Claim liveness was write-time only; `CLAIM_BROKEN` is now classified at validate time.

