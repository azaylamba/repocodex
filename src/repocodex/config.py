"""Load `.repocodex.toml` / `.repocodexignore` and pin the running engine version."""

from __future__ import annotations

import fnmatch
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from repocodex import ENGINE_VERSION
from repocodex.schema import envelope
from repocodex.tools.git import git_ls_files

DEFAULT_EXCLUSIONS = [
    "vendor/**",
    "node_modules/**",
    "dist/**",
    "build/**",
    ".git/**",
    "**/.venv/**",
    "**/__pycache__/**",
    "**/cdk.out/**",
    "**/.kiro/**",
    "**/coverage/**",
    "**/.next/**",
]


def _skip_walk_dir_names(exclusions: list[str]) -> frozenset[str]:
    """Collect directory names that tree walks should skip from exclusion globs."""
    names = {"venv", "env", ".nuxt", ".tox", ".mypy_cache", ".pytest_cache", ".cache", ".turbo"}
    for glob in exclusions:
        stem = glob.replace("/**", "").replace("**/", "").strip("/")
        if stem and "*" not in stem and "/" not in stem:
            names.add(stem)
    return frozenset(names)


SKIP_WALK_DIR_NAMES = _skip_walk_dir_names(DEFAULT_EXCLUSIONS)


class EngineVersionMismatch(Exception):
    """Raised when `.repocodex.toml` pins a different engine than this package."""

    def __init__(self, pinned: str, running: str) -> None:
        super().__init__(f"engine_version_mismatch: pinned={pinned} running={running}")
        self.pinned = pinned
        self.running = running

    def to_json(self) -> dict:
        """Return a CLI envelope describing the pin mismatch."""
        return envelope(
            {
                "error": "engine_version_mismatch",
                "pinned": self.pinned,
                "running": self.running,
            }
        )


@dataclass
class RepoConfig:
    """Resolved engine settings for one repository root."""

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
        """Config exclusions plus ignore-file globs, first occurrence kept."""
        seen: list[str] = []
        for glob in [*self.exclusions, *self.ignore_globs]:
            if glob not in seen:
                seen.append(glob)
        return seen


def normalize_repo_path(path: str) -> str:
    """Normalize slashes and strip a leading ``./`` from a repo-relative path."""
    normalized = path.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def matches_exclusion(path: str, globs: list[str]) -> bool:
    """Return True when ``path`` matches any gitignore-style exclusion glob."""
    normalized = normalize_repo_path(path)
    name = Path(normalized).name
    for glob in globs:
        if fnmatch.fnmatch(normalized, glob) or fnmatch.fnmatch(name, glob):
            return True
        if glob.endswith("/**") and normalized.startswith(glob[:-3]):
            return True
    return False


def _default_ceiling(root: Path, exclusions: list[str]) -> int:
    """Derive a distinctiveness ceiling from the size of the tracked tree."""
    files = [
        path
        for path in git_ls_files(root)
        if not matches_exclusion(path, exclusions)
    ]
    n = max(1, len(files)) if files else 1
    return max(20, min(500, n // 2 + 20))


def load_ignore_file(path: Path) -> list[str]:
    """Return non-comment glob lines from an ignore file, or ``[]`` if missing."""
    if not path.exists():
        return []
    globs: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            globs.append(stripped)
    return globs


def load_config(root: Path, *, enforce_pin: bool = True) -> RepoConfig:
    """Load repo config from `.repocodex.toml` and `.repocodexignore`.

    Args:
        root: Repository root.
        enforce_pin: When True, raise if the file's engine_version disagrees
            with this package.

    Raises:
        EngineVersionMismatch: Pin disagrees with ``ENGINE_VERSION``.
    """
    root = root.resolve()
    data: dict = {}
    toml_path = root / ".repocodex.toml"
    if toml_path.exists():
        data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
    ignore = load_ignore_file(root / ".repocodexignore")
    exclusions = list(data.get("exclusions", DEFAULT_EXCLUSIONS))
    ceiling = data.get("distinctiveness_ceiling")
    if ceiling is None:
        ceiling = _default_ceiling(root, [*exclusions, *ignore])
    config = RepoConfig(
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
    if enforce_pin and config.engine_version != ENGINE_VERSION:
        raise EngineVersionMismatch(config.engine_version, ENGINE_VERSION)
    return config
