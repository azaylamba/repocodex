"""Compile anchor terms and find their co-occurrence regions in a file."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from repocodex.schema import Anchor, Claim

MARKER_RE = re.compile(r"why:\s*", re.IGNORECASE)
IMPORT_RE = re.compile(
    r"^\s*(import\s+|from\s+\S+\s+import|require\(|#include\s+|use\s+|using\s+)",
    re.IGNORECASE,
)
IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
TOKEN_CHAR = r"[A-Za-z0-9_]"


def is_regex_term(term: str) -> bool:
    """Return True when ``term`` is a slash-wrapped regular expression."""
    return len(term) > 2 and term.startswith("/") and term.endswith("/")


def is_marker_term(term: str) -> bool:
    """Return True when ``term`` looks like a ``why:`` marker."""
    return bool(MARKER_RE.search(term)) or "why:" in term.lower()


def compile_term(term: str) -> re.Pattern[str]:
    """Compile ``term`` to a regex, using word boundaries for identifiers."""
    if is_regex_term(term):
        return re.compile(term[1:-1])
    if IDENTIFIER_RE.fullmatch(term):
        return re.compile(rf"\b{re.escape(term)}\b")
    parts = re.split(r"(\s+)", term)
    pattern = "".join(r"\s+" if part.isspace() else re.escape(part) for part in parts)
    return re.compile(pattern)


def term_hits(term: str, lines: list[str]) -> list[int]:
    """Return 0-based line indexes where ``term`` matches."""
    text = "\n".join(lines)
    pattern = compile_term(term)
    hits: list[int] = []
    for match in pattern.finditer(text):
        line_no = text[: match.start()].count("\n")
        hits.append(line_no)
    return hits


def term_in_text(term: str, text: str) -> bool:
    """Return True when ``term`` occurs anywhere in ``text``."""
    return bool(compile_term(term).search(text))


def literal_as_token(literal: str, text: str) -> bool:
    """Return True when ``literal`` appears as its own token in ``text``."""
    if not literal or not text:
        return False
    escaped = re.escape(literal)
    if re.fullmatch(rf"{TOKEN_CHAR}+", literal):
        return bool(re.search(rf"(?<!{TOKEN_CHAR}){escaped}(?!{TOKEN_CHAR})", text))
    return literal in text


def claim_in_terms(literal: str, terms: list[str]) -> bool:
    """Return True when ``literal`` is a token of any term, or equals a term."""
    return any(literal_as_token(literal, term) or literal == term for term in terms)


def resolve_claim_owner(claim: Claim, anchors: list[Anchor]) -> tuple[int | None, str | None]:
    """Return ``(anchor_index, error)`` for the claim's owning anchor.

    ``error`` is None when the owner is unambiguous. Otherwise it is
    ``out_of_range``, ``claim_not_anchored``, or ``ambiguous``.
    """
    n = len(anchors)
    if claim.anchor is not None:
        if claim.anchor < 0 or claim.anchor >= n:
            return None, "out_of_range"
        return claim.anchor, None
    if n == 1:
        return 0, None
    matches = [i for i, anchor in enumerate(anchors) if claim_in_terms(claim.literal, anchor.all_of)]
    if len(matches) == 1:
        return matches[0], None
    if not matches:
        return None, "claim_not_anchored"
    return None, "ambiguous"


@dataclass
class Region:
    """A contiguous line span and the anchor terms that hit it."""

    start: int
    end: int
    terms_hit: list[str] = field(default_factory=list)

    def overlaps(self, other: Region, gap: int = 0) -> bool:
        """Return True when the spans overlap, allowing ``gap`` lines between them."""
        return self.start <= other.end + gap and other.start <= self.end + gap

    def merge(self, other: Region) -> Region:
        """Return a region covering both spans and the union of terms hit."""
        return Region(
            start=min(self.start, other.start),
            end=max(self.end, other.end),
            terms_hit=sorted(set(self.terms_hit) | set(other.terms_hit)),
        )

    def source(self, lines: list[str]) -> str:
        """Return the source text for this inclusive line span."""
        return "\n".join(lines[self.start : self.end + 1])


@dataclass
class AnchorMatch:
    """All matching regions for one anchor in one file."""

    path: str
    regions: list[Region]
    term_lines: dict[str, list[int]]
    missing_file: bool = False

    @property
    def best(self) -> Region | None:
        """Tightest matching region, preferring more terms then earlier start."""
        if not self.regions:
            return None
        return max(self.regions, key=lambda region: (len(region.terms_hit), -region.start))

    def hits_for_best(self) -> int:
        """Return how many terms the best region hit, or 0 if none."""
        return len(self.best.terms_hit) if self.best else 0


def _merge_regions(regions: list[Region], gap: int) -> list[Region]:
    """Merge regions that overlap within ``gap`` lines."""
    if not regions:
        return []
    ordered = sorted(regions, key=lambda region: region.start)
    merged = [ordered[0]]
    for region in ordered[1:]:
        if merged[-1].overlaps(region, gap=gap):
            merged[-1] = merged[-1].merge(region)
        else:
            merged.append(region)
    return merged


def match_anchor(anchor: Anchor, text: str, *, default_scope: int = 40) -> AnchorMatch:
    """Find co-occurrence regions for ``anchor`` inside ``text``."""
    lines = text.splitlines() or [""]
    term_lines = {term: term_hits(term, lines) for term in anchor.all_of}
    scope = anchor.scope_lines or default_scope
    regions: list[Region] = []

    if anchor.near:
        for near_line in term_hits(anchor.near, lines):
            start = max(0, near_line - scope)
            end = min(len(lines) - 1, near_line + scope)
            hit = [
                term
                for term, hits in term_lines.items()
                if any(start <= line_no <= end for line_no in hits)
            ]
            if hit:
                regions.append(Region(start=start, end=end, terms_hit=hit))
        regions = _merge_regions(regions, gap=0)
    else:
        all_lines = sorted({line for hits in term_lines.values() for line in hits})
        if all_lines:
            cluster: list[int] = [all_lines[0]]
            clusters: list[list[int]] = []
            for line_no in all_lines[1:]:
                if line_no - cluster[-1] <= scope:
                    cluster.append(line_no)
                else:
                    clusters.append(cluster)
                    cluster = [line_no]
            clusters.append(cluster)
            for cluster_lines in clusters:
                start, end = cluster_lines[0], cluster_lines[-1]
                hit = [
                    term
                    for term, hits in term_lines.items()
                    if any(start <= line_no <= end for line_no in hits)
                ]
                if hit:
                    regions.append(Region(start=start, end=end, terms_hit=hit))

    return AnchorMatch(path=anchor.path, regions=regions, term_lines=term_lines)


def min_match_for(anchor: Anchor) -> int:
    """Return the required term-hit count, defaulting to every ``all_of`` term."""
    if anchor.min_match is None:
        return len(anchor.all_of)
    return max(1, min(anchor.min_match, len(anchor.all_of)))


def read_pinned(root: Path, path: str) -> str | None:
    """Return the pinned file's text, or None if it is missing."""
    target = root / path
    if not target.is_file():
        return None
    return target.read_text(encoding="utf-8", errors="replace")


def evaluate_file(anchor: Anchor, root: Path, *, default_scope: int = 40) -> AnchorMatch:
    """Match ``anchor`` against its pinned file on disk."""
    text = read_pinned(root, anchor.path)
    if text is None:
        return AnchorMatch(
            path=anchor.path,
            regions=[],
            term_lines={term: [] for term in anchor.all_of},
            missing_file=True,
        )
    return match_anchor(anchor, text, default_scope=default_scope)


def only_import_hits(anchor: Anchor, text: str) -> bool:
    """Return True when every term hit in ``text`` is on an import-like line."""
    lines = text.splitlines()
    for term in anchor.all_of:
        hits = term_hits(term, lines)
        if hits and any(not IMPORT_RE.search(lines[i]) for i in hits):
            return False
    return True
