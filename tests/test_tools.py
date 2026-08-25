from __future__ import annotations

from pathlib import Path

from repocodex.tools.git import git_version, run_git
from repocodex.tools.ripgrep import rg_count, rg_version, search_file


def test_reports_rg_and_git_versions():
    assert "ripgrep" in rg_version().lower() or rg_version()[0].isdigit()
    assert git_version().startswith("git version") or git_version()[0].isdigit()


def test_rg_counts_and_file_search(tmp_path: Path):
    target = tmp_path / "a.py"
    target.write_text("yield from iter_batches()\n", encoding="utf-8")
    hits = search_file("yield", target)
    assert hits
    assert rg_count("yield", tmp_path) >= 1


def test_git_wrapper_structured_result(tmp_path: Path):
    run_git(["init"], cwd=tmp_path)
    result = run_git(["rev-parse", "--is-inside-work-tree"], cwd=tmp_path)
    assert result.returncode == 0
    assert "true" in result.stdout
