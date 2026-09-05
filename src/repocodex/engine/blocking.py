"""Reasons that promote a validate finding into a required (blocking) check."""

from __future__ import annotations

REQUIRED_CHECK_REASONS = frozenset(
    {
        "drift",
        "claim_broken",
        "skipped_memory",
        "index_sync",
        "contradiction",
    }
)
