from __future__ import annotations

from collections import defaultdict

from repocodex.schema import ConceptDocument, ConceptStatus


def overlapping_claim_conflicts(concepts: list[ConceptDocument], root) -> list[dict]:
    flags: list[dict] = []
    live = [doc for doc in concepts if doc.status != ConceptStatus.deprecated]
    for i, left in enumerate(live):
        for right in live[i + 1 :]:
            shared = set(left.pinned_paths) & set(right.pinned_paths)
            if not shared:
                continue
            left_claims = {c.literal for c in (left.frontmatter.claims or [])}
            right_claims = {c.literal for c in (right.frontmatter.claims or [])}
            if left_claims and right_claims and left_claims != right_claims:
                flags.append(
                    {
                        "kind": "CONTRADICTION",
                        "left": left.identity,
                        "right": right.identity,
                        "reason": "conflicting_claims",
                        "paths": sorted(shared),
                    }
                )
    return flags


def double_supersede_conflicts(concepts: list[ConceptDocument]) -> list[dict]:
    by_parent: dict[str, list[str]] = defaultdict(list)
    for doc in concepts:
        parent = doc.frontmatter.supersedes
        if parent and doc.status != ConceptStatus.deprecated:
            by_parent[parent].append(doc.identity)
    flags: list[dict] = []
    for parent, children in by_parent.items():
        if len(children) > 1:
            flags.append(
                {
                    "kind": "CONTRADICTION",
                    "supersedes": parent,
                    "concepts": children,
                    "reason": "double_supersede",
                }
            )
    return flags


def contradiction_flags(concepts: list[ConceptDocument], root) -> list[dict]:
    return overlapping_claim_conflicts(concepts, root) + double_supersede_conflicts(concepts)
