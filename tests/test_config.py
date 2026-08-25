from __future__ import annotations

from pathlib import Path

from repocodex.config import load_config


def test_loads_toml_and_ignore_file(tmp_path: Path):
    (tmp_path / ".repocodex.toml").write_text(
        'engine_version = "1.0.0"\n'
        'posture = "shadow"\n'
        "distinctiveness_ceiling = 12\n"
        "scope_lines = 25\n"
        'exclusions = ["vendor/**"]\n',
        encoding="utf-8",
    )
    (tmp_path / ".repocodexignore").write_text("generated/**\n*.min.js\n", encoding="utf-8")
    cfg = load_config(tmp_path)
    assert cfg.engine_version == "1.0.0"
    assert cfg.posture == "shadow"
    assert cfg.distinctiveness_ceiling == 12
    assert cfg.scope_lines == 25
    assert "vendor/**" in cfg.exclusions
    assert "generated/**" in cfg.ignore_globs
    assert "*.min.js" in cfg.ignore_globs


def test_defaults_when_files_missing(tmp_path: Path):
    cfg = load_config(tmp_path)
    assert cfg.engine_version == "1.0.0"
    assert cfg.posture == "shadow"
    assert cfg.scope_lines == 40
    assert cfg.distinctiveness_ceiling > 0
