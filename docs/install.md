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

## Engine pin

`.repocodex.toml` pins the engine:

```toml
engine_version = "0.0.1"
posture = "shadow"
```

Hook, local CLI, and CI resolve that pin so verdicts agree. A running engine that does not match `engine_version` refuses to run.

Keep the pin in the same commit as the workflow. The Action installs from `git+https://github.com/azaylamba/repocodex.git@v<engine_version>` (tag `v0.0.1` when the pin is `0.0.1`).

Default `posture` is `shadow` (report, do not block). Promote to `ratchet` or `full` when you want the hook and required check to deny.

## Hook and CI wrap validate

Both wrap `repocodex validate`. Locally:

```bash
repocodex validate --diff
```

`--check` (used by CI) exits 1 on deterministic blocking outcomes. `--hook` is what the pre-commit script passes.

The required Action job is the one to protect on the branch. The advisory job is `continue-on-error` and never decides the required verdict.
