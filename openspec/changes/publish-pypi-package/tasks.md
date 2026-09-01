## 1. Action and tests

- [ ] 1.1 Change `src/repocodex/data/action/repocodex.yml` so required and advisory jobs install with `pip install "repocodex==${PIN}"` instead of the git+https tag URL
- [ ] 1.2 Update tests in `tests/test_commands.py`, `tests/test_enforcement.py`, and `tests/test_review_gaps.py` that assert the git install URL so they assert the PyPI pin and reject `git+https://github.com/azaylamba/repocodex.git` as the Action install source

## 2. User docs and metadata

- [ ] 2.1 Update `README.md` primary install to `pip install "repocodex==0.0.1"`; keep experimental `0.0.1`; keep a clone/`-e .` path
- [ ] 2.2 Update `docs/install.md` CLI, MCP extra (`repocodex[mcp]==0.0.1`), engine pin, and Action description to PyPI `repocodex==<engine_version>`; git-tag install as fallback only
- [ ] 2.3 Optionally add `Development Status :: 3 - Alpha` to `pyproject.toml` classifiers; leave version `0.0.1`

## 3. Publish workflow

- [ ] 3.1 Add `.github/workflows/` publish job: on tag `v*`, Python 3.11, `python -m build`, `pypa/gh-action-pypi-publish` with OIDC and a GitHub Environment (no API token in the repo)
- [ ] 3.2 Confirm `python -m build` and `python -m twine check dist/*` succeed locally and the sdist still includes `LICENSE`

## 4. Verification

- [ ] 4.1 Grep the tree for remaining user-facing git-only install as the primary path (`git+https://github.com/azaylamba/repocodex.git` in README, install docs, Action); leave `docs/research/` and this change’s history alone
- [ ] 4.2 Run pytest
- [ ] 4.3 Run `openspec validate --all --strict` (or the project’s equivalent) for this change

## 5. Owner last mile (after in-repo work lands)

- [ ] 5.1 Create PyPI and TestPyPI accounts with 2FA; register pending Trusted Publishers for `azaylamba/repocodex` matching the workflow file and environment
- [ ] 5.2 Dry-run: upload to TestPyPI and `pip install` `repocodex==0.0.1` from TestPyPI (`--extra-index-url` for dependencies); confirm `repocodex --help` and `engine_version` `0.0.1`
- [ ] 5.3 Point git tag `v0.0.1` at the PyPI-ready commit (create or move); push the tag
- [ ] 5.4 Upload `0.0.1` to production PyPI via Trusted Publishing (twine fallback only if OIDC is not yet registered)
- [ ] 5.5 Confirm `pip install "repocodex==0.0.1"` from PyPI and that a consuming `repocodex install` writes an Action that uses that pin
