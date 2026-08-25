# Tasks: add-repocodex-v1

## 1. Foundation

- [ ] 1.1 Scaffold Python package (Typer CLI entry point, `pyproject.toml`, test harness)
- [ ] 1.2 Pydantic schema for OKF v0.2 frontmatter + extensions (`verification`, `claims`, `supersedes`, `rationale`, `format_version`)
- [ ] 1.3 `.repocodex.toml` config loader (engine version pin, posture, distinctiveness ceilings, `scope_lines` default, exclusion globs) and `.repocodexignore` support
- [ ] 1.4 ripgrep + git subprocess wrappers with structured results and version reporting

## 2. Memory store

- [ ] 2.1 `.context/` bundle reader/writer: one concept per file, path identity, `index.md` catalogs, `log.md` appends
- [ ] 2.2 Concept types: TechnicalDecision, InvariantContract, BusinessWorkflow (multi-anchor), GuardrailDecision
- [ ] 2.3 Reverse-index generator (`reverse-index.md`), regenerated on accepted write/reanchor; sync verifier for CI
- [ ] 2.4 Monorepo sharding: per-directory `.context/` mirroring and per-shard reverse indexes

## 3. Anchor engine

- [ ] 3.1 Anchor evaluator: `all_of` terms/regex, `near` + `scope_lines`, `min_match` (N-of-M), multi-anchor concepts
- [ ] 3.2 Write gate: zero-hit reject, in-file uniqueness, distinctiveness ceilings with reported term counts, claims-anchored check, exclusion enforcement; JSON reject payloads with tighten reasons and suggestions
- [ ] 3.3 Liveness classifier: LIVE / WEAK / REANCHOR / DRIFT per touched anchor, diff-scoped via reverse index
- [ ] 3.4 Relocation: `git diff -M` rename detection + `git log -S` pickaxe candidate search; unique candidate → anchor patch emission (caller applies)
- [ ] 3.5 RECONCILE JSON: lost anchors, candidates, `impacted_scenarios`, `engine_version`
- [ ] 3.6 Dilution warnings attached to the PR introducing duplicate terms

## 4. CLI

- [ ] 4.1 `repocodex validate --diff` (all outcomes, JSON)
- [ ] 4.2 `repocodex write` / `repocodex reconcile` (gate-enforced)
- [ ] 4.3 `repocodex context <paths>` (staged retrieval, machine-readable)
- [ ] 4.4 `repocodex repair` (invoke repair agent on current RECONCILE state)
- [ ] 4.5 `repocodex install` (pre-commit hook + GitHub Action + skills + optional MCP registration)
- [ ] 4.6 `repocodex bootstrap` (mine history/comments/docs; gate-passing only; `status: draft`, `stale_after`, mandatory `sources`)
- [ ] 4.7 `repocodex audit` (sampling truth audit + distinctiveness re-scoring)

## 5. Retrieval and impact

- [ ] 5.1 Staged retrieval: reverse index → catalogs → bodies on demand; 1 link-hop titles
- [ ] 5.2 Ranking: provenance-weighted, churn down-ranked (inferred from git history)
- [ ] 5.3 Intent-side impact walk (deterministic): changed files → concepts → OKF links → other pinned paths; included in validate output
- [ ] 5.4 Code-side impact recipe in skills: bounded grep/read walk (hit ranking, read caps, exclusions)

## 6. Enforcement

- [ ] 6.1 Git pre-commit hook: deny commit on DRIFT; filter `git commit` inside hook body
- [ ] 6.2 GitHub Action (required check): DRIFT, ratcheted skipped-memory, index sync — deterministic only
- [ ] 6.3 Rollout postures `shadow` / `ratchet` / `full` with metrics instrumentation (false-drift rate, rejection reasons, reconcile retries, tokens per turn, latency)
- [ ] 6.4 `memory-exempt` escape hatch: review-agent acknowledgment, `log.md` audit entry, follow-up repair task
- [ ] 6.5 Post-merge re-attest and CONTRADICTION on conflicting supersedes

## 7. Agent surfaces

- [ ] 7.1 Coding-agent skill: context before edit, impact on diff, reconcile handling, anchor-authoring guidance (stable-token preference)
- [ ] 7.2 Review-agent skill: impact recipe, prose-vs-diff verification for new concepts, weakening/contradiction/churn flags; advisory check output
- [ ] 7.3 Optional MCP server wrapping the CLI (`get_context`, `get_impact`, `read_concept`, `write_memory`, `validate_diff`, `reconcile_memory`)
- [ ] 7.4 Agent Plugins 1.0 packaging (`plugin.json`, `mcp.json`, `skills/`) + Claude/Cursor hook adapters

## 8. Verification

- [ ] 8.1 Attest fixtures: architecture §5.4/§5.5 examples must pass the gate and classify correctly under formatting, rename, move, and literal-change edits
- [ ] 8.2 Determinism test: identical verdicts across two environments at the pinned engine version
- [ ] 8.3 Brownfield simulation: zero-coverage repo passes `ratchet`; covered-file edits enforce correctly
- [ ] 8.4 End-to-end: agent loop (context → edit → validate → reconcile → commit) against a sample repo
