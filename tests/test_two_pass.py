import json

from hermes_tool_slimmer.config import ToolSlimmerConfig
from hermes_tool_slimmer.integration import _HYDRATED_BY_SESSION, build_decision_context, select_tool_schemas_callback
from hermes_tool_slimmer.tools import tool_slimmer_hydrate_tools
from hermes_tool_slimmer.two_pass import (
    HYDRATE_REQUEST_MARKER,
    HYDRATE_TOOL_NAME,
    compact_catalog,
    hydrate_tool_schema,
    render_compact_catalog,
    requested_hydration_tools,
)


SCHEMAS = [
    {"name": "terminal", "description": "Run shell commands"},
    {"name": "memory", "description": "Remember important facts"},
    {"name": "web_search", "toolset": "web", "description": "Search the web for current information"},
    {"name": "read_file", "description": "Read a local file"},
    {"name": "tool_slimmer_request_full_tools", "description": "Request every tool"},
    {"name": HYDRATE_TOOL_NAME, "description": "Hydrate tools", "parameters": {"type": "object", "properties": {}}},
]


def test_build_decision_context_marks_kanban_worker(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "profiles" / "frontend-eng"))
    monkeypatch.setenv("HERMES_PROFILE", "frontend-eng")
    monkeypatch.setenv("HERMES_KANBAN_TASK", "t_abc12345")
    monkeypatch.setenv("HERMES_KANBAN_BOARD", "kanban-navigator-live-operator")
    monkeypatch.setenv("HERMES_KANBAN_RUN_ID", "93")
    monkeypatch.setenv("HERMES_KANBAN_WORKSPACE", "/tmp/workspace")

    context = build_decision_context(
        provider="openai-codex",
        model="gpt-5.5",
        platform="cli",
        session_id="20260625_173453_ead4ff",
        dry_run=True,
        schema_count=257,
    )

    assert context["execution_kind"] == "kanban_worker"
    assert context["assignee_profile"] == "frontend-eng"
    assert context["active_profile"] == "frontend-eng"
    assert context["profile_home"] == str(tmp_path / "profiles" / "frontend-eng")
    assert context["kanban_task_id"] == "t_abc12345"
    assert context["kanban_board"] == "kanban-navigator-live-operator"
    assert context["kanban_run_id"] == "93"
    assert context["kanban_workspace"] == "/tmp/workspace"


def test_build_decision_context_marks_subagent():
    context = build_decision_context(
        provider=None,
        model="gpt-5.5",
        platform="subagent",
        session_id="child-session",
        dry_run=True,
        schema_count=100,
    )

    assert context["execution_kind"] == "subagent"
    assert "kanban_task_id" not in context


def test_build_decision_context_marks_profile_delegate(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "profiles" / "reviewer"))
    monkeypatch.setenv("HERMES_PROFILE", "reviewer")
    monkeypatch.setenv("HERMES_SESSION_SOURCE", "profile-delegate")

    context = build_decision_context(
        provider="openai-codex",
        model="gpt-5.5",
        platform="cli",
        session_id="delegate-session",
        dry_run=True,
        schema_count=100,
    )

    assert context["execution_kind"] == "profile_delegate"
    assert context["assignee_profile"] == "reviewer"
    assert context["session_source"] == "profile-delegate"


def test_selector_decision_log_includes_kanban_context(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "profiles" / "platform-eng"))
    monkeypatch.setenv("HERMES_PROFILE", "platform-eng")
    monkeypatch.setenv("HERMES_KANBAN_TASK", "t_decision")
    monkeypatch.setenv("HERMES_KANBAN_BOARD", "measurement-board")
    cfg = ToolSlimmerConfig.from_mapping(
        {
            "dry_run": True,
            "always_include": [],
            "min_estimated_reduction_percent": 0,
            "top_k": 1,
        }
    )

    selected = select_tool_schemas_callback(
        "read a local file",
        [],
        SCHEMAS,
        "model",
        "cli",
        provider="openai-codex",
        session_id="worker-session",
        config=cfg,
    )

    assert selected is None
    event = json.loads(
        (tmp_path / "profiles" / "platform-eng" / "tool-slimmer" / "decisions.jsonl")
        .read_text()
        .splitlines()[-1]
    )
    assert event["context"]["execution_kind"] == "kanban_worker"
    assert event["context"]["assignee_profile"] == "platform-eng"
    assert event["context"]["kanban_task_id"] == "t_decision"
    assert event["context"]["kanban_board"] == "measurement-board"


def test_select_tool_schemas_fails_open_on_invalid_platform_profile_overlay():
    cfg = ToolSlimmerConfig(
        enabled=True,
        profiles={"discord": {"top_k": -1}},
    )

    selected = select_tool_schemas_callback(
        "search the web",
        [],
        SCHEMAS,
        "claude-sonnet",
        "discord",
        config=cfg,
    )

    assert selected is None


