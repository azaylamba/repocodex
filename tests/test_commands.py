from __future__ import annotations

import json
from pathlib import Path

from tests.conftest import run_cli
from tests.fixtures.repos import GRACE_CONCEPT


def test_validate_json_engine_version(repo):
    result = run_cli(["validate", "--diff"], cwd=repo.root)
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["engine_version"] == "1.0.0"


def test_context_staged_retrieval(repo):
    result = run_cli(["context", "src/billing/PaymentGateway.ts"], cwd=repo.root)
    payload = json.loads(result.stdout)
    identities = [c["identity"] for c in payload["concepts"]]
    assert "invariants/enterprise-grace-period" in identities
    bodies = [c.get("body") for c in payload["concepts"] if c["identity"] == "invariants/enterprise-grace-period"]
    assert bodies and "grace" in bodies[0].lower()
    titles_only = payload["related"]
    assert all("body" not in item for item in titles_only)


def test_write_and_reconcile_gate(repo):
    concept = repo.root / "incoming.md"
    concept.write_text(GRACE_CONCEPT.replace("enterprise-grace-period", "enterprise-grace-period-2"), encoding="utf-8")
    result = run_cli(
        ["write", str(concept), "--identity", "invariants/enterprise-grace-period-2"],
        cwd=repo.root,
    )
    payload = json.loads(result.stdout)
    assert payload["accepted"] is True
    assert (repo.root / ".context" / "invariants" / "enterprise-grace-period-2.md").exists()
    rec = run_cli(
        ["reconcile", str(concept), "--identity", "invariants/enterprise-grace-period-2"],
        cwd=repo.root,
    )
    assert json.loads(rec.stdout)["accepted"] is True


def test_repair_install_bootstrap_audit(repo):
    repair = json.loads(run_cli(["repair"], cwd=repo.root).stdout)
    assert "engine_version" in repair
    assert "task" in repair
    installed = json.loads(run_cli(["install"], cwd=repo.root).stdout)
    assert any("pre-commit" in item for item in installed["installed"])
    assert any("repocodex.yml" in item for item in installed["installed"])
    assert (repo.root / ".cursor" / "skills" / "repocodex-coding" / "SKILL.md").exists()
    boot = json.loads(run_cli(["bootstrap"], cwd=repo.root).stdout)
    assert boot.get("status") == "draft"
    audit = json.loads(run_cli(["audit", "--sample-size", "2"], cwd=repo.root).stdout)
    assert "sampled" in audit
    assert "distinctiveness" in audit
