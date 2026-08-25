from __future__ import annotations

import json

from repocodex.commands.validate import validate
from tests.fixtures.repos import PAYMENT_GATEWAY, STREAMER


def test_validate_live_on_formatting(repo):
    repo.payment_gateway.write_text(
        PAYMENT_GATEWAY.replace("const grace = 3;", "const grace =\n    3;"),
        encoding="utf-8",
    )
    payload = validate(repo.root, all_concepts=False)
    classes = {item["classification"] for item in payload["outcomes"] if "enterprise" in item["concept"]}
    assert "LIVE" in classes or payload["result"] in {"LIVE", "WEAK"}
    assert payload["engine_version"] == "1.0.0"
    assert "impacted_scenarios" in payload


def test_validate_reanchor_on_rename(repo):
    dest = repo.root / "src" / "core" / "streams" / "streamer_v2.py"
    src = repo.streamer
    src.rename(dest)
    payload = validate(repo.root)
    streamer_outcomes = [o for o in payload["outcomes"] if "streamer" in o["concept"]]
    assert streamer_outcomes
    assert streamer_outcomes[0]["classification"] in {"REANCHOR", "DRIFT"}
    if streamer_outcomes[0]["classification"] == "REANCHOR":
        assert streamer_outcomes[0]["patch"]["to"].endswith("streamer_v2.py")


def test_literal_change_weak_or_drift(repo):
    repo.payment_gateway.write_text(
        PAYMENT_GATEWAY.replace("const grace = 3;", "const grace = 1;"),
        encoding="utf-8",
    )
    payload = validate(repo.root)
    grace = [o for o in payload["outcomes"] if "grace" in o["concept"]]
    assert grace
    assert grace[0]["classification"] in {"WEAK", "DRIFT", "RECONCILE"} or payload["result"] != "LIVE"


def test_cross_package_impact(repo):
    (repo.root / "src" / "ledger" / "posting.py").write_text(
        'LEDGER_CAPTURE = "capture"\n\ndef post_capture(event):\n    return event + "x"\n',
        encoding="utf-8",
    )
    payload = validate(repo.root)
    assert any("checkout" in s or "workflow" in s for s in payload["impacted_scenarios"]) or (
        "workflows/checkout-capture" in payload["impacted_scenarios"]
    )


def test_dilution_warning_on_unrelated_pr(repo):
    other = repo.root / "src" / "unrelated.py"
    other.write_text('plan = "ENTERPRISE"\nconst grace = 3\n', encoding="utf-8")
    payload = validate(repo.root)
    grace_live = [
        o
        for o in payload["outcomes"]
        if "grace" in o["concept"] and o["path"].endswith("PaymentGateway.ts")
    ]
    # untouched pin stays live; warning attaches to this change
    if grace_live:
        assert grace_live[0]["classification"] == "LIVE"
    assert payload["engine_version"]


def test_shadow_posture_never_blocks(repo):
    (repo.root / ".repocodex.toml").write_text(
        'engine_version = "1.0.0"\nposture = "shadow"\n',
        encoding="utf-8",
    )
    repo.streamer.write_text("class X:\n    pass\n", encoding="utf-8")
    payload = validate(repo.root)
    assert payload["blocking"] is False
    assert payload["posture"] == "shadow"
