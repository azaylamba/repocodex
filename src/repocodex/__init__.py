"""RepoCodex engine: repository-native executable memory for coding agents."""

from __future__ import annotations

ENGINE_VERSION = "0.0.2"
ENGINE_VERSION_TOKEN = "__ENGINE_VERSION__"
__version__ = ENGINE_VERSION


def render_engine_version(text: str) -> str:
    """Replace the engine-version token in packaged templates with ``ENGINE_VERSION``.

    Args:
        text: Template text that may contain ``ENGINE_VERSION_TOKEN``.

    Returns:
        ``text`` with every token replaced by the running engine version.
    """
    return text.replace(ENGINE_VERSION_TOKEN, ENGINE_VERSION)
