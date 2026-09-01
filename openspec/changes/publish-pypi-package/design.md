## Context

`prepare-first-oss-release` made git tag `v0.0.1` the install pin so the repo could go public without a PyPI project. Package metadata, `ENGINE_VERSION`, default `.repocodex.toml`, and docs already agree on experimental `0.0.1`. The shipped Action and README still run:

`pip install "git+https://github.com/azaylamba/repocodex.git@v${PIN}"`

PyPI has no `repocodex` project. Pin matching is an exact string compare (`engine_version` vs `ENGINE_VERSION`). Constraints: CLI remains canonical; consuming CI is still `validate --diff --check`; version identity must not fork between git and PyPI.

## Goals / Non-Goals

**Goals:**

- A visitor can `pip install "repocodex==0.0.1"` (and `repocodex[mcp]==0.0.1`) from PyPI and run CLI, hook, and pin-check Action.
- The shipped Action installs `repocodex==<engine_version>` from PyPI.
- The wheel, sdist, git tag `v0.0.1`, pyproject version, and `ENGINE_VERSION` are the same `0.0.1` identity.
- This repository can publish that version via Trusted Publishing (after a TestPyPI dry-run).
- Docs still call the cut experimental.

**Non-Goals:**

- PEP 440 pre-releases (`0.0.1a1`, `0.1.0a1`, `0.1.0b1`).
- Bumping the engine past `0.0.1`.
- Changing validate, MCP protocol, or posture behavior.
- A GitHub organization or a second PyPI/GitHub namespace.
- Automating PyPI account creation or 2FA (owner).

## Decisions

### 1. Publish `0.0.1`, not an alpha version string

Keep pyproject version, `ENGINE_VERSION`, default pin, Action fallback, and PyPI release at `0.0.1`. Signal “not 1.0” with existing experimental copy plus optional `Development Status :: 3 - Alpha` in `pyproject.toml` classifiers.

**Alternative considered:** `0.1.0a1` so default `pip install repocodex` hides the cut. Rejected — that splits identity from git `v0.0.1` and existing pins (`engine_version` is exact string match), and forces `--pre` for the path this change exists to restore.

**Alternative considered:** `0.0.1a1`. Rejected — PEP 440 treats that as older than the already-tagged `0.0.1`.

### 2. Default install is a pinned PyPI version

README and `docs/install.md` primary snippet:

`pip install "repocodex==0.0.1"`

MCP extra: `pip install "repocodex[mcp]==0.0.1"`. Local `pip install -e .` / `-e ".[mcp]"` stays for developers. Git-tag install remains a short fallback in `docs/install.md` only.

The Action (required and advisory) becomes:

`pip install "repocodex==${PIN}"`

where `PIN` is still read from `.repocodex.toml` `engine_version` (fallback `0.0.1`). Exact `==` means consuming CI does not need `--pre` and will not float to a later release.

**Alternative considered:** unpinned `pip install repocodex` in the Action. Rejected — the product pin is the version string; CI must resolve the same identity as hook and local CLI.

**Alternative considered:** keep git install in the Action and only document PyPI for humans. Rejected — the first OSS design already named this switch as the follow-up; two install sources for the same pin would diverge.

### 3. Git tag `v0.0.1` and PyPI `0.0.1` are the same commit

Build and upload from the commit that contains the PyPI install-path switch. Owner points tag `v0.0.1` at that commit (create or move). Moving is acceptable here because PyPI is empty and `0.0.1` was always experimental; leaving the old tag would publish a different tree under the same pin.

**Alternative considered:** bump to `0.0.2` so the existing tag stays. Rejected — nothing is on PyPI yet, and the agreed identity for this first PyPI cut is `0.0.1`.

### 4. Trusted Publishing from GitHub, TestPyPI first

Add a workflow on this repo that builds with `python -m build` and publishes with `pypa/gh-action-pypi-publish` using OIDC (environment e.g. `pypi`), triggered on tag `v*`. Owner registers a pending publisher on TestPyPI and PyPI for `azaylamba/repocodex` before the first upload. Tasks include a TestPyPI dry-run (`twine upload --repository testpypi` or the TestPyPI trusted publisher) and an install check before production.

Do not store PyPI API tokens in the repo. Manual `twine` remains a documented fallback if OIDC is not ready for the first claim.

**Alternative considered:** only manual twine, no workflow. Rejected — Trusted Publishing is the bar the first OSS design deferred; this change should land the path, not another deferral.

### 5. Tests follow the Action, not git

Replace assertions that the Action template contains `git+https://github.com/azaylamba/repocodex.git@v${PIN}` and does not `pip install repocodex==`. New assertions: template contains `pip install "repocodex==${PIN}"` (or equivalent) and does not use the git+https install URL for the engine.

Leave `docs/research/` history alone.

## Risks / Trade-offs

- **[Risk] Existing `v0.0.1` tag points at the git-install tree.** → Owner moves the tag to the PyPI-ready commit before upload; do not upload a wheel whose contents disagree with the tag.
- **[Risk] `pip install repocodex` (unpinned) will take `0.0.1` as a stable PEP 440 release.** → Accepted. Docs keep “experimental”; classifier Alpha is optional extra signal. Action and README pin `==0.0.1`.
- **[Risk] First PyPI upload is immutable.** → TestPyPI + `twine check` + local install of the built wheel before production. Wrong `0.0.1` cannot be overwritten (yank only).
- **[Risk] Consuming repos still have the old Action until they re-run `repocodex install`.** → Expected. Old git install keeps working; docs say re-install to pick up PyPI.
- **[Risk] Pending Trusted Publisher is misconfigured (workflow name, environment, repo).** → Tasks spell the publisher fields; fallback is owner-run twine for the first claim only.
- **[Trade-off] Git fallback stays in install docs.** → Helps if PyPI is down or someone wants a commit; it is not the pin-check CI path.

## Migration Plan

1. Land in-repo switch (Action, docs, tests, publish workflow) on `main` with version still `0.0.1`.
2. Owner: TestPyPI account, pending publishers, dry-run upload and `pip install` from TestPyPI.
3. Owner: align tag `v0.0.1` to that commit; production Trusted Publisher upload (or twine fallback).
4. Confirm `pip install "repocodex==0.0.1"` and that `repocodex validate` reports `engine_version` `0.0.1`.
5. Consuming repos: `repocodex install` to rewrite the Action; pin stays `0.0.1`.
6. Rollback: yank PyPI `0.0.1` only if the artifact is wrong; restore git install in a follow-up commit. Yank does not un-claim the name.

## Open Questions

- Exact GitHub Environment name (`pypi` vs `release`) and whether TestPyPI uses a second environment — owner preference at publisher registration; workflow should match.
- Whether to force-move `v0.0.1` if it is already on the remote at an older commit (recommended: yes, before first upload).
