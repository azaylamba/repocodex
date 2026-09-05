# RepoCodex

[![Engine tests](https://img.shields.io/github/actions/workflow/status/azaylamba/repocodex/engine-tests.yml?branch=main&label=Engine%20tests)](https://github.com/azaylamba/repocodex/actions/workflows/engine-tests.yml)

**Git-native why next to code — with a pin check that proves it still matches.**

Coding agents write syntax well and forget _why_. Comments rot. Instruction files (`CLAUDE.md`, `AGENTS.md`, Cursor rules) never prove they still describe live text. Tests check behavior you remembered to assert; they do not keep institutional why attached to the lines that implement it.

RepoCodex stores that why in git beside the code. Agents retrieve it before they edit. A deterministic pin check (ripgrep + git) attests the attachment. Built for repositories where coding agents make the changes.

**Not** a test suite. **Not** another instruction file. **Not** a linter.

Experimental `0.0.1`. Requires Python 3.11+ and [ripgrep](https://github.com/BurntSushi/ripgrep) (`rg`) on `PATH`.

## Install

```bash
pip install "git+https://github.com/azaylamba/repocodex.git@v0.0.1"
# or from a local clone: pip install -e .
repocodex install
```

`repocodex install` writes the pre-commit hook, GitHub Action, agent skills, and `.repocodex.toml` (engine pin). The product is that loop: agents retrieve stored why before they edit, so they do not silently break existing behavior; the pin check fails the turn when why and code diverge, and a first substantive edit of an uncovered file is denied until a pinning concept is written.

```bash
repocodex context src/billing/PaymentGateway.ts   # retrieve why before edit
repocodex validate --diff                         # attest pins still hold
```

Pin the engine in `.repocodex.toml`. Hook, local CLI, and CI resolve that pin so verdicts agree.

## What a concept looks like

Types are orthogonal — one change may write more than one. Three common shapes:

**TechnicalDecision** (`decisions/…`) — why this construct exists:

```yaml
---
title: Capture streams enterprise retries instead of buffering
type: TechnicalDecision
verification:
  engine: ripgrep
  anchors:
    - path: src/billing/PaymentGateway.ts
      all_of: ["yield", "ENTERPRISE", "capturePayment"]
---
Enterprise capture is a generator so retries stay backpressure-aware. Do not
replace with an in-memory list of attempts.
```

**InvariantContract** (`invariants/…`) — must-hold token (requires `claims`):

```yaml
---
title: Enterprise capture grace is three attempts
type: InvariantContract
verification:
  engine: ripgrep
  anchors:
    - path: src/billing/PaymentGateway.ts
      all_of: ["ENTERPRISE", "grace", "= 3"]
claims:
  - subject: enterprise_grace_attempts
    literal: "3"
---
Enterprise plans get three capture retries before failure. Do not silently shrink this window.
```

**BusinessWorkflow** (`workflows/…`) — thin cross-package flow (one anchor per site):

```yaml
---
title: Checkout capture flows api → billing → ledger
type: BusinessWorkflow
verification:
  engine: ripgrep
  anchors:
    - path: src/api/checkout.ts
      all_of: ["capturePayment", "billing"]
    - path: src/billing/PaymentGateway.ts
      all_of: ["capturePayment", "ledger"]
    - path: src/ledger/posting.ts
      all_of: ["postCapture", "idempotency"]
---
Checkout capture crosses api, billing, then ledger. Keep that order; do not
post to the ledger from the API layer.
```

## Docs

| Doc                                  | Job                                                                            |
| ------------------------------------ | ------------------------------------------------------------------------------ |
| [How it works](docs/how-it-works.md) | Purpose, benefit, and the retrieve → read → edit → update why → pin-check loop |
| [Memory](docs/memory.md)             | How to read `.context/`                                                        |
| [Agents](docs/agents.md)             | How coding agents (and optionally humans) run the loop                         |
| [Install](docs/install.md)           | CLI, pin, hook, GitHub Action, optional MCP                                    |
| [Architecture](docs/architecture.md) | Current engine architecture (further reading)                                  |

## License and contributing

[MIT](LICENSE) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md)

Created by [Ajay Lamba](https://github.com/azaylamba/repocodex).
