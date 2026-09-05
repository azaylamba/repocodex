"""Accept or reject a concept write using local ripgrep counts and file reads."""

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
    resolve_claim_owner,
)
from repocodex.schema import ConceptDocument, ConceptType, type_str
from repocodex.tools.git import git_check_ignore
from repocodex.tools.ripgrep import rg_count, run_rg


SUGGESTIONS = [
    "use a string literal, user-facing error message, enum value, or numeric threshold",
    "prefer stable tokens over renameable identifiers",
]

CLAIMS_REQUIRED_REASON = "InvariantContract requires at least one claims entry"
CLAIMS_REQUIRED_SUGGESTION = (
    "declare claims with frozen literals (thresholds, enums, contract error strings)"
)

# Authored types → required first path segment(s) under the owning .context/ shard.
AUTHORED_TYPE_PREFIXES: dict[str, tuple[str, ...]] = {
    ConceptType.TechnicalDecision.value: ("decisions/",),
    ConceptType.InvariantContract.value: ("invariants/",),
    ConceptType.BusinessWorkflow.value: ("workflows/",),
    ConceptType.GuardrailDecision.value: ("decisions/", "guardrails/"),
}

IDENTITY_PREFIX_MISMATCH = "identity_prefix_mismatch"


def missing_invariant_claims(doc: ConceptDocument) -> bool:
    """Return True when an InvariantContract has no claims."""
    return doc.frontmatter.type == ConceptType.InvariantContract.value and not doc.frontmatter.claims


def claims_required_reject() -> GateResult:
    """Return a rejecting result for an InvariantContract with no claims."""
    return GateResult(
        accepted=False,
        tighten=["claims_required"],
        suggestions=[CLAIMS_REQUIRED_SUGGESTION],
        reasons=[CLAIMS_REQUIRED_REASON],
    )


def allowed_prefixes(concept_type: str | ConceptType | None) -> tuple[str, ...] | None:
    """Return required identity prefixes for an authored type, or None if unrestricted."""
    key = type_str(concept_type) if concept_type is not None else ""
    if not key:
        return None
    return AUTHORED_TYPE_PREFIXES.get(key)


def identity_prefix_ok(concept_type: str | ConceptType | None, identity: str) -> bool:
    """Return True when ``identity`` sits under a required type folder."""
    prefixes = allowed_prefixes(concept_type)
    if prefixes is None:
        return True
    normalized = identity.replace("\\", "/").lstrip("/")
    return any(normalized.startswith(prefix) for prefix in prefixes)


def suggested_identity(concept_type: str | ConceptType | None, identity: str) -> str | None:
    """Return the first allowed prefix plus the identity leaf, or None if unrestricted."""
    prefixes = allowed_prefixes(concept_type)
    if prefixes is None:
        return None
    leaf = Path(identity.replace("\\", "/")).name
    return f"{prefixes[0]}{leaf}"


def identity_prefix_suggestion(concept_type: str | ConceptType | None, identity: str) -> str:
    """Return a human suggestion to move ``identity`` under its type folder."""
    suggested = suggested_identity(concept_type, identity) or identity
    return f"use identity {suggested}"


def identity_prefix_mismatch_reject(
    concept_type: str | ConceptType | None, identity: str
) -> GateResult:
    """Return a rejecting result for a new write whose identity lacks its type folder."""
    suggested = suggested_identity(concept_type, identity) or identity
    return GateResult(
        accepted=False,
        tighten=[IDENTITY_PREFIX_MISMATCH],
        suggestions=[identity_prefix_suggestion(concept_type, identity)],
        reasons=[f"authored type requires identity under {suggested.rsplit('/', 1)[0]}/"],
    )


