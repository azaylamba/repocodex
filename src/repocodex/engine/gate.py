from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import fnmatch

from repocodex.config import RepoConfig
from repocodex.engine.match import (
    is_marker_term,
    is_regex_term,
    match_anchor,
    min_match_for,
    only_import_hits,
    read_pinned,
    term_in_text,
)
from repocodex.schema import ConceptDocument
from repocodex.tools.git import git_check_ignore
from repocodex.tools.ripgrep import rg_count


SUGGESTIONS = [
    "use a string literal, user-facing error message, enum value, or numeric threshold",
    "prefer stable tokens over renameable identifiers",
]


@dataclass
class GateResult:
    accepted: bool
    tighten: list[str] = field(default_factory=list)
    term_counts: dict[str, int] = field(default_factory=dict)
    suggestions: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    def to_json(self) -> dict:
        return {
            "accepted": self.accepted,
            "tighten": self.tighten,
            "term_counts": self.term_counts,
            "suggestions": self.suggestions,
            "reasons": self.reasons,
        }


def path_excluded(path: str, config: RepoConfig) -> bool:
    normalized = path.replace("\\", "/").lstrip("./")
    if git_check_ignore(normalized, config.root):
        return True
    for glob in config.all_exclusions:
        if fnmatch.fnmatch(normalized, glob) or fnmatch.fnmatch(Path(normalized).name, glob):
            return True
        if glob.endswith("/**") and normalized.startswith(glob[:-3]):
            return True
    return False


def _term_count(term: str, config: RepoConfig) -> int:
    fixed = not is_regex_term(term)
    pattern = term[1:-1] if is_regex_term(term) else term
    return rg_count(pattern, config.root, fixed=fixed, exclusions=config.all_exclusions)


def evaluate_write(doc: ConceptDocument, config: RepoConfig) -> GateResult:
    tighten: list[str] = []
    reasons: list[str] = []
    term_counts: dict[str, int] = {}

    if not doc.anchors:
        return GateResult(
            accepted=False,
            tighten=["no_match"],
            suggestions=SUGGESTIONS,
            reasons=["concept has no anchors"],
        )

    for anchor in doc.anchors:
        if path_excluded(anchor.path, config):
            tighten.append("excluded_path")
            reasons.append(f"{anchor.path} is excluded")
            continue
        if not anchor.all_of:
            tighten.append("not_distinctive")
            reasons.append(f"{anchor.path} is path-only")
            continue
        marker_terms = [t for t in anchor.all_of if is_marker_term(t)]
        if marker_terms and len(marker_terms) == len(anchor.all_of):
            tighten.append("marker_only")
            reasons.append("marker cannot be the sole anchor")
            continue
        if len(marker_terms) > 1:
            tighten.append("marker_only")
            reasons.append("at most one marker term is allowed")

        for term in anchor.all_of:
            term_counts[term] = _term_count(term, config)

        text = read_pinned(config.root, anchor.path)
        if text is None:
            tighten.append("no_match")
            reasons.append(f"{anchor.path} is missing")
            continue

        matched = match_anchor(anchor, text, default_scope=config.scope_lines)
        required = min_match_for(anchor)
        full_regions = [
            region for region in matched.regions if len(region.terms_hit) >= len(anchor.all_of)
        ]
        if required == len(anchor.all_of):
            live_regions = full_regions
        else:
            live_regions = [
                region for region in matched.regions if len(region.terms_hit) >= required
            ]

        if not live_regions and not full_regions:
            tighten.append("no_match")
            reasons.append(f"zero hits for {anchor.path}")
        elif len(full_regions) > 1:
            tighten.append("ambiguous_in_file")
            reasons.append(f"multiple disjoint regions in {anchor.path}")

        distinctive = any(
            term_counts.get(term, 10**9) < config.distinctiveness_ceiling for term in anchor.all_of
        )
        if not distinctive:
            tighten.append("not_distinctive")
            reasons.append(f"no term under distinctiveness ceiling for {anchor.path}")

        if only_import_hits(anchor, text) and all(
            term_counts.get(term, 0) >= config.distinctiveness_ceiling for term in anchor.all_of
        ):
            tighten.append("not_distinctive")
            reasons.append(f"import-line terms only for {anchor.path}")

        if doc.frontmatter.claims:
            region_text = full_regions[0].source(text.splitlines()) if full_regions else text
            joined_terms = " ".join(anchor.all_of)
            for claim in doc.frontmatter.claims:
                in_terms = claim.literal in joined_terms or any(
                    claim.literal in term for term in anchor.all_of
                )
                in_source = term_in_text(claim.literal, region_text) or claim.literal in region_text
                if not in_terms or not in_source:
                    tighten.append("claim_not_anchored")
                    reasons.append(f'claim "{claim.literal}" is not anchored')

    tighten = list(dict.fromkeys(tighten))
    accepted = not tighten
    suggestions = SUGGESTIONS if not accepted else []
    if "not_distinctive" in tighten:
        suggestions = [
            "use the enum literal or the user-facing error string as a term",
            *SUGGESTIONS,
        ]
    return GateResult(
        accepted=accepted,
        tighten=tighten,
        term_counts=term_counts,
        suggestions=list(dict.fromkeys(suggestions)),
        reasons=reasons,
    )
