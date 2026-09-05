"""Pin first-touch skipped_memory rules for uncovered files.

Substantive edits to files without a pinning concept require WRITE. Comments,
lockfiles, and a successful write discharge do not leave skipped_memory armed.
"""

from __future__ import annotations

import json
from pathlib import Path

from repocodex.commands.validate import validate
from repocodex.commands.write import write_memory
from tests.conftest import run_cli
from tests.fixtures.repos import STREAMER

SHADOW_TOML = 'engine_version = "0.0.1"\nposture = "shadow"\n'
RATCHET_TOML = 'engine_version = "0.0.1"\nposture = "ratchet"\n'
FIRST_TOUCH_SOURCE = 'def main():\n    FIRST_TOUCH_QZX9 = 1\n    return FIRST_TOUCH_QZX9\n'
FIRST_TOUCH_CONCEPT = """\
---
type: TechnicalDecision
title: Handler returns the first-touch token
generated: { by: test/repocodex, at: 2026-09-01T00:00:00Z }
status: stable
verification:
  engine: ripgrep
  anchors:
    - path: src/app.py
      all_of: ["FIRST_TOUCH_QZX9", "main"]
---

Keep FIRST_TOUCH_QZX9 in main so the uncovered handler stays pinned.
"""


def _shadow(root: Path) -> None:
    (root / ".repocodex.toml").write_text(SHADOW_TOML, encoding="utf-8")


def _first_touch_entry(payload: dict, path: str = "src/app.py") -> dict | None:
    for item in payload.get("skipped_memory") or []:
        if item.get("path") == path:
            return item
    return None


def test_uncovered_substantive_edit_is_write_and_blocking(uncovered_repo: Path):
    _shadow(uncovered_repo)
    (uncovered_repo / "src" / "app.py").write_text("def main():\n    return 2\n", encoding="utf-8")
    payload = validate(uncovered_repo)
    entry = _first_touch_entry(payload)
    assert entry is not None
    assert entry["reason"] == "uncovered_file_without_memory"
    assert payload["result"] == "WRITE"
    assert "skipped_memory" in payload["blocking_reasons"]
    assert payload["blocking"] is True


def test_writing_pinning_concept_discharges_first_touch(uncovered_repo: Path):
    _shadow(uncovered_repo)
    (uncovered_repo / "src" / "app.py").write_text(FIRST_TOUCH_SOURCE, encoding="utf-8")
    armed = validate(uncovered_repo)
    assert _first_touch_entry(armed) is not None
    result = write_memory(
        uncovered_repo,
        ".",
        identity="decisions/first-touch-app",
        stdin_text=FIRST_TOUCH_CONCEPT,
    )
    assert result["accepted"] is True
    payload = validate(uncovered_repo)
    assert _first_touch_entry(payload) is None
    assert "skipped_memory" not in payload["blocking_reasons"]
    assert payload["blocking"] is False


def test_lockfile_and_gitignore_skip_first_touch(uncovered_repo: Path):
    _shadow(uncovered_repo)
    (uncovered_repo / "uv.lock").write_text('foo = "1"\n', encoding="utf-8")
    lock_only = validate(uncovered_repo)
    assert lock_only["skipped_memory"] == []
    assert lock_only["blocking"] is False

    (uncovered_repo / ".gitignore").write_text("*.pyc\n", encoding="utf-8")
    (uncovered_repo / "src" / "app.py").write_text("def main():\n    return 2\n", encoding="utf-8")
    paired = validate(uncovered_repo)
    paths = [item["path"] for item in paired["skipped_memory"]]
    assert "src/app.py" in paths
    assert ".gitignore" not in paths
    assert "uv.lock" not in paths
    assert _first_touch_entry(paired)["reason"] == "uncovered_file_without_memory"


def test_comment_or_whitespace_uncovered_edit_does_not_arm(uncovered_repo: Path):
    _shadow(uncovered_repo)
    (uncovered_repo / "src" / "app.py").write_text(
        "def main():\n    # note only\n    return 1\n",
        encoding="utf-8",
    )
    comment_only = validate(uncovered_repo)
    assert comment_only["skipped_memory"] == []
    assert comment_only["blocking"] is False

    (uncovered_repo / "src" / "app.py").write_text("def main():\n    return 1\n\n", encoding="utf-8")
    whitespace_only = validate(uncovered_repo)
    assert whitespace_only["skipped_memory"] == []
    assert whitespace_only["blocking"] is False


def test_shadow_blocks_skipped_memory_not_claim_broken(repo):
    _shadow(repo.root)
    from tests.fixtures.repos import PAYMENT_GATEWAY

    repo.payment_gateway.write_text(
        PAYMENT_GATEWAY.replace("const grace = 3;", "const grace = 1;"),
        encoding="utf-8",
    )
    claim_only = validate(repo.root)
    assert claim_only["claim_findings"]
    assert "claim_broken" in claim_only["blocking_reasons"]
    assert not claim_only["skipped_memory"]
    assert claim_only["blocking"] is False

    _append_outside_region(repo.streamer, "def refund_batches():\n    return []\n")
    skipped = validate(repo.root)
    assert skipped["skipped_memory"]
    assert "skipped_memory" in skipped["blocking_reasons"]
    assert skipped["blocking"] is True


