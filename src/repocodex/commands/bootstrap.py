from __future__ import annotations

import hashlib
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
    Source,
    Verification,
    envelope,
)
from repocodex.store.bundle import write_concept
from repocodex.store.reverse_index import regenerate_all
from repocodex.tools.git import git_ls_files, run_git

WHY_COMMENT = re.compile(r"(?://|#|/\*)\s*why:\s*(.+)")
DOC_WHY = re.compile(r"(?i)^(?:why|decision|invariant)\s*[:\-]\s*(.+)$")


def _stale_after(days: int = 30) -> str:
    when = datetime.now(timezone.utc) + timedelta(days=days)
    return when.date().isoformat()


def _stable_id(rel: str, note: str) -> str:
    digest = hashlib.sha256(f"{rel}\n{note}".encode("utf-8")).hexdigest()[:12]
    return f"bootstrap/{Path(rel).stem}-{digest}"


def _commit_for(repo: Path, rel: str) -> str | None:
    result = run_git(["log", "-n", "1", "--pretty=%H", "--", rel], cwd=repo)
    sha = result.stdout.strip()
    return sha or None


def _candidates_from_comments(repo: Path, files: list[str]) -> list[tuple[str, str, list[str], str | None]]:
    SKIP_SUFFIX = {".py", ".ts", ".js", ".go", ".rs", ".java", ".md"}
    found: list[tuple[str, str, list[str], str | None]] = []
    for rel in files:
        if Path(rel).suffix not in SKIP_SUFFIX:
            continue
        path = repo / rel
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for match in WHY_COMMENT.finditer(text):
            note = match.group(1).strip()
            terms = [part for part in re.findall(r"[A-Za-z_][A-Za-z0-9_]{3,}", note)][:3]
            if terms:
                found.append((rel, note, terms, _commit_for(repo, rel)))
        if rel.endswith(".md") and not rel.startswith(".context/"):
            for match in DOC_WHY.finditer(text):
                note = match.group(1).strip()
                terms = [part for part in re.findall(r"[A-Za-z_][A-Za-z0-9_]{3,}", note)][:3]
                if terms:
                    found.append((rel, note, terms, _commit_for(repo, rel)))
    return found


def _candidates_from_history(repo: Path) -> list[tuple[str, str, list[str], str | None]]:
    log = run_git(["log", "--pretty=%H%x09%s", "-n", "100"], cwd=repo)
    found: list[tuple[str, str, list[str], str | None]] = []
    for line in log.stdout.splitlines():
        if "\t" not in line:
            continue
        sha, subject = line.split("\t", 1)
        lower = subject.lower()
        if not any(token in lower for token in ("why:", "because", "decision:", "do not ")):
            continue
        files = run_git(["diff-tree", "--no-commit-id", "--name-only", "-r", sha], cwd=repo)
        paths = [p for p in files.stdout.splitlines() if p.strip()]
        if not paths:
            continue
        rel = paths[0]
        terms = [part for part in re.findall(r"[A-Za-z_][A-Za-z0-9_]{3,}", subject)][:3]
        if terms:
            found.append((rel, subject.strip(), terms, sha))
    return found


def bootstrap(repo: Path) -> dict:
    config = load_config(repo)
    kept: list[str] = []
    rejected: list[dict] = []
    tracked = git_ls_files(repo)
    candidates = [
        *_candidates_from_comments(repo, tracked),
        *_candidates_from_history(repo),
    ]
    seen: set[str] = set()
    for rel, note, terms, source in candidates:
        identity = _stable_id(rel, note)
        if identity in seen:
            continue
        seen.add(identity)
        if not source:
            rejected.append({"identity": identity, "tighten": ["no_evidencing_source"]})
            continue
        doc = ConceptDocument(
            identity=identity,
            frontmatter=ConceptFrontmatter(
                type=ConceptType.TechnicalDecision,
                title=note[:80],
                status=ConceptStatus.draft,
                stale_after=_stale_after(),
                sources=[Source(resource=f"git://commit/{source}", title="commit", id=source)],
                verification=Verification(
                    engine="ripgrep",
                    anchors=[Anchor(path=rel, all_of=terms)],
                ),
            ),
            body=f"Bootstrapped from `{rel}`.\n\n{note}\n",
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
