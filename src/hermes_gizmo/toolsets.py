from __future__ import annotations

from typing import Any

from .corpus import tool_name


def schema_origin(schema: dict[str, Any] | object) -> str:
    """Classify a Hermes tool schema as `mcp` or `native` from known metadata/name shapes."""
    if not isinstance(schema, dict):
        return "native"
    for key in ("toolset", "tool_set", "namespace"):
        value = str(schema.get(key) or "").lower()
        if value in {"mcp", "mcp_tools"} or value.startswith(("mcp:", "mcp-")):
            return "mcp"
    if schema.get("mcp_server"):
        return "mcp"
    # Hermes MCP tools are registered into toolsets named mcp-{server}, and
    # converted MCP schema names are prefixed mcp_{server}_{tool}.
    server = str(schema.get("server") or "").lower()
    name = tool_name(schema).lower()
    if server or name.startswith("mcp_"):
        return "mcp"
    return "native"


def is_mcp_toolset(toolset: str | None) -> bool:
    value = (toolset or "native").lower()
    return value in {"mcp", "mcp_tools"} or value.startswith(("mcp:", "mcp-"))


def is_mcp_schema(schema: dict[str, Any] | object) -> bool:
    return schema_origin(schema) == "mcp"
