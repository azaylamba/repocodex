# Design: align-okf-v02-conventions

## Context

OKF v0.2 is a directory of markdown with YAML frontmatter. It standardizes a small set of fields (type, provenance, trust, lifecycle, links, indexes, logs) and one optional computation type. It does not define InvariantContract, anchors, or a required CI check.

RepoCodex’s product is: the why of code lives in that directory; agents retrieve it and read the code it points at; new work updates the why in the same change; a deterministic engine attests that the why is still pinned to live text. That loop must survive this change.

Today the store uses OKF *shape* with a private profile: extra reserved file, string `sources`, `agent:` actors, `format_version`, default `draft`, closed type enum, skip-without-anchors, and `verified` stamped on every gate pass.

## Goals / Non-Goals

**Goals:**

- Make `.context/` a bundle a v0.2 consumer can parse without RepoCodex.
- Keep writing and validating pinning concepts as one file per why, with anchors as extra keys.
- Keep the required check a pin check. Do not store attest receipts as `verified`.

**Non-Goals:**

- Adopting `type: Attested Computation` as the memory unit (executor/receipt/runtime for SQL-style computations). That is the wrong grain: it splits why from pin and adds a file per check.
- Implementing OKF’s deferred attester ABI, receipt wire format, or Skills packaging.
- Changing CLAIM_BROKEN, owned claims, ratchet scoping, or the agent-read scenario loop.
- Requiring humans to author or verify concepts.

## Decisions

### Anchors stay on the why document

OKF allows unknown keys. `verification` and `claims` remain producer extensions on the same concept that holds the prose. Optional `resource` may name a primary path for generic readers. The pin check continues to use anchors.

*Alternative considered:* one Attested Computation per invariant, narrative concept links to it. Rejected: two files per why, agents must keep them in sync, and “computation/runtime/parameters” does not describe ripgrep-over-source. OKF’s attester *pattern* (deterministic, consumer-side, result not stored) is already our validate run.

### Reverse index leaves the bundle

OKF reserves only `index.md` and `log.md`. A generated `reverse-index.md` inside `.context/` is either an illegal concept (no `type`) or a fake reserved name. Write it beside metrics, e.g. `.repocodex/reverse-index.md` (per shard: `.repocodex/reverse-index/<escaped-context-root>.md` or one file per `.context` sibling path). Validate and context keep using it. CI sync check follows the new path.

*Alternative considered:* make reverse-index a concept `type: ReverseIndex`. Rejected: it is a derived artifact, not knowledge; agents should not retrieve it as why.

### `verified` is never a gate side effect

Write and reanchor stop assigning `verified`. Validate remains read-only. If we need a machine signal that a pin was last attested, it belongs in the verdict or metrics, not in OKF trust fields.

### Parser becomes permissive; gate stays strict for pins

Load every `.md` with a `type` except reserved names. Unknown types are strings, not enum failures. Concepts without anchors are first-class for retrieval and links. `repocodex write` of a concept that *declares* anchors still must pass the gate. A write with no anchors is allowed only for types that are not claiming to pin code; it does not enter the reverse index and does not arm the ratchet.

Default `status` when omitted: `stable`. Bootstrap still sets `draft` + `stale_after` explicitly.

### Sources and actors are rewritten at the boundary

On write, a string source becomes `{ resource: <that string> }` if it already looks like a URI or path; `commit:<sha>` becomes `{ resource: git://commit/<sha>, title: commit }` or a repo-relative `resource` plus `id`. Do not keep dual on-disk forms. Actors: map legacy `agent:cursor/grok-4.6` → `cursor/grok-4.6` on read for compatibility; new writes never emit `agent:`.

### Version key

Root index frontmatter: only `okf_version: "0.2"`. Engine schema version stays in `.repocodex.toml` / CLI envelope (`engine_version`), not in the OKF index.

## Risks / Trade-offs

- **Unanchored pages can accumulate without pin checks.** → Intended: they are knowledge. The ratchet still fires when a *covered* (pinned) file changes. Skills still tell the agent to write anchors when the page is about live code.
- **External OKF tools still will not understand `verification.anchors`.** → They will ignore extra keys and still see title, body, links, sources. That is enough for interchange of *why*. Pin semantics stay RepoCodex-specific, which is producer policy OKF allows.
- **Moving the reverse index breaks old CI caches.** → One-time path change; install/Action look at the new location.
- **Existing fixtures use `agent:` and string sources.** → Compatibility read + rewrite on next write; tests updated in this change.

## Migration Plan

1. Schema and parser (permissive types, sources objects, status default, okf_version).
2. Stop stamping `verified` on write/reanchor.
3. Relocate reverse index; update validate sync and install docs.
4. Catalog/log format; bootstrap sources objects; actor emission.
5. Rewrite fixtures and architecture §5 examples. Do not require bundle rewrites in customer repos until their next write, except reverse-index path which CI will flag as desync until regenerated.

**Rollback:** revert the change; leave customer `.context/` bodies intact (anchors unchanged). Restore reverse-index path if needed.

## Open Questions

- Exact on-disk path for a sharded reverse index (single file with prefixes vs one file per `.context` root).
- Whether `repocodex write` of a no-anchor Playbook should be a supported CLI path in this change or only load/retrieve.
