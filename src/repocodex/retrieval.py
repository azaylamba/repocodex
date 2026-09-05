"""Staged concept retrieval: reverse index, ranked bodies, and one link hop."""

from __future__ import annotations

from pathlib import Path

from repocodex.engine.impact import linked_identities
from repocodex.schema import ConceptDocument, ConceptStatus, type_str
from repocodex.store.bundle import discover_context_roots, load_concepts
from repocodex.store.reverse_index import merged_index
from repocodex.tools.git import run_git


def _concept_file(root: Path, identity: str) -> Path | None:
    """Return the markdown path for ``identity`` if it exists in a context shard."""
    fallback = root / ".context" / f"{identity}.md"
    if fallback.is_file():
        return fallback
    for ctx in discover_context_roots(root):
        path = ctx / f"{identity}.md"
        if path.is_file():
            return path
    return None


def _churn_count(root: Path, identity: str) -> int:
    """Count commits that touched the concept file (used to demote noisy pages)."""
    path = _concept_file(root, identity)
    rel = str(path.relative_to(root)).replace("\\", "/") if path else f".context/{identity}.md"
    result = run_git(["rev-list", "--count", "HEAD", "--", rel], cwd=root)
    try:
        return int((result.stdout or "0").strip() or "0")
    except ValueError:
        return 0


def rank_score(doc: ConceptDocument, root: Path) -> float:
    """Score a concept for retrieval: sources, stable, verified, minus git churn."""
    score = 0.0
    if doc.frontmatter.sources:
        score += 100.0
    if doc.status == ConceptStatus.stable:
        score += 20.0
    if doc.frontmatter.verified:
        score += 10.0
    score -= float(_churn_count(root, doc.identity)) * 5.0
    return score


def _catalog_siblings(root: Path, doc: ConceptDocument, selected_ids: set[str]) -> list[dict]:
    """Parse catalog links from the concept's folder ``index.md``, excluding selected ids."""
    path = _concept_file(root, doc.identity)
    if path is None:
        return []
    index_path = path.parent / "index.md"
    if not index_path.is_file():
        return []
    prefix = doc.identity.rsplit("/", 1)[0] if "/" in doc.identity else ""
    siblings: list[dict] = []
    seen: set[str] = set()
    for line in index_path.read_text(encoding="utf-8").splitlines():
        if "](" not in line:
            continue
        start = line.find("](")
        end = line.find(")", start)
        href = line[start + 2 : end].strip()
        name = Path(href).name
        if not name.endswith(".md"):
            continue
        leaf = name[: -len(".md")]
        identity = f"{prefix}/{leaf}" if prefix else leaf
        if identity in selected_ids or identity == doc.identity or identity in seen:
            continue
        title_start = line.find("[")
        title_end = line.find("]")
        title = line[title_start + 1 : title_end] if title_start >= 0 and title_end > title_start else leaf
        seen.add(identity)
        siblings.append({"identity": identity, "title": title, "type": None})
    return siblings


def retrieve(
    root: Path,
    paths: list[str],
    *,
    include_drafts: bool = False,
    include_bodies: bool = True,
) -> dict:
    """Select concepts pinned to ``paths``, ranked, plus related titles.

    Looks up identities in the merged reverse index, drops deprecated
    (and drafts unless ``include_drafts``), sorts by ``rank_score``, then
    adds one hop of ``related`` / catalog sibling titles.

    Returns:
        Envelope-shaped dict with ``paths``, ``concepts``, ``related``,
        and ``catalog``.
    """
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
    selected_ids = {doc.identity for doc in selected}
    related: list[dict] = []
    seen = set(selected_ids)
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
                    "type": type_str(other.frontmatter.type) if other else None,
                }
            )
        for sibling in _catalog_siblings(root, doc, selected_ids):
            if sibling["identity"] in seen:
                continue
            seen.add(sibling["identity"])
            other = by_id.get(sibling["identity"])
            if other:
                sibling["title"] = other.frontmatter.title or sibling["title"]
                sibling["type"] = type_str(other.frontmatter.type)
            related.append(sibling)
    payload_concepts = []
    for doc in selected:
        item = {
            "identity": doc.identity,
            "title": doc.frontmatter.title,
            "type": type_str(doc.frontmatter.type),
            "status": doc.status.value,
            "tags": doc.frontmatter.tags,
            "sources": [
                item.model_dump(mode="python", exclude_none=True) if hasattr(item, "model_dump") else item
                for item in (doc.frontmatter.sources or [])
            ]
            if doc.frontmatter.sources
            else None,
        }
        if include_bodies:
            item["body"] = doc.body
        payload_concepts.append(item)
    catalog: list[dict] = []
    for doc in selected:
        catalog.extend(_catalog_siblings(root, doc, selected_ids))
    return {
        "paths": paths,
        "concepts": payload_concepts,
        "related": related,
        "catalog": catalog,
    }
