from __future__ import annotations

import logging
from typing import Iterable

from .config import GizmoConfig
from .corpus import tool_name, tool_toolset
from .toolsets import is_mcp_schema
from .types import Schema

LOG = logging.getLogger(__name__)


def eligible_schemas(schemas: Iterable[Schema], cfg: GizmoConfig) -> list[Schema]:
    """Return the shippable schema list with disabled filters applied.

    MCP schemas are always retained: since the 2026-07-27 retirement Gizmo
    never drops or ranks MCP schemas — native Hermes tool_search owns MCP
    disclosure (its tiered progressive disclosure always defers MCP/plugin
    tools). Eligible MCP schemas pass through untouched unless explicitly
    disabled via ``disabled_tools`` / ``disabled_toolsets``.
    """
    disabled = set(cfg.disabled_tools)
    disabled_toolsets = set(cfg.disabled_toolsets)
    out: list[Schema] = []
    for schema in schemas:
        if not isinstance(schema, dict):
            LOG.warning("skipping non-dict tool schema: type=%s", type(schema).__name__)
            continue
        name = tool_name(schema)
        toolset = tool_toolset(schema)
        if name in disabled or (toolset and toolset in disabled_toolsets):
            continue
        if not is_mcp_schema(schema) and not cfg.include_native_tools:
            continue
        out.append(schema)
    return out


def split_mcp_passthrough(schemas: Iterable[Schema]) -> tuple[list[Schema], list[Schema]]:
    """Partition an eligible schema list into ``(selectable, mcp_passthrough)``.

    The first list is Gizmo's ranking universe (native/plugin-registered
    tools); the second is MCP schemas, which ship untouched and unranked.
    """
    selectable: list[Schema] = []
    passthrough: list[Schema] = []
    for schema in schemas:
        (passthrough if is_mcp_schema(schema) else selectable).append(schema)
    return selectable, passthrough
