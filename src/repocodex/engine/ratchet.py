from __future__ import annotations

import re
from pathlib import Path

from repocodex.config import RepoConfig
from repocodex.engine.gate import path_excluded
from repocodex.engine.match import _merge_regions, evaluate_file
from repocodex.schema import ConceptDocument
from repocodex.tools.git import run_git


COMMENT_PREFIXES = ("#", "//", "/*", "*", "--", ";", "<!--")
HUNK_HEADER_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")

FIRST_TOUCH_SKIP_BASENAMES = frozenset(
    {
        ".gitignore",
        ".gitattributes",
        ".repocodex.toml",
        ".repocodexignore",
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "npm-shrinkwrap.json",
        "uv.lock",
        "Cargo.lock",
        "poetry.lock",
        "Pipfile.lock",
        "composer.lock",
        "Gemfile.lock",
        "go.sum",
    }
)


def _is_comment_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    return any(stripped.startswith(prefix) for prefix in COMMENT_PREFIXES)


def _lines_are_substantive(removed: list[str], added: list[str]) -> bool:
    content = [*removed, *added]
    if not content:
        return False
    if all(not line.strip() for line in content):
        return False
    if all(_is_comment_line(line) for line in content):
        return False
    if re.findall(r"\S+", "\n".join(removed)) == re.findall(r"\S+", "\n".join(added)):
        return False
    return True


def _untracked_is_substantive(root: Path, path: str) -> bool:
    target = root / path
    if not target.is_file():
        return False
    added = target.read_text(encoding="utf-8", errors="replace").splitlines()
    return _lines_are_substantive([], added)


def is_substantive_change(root: Path, path: str, *, staged: bool = False, base: str | None = None) -> bool:
    args = ["diff", "-U0", "--", path]
    if staged:
        args = ["diff", "-U0", "--cached", "--", path]
    elif base:
        args = ["diff", "-U0", base, "--", path]
    else:
        args = ["diff", "-U0", "HEAD", "--", path]
    diff = run_git(args, cwd=root).stdout
    if "Binary files" in diff:
        return True
    removed = [line[1:] for line in diff.splitlines() if line.startswith("-") and not line.startswith("---")]
    added = [line[1:] for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++")]
    if _lines_are_substantive(removed, added):
        return True
    if not staged and not base:
        in_head = run_git(["cat-file", "-e", f"HEAD:{path}"], cwd=root).returncode == 0
        if not in_head:
            return _untracked_is_substantive(root, path)
    return False


def changed_line_ranges(
    root: Path,
    path: str,
    *,
    staged: bool = False,
    base: str | None = None,
) -> list[tuple[int, int]] | None:
    """Return 0-based inclusive (start, end) ranges for `path`, or None if unattributable."""
    if staged:
        args = ["diff", "-U0", "--cached", "--", path]
    elif base:
        args = ["diff", "-U0", base, "--", path]
    else:
        args = ["diff", "-U0", "HEAD", "--", path]
    result = run_git(args, cwd=root)
    diff = result.stdout
    if "Binary files" in diff:
        return None
    in_head = run_git(["cat-file", "-e", f"HEAD:{path}"], cwd=root).returncode == 0
    if not in_head and not staged and not base:
        target = root / path
        if target.is_file():
            n = max(1, len(target.read_text(encoding="utf-8", errors="replace").splitlines()))
            return [(0, n - 1)]
        return None
    ranges: list[tuple[int, int]] = []
    for line in diff.splitlines():
        match = HUNK_HEADER_RE.match(line)
        if not match:
            continue
        new_start = int(match.group(3))
        new_count = int(match.group(4) if match.group(4) is not None else 1)
        if new_count == 0:
            line0 = max(0, new_start - 1)
            ranges.append((line0, line0))
        else:
            start0 = max(0, new_start - 1)
            ranges.append((start0, start0 + new_count - 1))
    if not ranges:
        return None if diff.strip() else []
    return ranges


def _hunks_inside_regions(ranges: list[tuple[int, int]], regions: list) -> bool:
    for start, end in ranges:
        if not any(region.start <= start and end <= region.end for region in regions):
            return False
    return True


def _matched_regions_for_path(
    path: str,
    concepts: list[ConceptDocument],
    reverse_index: dict[str, list[str]],
    config: RepoConfig,
) -> list | None:
    normalized = path.replace("\\", "/")
    identities = reverse_index.get(path) or reverse_index.get(normalized) or []
    by_id = {doc.identity: doc for doc in concepts}
    regions = []
    for identity in identities:
        doc = by_id.get(identity)
        if not doc:
            continue
        for anchor in doc.anchors:
            if anchor.path not in {path, normalized}:
                continue
            matched = evaluate_file(anchor, config.root, default_scope=config.scope_lines)
            regions.extend(matched.regions)
    if not regions:
        return None
    return _merge_regions(regions, gap=0)


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


def _identities_pinning_path(path: str, concepts: list[ConceptDocument]) -> set[str]:
    normalized = path.replace("\\", "/")
    found: set[str] = set()
    for doc in concepts:
        for pinned in doc.pinned_paths:
            if pinned.replace("\\", "/") in {path, normalized}:
                found.add(doc.identity)
                break
    return found


def _is_memory_path(normalized: str) -> bool:
    # Plugin-managed skill copies live under .repocodex/plugin/, .claude/skills/,
    # and .cursor/skills/.  They are auto-generated artefacts, not source files,
    # so they must not arm first-touch.
    _PLUGIN_PREFIXES = (
        ".context/",
        ".repocodex/",
        ".claude/skills/",
        ".cursor/skills/",
    )
    return (
        any(normalized.startswith(p) for p in _PLUGIN_PREFIXES)
        or any(f"/{p}" in f"/{normalized}" for p in _PLUGIN_PREFIXES)
        or normalized.endswith("reverse-index.md")
    )


def skipped_memory(
    changed_files: list[str],
    concepts: list[ConceptDocument],
    reverse_index: dict[str, list[str]],
    config: RepoConfig,
    *,
    posture: str,
    staged: bool = False,
    base: str | None = None,
) -> list[dict]:
    del posture  # first-touch applies in every posture
    covered = {path for path, ids in reverse_index.items() if ids}
    pinning_updated = _concept_identities_from_paths(changed_files, concepts)
    flags: list[dict] = []
    for path in changed_files:
        normalized = path.replace("\\", "/")
        if _is_memory_path(normalized):
            continue
        has_memory = path in covered or normalized in covered
        if not has_memory:
            if path_excluded(path, config) or Path(normalized).name in FIRST_TOUCH_SKIP_BASENAMES:
                continue
            if not is_substantive_change(config.root, path, staged=staged, base=base):
                continue
            pinning = _identities_pinning_path(path, concepts)
            if pinning & pinning_updated:
                continue
            flags.append(
                {
                    "path": path,
                    "reason": "uncovered_file_without_memory",
                }
            )
            continue
        if not is_substantive_change(config.root, path, staged=staged, base=base):
            continue
        pinning = set(reverse_index.get(path, []) or reverse_index.get(normalized, []))
        pinning |= _identities_pinning_path(path, concepts)
        if pinning & pinning_updated:
            continue
        ranges = changed_line_ranges(config.root, path, staged=staged, base=base)
        regions = _matched_regions_for_path(path, concepts, reverse_index, config)
        if ranges is None or regions is None or not _hunks_inside_regions(ranges, regions):
            flags.append(
                {
                    "path": path,
                    "reason": "covered_file_without_memory_update",
                    "concepts": sorted(pinning),
                }
            )
    return flags
