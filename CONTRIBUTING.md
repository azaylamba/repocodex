# Contributing to RepoCodex

This repository is the **engine**: the CLI, attester, store, and packaging, at [github.com/azaylamba/repocodex](https://github.com/azaylamba/repocodex). Application-repo usage (installing the CLI into another project, running the agent loop) is documented in [README.md](README.md) and [docs/](docs/how-it-works.md). Do not treat this file as that guide. Coding agents: project conventions, formatting, and docstring rules live in [AGENTS.md](AGENTS.md).

## Setup

Python 3.11+ and [ripgrep](https://github.com/BurntSushi/ripgrep) on `PATH`.

```bash
pip install -e ".[dev]"
```

To run `repocodex mcp` locally, also install the optional extra: `pip install -e ".[dev,mcp]"`. Engine tests stub that extra and do not require it for pytest.

## Tests

Engine-package tests pin the CLI and the attester. They are not how application scenarios are verified. GitHub Actions on this repository runs the same suite on pull requests and on push to `main` (Python 3.11, ripgrep, `pip install -e ".[dev]"`, ruff docstring check, pytest).

```bash
ruff check src tests
pytest
```

Public Python APIs use Google-style docstrings. `ruff check` enforces pydocstyle (Google) on `src/` and `tests/`. Test modules need a module docstring only; `test_*` functions do not.

## Specs

Behavior changes go through [OpenSpec](https://github.com/Fission-AI/OpenSpec) in `openspec/`. Propose a change, keep `proposal.md` / `design.md` / delta specs / `tasks.md` aligned, then implement. Commit current specs under `openspec/specs/` and in-flight work under `openspec/changes/<name>/`. Do not commit `openspec/changes/archive/` — that directory is gitignored so local archive history stays off the public tree.

```bash
openspec validate --all --strict
```

Do not rewrite [docs/architecture.md](docs/architecture.md) as a side effect of a small engine change; update it when the current system design actually moved. Do not commit `docs/research/design-history.md` or `docs/superpowers/` — both are gitignored local research, not the shipped contract.
