from __future__ import annotations

from pathlib import Path

CODING_SKILLS = [
    Path("src/repocodex/data/skills/repocodex-coding/SKILL.md"),
    Path("src/repocodex/data/plugin/skills/repocodex-coding/SKILL.md"),
    Path("plugin/skills/repocodex-coding/SKILL.md"),
]

REVIEW_SKILLS = [
    Path("src/repocodex/data/skills/repocodex-review/SKILL.md"),
    Path("src/repocodex/data/plugin/skills/repocodex-review/SKILL.md"),
    Path("plugin/skills/repocodex-review/SKILL.md"),
]


def test_coding_skill_teaches_orthogonal_types():
    for path in CODING_SKILLS:
        text = path.read_text(encoding="utf-8")
        for name in (
            "TechnicalDecision",
            "InvariantContract",
            "BusinessWorkflow",
            "GuardrailDecision",
        ):
            assert name in text, f"{path} missing {name}"
        assert "Requires `claims`" in text or "**Requires `claims`**" in text
        assert "InvariantContract" in text and "claims" in text
        # WRITE bullet must force the recipe before write (not only a section below the loop)
        write_lines = [
            line
            for line in text.splitlines()
            if "WRITE" in line or "skipped_memory" in line
        ]
        write_blob = "\n".join(write_lines).lower()
        assert "all four" in write_blob or "choose type" in write_blob
        assert "one concept per why" in text.lower() or "One concept per why" in text
        lowered = text.lower()
        assert "independent" in lowered or "coexist" in lowered or "all four" in lowered
        assert "exactly one type" not in lowered
        assert "first match wins" not in lowered
        assert "together" in lowered  # skipped_memory discharge
        assert "enforcement config" in lowered or "enforcement" in lowered


def test_review_skill_flags_type_misuse_not_multi_type():
    for path in REVIEW_SKILLS:
        text = path.read_text(encoding="utf-8")
        assert "InvariantContract" in text
        assert "missing `claims`" in text or "missing claims" in text.lower()
        assert "enforcement config" in text.lower() or "enforcement" in text.lower()
        assert "same" in text.lower() and "why" in text.lower()
        lowered = text.lower()
        assert "do **not** flag" in text.lower() or "do not flag" in lowered
        assert "distinct whys" in lowered or "distinct why" in lowered
