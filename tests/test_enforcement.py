"""Pin enforcement posture, exemptions, and install hook contracts.

Cover first-touch on brownfield, ratchet on covered files without memory,
memory-exempt acknowledgments, supersede contradictions, and CI pin install.
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

from repocodex.commands.install import install
from repocodex.commands.validate import validate
from tests.fixtures.repos import init_git_repo


def test_brownfield_uncovered_fails_first_touch(uncovered_repo: Path):
    (uncovered_repo / ".repocodex.toml").write_text(
        'engine_version = "0.0.1"\nposture = "ratchet"\n',
        encoding="utf-8",
    )
    (uncovered_repo / "src" / "app.py").write_text("def main():\n    return 2\n", encoding="utf-8")
    payload = validate(uncovered_repo)
    assert payload["blocking"] is True
    assert any(
        item.get("reason") == "uncovered_file_without_memory" for item in payload["skipped_memory"]
    )


def test_covered_file_without_memory_fails_ratchet(repo):
    text = repo.streamer.read_text(encoding="utf-8")
    repo.streamer.write_text(text.rstrip() + "\n" + ("\n" * 80) + "def refund_batches():\n    return []\n", encoding="utf-8")
    payload = validate(repo.root)
    assert payload["skipped_memory"]
    assert payload["blocking"] is True


def test_memory_exempt_requires_ack_and_logs(repo):
    repo.streamer.write_text("broken\n", encoding="utf-8")
    denied = validate(repo.root, memory_exempt=True)
    assert denied["blocking"] is True
    assert denied.get("exemption_refused") == "missing_acknowledgment"
    import json
    import subprocess

    ack = repo.root / ".repocodex" / "acknowledgments" / "memory-exempt.json"
    ack.parent.mkdir(parents=True, exist_ok=True)
    ack.write_text(
        json.dumps({"kind": "memory-exempt", "reviewer": "agent:repocodex-review"}),
        encoding="utf-8",
    )
    subprocess.run(["git", "add", str(ack)], cwd=repo.root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "ack", "--no-verify"], cwd=repo.root, check=True, capture_output=True)
    allowed = validate(repo.root, memory_exempt=True, ack_file=str(ack.relative_to(repo.root)))
    assert allowed["memory_exempt"] is True
    assert allowed["blocking"] is False
    assert allowed["audit_entries"]
    assert allowed["repair_tasks"]
    assert "memory-exempt" not in (repo.root / ".context" / "log.md").read_text(encoding="utf-8")


def test_contradiction_on_double_supersede(repo):
    from repocodex.schema import parse_concept, serialize_concept

    a = repo.root / ".context" / "invariants" / "v2.md"
    b = repo.root / ".context" / "invariants" / "v3.md"
    base = (repo.root / ".context" / "invariants" / "enterprise-grace-period.md").read_text(encoding="utf-8")
    doc = parse_concept(base, "invariants/v2")
    doc.frontmatter.supersedes = "invariants/enterprise-grace-period"
    doc.frontmatter.rationale = "change"
    a.write_text(serialize_concept(doc), encoding="utf-8")
    doc.identity = "invariants/v3"
    b.write_text(serialize_concept(doc).replace("invariants/v2", "invariants/v3"), encoding="utf-8")
    payload = validate(repo.root, all_concepts=True)
    assert payload["contradictions"]


def test_install_hook_is_executable(repo):
    install(repo.root)
    hook = repo.root / ".git" / "hooks" / "pre-commit"
    assert hook.exists()
    assert hook.stat().st_mode & stat.S_IXUSR
    text = hook.read_text(encoding="utf-8")
    assert "validate" in text
    assert "git commit" in text or "Filters" in text or "filters" in text.lower()


def test_install_writes_default_pin_and_pypi_action(tmp_path: Path):
    (tmp_path / "README.md").write_text("sample\n", encoding="utf-8")
    init_git_repo(tmp_path)
    payload = install(tmp_path)
    assert payload["ok"] is True
    pin = (tmp_path / ".repocodex.toml").read_text(encoding="utf-8")
    assert 'engine_version = "0.0.1"' in pin
    action = (tmp_path / ".github" / "workflows" / "repocodex.yml").read_text(encoding="utf-8")
    assert 'pip install "repocodex==${PIN}"' in action
    assert "git+https://github.com/azaylamba/repocodex.git" not in action
