"""MCP-schema selection retirement (2026-07-27).

Gizmo never ranks or drops MCP schemas: native Hermes tool_search owns MCP
disclosure (its tiered progressive disclosure always defers MCP/plugin
tools). Eligible MCP schemas pass through every selection untouched, and the
legacy ``include_mcp_tools`` config key is ignored with a warning.
"""
from __future__ import annotations

import logging

from hermes_gizmo.config import GizmoConfig
from hermes_gizmo.integration import select_tool_schemas_callback
from hermes_gizmo.policy import eligible_schemas, split_mcp_passthrough

NATIVE = [
    {"name": "terminal", "toolset": "native", "description": "Run shell commands"},
    {"name": "read_file", "toolset": "native", "description": "Read a file"},
    {"name": "search_files", "toolset": "native", "description": "Search files in repo"},
]
MCP = [
    {"name": "mcp_github_read_issue", "toolset": "mcp:github", "description": "Read a GitHub issue"},
    {"name": "linear_create", "mcp_server": "linear", "description": "Create a Linear issue"},
]


def test_legacy_include_mcp_tools_key_is_ignored_with_warning(caplog):
    with caplog.at_level(logging.WARNING, logger="hermes_gizmo.config"):
        cfg = GizmoConfig.from_mapping({"include_mcp_tools": False, "top_k": 4})
    assert not hasattr(cfg, "include_mcp_tools")
    assert cfg.top_k == 4
    assert any("include_mcp_tools" in record.getMessage() for record in caplog.records)


def test_legacy_key_in_platform_profile_is_tolerated():
    cfg = GizmoConfig.from_mapping({"profiles": {"cron": {"include_mcp_tools": False, "top_k": 2}}})
    overlaid = cfg.for_context(platform="cron")
    assert overlaid.top_k == 2


def test_eligible_schemas_keeps_mcp():
    cfg = GizmoConfig()
    out = eligible_schemas([*NATIVE, *MCP], cfg)
    assert [s["name"] for s in out] == [s["name"] for s in [*NATIVE, *MCP]]


def test_split_mcp_passthrough_partition():
    selectable, passthrough = split_mcp_passthrough([*NATIVE, *MCP])
    assert [s["name"] for s in selectable] == ["terminal", "read_file", "search_files"]
    assert [s["name"] for s in passthrough] == ["mcp_github_read_issue", "linear_create"]


def test_callback_ships_mcp_untouched_alongside_selection():
    out = select_tool_schemas_callback(
        "search files",
        [],
        [*NATIVE, *MCP],
        "model",
        "cli",
        config=GizmoConfig(
            top_k=1,
            always_include=[],
            min_total_tools=0,
            log_decisions=False,
            min_estimated_reduction_percent=0,
        ),
    )
    assert out is not None
    names = [s.get("name") for s in out]
    assert "search_files" in names
    for schema in MCP:
        assert schema in out  # identical dicts: shipped untouched


def test_callback_never_drops_mcp_on_low_relevance_queries():
    out = select_tool_schemas_callback(
        "completely unrelated request",
        [],
        [*NATIVE, *MCP],
        "model",
        "cli",
        config=GizmoConfig(
            top_k=1,
            always_include=["terminal"],
            min_total_tools=0,
            log_decisions=False,
            min_estimated_reduction_percent=0,
        ),
    )
    assert out is None or all(schema in out for schema in MCP)


def test_callback_drops_disabled_mcp():
    out = select_tool_schemas_callback(
        "search files",
        [],
        [*NATIVE, *MCP],
        "model",
        "cli",
        config=GizmoConfig(
            top_k=1,
            always_include=[],
            min_total_tools=0,
            log_decisions=False,
            min_estimated_reduction_percent=0,
            disabled_tools=["mcp_github_read_issue"],
        ),
    )
    assert out is not None
    names = [s.get("name") for s in out]
    assert "mcp_github_read_issue" not in names
    assert "linear_create" in names
