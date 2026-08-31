## Why

The engine is a private repo under `azaylamba` whose README, Action, and package metadata describe a finished 1.0 others `pip install`. That first run is false, the license is not a file, MCP does not start, and authorship is the placeholder “RepoCodex”. Opening the source without fixing those items would publish a broken install and hide that Ajay Kumar built it. This change is the must-have floor for a first public release as a personal achievement on that existing GitHub user — not a 1.0 product launch and not a new account or organization.

## What Changes

- Add an MIT `LICENSE` and declare it in package metadata so GitHub and downstream can detect the license.
- Mark the project experimental (`0.x`, not `1.0.0`) in package metadata, CLI `engine_version`, default pin, and docs so the first public cut does not overclaim.
- Make install instructions and the shipped GitHub Action succeed **without PyPI**: install from the public git tag/ref that matches `engine_version`.
- Add engine-repo CI (pytest + ripgrep) so `main` is checkable once public.
- Stop advertising MCP as a working extra until a server actually starts; `install --mcp` must not claim success for a non-starting server.
- Attribute the project to **Ajay Kumar** (`azaylamba`) in package metadata, README, and security contact. Primary contact is GitHub issues on `azaylamba/repocodex`.
- Add `SECURITY.md` and enough `CONTRIBUTING` / README byline that a visitor can see who built it and how to report issues.
- Keep the GitHub home as the existing personal repo (`azaylamba/repocodex`). Do not create a second user or an org as part of this change.

**BREAKING** (for anyone who already pinned `engine_version = "1.0.0"` locally): the running engine version becomes `0.0.1` so it matches the first public tag. Unpublished 1.0.0 was never on PyPI.

## Capabilities

### New Capabilities

- `oss-release`: Must-have packaging, license, version, engine CI, security contact, git-based install, and personal attribution for the first public release. Covers what “open source under my username” requires in-repo; flipping GitHub visibility remains a manual owner action listed in tasks.

### Modified Capabilities

- `user-docs`: README and install docs SHALL state experimental status, git (not PyPI) install, author byline, and license. They SHALL NOT tell a first-time visitor to `pip install repocodex` until a PyPI project exists.
- `agent-interfaces`: The shipped Action SHALL install the pinned engine from git (or another source that exists). MCP remains optional in the architecture but SHALL NOT be documented or reported as installed-and-working on the first public release while `run_mcp` cannot start.

## Impact

- `pyproject.toml`, `src/repocodex/__init__.py` (`ENGINE_VERSION`), default `.repocodex.toml` written by `install`
- `README.md`, `docs/install.md`, `CONTRIBUTING.md`, new `LICENSE`, `SECURITY.md`
- `src/repocodex/data/action/repocodex.yml` (and the copy `install` writes)
- Tests and docs that hard-code `1.0.0` as `engine_version`
- New `.github/workflows/` on **this** repository (engine pytest)
- `src/repocodex/commands/install.py` and user-facing MCP mentions (`install --mcp`, README, plugin docs)
- Tests that assert MCP packaging exists may stay; tests and docs must not require a starting MCP server for the public v0 cut

Out of scope: publishing to PyPI, implementing a working MCP server, seeding `.context/` on this repo, creating a GitHub organization or a second username, the advisory review-agent job, scheduled audits.
