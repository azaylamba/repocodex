from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from repocodex.config import load_config
from repocodex.engine.gate import evaluate_write
from repocodex.schema import (
    Anchor,
    ConceptDocument,
    ConceptFrontmatter,
    ConceptStatus,
    ConceptType,
    Verification,
    envelope,
)
from repocodex.store.bundle import write_concept
from repocodex.store.reverse_index import regenerate_all
from repocodex.tools.git import run_git

WHY_COMMENT = re.compile(r"(?://|#|/\*)\s*why:\s*(.+)")


def _stale_after(days: int = 30) -> str:
    when = datetime.now(timezone.utc) + timedelta(days=days)
    return when.date().isoformat()


def bootstrap(repo: Path) -> dict:
    config = load_config(repo)
    kept: list[str] = []
    rejected: list[dict] = []
    sources_commits = run_git(["log", "--pretty=%H %s", "-n", "50"], cwd=repo).stdout.splitlines()
    SKIP = {".git", ".context", ".cursor", ".claude", ".repocodex", "node_modules", "plugin", "hooks"}
    comments: list[tuple[str, str]] = []
    for path in repo.rglob("*"):
        if not path.is_file() or any(part in SKIP for part in path.parts):
            continue
        if path.suffix not in {".py", ".ts", ".js", ".go", ".rs", ".java", ".md"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        rel = str(path.relative_to(repo)).replace("\\", "/")
        for match in WHY_COMMENT.finditer(text):
            comments.append((rel, match.group(1).strip()))

    candidates: list[tuple[str, str, list[str]]] = []
    for rel, note in comments:
        terms = [part for part in re.findall(r"[A-Za-z_][A-Za-z0-9_]{3,}", note)][:3]
        if terms:
            candidates.append((rel, note, terms))

    for rel, note, terms in candidates:
        identity = f"bootstrap/{Path(rel).stem}-{abs(hash(note)) % 10_000}"
        doc = ConceptDocument(
            identity=identity,
            frontmatter=ConceptFrontmatter(
                type=ConceptType.TechnicalDecision,
                title=note[:80],
                status=ConceptStatus.draft,
                stale_after=_stale_after(),
                sources=[line.split(" ", 1)[0] for line in sources_commits[:3] if line] or ["git-history"],
                verification=Verification(
                    engine="ripgrep",
                    anchors=[Anchor(path=rel, all_of=terms)],
                ),
            ),
            body=f"Bootstrapped from comment in `{rel}`.\n\n{note}\n",
        )
        gate = evaluate_write(doc, config)
        if not gate.accepted:
            rejected.append({"identity": identity, "tighten": gate.tighten})
            continue
        write_concept(repo, doc)
        kept.append(identity)

    if kept:
        regenerate_all(repo)
    return envelope({"kept": kept, "rejected": rejected, "status": "draft"})
