# RepoCodex

RepoCodex stores *why* next to the code, in git, as an OKF v0.2 bundle. Agents retrieve that why and read the pinned source before they edit; a deterministic pin check (ripgrep + git) attests the attachment. Instruction files and tests do not give that guarantee.

Git-native why next to code; pin check, not a test suite.

Experimental `0.0.1`. Created by [Ajay Lamba](https://github.com/azaylamba/repocodex).

```bash
pip install "git+https://github.com/azaylamba/repocodex.git@v0.0.1"
# or from a local clone: pip install -e .
repocodex install
repocodex context src/billing/PaymentGateway.ts
repocodex validate --diff
```

Pin the engine in `.repocodex.toml`. Hook, local CLI, and CI resolve that pin so verdicts agree.

| Doc | Job |
| --- | --- |
| [How it works](docs/how-it-works.md) | Purpose, benefit, and the retrieve → read → edit → update why → pin-check loop |
| [Memory](docs/memory.md) | How to read `.context/` |
| [Agents](docs/agents.md) | How coding agents (and optionally humans) run the loop |
| [Install](docs/install.md) | CLI, pin, hook, GitHub Action, optional MCP |
| [Architecture](docs/research/architecture.md) | Current engine architecture (further reading) |