def test_shadow_and_ratchet_agree_on_first_touch_reasons(uncovered_repo: Path):
    (uncovered_repo / "src" / "app.py").write_text("def main():\n    return 2\n", encoding="utf-8")
    (uncovered_repo / ".repocodex.toml").write_text(RATCHET_TOML, encoding="utf-8")
    ratchet = validate(uncovered_repo)
    _shadow(uncovered_repo)
    shadow = validate(uncovered_repo)
    assert shadow["blocking_reasons"] == ratchet["blocking_reasons"]
    assert "skipped_memory" in shadow["blocking_reasons"]
    assert shadow["blocking"] is True
    assert ratchet["blocking"] is True


def test_drift_plus_skipped_memory_keeps_reconcile(repo):
    from tests.fixtures.repos import STREAMER as STREAMER_SRC

    (repo.root / "src" / "decoy_a.py").write_text(STREAMER_SRC, encoding="utf-8")
    (repo.root / "src" / "decoy_b.py").write_text(STREAMER_SRC, encoding="utf-8")
    repo.streamer.write_text("broken\n", encoding="utf-8")
    payload = validate(repo.root)
    assert payload["result"] == "RECONCILE"
    assert payload["skipped_memory"]
    assert "skipped_memory" in payload["blocking_reasons"]
    assert payload["blocking"] is True


def test_hook_and_check_exit_1_on_first_touch(uncovered_repo: Path):
    import subprocess

    _shadow(uncovered_repo)
    (uncovered_repo / "src" / "app.py").write_text("def main():\n    return 2\n", encoding="utf-8")
    check = run_cli(["validate", "--diff", "--check"], cwd=uncovered_repo)
    assert check.returncode == 1
    subprocess.run(["git", "add", "src/app.py"], cwd=uncovered_repo, check=True, capture_output=True)
    hook = run_cli(["validate", "--diff", "--hook"], cwd=uncovered_repo)
    assert hook.returncode == 1
    hook_payload = json.loads(hook.stdout)
    assert hook_payload["blocking"] is True


def test_write_discharges_out_of_region_hunks_on_the_same_run(uncovered_repo: Path):
    """A pinning write must clear skipped-memory even when new code sits outside the anchor region.

    Typical agent session: edit a tracked file, `repocodex write` (untracked `.context/`),
    re-validate. If changed_files omits untracked memory, pinning_updated is empty and
    covered-file ratchet re-arms as covered_file_without_memory_update.
    """
    _shadow(uncovered_repo)
    (uncovered_repo / "src" / "app.py").write_text(
        FIRST_TOUCH_SOURCE.rstrip() + "\n" + ("\n" * 80) + "def refund_batches():\n    return []\n",
        encoding="utf-8",
    )
    result = write_memory(
        uncovered_repo,
        ".",
        identity="decisions/first-touch-app",
        stdin_text=FIRST_TOUCH_CONCEPT,
    )
    assert result["accepted"] is True
    payload = validate(uncovered_repo)
    assert any(path.startswith(".context/") for path in payload["changed_files"])
    assert not payload["skipped_memory"]
    assert payload["blocking"] is False


def test_untracked_new_file_listed_alongside_tracked_edit(uncovered_repo: Path):
    _shadow(uncovered_repo)
    (uncovered_repo / "src" / "app.py").write_text("def main():\n    return 2\n", encoding="utf-8")
    (uncovered_repo / "src" / "new_handler.py").write_text("def handle():\n    return 1\n", encoding="utf-8")
    payload = validate(uncovered_repo)
    assert "src/app.py" in payload["changed_files"]
    assert "src/new_handler.py" in payload["changed_files"]
    reasons = {item["path"]: item["reason"] for item in payload["skipped_memory"]}
    assert reasons.get("src/app.py") == "uncovered_file_without_memory"
    assert reasons.get("src/new_handler.py") == "uncovered_file_without_memory"


def test_coding_skill_names_write_and_forbids_live_with_skipped_memory():
    roots = [
        Path("src/repocodex/data/skills/repocodex-coding/SKILL.md"),
        Path("src/repocodex/data/plugin/skills/repocodex-coding/SKILL.md"),
        Path("plugin/skills/repocodex-coding/SKILL.md"),
    ]
    for path in roots:
        text = path.read_text(encoding="utf-8")
        assert "WRITE" in text
        assert "skipped_memory" in text
        assert "repocodex write" in text
        lowered = text.lower()
        assert "blocking" in lowered
        live_lines = [line for line in text.splitlines() if "LIVE" in line]
        joined = "\n".join(live_lines)
        assert "skipped_memory" in joined


def _append_outside_region(path: Path, snippet: str) -> None:
    original = path.read_text(encoding="utf-8")
    path.write_text(original.rstrip() + "\n" + ("\n" * 80) + snippet, encoding="utf-8")
    assert STREAMER.splitlines()[0] in original
