from __future__ import annotations

import shutil
from pathlib import Path

from repocodex.commands.validate import validate
from repocodex.schema import envelope, utc_now
from repocodex.store.bundle import append_log, discover_context_roots


REPAIR_PROMPT = """RepoCodex repair task.

The current validate verdict is RECONCILE. Repair drifted anchors in the same
change: read the candidates, author new distinctive terms (stable tokens
preferred), and run `repocodex write` / `repocodex reconcile` until the write
gate accepts. Do not finish with unrepaired DRIFT.
"""


def repair(repo: Path, *, invoke_agent: bool = True) -> dict:
    verdict = validate(repo)
    roots = discover_context_roots(repo)
    root = roots[0] if roots else repo / ".context"
    root.mkdir(parents=True, exist_ok=True)
    task_dir = root / "repair-tasks"
    task_dir.mkdir(exist_ok=True)
    task_path = task_dir / f"repair-{utc_now().replace(':', '')}.md"
    task_path.write_text(
        REPAIR_PROMPT + "\n\n```json\n" + __import__("json").dumps(verdict, indent=2) + "\n```\n",
        encoding="utf-8",
    )
    append_log(root, f"repair task filed {task_path.name}")
    invoked = None
    if invoke_agent:
        for binary in ("cursor", "claude", "codex"):
            if shutil.which(binary):
                invoked = binary
                break
    return envelope(
        {
            "verdict": verdict.get("result"),
            "task": str(task_path.relative_to(repo)),
            "agent": invoked,
            "lost": verdict.get("lost", []),
            "candidates": verdict.get("candidates", []),
            "prompt": REPAIR_PROMPT.strip(),
        }
    )
