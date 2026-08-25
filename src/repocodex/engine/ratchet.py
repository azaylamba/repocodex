from __future__ import annotations

import re
from pathlib import Path

from repocodex.config import RepoConfig
from repocodex.schema import ConceptDocument
from repocodex.tools.git import run_git


SUBSTANTIVE_PREFIXES = ("+", "-")
COMMENT_PREFIXES = ("#", "//", "/*", "*", "--", ";", "<!--")
AGENT_AUTHOR_MARKERS = (
    "cursoragent@",
    "noreply@cursor",
    "claude@",
    "github-actions[bot]",
    "copilot@",
)
AGENT_TRAILER_KEYS = ("generated-by:", "co-authored-by:")
AGENT_TRAILER_VALUES = ("agent:", "cursor", "claude", "codex", "copilot")


def _is_agent_commit(root: Path) -> bool:
    author = run_git(["log", "-1", "--pretty=%ae"], cwd=root).stdout.strip().lower()
    if any(marker in author for marker in AGENT_AUTHOR_MARKERS):
        return True
    msg = run_git(["log", "-1", "--pretty=%B"], cwd=root).stdout
    for line in msg.splitlines():
        lower = line.strip().lower()
        if any(lower.startswith(key) for key in AGENT_TRAILER_KEYS):
            if any(value in lower for value in AGENT_TRAILER_VALUES):
                return True
    return False


def _is_comment_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    return any(stripped.startswith(prefix) for prefix in COMMENT_PREFIXES)


def is_substantive_change(root: Path, path: str, *, staged: bool = False, base: str | None = None) -> bool:
    args = ["diff", "-U0", "--", path]
    if staged:
        args = ["diff", "-U0", "--cached", "--", path]
    elif base:
        args = ["diff", "-U0", base, "--", path]
    diff = run_git(args, cwd=root).stdout
    content: list[str] = []
    for line in diff.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith(SUBSTANTIVE_PREFIXES):
            content.append(line[1:])
    if not content:
        return False
    if all(not line.strip() for line in content):
        return False
    if all(_is_comment_line(line) for line in content):
        return False
    removed = [line[1:] for line in diff.splitlines() if line.startswith("-") and not line.startswith("---")]
    added = [line[1:] for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++")]
    if re.findall(r"\S+", "\n".join(removed)) == re.findall(r"\S+", "\n".join(added)):
        return False
    return True


def _concept_identities_from_paths(paths: list[str], concepts: list[ConceptDocument]) -> set[str]:
    changed: set[str] = set()
    by_id = {doc.identity: doc for doc in concepts}
    for path in paths:
        normalized = path.replace("\\", "/")
        if "/.context/" not in f"/{normalized}" and not normalized.startswith(".context/"):
            continue
        if Path(normalized).name in {"index.md", "log.md", "reverse-index.md"}:
            continue
        stem = Path(normalized).stem
        # identity is path relative to .context without .md
        marker = ".context/"
        idx = normalized.find(marker)
        if idx >= 0:
            identity = normalized[idx + len(marker) :]
            if identity.endswith(".md"):
                identity = identity[: -len(".md")]
            if identity in by_id:
                changed.add(identity)
                continue
        for identity in by_id:
            if identity.endswith(stem) or identity.rsplit("/", 1)[-1] == stem:
                changed.add(identity)
    return changed


def skipped_memory(
    changed_files: list[str],
    concepts: list[ConceptDocument],
    reverse_index: dict[str, list[str]],
    config: RepoConfig,
    *,
    attested_identities: set[str] | None = None,
    posture: str,
    staged: bool = False,
    base: str | None = None,
) -> list[dict]:
    covered = {path for path, ids in reverse_index.items() if ids}
    pinning_updated = _concept_identities_from_paths(changed_files, concepts)
    attested = attested_identities or set()
    flags: list[dict] = []
    for path in changed_files:
        normalized = path.replace("\\", "/")
        if normalized.startswith(".context/") or normalized.endswith("reverse-index.md") or "/.context/" in normalized:
            continue
        has_memory = path in covered or normalized in covered
        if not has_memory:
            if posture == "full" and _is_agent_commit(config.root):
                flags.append(
                    {
                        "path": path,
                        "reason": "uncovered_agent_commit",
                    }
                )
            continue
        if not is_substantive_change(config.root, path, staged=staged, base=base):
            continue
        pinning = set(reverse_index.get(path, []) or reverse_index.get(normalized, []))
        if pinning & pinning_updated or pinning & attested:
            continue
        flags.append(
            {
                "path": path,
                "reason": "covered_file_without_memory_update",
                "concepts": sorted(pinning),
            }
        )
    return flags
