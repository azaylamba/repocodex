from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import tempfile

from repocodex.config import RepoConfig, matches_exclusion, normalize_repo_path
from repocodex.engine.match import (
    is_marker_term,
    is_regex_term,
    claim_in_terms,
    literal_as_token,
    match_anchor,
    min_match_for,
    only_import_hits,
    read_pinned,
)
from repocodex.schema import ConceptDocument
from repocodex.tools.git import git_check_ignore
from repocodex.tools.ripgrep import rg_count, run_rg


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
    normalized = normalize_repo_path(path)
    if git_check_ignore(normalized, config.root):
        return True
    return matches_exclusion(normalized, config.all_exclusions)


def _term_count(term: str, config: RepoConfig) -> int:
    fixed = not is_regex_term(term)
    pattern = term[1:-1] if is_regex_term(term) else term
    return rg_count(pattern, config.root, fixed=fixed, exclusions=config.all_exclusions)


def _regex_dialects_agree(term: str, root: Path) -> bool:
    if not is_regex_term(term):
        return True
    pattern = term[1:-1]
    try:
        import re

        re.compile(pattern)
        py_ok = True
    except re.error:
        py_ok = False
    with tempfile.NamedTemporaryFile(prefix="repocodex-rg-", suffix=".txt", delete=True) as handle:
        handle.write(b"\n")
        handle.flush()
        result = run_rg(["--quiet", "--", pattern, handle.name], cwd=root)
    rg_err = (result.stderr or "").lower()
    rg_ok = "regex parse error" not in rg_err and result.returncode != 2
    return py_ok and rg_ok


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
            if is_regex_term(term) and not _regex_dialects_agree(term, config.root):
                tighten.append("regex_dialect")
                reasons.append(f'regex term "{term}" is not portable across Python re and ripgrep')
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
            if not full_regions:
                for claim in doc.frontmatter.claims:
                    tighten.append("claim_not_anchored")
                    reasons.append(f'claim "{claim.literal}" is not anchored')
            else:
                region_text = full_regions[0].source(text.splitlines())
                for claim in doc.frontmatter.claims:
                    in_terms = claim_in_terms(claim.literal, anchor.all_of)
                    in_source = literal_as_token(claim.literal, region_text)
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
    if "regex_dialect" in tighten:
        suggestions = [
            "use a fixed-string stable token instead of a dialect-specific regex",
            *suggestions,
        ]
    return GateResult(
        accepted=accepted,
        tighten=tighten,
        term_counts=term_counts,
        suggestions=list(dict.fromkeys(suggestions)),
        reasons=reasons,
    )