def identity_prefix_warnings(concepts: list[ConceptDocument]) -> list[dict]:
    """List existing authored identities that sit outside their type folder.

    Returns:
        Dicts with ``concept``, ``type``, and ``suggested`` identity.
    """
    # Prefix mismatch on an already-written identity is a suggestion, not a
    # hard reject: failing the write would brick updates to grandfathered
    # flat pages. New writes still use identity_prefix_mismatch_reject.
    warnings: list[dict] = []
    for doc in concepts:
        if identity_prefix_ok(doc.frontmatter.type, doc.identity):
            continue
        suggested = suggested_identity(doc.frontmatter.type, doc.identity)
        warnings.append(
            {
                "concept": doc.identity,
                "type": type_str(doc.frontmatter.type),
                "suggested": suggested,
            }
        )
    return warnings


@dataclass
class GateResult:
    """Accept-or-reject outcome of evaluating a concept write."""

    accepted: bool
    tighten: list[str] = field(default_factory=list)
    term_counts: dict[str, int] = field(default_factory=dict)
    suggestions: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    def to_json(self) -> dict:
        """Return this result as a JSON-serializable dict."""
        return {
            "accepted": self.accepted,
            "tighten": self.tighten,
            "term_counts": self.term_counts,
            "suggestions": self.suggestions,
            "reasons": self.reasons,
        }


def path_excluded(path: str, config: RepoConfig) -> bool:
    """Return True when ``path`` is gitignored or matches a configured exclusion."""
    normalized = normalize_repo_path(path)
    if git_check_ignore(normalized, config.root):
        return True
    return matches_exclusion(normalized, config.all_exclusions)


def _term_count(term: str, config: RepoConfig) -> int:
    """Return the repo-wide ripgrep hit count for a term."""
    fixed = not is_regex_term(term)
    pattern = term[1:-1] if is_regex_term(term) else term
    return rg_count(pattern, config.root, fixed=fixed, exclusions=config.all_exclusions)


def _regex_dialects_agree(term: str, root: Path) -> bool:
    """Return True when Python re and ripgrep both accept the regex."""
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
    """Accept a write only when every anchor and claim is locally distinctive."""
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

    full_regions_by_index: dict[int, list] = {}
    texts_by_index: dict[int, str] = {}

    for index, anchor in enumerate(doc.anchors):
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
        texts_by_index[index] = text

        matched = match_anchor(anchor, text, default_scope=config.scope_lines)
        required = min_match_for(anchor)
        full_regions = [
            region for region in matched.regions if len(region.terms_hit) >= len(anchor.all_of)
        ]
        full_regions_by_index[index] = full_regions
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

    if missing_invariant_claims(doc):
        tighten.append("claims_required")
        reasons.append(CLAIMS_REQUIRED_REASON)

    if doc.frontmatter.claims:
        for claim in doc.frontmatter.claims:
            owner, error = resolve_claim_owner(claim, doc.anchors)
            if error == "out_of_range":
                tighten.append("invalid_claim_anchor")
                reasons.append(f"claim owner index {claim.anchor} is out of range")
                continue
            if error == "ambiguous":
                tighten.append("declare_anchor")
                reasons.append(
                    f'claim "{claim.literal}" matches multiple anchors; declare claims[].anchor'
                )
                continue
            if error == "claim_not_anchored" or owner is None:
                tighten.append("claim_not_anchored")
                reasons.append(f'claim "{claim.literal}" is not anchored')
                continue
            claim.anchor = owner
            owner_anchor = doc.anchors[owner]
            full_regions = full_regions_by_index.get(owner, [])
            text = texts_by_index.get(owner)
            if not full_regions or text is None:
                tighten.append("claim_not_anchored")
                reasons.append(f'claim "{claim.literal}" is not anchored')
                continue
            region_text = full_regions[0].source(text.splitlines())
            in_terms = claim_in_terms(claim.literal, owner_anchor.all_of)
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
    if "claims_required" in tighten:
        suggestions = [
            CLAIMS_REQUIRED_SUGGESTION,
            *suggestions,
        ]
    return GateResult(
        accepted=accepted,
        tighten=tighten,
        term_counts=term_counts,
        suggestions=list(dict.fromkeys(suggestions)),
        reasons=reasons,
    )
