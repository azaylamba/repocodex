## Why

The first public cut already exists as experimental `0.0.1` on git (`v0.0.1`), but humans and consuming CI still install from that tag because PyPI was deferred. The name `repocodex` is free and nothing is published yet, so this is the change that restores `pip install repocodex` without inventing a new version identity.

## What Changes

- Publish the existing engine identity `0.0.1` to the PyPI project `repocodex` (final PEP 440 version, not `a`/`b` pre-release).
- Switch README, `docs/install.md`, optional MCP extra install, and the shipped GitHub Action from git-tag install to `pip install repocodex==<pin>`.
- Keep git-tag / editable clone as a documented fallback, not the default path.
- Add engine-repo publishing (Trusted Publishing from GitHub, TestPyPI dry-run, then production upload) so the wheel on PyPI is the same `0.0.1` as `ENGINE_VERSION` and tag `v0.0.1`.
- Keep docs marking the cut experimental; optionally declare PyPI Development Status Alpha **without** changing the version string.

No **BREAKING** pin change: `engine_version` stays `"0.0.1"`. Re-running `repocodex install` in consuming repos rewrites the Action from git+https to PyPI.

## Capabilities

### New Capabilities

None. Publishing is the deferred bar of `oss-release`, not a new product surface.

### Modified Capabilities

- `oss-release`: Replace “install and CI work without PyPI” with a published `repocodex==0.0.1` project, matching git tag identity, and a Trusted Publishing path on this repository.
- `user-docs`: README and install docs SHALL present `pip install repocodex` from PyPI (pinned `0.0.1`) as the install path; git remains fallback. Optional MCP extra follows the same source.
- `agent-interfaces`: The shipped Action SHALL install `repocodex==<engine_version>` from PyPI instead of `git+https://github.com/azaylamba/repocodex.git@v<pin>`.

## Impact

- `src/repocodex/data/action/repocodex.yml` (required and advisory jobs)
- `README.md`, `docs/install.md` (CLI, MCP extra, Action pin source)
- Tests that assert the git install URL and forbid `pip install repocodex==`
- New `.github/workflows/` publish job on this repository (Trusted Publishing)
- `pyproject.toml` only if classifiers are added; version stays `0.0.1`
- Owner last mile: PyPI/TestPyPI accounts, pending publisher, tag alignment, first upload

Out of scope: PEP 440 alpha/beta versions, bumping past `0.0.1`, yanking, a GitHub org, engine behavior, MCP protocol changes.
