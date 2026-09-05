"""Warn when a change copies a stable concept's distinctive terms onto a new path."""

from __future__ import annotations

from pathlib import Path

from repocodex.config import RepoConfig
from repocodex.engine.match import compile_term
from repocodex.schema import ConceptDocument
from repocodex.tools.git import run_git


def _diff_text(root: Path, base: str | None, staged: bool) -> str:
    """Return a unified diff with zero context for the requested tree."""
    args = ["diff", "-U0"]
    if staged:
        args.append("--cached")
    elif base:
        args.append(base)
    return run_git(args, cwd=root).stdout


def dilution_warnings(
    concepts: list[ConceptDocument],
    changed_files: list[str],
    config: RepoConfig,
    *,
    base: str | None = None,
    staged: bool = False,
) -> list[dict]:
    """Warn when added lines nearly reproduce a stable concept's unused-path terms.

    Concepts whose pinned paths are in ``changed_files`` are skipped. The
    concept stays LIVE; this is advisory only.

    Returns:
        Dicts with ``concept``, ``path``, ``duplicate_terms``, and ``message``.
    """
    touched = set(changed_files)
    diff = _diff_text(config.root, base, staged)
    added_lines = [
        line[1:] for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++")
    ]
    for path in changed_files:
        target = config.root / path
        if not target.is_file():
            continue
        normalized_path = path.replace("\\", "/")
        if f"b/{path}" not in diff and f"b/{normalized_path}" not in diff:
            added_lines.extend(target.read_text(encoding="utf-8", errors="replace").splitlines())
    added = "\n".join(added_lines)
    warnings: list[dict] = []
    for doc in concepts:
        if doc.status.value != "stable":
            continue
        if any(path in touched for path in doc.pinned_paths):
            continue
        for anchor in doc.anchors:
            hits = [term for term in anchor.all_of if compile_term(term).search(added)]
            if len(hits) >= max(1, len(anchor.all_of) - 1) and hits:
                warnings.append(
                    {
                        "concept": doc.identity,
                        "path": anchor.path,
                        "duplicate_terms": hits,
                        "message": "term dilution introduced by this change; concept stays LIVE",
                    }
                )
    return warnings
