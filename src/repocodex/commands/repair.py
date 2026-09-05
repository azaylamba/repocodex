"""Invoke an agent harness to repair drifted anchors after validate."""

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

# Cursor owns the skill loop; Claude has CLAUDE.md/plugin; Codex is last-resort.
HARNESS_ORDER = ("cursor", "claude", "codex")


def _available_harness() -> str | None:
    """Return the first repair CLI found on PATH."""
    for binary in HARNESS_ORDER:
        if shutil.which(binary):
            return binary
    return None


def _invoke_argv(harness: str, prompt: str) -> list[str] | None:
    """Return the argv that delivers ``prompt`` to a known harness."""
    if harness == "claude":
        return ["claude", "-p", prompt]
    if harness == "codex":
        return ["codex", "exec", prompt]
    if harness == "cursor":
        return ["cursor", "agent", "--print", prompt]
    return None


def repair(repo: Path, *, invoke_agent: bool = True) -> dict:
    """Run validate, then invoke the first available harness with a repair prompt.

    Does not re-validate after the agent. ``invoke_agent`` false, or no CLI on
    PATH, yields ``no_agent_harness``. A known binary with no argv mapping
    yields ``undeliverable_harness``. Spawn or non-zero exit yields
    ``harness_invocation_failed``.

    Returns:
        Envelope with ``verdict``, ``lost``, ``candidates``, ``prompt``,
        ``ok``, ``invoked``, and on failure ``error`` plus optional
        ``agent``, ``reason``, ``invocation_error``, or ``returncode``.

    """
    verdict = validate(repo)
    prompt = REPAIR_PROMPT.strip()
    lost = verdict.get("lost", [])
    candidates = verdict.get("candidates", [])
    harness = _available_harness() if invoke_agent else None
    if not harness:
        return envelope(
            {
                "error": "no_agent_harness",
                "verdict": verdict.get("result"),
                "lost": lost,
                "candidates": candidates,
                "prompt": prompt,
                "ok": False,
                "invoked": False,
            }
        )
    argv = _invoke_argv(harness, prompt)
    if argv is None:
        return envelope(
            {
                "error": "undeliverable_harness",
                "reason": "undeliverable_harness",
                "agent": harness,
                "verdict": verdict.get("result"),
                "lost": lost,
                "candidates": candidates,
                "prompt": prompt,
                "ok": False,
                "invoked": False,
            }
        )
    try:
        completed = subprocess.run(
            argv,
            cwd=str(repo),
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        return envelope(
            {
                "error": "harness_invocation_failed",
                "invocation_error": str(exc),
                "agent": harness,
                "verdict": verdict.get("result"),
                "lost": lost,
                "candidates": candidates,
                "prompt": prompt,
                "ok": False,
                "invoked": False,
            }
        )
    invoked = completed.returncode == 0
    payload = {
        "verdict": verdict.get("result"),
        "agent": harness,
        "invoked": invoked,
        "lost": lost,
        "candidates": candidates,
        "prompt": prompt,
        "ok": invoked,
    }
    if not invoked:
        payload["ok"] = False
        payload["error"] = "harness_invocation_failed"
        payload["returncode"] = completed.returncode
    return envelope(payload)
