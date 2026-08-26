from __future__ import annotations

ACK_TOKEN = "repocodex-ack"


def qualifying_ack_evidence(
    reviews: list[dict],
    pr_author: str,
    token: str = ACK_TOKEN,
) -> str | None:
    """Return evidence for an approving review by someone other than the PR author."""
    needle = token.lower()
    author = (pr_author or "").lower()
    for review in reviews:
        user = review.get("user") if isinstance(review.get("user"), dict) else {}
        login = str(user.get("login") or review.get("author") or "")
        state = str(review.get("state") or "").upper()
        body = str(review.get("body") or "")
        if state != "APPROVED":
            continue
        if login.lower() == author:
            continue
        if needle not in body.lower():
            continue
        ident = review.get("id", login)
        return f"review:{ident}"
    return None
