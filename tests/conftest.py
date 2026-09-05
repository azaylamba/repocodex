"""Shared pytest fixtures and CLI helper for RepoCodex engine tests.

Provide a covered sample architecture repo, a brownfield uncovered repo, and
a subprocess wrapper that invokes the in-tree ``repocodex`` CLI.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from tests.fixtures.repos import SampleRepo, init_git_repo, write_architecture_fixtures

SRC = Path(__file__).resolve().parents[1] / "src"


@pytest.fixture
def repo(tmp_path: Path) -> SampleRepo:
    """Build a git-initialized sample repo with architecture fixtures.

    Writes the billing, streamer, ledger, and notify tree, commits it, and
    returns a SampleRepo for tests that need a covered architecture.
    """
    root = tmp_path / "repo"
    root.mkdir()
    sample = write_architecture_fixtures(root)
    init_git_repo(root)
    return sample


@pytest.fixture
def uncovered_repo(tmp_path: Path) -> Path:
    """Build a brownfield git repo with an uncovered ``src/app.py``.

    Used by first-touch and enforcement tests that start without a
    ``.context`` bundle.
    """
    root = tmp_path / "brownfield"
    root.mkdir()
    (root / "src").mkdir()
    (root / "src" / "app.py").write_text("def main():\n    return 1\n", encoding="utf-8")
    init_git_repo(root)
    return root


def run_cli(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run ``python3 -m repocodex`` with ``args`` in ``cwd``.

    Puts the engine ``src`` tree on PYTHONPATH so the in-tree package is used.

    Args:
        args: CLI arguments after the module name.
        cwd: Working directory for the subprocess.

    Returns:
        Completed process with captured text stdout and stderr.
    """
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        ["python3", "-m", "repocodex", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
