from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

PAYMENT_GATEWAY = '''\
export async function capturePayment(account: Account): Promise<void> {
  if (account.plan === "ENTERPRISE") {
    const grace = 3;
    if (account.consecutiveFailures < grace) {
      return scheduleRetry(account);
    }
  }
  await charge(account);
}
'''

STREAMER = '''\
class CustomDataStreamer:
    def iter_batches(self, source):
        for chunk in source:
            parsed = parse_xml(chunk)
            yield parsed.rows
'''

GRACE_CONCEPT = '''\
---
type: InvariantContract
title: Enterprise accounts get a 3-cycle grace period
tags: [billing, enterprise]
generated: { by: agent:claude-code/opus, at: 2026-08-25T12:10:00Z }
verified: { by: process:repocodex-rg, at: 2026-08-25T12:10:01Z }
status: stable
claims:
  - literal: "3"
  - literal: "ENTERPRISE"
verification:
  engine: ripgrep
  anchors:
    - path: src/billing/PaymentGateway.ts
      all_of: ["ENTERPRISE", "grace", "= 3"]
      near: "capturePayment"
---

Enterprise customers were churning when a single failed payment suspended
their account mid-quarter. Sales committed to a three-billing-cycle grace
window in enterprise contracts (2025 renewal terms), so suspension logic
must not run until the fourth consecutive failure. Changing the window is
a business-rule change: supersede this concept, do not silently edit the
code. Related: [dunning email schedule](./dunning-schedule.md).
'''

STREAMER_CONCEPT = '''\
---
type: TechnicalDecision
title: Custom data streamer must not become a list comprehension
description: Generators leaked the unparsed XML tree during batch ingestion.
tags: [ingestion, memory]
generated: { by: agent:cursor/grok-4.6, at: 2026-08-25T12:00:00Z }
verified: { by: process:repocodex-rg, at: 2026-08-25T12:00:01Z }
status: stable
verification:
  engine: ripgrep
  anchors:
    - path: src/core/streams/CustomDataStreamer.py
      all_of: ["yield", "iter_batches"]
      near: "def iter_batches"
      scope_lines: 40
---

Do not optimize `iter_batches` into a list comprehension. Standard generators
held references to the unparsed XML tree and leaked memory during batch
ingestion (incident 2025-11, see sources).
'''

WORKFLOW_CONCEPT = '''\
---
type: BusinessWorkflow
title: Checkout capture spans billing ledger and notify
tags: [checkout]
generated: { by: agent:test, at: 2026-08-25T12:00:00Z }
verified: { by: process:repocodex-rg, at: 2026-08-25T12:00:01Z }
status: stable
verification:
  engine: ripgrep
  anchors:
    - path: src/billing/PaymentGateway.ts
      all_of: ["ENTERPRISE", "capturePayment"]
    - path: src/ledger/posting.py
      all_of: ["post_capture", "LEDGER_CAPTURE"]
    - path: src/notify/emailer.py
      all_of: ["send_receipt", "RECEIPT_TEMPLATE"]
---

Capture must post to the ledger before the receipt is sent.
Related: [enterprise grace](../invariants/enterprise-grace-period.md).
'''

CLAIMED_WORKFLOW_CONCEPT = '''\
---
type: BusinessWorkflow
title: Checkout capture spans billing ledger and notify
tags: [checkout]
generated: { by: agent:test, at: 2026-08-25T12:00:00Z }
verified: { by: process:repocodex-rg, at: 2026-08-25T12:00:01Z }
status: stable
claims:
  - literal: "CHECKOUT_HOLD"
    subject: hold_token
    anchor: 0
verification:
  engine: ripgrep
  anchors:
    - path: src/billing/checkout_hold.ts
      all_of: ["CHECKOUT_HOLD", "billCheckout"]
    - path: src/ledger/posting.py
      all_of: ["post_capture", "LEDGER_CAPTURE"]
    - path: src/notify/emailer.py
      all_of: ["send_receipt", "RECEIPT_TEMPLATE"]
---

Capture must post to the ledger before the receipt is sent.
'''

CHECKOUT_HOLD_SOURCE = '''\
export function billCheckout() {
  const CHECKOUT_HOLD = "CHECKOUT_HOLD";
}
'''

