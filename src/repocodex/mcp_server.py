from __future__ import annotations

import json
from pathlib import Path

from repocodex.commands.context import context_for
from repocodex.commands.validate import validate
from repocodex.commands.write import write_memory
from repocodex.engine.impact import intent_impact
from repocodex.store.bundle import load_concepts
from repocodex.store.reverse_index import merged_index


def _root() -> Path:
    return Path.cwd()


def tool_get_context(paths: list[str]) -> dict:
    return context_for(_root(), paths)


def tool_get_impact(base: str | None = None) -> dict:
    verdict = validate(_root(), base=base, staged=False, all_concepts=False)
    concepts = load_concepts(_root())
    index = merged_index(_root())
    files = verdict.get("changed_files") or []
    return {
        "engine_version": verdict["engine_version"],
        "impacted_scenarios": intent_impact(files, concepts, index),
        "advisory": True,
    }


def tool_read_concept(identity: str) -> dict:
    for doc in load_concepts(_root()):
        if doc.identity == identity:
            return {
                "engine_version": context_for(_root(), []).get("engine_version"),
                "identity": identity,
                "frontmatter": json.loads(
                    # round-trip via model dump
                    json.dumps(doc.frontmatter.model_dump(mode="json"), default=str)
                ),
                "body": doc.body,
            }
    return {"error": "not_found", "identity": identity}


def tool_write_memory(markdown: str, identity: str | None = None) -> dict:
    return write_memory(_root(), ".", identity=identity, stdin_text=markdown)


def tool_validate_diff(base: str | None = None, staged: bool = False) -> dict:
    return validate(_root(), base=base, staged=staged, all_concepts=False)


def tool_reconcile_memory(markdown: str, identity: str | None = None) -> dict:
    result = write_memory(_root(), ".", identity=identity, stdin_text=markdown)
    result["mode"] = "reconcile"
    return result


MCP_EXTRA_HINT = "Optional extra 'mcp' is not installed. pip install 'repocodex[mcp]'"


def mcp_extra_available() -> bool:
    try:
        from mcp.server import MCPServer  # noqa: F401
    except ImportError:
        return False
    return True


def register_mcp_tools(server) -> None:
    @server.tool()
    def get_context(paths: list[str]) -> dict:
        return tool_get_context(paths)

    @server.tool()
    def get_impact(base: str | None = None) -> dict:
        return tool_get_impact(base)

    @server.tool()
    def read_concept(identity: str) -> dict:
        return tool_read_concept(identity)

    @server.tool()
    def write_memory(markdown: str, identity: str | None = None) -> dict:
        return tool_write_memory(markdown, identity)

    @server.tool()
    def validate_diff(base: str | None = None, staged: bool = False) -> dict:
        return tool_validate_diff(base, staged)

    @server.tool()
    def reconcile_memory(markdown: str, identity: str | None = None) -> dict:
        return tool_reconcile_memory(markdown, identity)


def run_mcp() -> None:
    if not mcp_extra_available():
        raise SystemExit(MCP_EXTRA_HINT)
    from mcp.server import MCPServer

    server = MCPServer("repocodex")
    register_mcp_tools(server)
    server.run()
