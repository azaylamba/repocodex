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
            left_by_subject: dict[str, str] = {}
            right_by_subject: dict[str, str] = {}
            for claim in left.frontmatter.claims or []:
                if claim.subject:
                    left_by_subject[claim.subject] = claim.literal
            for claim in right.frontmatter.claims or []:
                if claim.subject:
                    right_by_subject[claim.subject] = claim.literal
            for subject, literal in left_by_subject.items():
                other = right_by_subject.get(subject)
                if other is not None and other != literal:
                    flags.append(
                        {
                            "kind": "CONTRADICTION",
                            "left": left.identity,
                            "right": right.identity,
                            "reason": "conflicting_claims",
                            "subject": subject,
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
