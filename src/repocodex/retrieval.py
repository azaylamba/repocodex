from __future__ import annotations

from pathlib import Path

from repocodex.engine.impact import linked_identities
from repocodex.schema import ConceptDocument, ConceptStatus
from repocodex.store.bundle import load_concepts
from repocodex.store.reverse_index import merged_index
from repocodex.tools.git import run_git


def _churn_count(root: Path, identity: str) -> int:
    # Infer from git history of the concept file; never stored.
    result = run_git(
        ["log", "--follow", "--pretty=%H", "--", f".context/{identity}.md"],
        cwd=root,
    )
    commits = [line for line in result.stdout.splitlines() if line.strip()]
    return len(commits)


def rank_score(doc: ConceptDocument, root: Path) -> float:
    score = 0.0
    if doc.frontmatter.sources:
        score += 100.0
    if doc.status == ConceptStatus.stable:
        score += 20.0
    if doc.frontmatter.verified:
        score += 10.0
    score -= float(_churn_count(root, doc.identity)) * 5.0
    return score


def retrieve(
    root: Path,
    paths: list[str],
    *,
    include_drafts: bool = False,
    include_bodies: bool = True,
) -> dict:
    concepts = load_concepts(root)
    by_id = {doc.identity: doc for doc in concepts}
    index = merged_index(root)
    selected: list[ConceptDocument] = []
    for path in paths:
        for identity in index.get(path, []):
            doc = by_id.get(identity)
            if not doc:
                continue
            if doc.status == ConceptStatus.draft and not include_drafts:
                continue
            if doc.status == ConceptStatus.deprecated:
                continue
            if doc not in selected:
                selected.append(doc)
    selected.sort(key=lambda doc: rank_score(doc, root), reverse=True)
    related: list[dict] = []
    seen = {doc.identity for doc in selected}
    for doc in selected:
        for linked in linked_identities(doc):
            if linked in seen:
                continue
            seen.add(linked)
            other = by_id.get(linked)
            related.append(
                {
                    "identity": linked,
                    "title": other.frontmatter.title if other else linked,
                    "type": other.frontmatter.type.value if other else None,
                }
            )
    payload_concepts = []
    for doc in selected:
        item = {
            "identity": doc.identity,
            "title": doc.frontmatter.title,
            "type": doc.frontmatter.type.value,
            "status": doc.status.value,
            "tags": doc.frontmatter.tags,
            "sources": doc.frontmatter.sources,
        }
        if include_bodies:
            item["body"] = doc.body
        payload_concepts.append(item)
    return {
        "paths": paths,
        "concepts": payload_concepts,
        "related": related,
    }
