from __future__ import annotations

from pathlib import Path
from typing import Any

from repocodex.commands.validate import changed_files
from repocodex.config import load_config
from repocodex.engine.code_impact import rank_code_hits
from repocodex.schema import envelope

NOT_EVALUATED = "not_evaluated"
EVALUATED = "evaluated"


def _category(status: str, findings: list[dict] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"status": status}
    if status == EVALUATED:
        payload["findings"] = findings or []
    return payload


def advisory(
    repo: Path,
    *,
    base: str | None = None,
    staged: bool = False,
    judgments: dict[str, list[dict]] | None = None,
) -> dict:
    config = load_config(repo)
    files = changed_files(repo, base=base, staged=staged)
    code_side: list[dict] = []
    for path in files:
        if path.startswith(".context/") or path.endswith("reverse-index.md"):
            continue
        symbols = Path(path).stem
        hits = rank_code_hits(path, symbols, repo, cap=config.impact_read_cap, exclusions=config.all_exclusions)
        if hits:
            code_side.append({"path": path, "hits": hits})

    judgments = judgments or {}

    def category_for(name: str) -> dict[str, Any]:
        if name in judgments:
            return _category(EVALUATED, judgments[name])
        return _category(NOT_EVALUATED)

    prose = category_for("prose_versus_diff")
    skipped = category_for("skipped_recipe_steps")
    churn = category_for("churn_flags")
    any_judgment = any(cat["status"] == EVALUATED for cat in (prose, skipped, churn))
    return envelope(
        {
            "kind": "advisory",
            "code_side_impact": code_side,
            "prose_versus_diff": prose,
            "skipped_recipe_steps": skipped,
            "churn_flags": churn,
            "agent_judgment": any_judgment,
            "required_verdict_unaffected": True,
        }
    )


def scenario_integrity_status(root: Path) -> dict:
    """OKF-loop capability. Unsatisfied until a bundle exists; never falls back to a test table."""
    from repocodex.store.bundle import load_concepts

    concepts = load_concepts(root)
    if not concepts:
        return {"status": "unsatisfied", "reason": "no_okf_bundle"}
    return {"status": "available", "reason": "agent_read_okf"}
