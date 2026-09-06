"""Pin that ENGINE_VERSION is the only engine identity literal."""

from __future__ import annotations

import json
from pathlib import Path

from repocodex import ENGINE_VERSION, ENGINE_VERSION_TOKEN
from repocodex.commands.install import install
from tests.fixtures.repos import init_git_repo

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "repocodex"
INIT = SRC / "__init__.py"


def test_pyproject_version_reads_engine_version():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = {attr = "repocodex.ENGINE_VERSION"}' in text
    project = text.split("[project]", 1)[1].split("\n[", 1)[0]
    assert "version =" not in project


def test_packaged_templates_use_version_token():
    action = (SRC / "data" / "action" / "repocodex.yml").read_text(encoding="utf-8")
    plugin = (SRC / "data" / "plugin" / "plugin.json").read_text(encoding="utf-8")
    root_plugin = (ROOT / "plugin" / "plugin.json").read_text(encoding="utf-8")
    assert ENGINE_VERSION_TOKEN in action
    assert ENGINE_VERSION not in action
    assert json.loads(plugin)["version"] == ENGINE_VERSION_TOKEN
    assert plugin == root_plugin


def test_install_renders_engine_version(tmp_path: Path):
    (tmp_path / "README.md").write_text("sample\n", encoding="utf-8")
    init_git_repo(tmp_path)
    payload = install(tmp_path)
    assert payload["ok"] is True
    action = (tmp_path / ".github" / "workflows" / "repocodex.yml").read_text(encoding="utf-8")
    assert ENGINE_VERSION in action
    assert ENGINE_VERSION_TOKEN not in action
    plugin = json.loads((tmp_path / ".repocodex" / "plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert plugin["version"] == ENGINE_VERSION


def test_engine_version_literal_lives_only_in_init():
    hits: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in {".py", ".md", ".toml", ".yml", ".yaml", ".json"}:
            continue
        rel = path.relative_to(ROOT)
        parts = rel.parts
        if parts[0] in {".git", ".venv", "dist", "build", ".pytest_cache", ".ruff_cache"}:
            continue
        if "__pycache__" in parts or any(part.endswith(".egg-info") for part in parts):
            continue
        if parts[:2] == ("docs", "research") or parts[:2] == ("openspec", "changes"):
            continue
        if path.resolve() == INIT.resolve():
            continue
        if ENGINE_VERSION in path.read_text(encoding="utf-8"):
            hits.append(str(rel))
    assert hits == []


def test_uv_lock_editable_package_matches_engine_version():
    lock = (ROOT / "uv.lock").read_text(encoding="utf-8")
    marker = 'name = "repocodex"\nversion = "'
    idx = lock.find(marker)
    assert idx != -1
    version = lock[idx + len(marker) :].split('"', 1)[0]
    assert version == ENGINE_VERSION
