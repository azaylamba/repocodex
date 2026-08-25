from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from repocodex import ENGINE_VERSION

DEFAULT_EXCLUSIONS = [
    "vendor/**",
    "node_modules/**",
    "dist/**",
    "build/**",
    ".git/**",
    "**/.venv/**",
    "**/__pycache__/**",
]


@dataclass
class RepoConfig:
    root: Path
    engine_version: str = ENGINE_VERSION
    posture: str = "shadow"
    distinctiveness_ceiling: int = 100
    scope_lines: int = 40
    exclusions: list[str] = field(default_factory=lambda: list(DEFAULT_EXCLUSIONS))
    ignore_globs: list[str] = field(default_factory=list)
    impact_read_cap: int = 12
    audit_sample_size: int = 10

    @property
    def all_exclusions(self) -> list[str]:
        seen: list[str] = []
        for glob in [*self.exclusions, *self.ignore_globs]:
            if glob not in seen:
                seen.append(glob)
        return seen


def _default_ceiling(root: Path) -> int:
    try:
        files = [p for p in root.rglob("*") if p.is_file()]
        n = max(1, len(files))
    except OSError:
        n = 100
    return max(20, min(500, n // 2 + 20))


def load_ignore_file(path: Path) -> list[str]:
    if not path.exists():
        return []
    globs: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            globs.append(stripped)
    return globs


def load_config(root: Path) -> RepoConfig:
    root = root.resolve()
    data: dict = {}
    toml_path = root / ".repocodex.toml"
    if toml_path.exists():
        data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
    ignore = load_ignore_file(root / ".repocodexignore")
    ceiling = data.get("distinctiveness_ceiling")
    if ceiling is None:
        ceiling = _default_ceiling(root)
    exclusions = list(data.get("exclusions", DEFAULT_EXCLUSIONS))
    return RepoConfig(
        root=root,
        engine_version=str(data.get("engine_version", ENGINE_VERSION)),
        posture=str(data.get("posture", "shadow")),
        distinctiveness_ceiling=int(ceiling),
        scope_lines=int(data.get("scope_lines", 40)),
        exclusions=exclusions,
        ignore_globs=ignore,
        impact_read_cap=int(data.get("impact_read_cap", 12)),
        audit_sample_size=int(data.get("audit_sample_size", 10)),
    )