def test_compact_catalog_is_deterministic_and_excludes_safety_tools():
    cfg = ToolSlimmerConfig.from_mapping({"mode": "two_pass"})

    first = render_compact_catalog(compact_catalog(SCHEMAS, cfg))
    second = render_compact_catalog(compact_catalog(list(reversed(SCHEMAS)), cfg))

    assert first == second
    assert "web_search" in first
    assert f"- {HYDRATE_TOOL_NAME}:" not in first
    assert "tool_slimmer_request_full_tools" not in first


def test_compact_catalog_respects_disabled_policy():
    cfg = ToolSlimmerConfig.from_mapping({"mode": "two_pass", "disabled_tools": ["web_search"]})

    rendered = render_compact_catalog(compact_catalog(SCHEMAS, cfg))

    assert "web_search" not in rendered
    assert "read_file" in rendered


def test_hydrate_tool_schema_contains_catalog_and_enum():
    cfg = ToolSlimmerConfig.from_mapping({"mode": "two_pass"})
    tools = compact_catalog(SCHEMAS, cfg)
    schema = hydrate_tool_schema(SCHEMAS[-1], tools)

    assert "web_search" in schema["description"]
    assert schema["parameters"]["properties"]["tools"]["items"]["enum"] == [
        "memory",
        "read_file",
        "terminal",
        "web_search",
    ]


def test_hydrate_tool_handler_batches_requested_tools():
    result = json.loads(tool_slimmer_hydrate_tools({"tools": ["web_search", "read_file", "web_search"], "reason": "need web"}))

    assert result["ok"] is True
    assert result[HYDRATE_REQUEST_MARKER] is True
    assert result["tools"] == ["web_search", "read_file"]


def test_requested_hydration_tools_reads_json_tool_result():
    marker = json.dumps({HYDRATE_REQUEST_MARKER: True, "tools": ["web_search", "read_file"]})

    assert requested_hydration_tools([{"role": "tool", "content": marker}]) == ["web_search", "read_file"]


def test_two_pass_first_pass_selects_only_always_and_hydrator(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    cfg = ToolSlimmerConfig.from_mapping({"mode": "two_pass", "always_include": ["memory"]})

    selected = select_tool_schemas_callback(
        "search the web",
        [],
        SCHEMAS,
        "model",
        "tui",
        session_id="session-1",
        config=cfg,
    )

    assert [schema["name"] for schema in selected] == [
        "memory",
        "tool_slimmer_request_full_tools",
        HYDRATE_TOOL_NAME,
    ]
    hydrate_schema = selected[-1]
    assert "Compact tool catalog" in hydrate_schema["description"]
    assert "web_search" in hydrate_schema["description"]


def test_two_pass_hydrates_requested_tools_and_caches_by_session(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    _HYDRATED_BY_SESSION.clear()
    cfg = ToolSlimmerConfig.from_mapping({"mode": "two_pass", "always_include": ["memory"]})
    marker = json.dumps({HYDRATE_REQUEST_MARKER: True, "tools": ["web_search"]})

    selected = select_tool_schemas_callback(
        "continue",
        [{"role": "tool", "content": marker}],
        SCHEMAS,
        "model",
        "tui",
        session_id="session-2",
        config=cfg,
    )
    assert "web_search" in [schema["name"] for schema in selected]

    selected_again = select_tool_schemas_callback(
        "continue again",
        [],
        SCHEMAS,
        "model",
        "tui",
        session_id="session-2",
        config=cfg,
    )
    assert "web_search" in [schema["name"] for schema in selected_again]


def test_two_pass_hydration_respects_disabled_policy(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    _HYDRATED_BY_SESSION.clear()
    cfg = ToolSlimmerConfig.from_mapping({"mode": "two_pass", "always_include": ["memory"], "disabled_tools": ["web_search"]})
    marker = json.dumps({HYDRATE_REQUEST_MARKER: True, "tools": ["web_search", "read_file"]})

    selected = select_tool_schemas_callback(
        "continue",
        [{"role": "tool", "content": marker}],
        SCHEMAS,
        "model",
        "tui",
        session_id="session-disabled",
        config=cfg,
    )

    names = [schema["name"] for schema in selected]
    assert "read_file" in names
    assert "web_search" not in names


def test_two_pass_missing_hydrator_falls_back_to_keyword(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    cfg = ToolSlimmerConfig.from_mapping({"mode": "two_pass", "always_include": [], "min_estimated_reduction_percent": 0})
    schemas = [schema for schema in SCHEMAS if schema["name"] != HYDRATE_TOOL_NAME]

    selected = select_tool_schemas_callback(
        "search the web",
        [],
        schemas,
        "model",
        "tui",
        session_id="session-3",
        config=cfg,
    )

    assert "web_search" in [schema["name"] for schema in selected]
