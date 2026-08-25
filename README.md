# RepoCodex

Git-native executable memory for autonomous coding agents. Concepts live in `.context/` as OKF v0.2 markdown; distinctive textual anchors prove each record is about live code. The engine is a thin CLI over ripgrep and git — no model in the write gate, attester, or required CI check.

```bash
pip install repocodex
repocodex install
repocodex context src/billing/PaymentGateway.ts
repocodex validate --diff
```

Engine version is pinned in `.repocodex.toml`. Hook, local CLI, and CI resolve that pin so verdicts agree by construction.

See `docs/research/architecture.md` for the canonical design.
