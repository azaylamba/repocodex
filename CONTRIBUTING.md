# Contributing to RepoCodex

This repository is the **engine**: the CLI, attester, store, and packaging. Application-repo usage (installing the CLI into another project, running the agent loop) is documented in [README.md](README.md) and [docs/](docs/how-it-works.md). Do not treat this file as that guide.

## Setup

Python 3.11+ and [ripgrep](https://github.com/BurntSushi/ripgrep) on `PATH`.

```bash
pip install -e ".[dev]"
```

## Tests

Engine-package tests pin the CLI and the attester. They are not how application scenarios are verified.

```bash
pytest
```

## Specs

Behavior changes go through [OpenSpec](https://github.com/Fission-AI/OpenSpec) in `openspec/`. Propose a change, keep `proposal.md` / `design.md` / delta specs / `tasks.md` aligned, then implement.

```bash
openspec validate --all --strict
```

Do not rewrite [docs/research/architecture.md](docs/research/architecture.md) as a side effect of a small engine change; link it when the canonical design actually moved.
