# AGENTS.md

Contributor briefing for coding agents working on **this** repository: the RepoCodex engine (CLI, attester, store, packaging).

This is not an application repo that *uses* RepoCodex. There is no `.context/` bundle here. The product loop for installed repos is documented elsewhere — do not duplicate it in this file.

| Need | Read |
| --- | --- |
| Purpose, benefit, retrieve → pin-check loop | [docs/how-it-works.md](docs/how-it-works.md) |
| How agents run that loop in an app repo | [docs/agents.md](docs/agents.md) |
| Engine contributor setup / OpenSpec | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Current engine architecture (further reading) | [docs/research/architecture.md](docs/research/architecture.md) |
| Design history (not the shipped contract) | [docs/research/design-history.md](docs/research/design-history.md) |

Packaged installables (skills, rules, hooks) live under `src/repocodex/data/`. Do not treat this file as that content.

## Intention

RepoCodex stores git-native *why* next to code and attests attachment with a deterministic pin check (ripgrep + git). Instruction files and test suites do not give that guarantee.

This checkout builds that engine. Audience: coding agents first. Engine pytest pins CLI and attester behavior; it is not how application scenarios are verified. Do not rewrite `docs/research/architecture.md` as a side effect of a small change; update it when the current system design actually moved. Do not treat `docs/research/design-history.md` as the shipped contract.

## Layout

| Path | Role |
| --- | --- |
| `src/repocodex/cli.py` | Typer entry; JSON envelopes; non-zero exit on failure |
| `src/repocodex/commands/` | Command implementations |
| `src/repocodex/engine/` | Deterministic attester (gate, match, liveness, ratchet, …) — no LLM |
| `src/repocodex/store/` | OKF bundle and reverse index |
| `src/repocodex/tools/` | Thin ripgrep / git wrappers |
| `src/repocodex/schema.py` | Concept models, parse/serialize, envelopes |
| `src/repocodex/config.py` | Repo config and engine pin |
| `src/repocodex/retrieval.py` | Context retrieval |
| `src/repocodex/mcp_server.py` | Optional MCP wrapper |
| `tests/` | Engine-package tests |
| `openspec/` | Behavior specs and changes |
| `docs/` | User-facing and research docs |

## Rules

- Python 3.11+, src layout. Put `from __future__ import annotations` immediately after the module docstring.
- Type hints on public APIs; prefer `pathlib.Path`.
- Public behavior changes go through OpenSpec (`openspec validate --all --strict`). Keep proposal / design / delta specs / tasks aligned.
- CLI stays JSON-out. The engine path stays deterministic (no model calls in `engine/`).
- Small focused diffs. No drive-by refactors or whole-tree format.
- Do not add Python docstrings inside packaged skill markdown under `src/repocodex/data/`.

## Formatting

Ruff lint selects rule set `D` (pydocstyle) only. `ruff format` is not enabled. Match the surrounding file; do not restyle unrelated lines.

## Docstrings

Google-style (PEP 257 summary line, then `Args` / `Returns` / `Raises` when the signature is not enough). Enforced by `ruff check src tests` with `convention = "google"`.

| Surface | Docstring |
| --- | --- |
| Every `src/repocodex/**/*.py` and `tests/**/*.py` module | Yes — one paragraph on what the module is for |
| Public classes, functions, and methods in `src/` | Yes — summary plus sections when needed |
| Typer CLI commands in `cli.py` | Keep the existing `--help` docstring; expand only if too thin |
| Public fixtures and helpers in `tests/conftest.py` and `tests/fixtures/` | Yes — shared test API |
| `test_*` functions | No — names stay the docs |
| Private `_helpers` | One-line only (`D103` still applies to `_` names) |

Ruff ignores: `D105` (magic methods), `D107` (`__init__` covered by the class docstring). Per-file: `tests/test_*.py` ignore `D101` / `D102` / `D103` (module docs only).

Why-comments only on non-obvious branches in public functions (e.g. why findings are advisory vs blocking, why the ratchet skips comment-only diffs, why repair prefers Cursor then Claude then Codex, why write grandfathering allows an existing flat identity). No comments that restate the next line. Do not assert on docstring text in tests.

```python
# ✅ GOOD
def missing_invariant_claims(doc: ConceptDocument) -> bool:
    """Return True when an InvariantContract has no claims.

    Args:
        doc: Parsed concept document to inspect.

    Returns:
        True if type is InvariantContract and claims is empty.
    """
    return (
        doc.frontmatter.type == ConceptType.InvariantContract.value
        and not doc.frontmatter.claims
    )

# ❌ BAD — restating comment, no docstring
def missing_invariant_claims(doc):
    # Check if claims are missing
    return doc.frontmatter.type == "InvariantContract" and not doc.frontmatter.claims
```

## Verify before claiming done

```bash
pip install -e ".[dev]"   # once
ruff check src tests
pytest
```

Install `".[dev,mcp]"` only when changing `repocodex mcp`. CI (`.github/workflows/engine-tests.yml`) runs ruff then pytest.
