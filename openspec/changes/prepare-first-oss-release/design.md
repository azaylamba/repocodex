## Context

RepoCodex lives at `github.com/azaylamba/repocodex`, currently private. The engine implements the pin-check loop; packaging and docs describe a PyPI 1.0 with working MCP. The owner wants a first public release on that personal account as a showcase, not a new username or organization.

Constraints: CLI remains canonical; consuming-repo CI is `validate --diff --check`; MCP is optional in architecture and broken in code; `engine_version` in `.repocodex.toml` must match the running engine.

## Goals / Non-Goals

**Goals:**

- A visitor who clones or `pip install`s from git can run the CLI, hook, and pin-check Action without PyPI.
- GitHub detects an MIT license; package metadata names Ajay Lamba and points at this repo.
- Engine `main` has pytest CI once the repo is public.
- Docs and install do not claim MCP or `pip install repocodex` from PyPI.
- Version and pin are `0.0.1` so the first tag is honest.
- Attribution and security contact make the personal authorship obvious.

**Non-Goals:**

- Uploading to PyPI (a later change can restore `pip install repocodex` once a project exists).
- Implementing a working MCP server.
- Seeding `.context/` on this repository.
- Creating a GitHub organization or a second personal account.
- Advisory review-agent execution, scheduled audits, marker-agreement CI.
- Rewriting `docs/research/architecture.md`.

## Decisions

### 1. Git tag is the install pin, not PyPI

The shipped Action and `docs/install.md` install with:

`pip install "git+https://github.com/azaylamba/repocodex.git@v${PIN}"`

where `PIN` is `engine_version` from `.repocodex.toml`. The first public tag is `v0.0.1`, matching `ENGINE_VERSION` and pyproject version.

**Alternative considered:** keep `pip install repocodex==PIN` and publish to PyPI in this change. Rejected — PyPI is a separate bar (account, Trusted Publishing, TestPyPI). Git install unblocks OSS and consuming CI without that.

**Alternative considered:** install from a commit SHA. Rejected — the pin is a version string; tags keep hook, local CLI, and CI on the same identifier.

### 2. Version becomes `0.0.1` (breaking vs unpublished 1.0.0)

Update `pyproject.toml`, `ENGINE_VERSION`, install’s default `.repocodex.toml`, Action fallback, and tests that assert `1.0.0`. Nobody has a PyPI 1.0.0 to migrate.

**Alternative considered:** keep 1.0.0 and add an “experimental” badge only. Rejected — version is the strongest signal; 1.0.0 plus git-only install is a contradiction.

### 3. MIT LICENSE file + SPDX in pyproject

Add `LICENSE` at the repo root. Prefer PEP 639 `license = "MIT"` and `license-files = ["LICENSE"]` if the pinned setuptools floor allows; otherwise keep a working license declaration that still ships the file. GitHub license detection needs the file either way.

### 4. MCP: hide, do not ship a fake extra

Leave the tool-function module in the tree. First public release:

- README and `docs/install.md` do not offer `repocodex install --mcp` as a working step.
- `install --mcp` reports that MCP is not available in this release (failed or skipped), and does not merge a server config that cannot start.
- Plugin `mcp.json` may remain in package data for later; it is not a documented user path.

**Alternative considered:** fix FastMCP in this change. Rejected — not a must-have for OSS; a broken extra is worse than omission.

**Alternative considered:** delete MCP code. Rejected — architecture still wants the wrapper later; this change only stops advertising it.

### 5. Attribution lives in metadata and the README byline, not a new namespace

- `project.authors`: Ajay Lamba; `project.urls`: Homepage/Source/Issues → `https://github.com/azaylamba/repocodex`.
- README: one-line author (“Created by Ajay Lamba”) plus the GitHub user link. Keep README short (existing user-docs rule).
- `SECURITY.md`: report vulnerabilities via GitHub issues (or private vulnerability reporting once the repo is public). Do not require a personal email in-tree.
- GitHub home stays `azaylamba/repocodex`. Pinning the public repo on the profile is a manual owner task, not code.

**Alternative considered:** GitHub org `repocodex`. Rejected for this change — it detaches the personal-achievement URL; transfer remains possible later.

### 6. Engine CI on this repo is pytest + ripgrep only

A workflow on push/PR to `main`: checkout, Python 3.11, install ripgrep, `pip install -e ".[dev]"`, `pytest`. It does not run `repocodex validate` against this repo (no `.context/` bundle). Consuming-repo pin-check CI stays the Action template, now git-install based.

### 7. Manual last mile is listed in tasks, not automated

Making the GitHub repository public, creating tag `v0.0.1`, and pinning the repo on the `azaylamba` profile require the owner. Specs require in-repo files to be ready for that; they do not require the agent to change GitHub visibility.

## Risks / Trade-offs

- **[Risk] Consuming Action fails until `v0.0.1` exists on the public remote.** → Document: tag after merge, then `repocodex install` in app repos. Until the repo is public, git+https install 404s — expected.
- **[Risk] Private git+https install needs credentials.** → First release assumes the repo is public. No token story in v0.
- **[Risk] PEP 639 license field breaks older setuptools.** → Verify `python -m build` in tasks; fall back to a form the current build-system supports while still shipping `LICENSE`.
- **[Risk] Tests hard-code `1.0.0`.** → Grep and update in the same change; version-mismatch tests still apply.
- **[Trade-off] Git URLs in the Action are longer and GitHub-specific.** → Acceptable until PyPI; a later change can switch the Action back to `repocodex==PIN`.

## Migration Plan

1. Land in-repo files on `main` (still private is fine).
2. Owner: add `LICENSE` commit if not already in that PR, then set the GitHub repo public.
3. Tag `v0.0.1` on that commit; confirm `pip install git+https://github.com/azaylamba/repocodex.git@v0.0.1` works.
4. Pin the repo on the personal profile.
5. Rollback: revert the PR. No PyPI to yank. Existing local `engine_version = "1.0.0"` installs refuse to run against 0.0.1 until the pin is edited — intended.

## Open Questions

- Whether to enable GitHub private vulnerability reporting the same day as going public (owner toggle; `SECURITY.md` can say “use GitHub issues” regardless).
- Exact `project.authors` email: omit from pyproject (name + URLs only) unless the owner wants a public address.
