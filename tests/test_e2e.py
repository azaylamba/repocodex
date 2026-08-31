from __future__ import annotations

import json
import subprocess
from pathlib import Path

from tests.conftest import run_cli
from tests.fixtures.repos import PAYMENT_GATEWAY


def test_agent_loop_context_edit_validate_commit(repo):
    ctx = json.loads(run_cli(["context", "src/billing/PaymentGateway.ts"], cwd=repo.root).stdout)
    assert ctx["concepts"]
    repo.payment_gateway.write_text(
        PAYMENT_GATEWAY.replace("await charge(account);", "await charge(account);\n  return;"),
        encoding="utf-8",
    )
    verdict = json.loads(run_cli(["validate", "--diff"], cwd=repo.root).stdout)
    assert verdict["engine_version"] == "0.0.1"
    repair = json.loads(run_cli(["repair"], cwd=repo.root).stdout)
    assert "engine_version" in repair
    subprocess.run(["git", "add", "-A"], cwd=repo.root, check=True, capture_output=True)
    # commit without hook to confirm the repo stays consistent; hook deny is tested separately
    subprocess.run(
        ["git", "commit", "-m", "edit", "--no-verify"],
        cwd=repo.root,
        check=True,
        capture_output=True,
    )
    log = subprocess.run(
        ["git", "log", "-1", "--pretty=%s"],
        cwd=repo.root,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "edit" in log.stdout


def test_determinism_identical_payloads(repo):
    first = json.loads(run_cli(["validate", "--all"], cwd=repo.root).stdout)
    second = json.loads(run_cli(["validate", "--all"], cwd=repo.root).stdout)
    for key in ("result", "engine_version", "lost", "weak", "impacted_scenarios"):
        assert first[key] == second[key]
