from __future__ import annotations

from pathlib import Path

from repocodex.config import RepoConfig
from repocodex.schema import ConceptDocument
from repocodex.tools.git import run_git


SUBSTANTIVE_PREFIXES = ("+", "-")


def _is_agent_commit(root: Path) -> bool:
    msg = run_git(["log", "-1", "--pretty=%B"], cwd=root).stdout.lower()
    generated = run_git(["log", "-1", "--pretty=%s%n%b"], cwd=root).stdout.lower()
    markers = ("generated-by:", "agent:", "cursor:", "claude", "codex")
    return any(marker in generated for marker in markers) or "generated.by" in msg


def skipped_memory(
    changed_files: list[str],
    concepts: list[ConceptDocument],
    reverse_index: dict[str, list[str]],
    config: RepoConfig,
    *,
    context_touched: bool,
    posture: str,
) -> list[dict]:
    if posture == "shadow":
        return []
    covered = {path for path, ids in reverse_index.items() if ids}
    flags: list[dict] = []
    for path in changed_files:
        if path.startswith(".context/") or path.endswith("reverse-index.md"):
            continue
        has_memory = path in covered
        if not has_memory:
            if posture == "full" and _is_agent_commit(config.root):
                flags.append(
                    {
                        "path": path,
                        "reason": "uncovered_agent_commit",
                    }
                )
            continue
        if not context_touched:
            flags.append(
                {
                    "path": path,
                    "reason": "covered_file_without_memory_update",
                    "concepts": reverse_index.get(path, []),
                }
            )
    return flags
