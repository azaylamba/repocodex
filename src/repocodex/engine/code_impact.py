from __future__ import annotations

from pathlib import Path

from repocodex.tools.ripgrep import rg_files


TEST_HINTS = ("test", "spec", "tests/")


def _proximity(changed: str, hit: str) -> int:
    a = Path(changed).parts
    b = Path(hit).parts
    shared = 0
    for left, right in zip(a, b):
        if left != right:
            break
        shared += 1
    return shared


def rank_code_hits(
    changed_path: str,
    symbol: str,
    root: Path,
    *,
    cap: int = 12,
    exclusions: list[str] | None = None,
) -> list[dict]:
    files = rg_files(symbol, root, fixed=True, exclusions=exclusions)
    ranked = []
    for raw in files:
        rel = str(Path(raw).resolve().relative_to(root.resolve())).replace("\\", "/")
        if rel == changed_path:
            continue
        score = _proximity(changed_path, rel) * 10
        if any(hint in rel.lower() for hint in TEST_HINTS):
            score -= 3
        ranked.append({"path": rel, "score": score})
    ranked.sort(key=lambda item: (-item["score"], item["path"]))
    return ranked[:cap]
