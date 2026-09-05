# How RepoCodex works

Coding agents write syntax well and forget *why*. Comments rot. Instruction files (`AGENTS.md`, `CLAUDE.md`, Cursor rules) sit beside the repo and never prove they still describe live text. Tests check behavior the author remembered to assert; they do not keep institutional why attached to the lines that implement it.

RepoCodex stores that why in an [OKF](https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/main/SPEC.md) v0.2 bundle at `.context/`, next to the code, in git. Distinctive textual anchors pin each record to live source. A thin CLI over ripgrep and git attests those pins. The benefit: why cannot silently detach. Instruction files and test suites do not give that guarantee.

## A concrete turn

Suppose `.context/invariants/enterprise-grace.md` pins `src/billing/PaymentGateway.ts` with terms `ENTERPRISE`, `grace`, and `= 3`, plus a claim that the grace literal is `"3"`.

1. **Retrieve.** `repocodex context src/billing/PaymentGateway.ts` returns that concept. Read the body, then open the pinned file at the anchors.
2. **Edit.** An agent changes grace from `3` to `1` without updating memory.
3. **Pin-check.** `repocodex validate --diff` reports `CLAIM_BROKEN` (literal `"3"` gone from the matched region). Hook and required CI deny until the turn repairs: restore the code, or write a superseding concept with `rationale`.

Same file, uncovered path: if `context` returned nothing and the edit is substantive, validate reports `WRITE` with non-empty `skipped_memory`. `LIVE` is not success while that list is populated — write a pinning concept in the same change, then re-validate.

## The loop

A change to a pinned file is one turn:

1. **Retrieve why.** `repocodex context <paths>` (or the equivalent skill). Read the returned concept bodies.
2. **Read the pinned code.** Follow the anchors. Related pages come back as titles; open a body only if the edit might touch that scenario.
3. **Edit.** Keep the recorded why intact unless you intend a why-change.
4. **Update why** in the same change if intent changed (`repocodex write`, with `supersedes` + `rationale` on a why-change). If `repocodex context` returned no concepts for the files you edited, you still write a pinning concept after a substantive edit — empty context is not a free pass.
5. **Pin-check.** `repocodex validate --diff`. The required check attests that anchors, claims, the skipped-memory ratchet, and the reverse index still match live text. `LIVE` is not success while `skipped_memory` is non-empty (`result` is `WRITE`); write the pinning concept and re-validate.

That loop *is* the product. Scenario integrity is the agent reading OKF then the pinned code — not a pytest suite, not a scenario-to-test table, and not a human reviewing every concept.

Skipping retrieval does not make the change invisible. Hook and CI still fail later on `CLAIM_BROKEN`, unrepaired `DRIFT`, or skipped-memory (covered-file maintenance or first-touch of an uncovered file).

## What the required check is not

The required check (pre-commit hook and the deterministic GitHub Action) attests pins. It does not run the application test suite. Application tests may still exist; they are not how RepoCodex decides that existing scenarios still hold.

## Next

- How to read a concept: [memory.md](memory.md)
- How agents (and optionally humans) run the loop: [agents.md](agents.md)
- Install, pin, hook, CI, optional MCP: [install.md](install.md)

Current engine architecture (further reading): [architecture.md](architecture.md). You do not need it to understand purpose, benefit, or the loop.
