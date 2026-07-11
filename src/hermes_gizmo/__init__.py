from __future__ import annotations

from .integration import maybe_register_selector_hook
from .schemas import (
    CLEAR_VISIBLE_SKILL_PINS_SCHEMA,
    HYDRATE_TOOLS_SCHEMA,
    LOADED_TOOLS_SCHEMA,
    REQUEST_FULL_SKILL_INDEX_SCHEMA,
    REQUEST_FULL_TOOLS_SCHEMA,
    SELECT_SCHEMA,
    SKILL_DETAILS_SCHEMA,
    SKILL_SEARCH_SCHEMA,
    STATUS_SCHEMA,
    TOOL_DETAILS_SCHEMA,
    TOOL_SEARCH_SCHEMA,
    VISIBLE_SKILL_PINS_SCHEMA,
)
from .session_tools import gizmo_loaded_tools, gizmo_tool_details, gizmo_tool_search
from .tools import gizmo_hydrate_tools, gizmo_request_full_tools, gizmo_select, gizmo_status

__all__ = ["register"]
__version__ = "0.7.0"


def register(ctx):
    """Register the Hermes Gizmo plugin."""
    marker = "_hermes_gizmo_registered"
    if getattr(ctx, marker, False) is True:
        return
    setattr(ctx, marker, True)

    from .cli import handle_cli, setup_argparse
    from .commands import handle_slash_command
    from .skills_tools import (
        gizmo_clear_visible_skill_pins,
        gizmo_request_full_skill_index,
        gizmo_skill_details,
        gizmo_skill_search,
        gizmo_visible_skill_pins,
    )

    tools = (
        ("gizmo_status", STATUS_SCHEMA, gizmo_status),
        ("gizmo_select", SELECT_SCHEMA, gizmo_select),
        ("gizmo_request_full_tools", REQUEST_FULL_TOOLS_SCHEMA, gizmo_request_full_tools),
        ("gizmo_tool_search", TOOL_SEARCH_SCHEMA, gizmo_tool_search),
        ("gizmo_tool_details", TOOL_DETAILS_SCHEMA, gizmo_tool_details),
        ("gizmo_loaded_tools", LOADED_TOOLS_SCHEMA, gizmo_loaded_tools),
        ("gizmo_hydrate_tools", HYDRATE_TOOLS_SCHEMA, gizmo_hydrate_tools),
        ("gizmo_skill_search", SKILL_SEARCH_SCHEMA, gizmo_skill_search),
        ("gizmo_skill_details", SKILL_DETAILS_SCHEMA, gizmo_skill_details),
        ("gizmo_visible_skill_pins", VISIBLE_SKILL_PINS_SCHEMA, gizmo_visible_skill_pins),
        (
            "gizmo_clear_visible_skill_pins",
            CLEAR_VISIBLE_SKILL_PINS_SCHEMA,
            gizmo_clear_visible_skill_pins,
        ),
        (
            "gizmo_request_full_skill_index",
            REQUEST_FULL_SKILL_INDEX_SCHEMA,
            gizmo_request_full_skill_index,
        ),
    )
    for name, schema, handler in tools:
        ctx.register_tool(name=name, toolset="gizmo", schema=schema, handler=handler)

    ctx.register_command(
        "gizmo",
        handler=handle_slash_command,
        description="Inspect and manage Hermes Gizmo",
    )
    ctx.register_cli_command(
        name="gizmo",
        help="Inspect and manage Hermes Gizmo",
        setup_fn=setup_argparse,
        handler_fn=handle_cli,
    )
    maybe_register_selector_hook(ctx)
