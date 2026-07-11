from __future__ import annotations

from copy import deepcopy
from typing import Iterable

from .config import GizmoConfig
from .corpus import tool_name
from .types import Schema
from .toolsets import is_mcp_schema

TOOL_SEARCH_TYPES = {
    "bm25": "tool_search_tool_bm25_20251119",
    "regex": "tool_search_tool_regex_20251119",
}


def supports_anthropic_tool_search(
    provider: str | None,
    model: str | None = None,
    explicit_capability: bool | None = None,
) -> bool:
    """Return True only when the provider path is known to carry Tool Search.

    Model names alone are not enough: OpenRouter can expose Claude models but
    still needs OpenRouter-specific serialization/header support. Proxied
    Anthropic paths (Bedrock/Vertex/Azure) require an explicit capability flag
    from Hermes provider detection or user config.
    """
    provider_text = (provider or "").lower()
    if provider_text in {"anthropic", "claude"}:
        return True
    if provider_text in {"bedrock", "vertex", "azure"}:
        return explicit_capability is True
    return False


def is_anthropic_provider(provider: str | None, model: str | None = None) -> bool:
    return supports_anthropic_tool_search(provider, model)


def tool_search_tool(variant: str = "bm25") -> Schema:
    return {"type": TOOL_SEARCH_TYPES.get(variant, TOOL_SEARCH_TYPES["bm25"]), "name": f"tool_search_tool_{variant}"}


def apply_defer_loading(schemas: list[Schema], hot_tool_names: Iterable[str], config: GizmoConfig | None = None) -> list[Schema]:
    cfg = config or GizmoConfig(mode="anthropic_tool_search")
    hot = set(hot_tool_names) | set(cfg.never_defer) | set(cfg.anthropic.never_defer)
    transformed: list[Schema] = []
    defer_count = 0
    for schema in schemas:
        item = deepcopy(schema)
        name = tool_name(item)
        may_defer = name not in hot
        if is_mcp_schema(item):
            may_defer = may_defer and cfg.anthropic.defer_mcp_tools
        else:
            may_defer = may_defer and cfg.anthropic.defer_native_tools
        if may_defer:
            item["defer_loading"] = True
            defer_count += 1
        transformed.append(item)
    if transformed and defer_count == len(transformed):
        transformed[0].pop("defer_loading", None)
    return [tool_search_tool(cfg.anthropic.variant), *transformed]


def maybe_anthropic_tools(
    provider: str | None,
    model: str | None,
    schemas: list[Schema],
    hot_tool_names: list[str],
    config: GizmoConfig,
    explicit_capability: bool | None = None,
) -> list[Schema]:
    if config.mode != "anthropic_tool_search" or not supports_anthropic_tool_search(
        provider, model, explicit_capability
    ):
        return schemas
    return apply_defer_loading(schemas, hot_tool_names, config)
