## 1. License, version, and authorship metadata

- [ ] 1.1 Add root `LICENSE` (MIT) and declare MIT plus `license-files` in `pyproject.toml` so the sdist includes the file
- [ ] 1.2 Set version `0.0.1` in `pyproject.toml`, `ENGINE_VERSION`, install’s default `.repocodex.toml`, and the Action fallback pin
- [ ] 1.3 Set `project.authors` to Ajay Lamba (no placeholder `RepoCodex`) and `project.urls` Homepage, Source, and Issues to `https://github.com/azaylamba/repocodex`
- [ ] 1.4 Update tests and fixtures that assert `engine_version == "1.0.0"` to `0.0.1`

## 2. Git-based install and consuming CI

- [ ] 2.1 Change the shipped Action (`src/repocodex/data/action/repocodex.yml`) so the required and advisory jobs install from `git+https://github.com/azaylamba/repocodex.git@v<engine_version>` instead of PyPI
- [ ] 2.2 Confirm `repocodex install` still writes that Action and a matching `engine_version` pin
- [ ] 2.3 Add or update a test that the Action template contains the git install URL and does not `pip install repocodex==` from PyPI

## 3. Hide non-starting MCP from the first public cut

- [ ] 3.1 Make `repocodex install --mcp` report MCP as unavailable (not an installed working surface) while `run_mcp` cannot start
- [ ] 3.2 Add a test that `--mcp` does not set `ok` true solely by copying `mcp.json`

## 4. User docs

- [ ] 4.1 Rewrite README install to git tag or local editable clone; add experimental `0.0.1`; add a short Ajay Lamba byline linking `azaylamba/repocodex`; keep README the front door only
- [ ] 4.2 Update `docs/install.md` to the same git-tag install and Action behavior; omit MCP as a working step
- [ ] 4.3 Point `CONTRIBUTING.md` at this GitHub repo and engine pytest CI

## 5. Security and engine CI

- [ ] 5.1 Add `SECURITY.md` directing reports to GitHub issues (or private vulnerability reporting) on `azaylamba/repocodex`
- [ ] 5.2 Add `.github/workflows/` on this repository: Python 3.11, ripgrep, `pip install -e ".[dev]"`, pytest on pull_request and push to `main`
- [ ] 5.3 Confirm that workflow does not fail for a missing `.context/` bundle

## 6. Verification

- [ ] 6.1 Grep the tree for remaining `pip install repocodex` (PyPI) and `1.0.0` user-facing claims; leave architecture history alone
- [ ] 6.2 Run pytest
- [ ] 6.3 Run `openspec validate --all --strict`

## 7. Personal achievement (owner; after in-repo work lands)

- [ ] 7.1 Keep the project on the existing user `azaylamba`; do not create a second GitHub username or a RepoCodex organization for this release
- [ ] 7.2 Set `azaylamba/repocodex` to public
- [ ] 7.3 Create and push git tag `v0.0.1` on the release commit; verify `pip install git+https://github.com/azaylamba/repocodex.git@v0.0.1` works unauthenticated
- [ ] 7.4 Pin `repocodex` on the `azaylamba` GitHub profile
- [ ] 7.5 Confirm the public README byline, Issues link, and contributor identity show Ajay Lamba / `azaylamba`
