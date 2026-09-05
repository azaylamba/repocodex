"""Walk reverse-index seeds and markdown links to find impacted concepts."""

from __future__ import annotations

import re
from pathlib import Path

from repocodex.schema import ConceptDocument

LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def resolve_link(from_identity: str, target: str) -> str | None:
    """Resolve a markdown href to a concept identity relative to ``from_identity``.

    External URLs and in-page fragments return ``None``. A trailing ``.md``
    suffix is stripped after ``.`` / ``..`` normalization.
    """
    href = target.strip()
    if href.startswith("http://") or href.startswith("https://") or href.startswith("#"):
        return None
    href = href.split("#", 1)[0]
    if not href:
        return None
    base_dir = str(Path(from_identity).parent)
    combined = str(Path(base_dir) / href) if base_dir != "." else href
    normalized = Path(combined).as_posix()
    if normalized.endswith(".md"):
        normalized = normalized[: -len(".md")]
    parts: list[str] = []
    for part in normalized.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)
    return "/".join(parts)


def linked_identities(doc: ConceptDocument) -> list[str]:
    """Return unique concept identities linked from ``doc.body``, in order."""
    found: list[str] = []
    for match in LINK_RE.finditer(doc.body):
        identity = resolve_link(doc.identity, match.group(1))
        if identity and identity not in found:
            found.append(identity)
    return found


def intent_impact(
    changed_files: list[str],
    concepts: list[ConceptDocument],
    reverse_index: dict[str, list[str]],
) -> list[str]:
    """Return concept identities impacted by ``changed_files``.

    Seeds from reverse-index hits, then walks each seed's markdown links and
    any other concepts that pin the linked documents' paths.
    """
    by_id = {doc.identity: doc for doc in concepts}
    seeded: list[str] = []
    for path in changed_files:
        for identity in reverse_index.get(path, []):
            if identity not in seeded:
                seeded.append(identity)
    scenarios: list[str] = []
    for identity in seeded:
        if identity not in scenarios:
            scenarios.append(identity)
        doc = by_id.get(identity)
        if not doc:
            continue
        for linked in linked_identities(doc):
            if linked not in scenarios:
                scenarios.append(linked)
            linked_doc = by_id.get(linked)
            if linked_doc:
                for pin in linked_doc.pinned_paths:
                    for other in reverse_index.get(pin, []):
                        if other not in scenarios:
                            scenarios.append(other)
    return scenarios
