"""Pin retrieval ranking, draft exclusion, and code-hit caps.

Drafts stay out of default retrieve. Provenance ranks above bare concepts.
Code-side hits are capped, and churn counts skip ``--follow``.
"""

from __future__ import annotations

from pathlib import Path

from repocodex.engine.code_impact import rank_code_hits
from repocodex.retrieval import _churn_count, retrieve
from repocodex.schema import ConceptStatus, Source, parse_concept, serialize_concept
from tests.fixtures.repos import GRACE_CONCEPT, init_git_repo


def test_drafts_excluded_from_default_retrieval(repo):
    path = repo.root / ".context" / "invariants" / "draft-item.md"
    text = (repo.root / ".context" / "invariants" / "enterprise-grace-period.md").read_text(encoding="utf-8")
    doc = parse_concept(text, "invariants/draft-item")
    doc.frontmatter.status = ConceptStatus.draft
    doc.frontmatter.sources = [Source(resource="git://commit/abc", title="commit")]
    path.write_text(serialize_concept(doc), encoding="utf-8")
    from repocodex.store.reverse_index import regenerate_all

    regenerate_all(repo.root)
    payload = retrieve(repo.root, ["src/billing/PaymentGateway.ts"])
    ids = [c["identity"] for c in payload["concepts"]]
    assert "invariants/draft-item" not in ids
    with_drafts = retrieve(repo.root, ["src/billing/PaymentGateway.ts"], include_drafts=True)
    assert "invariants/draft-item" in [c["identity"] for c in with_drafts["concepts"]]


def test_provenance_ranks_above_bare(repo):
    sourced = parse_concept(
        (repo.root / ".context" / "invariants" / "enterprise-grace-period.md").read_text(encoding="utf-8"),
        "invariants/enterprise-grace-period",
    )
    sourced.frontmatter.sources = [Source(resource="PR-1")]
    (repo.root / ".context" / "invariants" / "enterprise-grace-period.md").write_text(
        serialize_concept(sourced), encoding="utf-8"
    )
    payload = retrieve(repo.root, ["src/billing/PaymentGateway.ts"])
    assert payload["concepts"][0]["identity"] in {
        "invariants/enterprise-grace-period",
        "workflows/checkout-capture",
    }


def test_code_side_hits_are_capped(repo):
    for i in range(30):
        (repo.root / "src" / f"hit_{i}.py").write_text("capturePayment = 1\n", encoding="utf-8")
    ranked = rank_code_hits("src/billing/PaymentGateway.ts", "capturePayment", repo.root, cap=12)
    assert len(ranked) <= 12


def test_churn_skips_follow_and_untracked_is_zero(tmp_path: Path, monkeypatch):
    from repocodex import retrieval

    root = tmp_path / "repo"
    root.mkdir()
    (root / ".context" / "invariants").mkdir(parents=True)
    (root / ".context" / "invariants" / "seed.md").write_text(GRACE_CONCEPT, encoding="utf-8")
    init_git_repo(root)
    (root / ".context" / "invariants" / "fresh.md").write_text(GRACE_CONCEPT, encoding="utf-8")

    calls: list[list[str]] = []
    original = retrieval.run_git

    def spy(args, cwd):
        calls.append(list(args))
        return original(args, cwd)

    monkeypatch.setattr(retrieval, "run_git", spy)
    assert _churn_count(root, "invariants/fresh") == 0
    assert _churn_count(root, "invariants/seed") >= 1
    git_args = [tuple(args) for args in calls]
    assert git_args
    assert all("--follow" not in args for args in git_args)
