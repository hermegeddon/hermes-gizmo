"""Regression gates for the completed Hermes Gizmo hard rename."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

import tomllib
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
LEGACY_FRAGMENTS = ("tool-slimmer", "tool_slimmer", "Tool Slimmer", "ToolSlimmer")
PROVENANCE_FILES = {REPO_ROOT / "NOTICE", REPO_ROOT / "LICENSE", Path(__file__).resolve()}
IGNORED_PARTS = {".git", ".venv", ".pytest_cache", ".ruff_cache", ".mypy_cache", "__pycache__"}


def test_only_gizmo_distribution_plugin_and_console_entrypoints_are_published() -> None:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())

    assert pyproject["project"]["name"] == "hermes-gizmo"
    assert pyproject["project"]["entry-points"]["hermes_agent.plugins"] == {
        "gizmo": "hermes_gizmo"
    }
    assert pyproject["project"]["scripts"] == {"hermes-gizmo": "hermes_gizmo.cli:main"}
    assert pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"] == [
        "src/hermes_gizmo"
    ]


def test_legacy_python_namespace_is_not_shipped() -> None:
    assert not (REPO_ROOT / "src" / "hermes_tool_slimmer").exists()
    assert importlib.util.find_spec("hermes_tool_slimmer") is None


def test_register_exposes_only_gizmo_runtime_names() -> None:
    from hermes_gizmo import register

    ctx = MagicMock()
    register(ctx)

    tool_names = {call.kwargs["name"] for call in ctx.register_tool.call_args_list}
    assert tool_names == {
        "gizmo_status",
        "gizmo_select",
        "gizmo_request_full_tools",
        "gizmo_hydrate_tools",
        "gizmo_loaded_tools",
        "gizmo_tool_search",
        "gizmo_tool_details",
        "gizmo_skill_search",
        "gizmo_skill_details",
        "gizmo_visible_skill_pins",
        "gizmo_clear_visible_skill_pins",
        "gizmo_request_full_skill_index",
    }
    assert {call.args[0] for call in ctx.register_command.call_args_list} == {"gizmo"}
    assert {call.kwargs["name"] for call in ctx.register_cli_command.call_args_list} == {"gizmo"}


def test_manifests_publish_only_gizmo_names() -> None:
    expected_tools = {
        "gizmo_status",
        "gizmo_select",
        "gizmo_request_full_tools",
        "gizmo_hydrate_tools",
        "gizmo_loaded_tools",
        "gizmo_tool_search",
        "gizmo_tool_details",
        "gizmo_skill_search",
        "gizmo_skill_details",
        "gizmo_visible_skill_pins",
        "gizmo_clear_visible_skill_pins",
        "gizmo_request_full_skill_index",
    }
    for path in (REPO_ROOT / "plugin.yaml", REPO_ROOT / "dashboard-plugin" / "gizmo" / "plugin.yaml"):
        manifest = yaml.safe_load(path.read_text())
        assert manifest["name"] == "gizmo"
        assert set(manifest["provides_tools"]) == expected_tools
        assert manifest["provides_commands"] == ["gizmo"]
        assert manifest["provides_cli"] == ["gizmo"]


def test_no_active_legacy_named_paths_or_text_remain() -> None:
    findings: list[str] = []
    for path in REPO_ROOT.rglob("*"):
        if any(part in IGNORED_PARTS for part in path.parts) or path in PROVENANCE_FILES:
            continue
        relative = path.relative_to(REPO_ROOT)
        if any(fragment.lower() in str(relative).lower() for fragment in LEGACY_FRAGMENTS):
            findings.append(f"path:{relative}")
        if path.is_file():
            try:
                text = path.read_text()
            except UnicodeDecodeError:
                continue
            for fragment in LEGACY_FRAGMENTS:
                if fragment in text:
                    findings.append(f"text:{relative}:{fragment}")
    assert findings == []
