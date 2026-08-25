from __future__ import annotations

import re
from pathlib import Path

from repocodex.schema import ConceptDocument

LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def resolve_link(from_identity: str, target: str) -> str | None:
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
