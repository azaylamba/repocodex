# How to read `.context/`

RepoCodex memory is an [OKF v0.2](https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/main/SPEC.md) knowledge bundle at `.context/`. This page is a consumer guide: enough to open a file usefully. Field catalogs live in the OKF spec; do not treat this file as a schema.

## What lives in the bundle

| Path | Role |
| --- | --- |
| `.context/index.md` | Root catalog. Frontmatter is `okf_version: "0.2"` only. |
| `.context/log.md` | Chronological writes, grouped under `## YYYY-MM-DD`. |
| Nested `index.md` | Directory catalogs (title — description links). Not concepts. |
| Every other `.md` | A concept. Identity is the path relative to `.context/` without `.md`. |

Reserved filenames at any level are only `index.md` and `log.md`. Everything else with a `type` is a concept.

The reverse index is **not** a concept and is **not** in the bundle. It is generated at `.repocodex/reverse-index.md` (shards: `.repocodex/reverse-index/<escaped-path-parent>.md`). Do not look for `reverse-index.md` under `.context/`.

## Sample concepts

Types are orthogonal. Identity folders: `decisions/`, `invariants/`, `workflows/`.

### TechnicalDecision

Identity: `decisions/capture-streams-retries` → `.context/decisions/capture-streams-retries.md`.

```markdown
---
title: Capture streams enterprise retries instead of buffering
type: TechnicalDecision
status: stable
verification:
  engine: ripgrep
  anchors:
    - path: src/billing/PaymentGateway.ts
      all_of: ["yield", "ENTERPRISE", "capturePayment"]
---

Enterprise capture is a generator so retries stay backpressure-aware. Do not
replace with an in-memory list of attempts.
```

### InvariantContract

Identity: `invariants/enterprise-grace` → `.context/invariants/enterprise-grace.md`.

```markdown
---
title: Enterprise capture grace is three attempts
type: InvariantContract
status: stable
verification:
  engine: ripgrep
  anchors:
    - path: src/billing/PaymentGateway.ts
      all_of: ["ENTERPRISE", "grace", "= 3"]
      near: "capturePayment"
claims:
  - subject: enterprise_grace_attempts
    literal: "3"
---

Enterprise plans get three capture retries before failure. Shrinking this
window silently breaks the billing contract with customers on that tier.
```

Read the body as why. Follow `verification.anchors` into the source. `claims` freeze checkable literals; if `"3"` disappears from the matched region, validate reports `CLAIM_BROKEN`.

### BusinessWorkflow

Identity: `workflows/checkout-capture` → `.context/workflows/checkout-capture.md`.

```markdown
---
title: Checkout capture flows api → billing → ledger
type: BusinessWorkflow
status: stable
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

One anchor per participating site. The page stays thin: ordering and boundaries, not a dump of every step's construct why.

## Opening a concept

1. **Read the body as why.** The markdown after the frontmatter is the payload: why this decision, invariant, workflow, or guardrail exists.
2. **Note `type`.** RepoCodex authors `TechnicalDecision`, `InvariantContract`, `BusinessWorkflow`, and `GuardrailDecision`. `type` is **author intent** (catalog), not a closed engine enum. The four types are orthogonal: one change may carry more than one when each page is a distinct why. `InvariantContract` is a must-hold **token** contract and requires `claims` — not a general structural invariant. Unknown types are still concepts; they load. Unanchored pages (no `verification`) are valid knowledge; they are not reverse-indexed and do not arm the pin check.
3. **Follow anchors to code.** When the concept pins live text, `verification.anchors` lists paths and distinctive terms. Open those files. `claims` (when present) are checkable literals that must appear in the owning anchor's matched region; absence at validate time is `CLAIM_BROKEN`.
4. **Follow markdown links for related why.** Links between concept files are the graph. Retrieval returns one hop of titles; open a linked body only if the edit might touch that scenario.

`verification.anchors` and `claims` are RepoCodex extensions on the same why document. The memory unit is not `type: Attested Computation`.

For OKF families (`title`, `description`, `tags`, `generated`, `status`, `sources`, and the rest), use the [OKF v0.2 spec](https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/main/SPEC.md).

## `verified` is not a gate stamp

OKF `verified` records definition review against `sources` (a reviewer confirming the *why*). It is optional.

- Missing `verified` does **not** fail CI.
- A passing pin check does **not** write `verified`.

Trust tiers inferred from actor prefixes (`human:…` vs producer/version) also do not affect the required pin check. Liveness is a runtime verdict (`LIVE`, `CLAIM_BROKEN`, `DRIFT`, …), not a field on the concept.

## Next

How agents retrieve and maintain this: [agents.md](agents.md). What the loop is for: [how-it-works.md](how-it-works.md).
