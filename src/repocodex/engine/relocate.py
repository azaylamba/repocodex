from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from repocodex.config import RepoConfig
from repocodex.engine.match import evaluate_file, is_regex_term, match_anchor, read_pinned
from repocodex.schema import Anchor
from repocodex.tools.git import run_git
from repocodex.tools.ripgrep import rg_count, rg_files


@dataclass
class Relocation:
    unique: bool
    via: str
    candidates: list[dict] = field(default_factory=list)


def parse_renames(cwd: Path, base: str | None = None) -> dict[str, str]:
    args = ["diff", "-M", "--name-status"]
    if base:
        args.append(base)
    result = run_git(args, cwd=cwd)
    mapping: dict[str, str] = {}
    for line in result.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 3 and parts[0].startswith("R"):
            mapping[parts[1]] = parts[2]
    return mapping


def _most_distinctive_term(anchor: Anchor, config: RepoConfig) -> str:
    scored: list[tuple[int, str]] = []
    for term in anchor.all_of:
        pattern = term[1:-1] if is_regex_term(term) else term
        count = rg_count(
            pattern,
            config.root,
            fixed=not is_regex_term(term),
            exclusions=config.all_exclusions,
        )
        scored.append((count, term))
    scored.sort()
    return scored[0][1] if scored else anchor.all_of[0]


def relocate_anchor(
    anchor: Anchor,
    config: RepoConfig,
    *,
    diff_files: list[str] | None = None,
) -> Relocation:
    renames = parse_renames(config.root)
    if anchor.path in renames:
        new_path = renames[anchor.path]
        relocated = Anchor(
            path=new_path,
            all_of=anchor.all_of,
            near=anchor.near,
            scope_lines=anchor.scope_lines,
            min_match=anchor.min_match,
        )
        matched = evaluate_file(relocated, config.root, default_scope=config.scope_lines)
        if matched.regions:
            return Relocation(
                unique=True,
                via="rename",
                candidates=[{"path": new_path, "via": "git diff -M"}],
            )

    term = _most_distinctive_term(anchor, config)
    pattern = term[1:-1] if is_regex_term(term) else term
    files = rg_files(
        pattern,
        config.root,
        fixed=not is_regex_term(term),
        exclusions=config.all_exclusions,
    )
    candidates: list[dict] = []
    for raw in files:
        rel = str(Path(raw).resolve().relative_to(config.root)).replace("\\", "/")
        if rel == anchor.path:
            continue
        text = read_pinned(config.root, rel)
        if text is None:
            continue
        probe = Anchor(
            path=rel,
            all_of=anchor.all_of,
            near=anchor.near,
            scope_lines=anchor.scope_lines,
            min_match=anchor.min_match,
        )
        matched = match_anchor(probe, text, default_scope=config.scope_lines)
        if any(len(region.terms_hit) >= len(anchor.all_of) for region in matched.regions):
            candidates.append({"path": rel, "via": f"pickaxe:{term}"})

    if not candidates:
        pickaxe = run_git(["log", "-S", term, "--name-only", "--pretty=format:"], cwd=config.root)
        seen: set[str] = set()
        for line in pickaxe.stdout.splitlines():
            path = line.strip()
            if not path or path == anchor.path or path in seen:
                continue
            seen.add(path)
            text = read_pinned(config.root, path)
            if text is None:
                continue
            probe = Anchor(path=path, all_of=anchor.all_of, near=anchor.near)
            matched = match_anchor(probe, text, default_scope=config.scope_lines)
            if any(len(region.terms_hit) >= len(anchor.all_of) for region in matched.regions):
                candidates.append({"path": path, "via": f"pickaxe:{term}"})

    unique = len(candidates) == 1
    return Relocation(
        unique=unique,
        via="pickaxe" if candidates else "full_miss",
        candidates=candidates,
    )
