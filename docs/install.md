# Install

Mechanical floor for an application repo: CLI, pin, hook, required CI. What the check means: [how-it-works.md](how-it-works.md).

Requires Python 3.11+ and [ripgrep](https://github.com/BurntSushi/ripgrep) (`rg`) on `PATH`.

## CLI

The first public release is experimental `0.0.1`. Install from the git tag (there is no PyPI package yet):

```bash
pip install "git+https://github.com/azaylamba/repocodex.git@v0.0.1"
```

From a local clone:

```bash
pip install -e .
```

## Wire the repo

From the repository root:

```bash
repocodex install
```

This writes:

- `.git/hooks/pre-commit` — runs `repocodex validate --diff --staged --hook`
- `.github/workflows/repocodex.yml` — required (deterministic) check plus an advisory job
- coding and review skills under `.cursor/skills/` and `.claude/skills/`
- `.repocodex.toml` if it does not already exist

### First hour after install

Default posture is `shadow`, but **undischarged skipped-memory still blocks**. The next substantive edit of an uncovered eligible source file is denied by the hook and `--check` until a pinning concept is written in the same change. That is intentional: empty context is not a free pass.

For a brownfield repo with many uncovered files, optionally seed draft `TechnicalDecision` pages first:

```bash
repocodex bootstrap
```

Then review, tighten, and commit what you keep. Promote `posture` to `ratchet` or `full` when you also want the hook and required check to deny drift and `CLAIM_BROKEN`.

## Optional MCP

For hosts that speak MCP over stdio (Cursor and similar), install the extra and register the server. This is not required for CLI, hook, or the pin-check Action. Start the host process at the repository root so tools see the same cwd as the CLI.

```bash
pip install "repocodex[mcp] @ git+https://github.com/azaylamba/repocodex.git@v0.0.1"
# or from a local clone:
pip install -e ".[mcp]"
repocodex install --mcp
```

That merges the packaged stdio config into `.cursor/mcp.json`. `repocodex mcp` starts the server. Without the extra, `--mcp` does not write that config.

## Engine pin

`.repocodex.toml` pins the engine:

```toml
engine_version = "0.0.1"
posture = "shadow"
```

Hook, local CLI, and CI resolve that pin so verdicts agree. A running engine that does not match `engine_version` refuses to run.

Keep the pin in the same commit as the workflow. The Action installs from `git+https://github.com/azaylamba/repocodex.git@v<engine_version>` (tag `v0.0.1` when the pin is `0.0.1`).

Default `posture` is `shadow`: pin-check findings (drift, `CLAIM_BROKEN`, contradiction, index desync) are reported but do not deny. Undischarged skipped-memory — including first-touch of an uncovered source file — **is** blocking in `shadow`, so the hook and `--check` deny a change that recorded no why. Promote to `ratchet` or `full` when you also want the hook and required check to deny drift and `CLAIM_BROKEN`.

## Hook and CI wrap validate

Both wrap `repocodex validate`. Locally:

```bash
repocodex validate --diff
```

`--check` (used by CI) exits 1 on deterministic blocking outcomes. `--hook` is what the pre-commit script passes.

The required Action job is the one to protect on the branch. The advisory job is `continue-on-error` and never decides the required verdict.
