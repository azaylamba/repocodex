from __future__ import annotations

from pathlib import Path

from repocodex.commands.validate import changed_files
from repocodex.config import load_config
from repocodex.engine.code_impact import rank_code_hits
from repocodex.schema import envelope
from repocodex.store.bundle import load_concepts
from repocodex.store.reverse_index import merged_index


def advisory(repo: Path, *, base: str | None = None, staged: bool = False) -> dict:
    config = load_config(repo)
    files = changed_files(repo, base=base, staged=staged)
    index = merged_index(repo)
    concepts = load_concepts(repo)
    by_id = {doc.identity: doc for doc in concepts}
    code_side: list[dict] = []
    weakenings: list[dict] = []
    for path in files:
        if path.startswith(".context/") or path.endswith("reverse-index.md"):
            continue
        symbols = Path(path).stem
        hits = rank_code_hits(path, symbols, repo, cap=config.impact_read_cap, exclusions=config.all_exclusions)
        if hits:
            code_side.append({"path": path, "hits": hits})
        for identity in index.get(path, []):
            doc = by_id.get(identity)
            if doc and doc.frontmatter.claims:
                weakenings.append(
                    {
                        "path": path,
                        "concept": identity,
                        "note": "review agent should verify prose against the diff",
                    }
                )
    return envelope(
        {
            "kind": "advisory",
            "code_side_impact": code_side,
            "prose_versus_diff": weakenings,
            "skipped_recipe_steps": [],
            "churn_flags": [],
            "required_verdict_unaffected": True,
        }
    )