GUARDRAIL_CONCEPT = '''\
---
type: GuardrailDecision
title: Domain must not import infrastructure
tags: [architecture]
generated: { by: agent:test, at: 2026-08-25T12:00:00Z }
verified: { by: process:repocodex-rg, at: 2026-08-25T12:00:01Z }
status: stable
verification:
  engine: ripgrep
  anchors:
    - path: .importlinter
      all_of: ["domain", "infrastructure", "forbidden"]
---

Keep domain independent of infrastructure adapters.
'''

ROOT_INDEX = '''\
---
format_version: "1.0"
---

# Context catalog
'''

DEFAULT_CONFIG = '''\
engine_version = "1.0.0"
posture = "ratchet"
distinctiveness_ceiling = 200
scope_lines = 40
exclusions = ["vendor/**", "node_modules/**", "dist/**"]
'''


@dataclass
class SampleRepo:
    root: Path
    payment_gateway: Path
    streamer: Path


def init_git_repo(root: Path) -> None:
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)


def write_architecture_fixtures(root: Path) -> SampleRepo:
    billing = root / "src" / "billing"
    streams = root / "src" / "core" / "streams"
    ledger = root / "src" / "ledger"
    notify = root / "src" / "notify"
    for path in (billing, streams, ledger, notify):
        path.mkdir(parents=True, exist_ok=True)

    payment = billing / "PaymentGateway.ts"
    streamer = streams / "CustomDataStreamer.py"
    payment.write_text(PAYMENT_GATEWAY, encoding="utf-8")
    streamer.write_text(STREAMER, encoding="utf-8")
    (ledger / "posting.py").write_text(
        'LEDGER_CAPTURE = "capture"\n\ndef post_capture(event):\n    return event\n',
        encoding="utf-8",
    )
    (notify / "emailer.py").write_text(
        'RECEIPT_TEMPLATE = "receipt"\n\ndef send_receipt(order):\n    return order\n',
        encoding="utf-8",
    )
    (root / ".importlinter").write_text(
        "[forbidden]\nsource = domain\nforbidden = infrastructure\n",
        encoding="utf-8",
    )

    context = root / ".context"
    (context / "invariants").mkdir(parents=True)
    (context / "decisions").mkdir()
    (context / "workflows").mkdir()
    (context / "invariants" / "enterprise-grace-period.md").write_text(
        GRACE_CONCEPT, encoding="utf-8"
    )
    (context / "decisions" / "custom-data-streamer.md").write_text(
        STREAMER_CONCEPT, encoding="utf-8"
    )
    (context / "workflows" / "checkout-capture.md").write_text(
        WORKFLOW_CONCEPT, encoding="utf-8"
    )
    (context / "decisions" / "layering-no-domain-to-infra.md").write_text(
        GUARDRAIL_CONCEPT, encoding="utf-8"
    )
    (context / "index.md").write_text(ROOT_INDEX, encoding="utf-8")
    (context / "log.md").write_text("# log\n", encoding="utf-8")
    (context / "invariants" / "index.md").write_text(
        "# Invariants\n\n- [enterprise grace](./enterprise-grace-period.md)\n",
        encoding="utf-8",
    )
    (context / "decisions" / "index.md").write_text(
        "# Decisions\n\n- [streamer](./custom-data-streamer.md)\n",
        encoding="utf-8",
    )
    (context / "workflows" / "index.md").write_text(
        "# Workflows\n\n- [checkout](./checkout-capture.md)\n",
        encoding="utf-8",
    )

    (root / ".repocodex.toml").write_text(DEFAULT_CONFIG, encoding="utf-8")
    (root / ".repocodexignore").write_text("generated/**\n", encoding="utf-8")
    (root / ".gitignore").write_text(".repocodex/metrics.jsonl\n", encoding="utf-8")

    from repocodex.store.reverse_index import regenerate_all

    regenerate_all(root)
    return SampleRepo(root=root, payment_gateway=payment, streamer=streamer)


def write_claimed_workflow(root: Path, *, commit: bool = False) -> Path:
    billing = root / "src" / "billing" / "checkout_hold.ts"
    billing.parent.mkdir(parents=True, exist_ok=True)
    billing.write_text(CHECKOUT_HOLD_SOURCE, encoding="utf-8")
    path = root / ".context" / "workflows" / "checkout-hold.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(CLAIMED_WORKFLOW_CONCEPT, encoding="utf-8")
    from repocodex.store.reverse_index import regenerate_all

    regenerate_all(root)
    if commit:
        subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "claimed workflow", "--no-verify"],
            cwd=root,
            check=True,
            capture_output=True,
        )
    return path
