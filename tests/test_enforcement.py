from __future__ import annotations

import json
import os
import stat
from pathlib import Path

from repocodex.commands.install import install
from repocodex.commands.validate import validate
from tests.fixtures.repos import init_git_repo


def test_brownfield_uncovered_passes_ratchet(uncovered_repo: Path):
    (uncovered_repo / ".repocodex.toml").write_text(
        'engine_version = "1.0.0"\nposture = "ratchet"\n',
        encoding="utf-8",
    )
    (uncovered_repo / "src" / "app.py").write_text("def main():\n    return 2\n", encoding="utf-8")
    payload = validate(uncovered_repo)
    assert payload["blocking"] is False


def test_covered_file_without_memory_fails_ratchet(repo):
    repo.payment_gateway.write_text(
        repo.payment_gateway.read_text(encoding="utf-8") + "\nexport const extra = 1;\n",
        encoding="utf-8",
    )
    payload = validate(repo.root)
    assert payload["skipped_memory"]
    assert payload["blocking"] is True


def test_memory_exempt_requires_ack_and_logs(repo):
    repo.streamer.write_text("broken\n", encoding="utf-8")
    denied = validate(repo.root, memory_exempt=True, review_ack=False)
    assert "exempt_requires_review_ack" in denied["blocking_reasons"]
    allowed = validate(repo.root, memory_exempt=True, review_ack=True)
    assert allowed["memory_exempt"] is True
    assert allowed["blocking"] is False
    log = (repo.root / ".context" / "log.md").read_text(encoding="utf-8")
    assert "memory-exempt" in log
    assert list((repo.root / ".context" / "repair-tasks").glob("exempt-*.md"))


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
