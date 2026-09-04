---
name: repocodex-review
description: Run RepoCodex impact on every PR, verify new concept prose against the diff, and post advisory findings only.
---

# RepoCodex review-agent skill

Findings from this skill post to the **advisory** check only. Never fail the required deterministic check.

## On every PR

1. Run `repocodex validate --diff --base <merge-base>`. Read `impacted_scenarios` (deterministic intent-side walk).

2. **Code-side impact recipe:** grep changed symbols, rank by path proximity and test-file status, read within the cap, respect exclusions. Flag a skipped recipe step.

3. **New concepts:** while the originating diff is in context, verify each new `.context/**/*.md` body's narrative against the diff. Flag mismatches as advisory findings.

4. Flag:
   - unrepaired DRIFT / unapplied RECONCILE
   - why-change without `supersedes` + `rationale`
   - weakenings (claims dropped, grace windows shortened, guardrails loosened)
   - CONTRADICTION (overlapping claims or double `supersedes`)
   - high churn (concept rewritten repeatedly)
   - workflow pages whose multi-package pins were touched without the page being considered
   - `memory-exempt` without review acknowledgment
   - `uncovered_file_without_memory` (and other skipped-memory first-touch misses) — missing pinning concept; advisory only
   - `InvariantContract` missing `claims`
   - contractual token (numeric threshold, plan enum, contract error string) in a `TechnicalDecision` body with no `claims`
   - `GuardrailDecision` whose only anchors are application source, not enforcement config
   - thick single-package page typed as `BusinessWorkflow`
   - multiple new pages for the **same** why
   - new authored-type concepts at `.context/` root (missing `decisions/` / `invariants/` / `workflows/` / `guardrails/` prefix); also note validate `identity_prefix_warnings`

5. Do **not** flag a PR solely because it adds more than one concept type when the bodies are distinct whys. Types are independent and may coexist in one change.

6. Post all of the above to the advisory check. Do not block merge yourself.
