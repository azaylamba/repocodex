from __future__ import annotations

from tests.conftest import run_cli


def test_cli_module_exposes_help(tmp_path):
    result = run_cli(["--help"], cwd=tmp_path)
    assert result.returncode == 0
    assert "validate" in result.stdout
    assert "write" in result.stdout
    assert "reconcile" in result.stdout
    assert "context" in result.stdout
    assert "repair" in result.stdout
    assert "install" in result.stdout
    assert "bootstrap" in result.stdout
    assert "audit" in result.stdout
