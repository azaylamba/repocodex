from __future__ import annotations

from pathlib import Path

from repocodex.conformance import SCENARIO_TESTS, collect_scenarios, unmapped_scenarios


def test_unmapped_scenarios_are_reported():
    collected = collect_scenarios()
    assert collected
    missing = unmapped_scenarios()
    assert missing == [], f"unmapped scenarios: {missing}"


def test_conformance_map_points_at_real_tests():
    tests_root = Path(__file__).resolve().parent
    corpus = "\n".join(path.read_text(encoding="utf-8") for path in tests_root.glob("test_*.py"))
    missing = [title for title, node in SCENARIO_TESTS.items() if f"def {node}(" not in corpus]
    assert missing == [], f"mapped tests do not exist: {missing}"
