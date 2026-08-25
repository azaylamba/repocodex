from __future__ import annotations

from pathlib import Path

from repocodex.config import RepoConfig
from repocodex.engine.match import compile_term
from repocodex.schema import ConceptDocument
from repocodex.tools.git import run_git


def _diff_text(root: Path, base: str | None, staged: bool) -> str:
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
    touched = set(changed_files)
    diff = _diff_text(config.root, base, staged)
    added_lines = [
        line[1:] for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++")
    ]
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
