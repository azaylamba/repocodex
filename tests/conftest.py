from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from tests.fixtures.repos import SampleRepo, init_git_repo, write_architecture_fixtures

SRC = Path(__file__).resolve().parents[1] / "src"


@pytest.fixture
def repo(tmp_path: Path) -> SampleRepo:
    root = tmp_path / "repo"
    root.mkdir()
    sample = write_architecture_fixtures(root)
    init_git_repo(root)
    return sample


@pytest.fixture
def uncovered_repo(tmp_path: Path) -> Path:
    root = tmp_path / "brownfield"
    root.mkdir()
    (root / "src").mkdir()
    (root / "src" / "app.py").write_text("def main():\n    return 1\n", encoding="utf-8")
    init_git_repo(root)
    return root


def run_cli(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
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
