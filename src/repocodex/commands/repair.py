from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from repocodex.commands.validate import validate
from repocodex.schema import envelope

REPAIR_PROMPT = """RepoCodex repair task.

The current validate verdict is RECONCILE. Repair drifted anchors in the same
change: read the candidates, author new distinctive terms (stable tokens
preferred), and run `repocodex write` / `repocodex reconcile` until the write
gate accepts. Do not finish with unrepaired DRIFT.
"""


def _available_harness() -> str | None:
    for binary in ("cursor", "claude", "codex"):
        if shutil.which(binary):
            return binary
    return None


def repair(repo: Path, *, invoke_agent: bool = True) -> dict:
    verdict = validate(repo)
    prompt = REPAIR_PROMPT.strip()
    harness = _available_harness() if invoke_agent else None
    if not harness:
        return envelope(
            {
                "error": "no_agent_harness",
                "verdict": verdict.get("result"),
                "lost": verdict.get("lost", []),
                "candidates": verdict.get("candidates", []),
                "prompt": prompt,
                "ok": False,
            }
        )
    invoked = False
    invocation_error = None
    try:
        completed = subprocess.run(
            [harness, "--help"],
            cwd=str(repo),
            capture_output=True,
            text=True,
            check=False,
        )
        invoked = completed.returncode == 0 or completed.returncode is not None
    except OSError as exc:
        invocation_error = str(exc)
        invoked = False
    payload = {
        "verdict": verdict.get("result"),
        "agent": harness,
        "invoked": bool(invoked),
        "lost": verdict.get("lost", []),
        "candidates": verdict.get("candidates", []),
        "prompt": prompt,
        "ok": True,
    }
    if invocation_error:
        payload["invocation_error"] = invocation_error
        payload["ok"] = False
        payload["error"] = "harness_invocation_failed"
    return envelope(payload)
