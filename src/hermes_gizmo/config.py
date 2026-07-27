from __future__ import annotations

import logging
import os
import math
from collections.abc import Collection
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml


LOG = logging.getLogger("hermes_gizmo.config")

VALID_MODES = {"eager", "keyword", "hybrid", "anthropic_tool_search", "semantic_hybrid"}
# Modes that used to exist. Configs that still reference them fall back to
# "keyword" with a logged warning instead of failing validation, so stale
# profile overlays or restored config backups cannot break the selector hook.
REMOVED_MODES = {"two_pass"}
# Config keys that used to exist. Values are ignored with a logged warning so
# stale configs or restored backups cannot break the selector hook.
# - include_mcp_tools: removed 2026-07-27 — Gizmo no longer selects or drops
#   MCP schemas; they always pass through (native Hermes tool_search owns MCP
#   disclosure via its always-defer tiered progressive disclosure).
REMOVED_KEYS = ("include_mcp_tools",)
_LIST_FIELDS = {
    "always_exclude",
    "always_include",
    "never_defer",
    "disabled_tools",
    "disabled_toolsets",
}
_BOOL_FIELDS = {"enabled", "include_native_tools", "log_decisions", "fail_open", "dry_run", "semantic_cache_enabled", "progressive_enabled"}
_ANTHROPIC_LIST_FIELDS = {"never_defer"}
_ANTHROPIC_BOOL_FIELDS = {"defer_mcp_tools", "defer_native_tools", "tool_search_supported"}
_PROFILE_ALIASES = {
    "chat": "cli",
    "console": "cli",
    "terminal": "cli",
    "tui": "cli",
    "telegram_bot": "telegram",
    "slack_bot": "slack",
    "scheduled": "cron",
}


@dataclass
class AnthropicConfig:
    variant: str = "bm25"
    defer_mcp_tools: bool = True
    defer_native_tools: bool = False
    tool_search_supported: bool | None = None
    never_defer: list[str] = field(default_factory=lambda: ["terminal", "read_file", "search_files"])


@dataclass
class GizmoConfig:
    enabled: bool = True
    mode: str = "keyword"
    top_k: int = 8
    always_include: list[str] = field(default_factory=lambda: ["terminal", "read_file", "write_file", "patch", "search_files"])
    never_defer: list[str] = field(default_factory=lambda: ["terminal", "read_file"])
    disabled_tools: list[str] = field(default_factory=list)
    disabled_toolsets: list[str] = field(default_factory=list)
    include_native_tools: bool = True
    log_decisions: bool = True
    fail_open: bool = True
    dry_run: bool = False
    min_total_tools: int = 0
    min_estimated_reduction_percent: float = 5.0
    min_score: float = 0.25
    aliases: dict[str, list[str]] = field(default_factory=dict)
    profiles: dict[str, dict[str, Any]] = field(default_factory=dict)
    anthropic: AnthropicConfig = field(default_factory=AnthropicConfig)
    semantic_provider: str = "fake"
    semantic_openai_model: str = "text-embedding-3-small"
    semantic_openai_base_url: str | None = None
    semantic_openai_timeout: float = 30.0
    semantic_dim: int | None = None
    rrf_k: float = 60.0
    semantic_cache_enabled: bool = True
    progressive_enabled: bool = False
    progressive_max_loaded: int = 20
    progressive_ttl_seconds: int = 3600

    @classmethod
    def from_mapping(cls, data: dict[str, Any] | None) -> "GizmoConfig":
        raw = dict(data or {})
        if "always_exclude" in raw and "disabled_tools" not in raw:
            raw["disabled_tools"] = raw["always_exclude"]
        profiles_raw = raw.pop("profiles", {}) or {}
        anthropic_raw = raw.pop("anthropic", {}) or {}
        raw.pop("two_pass", None)  # removed 2026-07-15; tolerated in old configs
        for removed_key in REMOVED_KEYS:
            if removed_key in raw:
                LOG.warning(
                    "gizmo.%s was removed; MCP schemas now always pass through to native tool_search",
                    removed_key,
                )
                raw.pop(removed_key)
        if not isinstance(anthropic_raw, dict):
            anthropic_raw = {}
        mode_raw = raw.get("mode")
        if isinstance(mode_raw, str) and mode_raw.strip().lower() in REMOVED_MODES:
            LOG.warning("gizmo.mode %r was removed; falling back to 'keyword'", mode_raw)
            raw["mode"] = "keyword"
        raw = _normalize_mapping(raw, cls.__dataclass_fields__, _LIST_FIELDS, _BOOL_FIELDS)
        raw["profiles"] = _normalize_profiles(profiles_raw)
        anthropic_raw = _normalize_mapping(
            anthropic_raw,
            AnthropicConfig.__dataclass_fields__,
            _ANTHROPIC_LIST_FIELDS,
            _ANTHROPIC_BOOL_FIELDS,
            allow_none_booleans=True,
        )
        cfg = cls(**{key: value for key, value in raw.items() if key in cls.__dataclass_fields__ and key != "anthropic"})
        cfg.anthropic = AnthropicConfig(**{key: value for key, value in anthropic_raw.items() if key in AnthropicConfig.__dataclass_fields__})
        cfg.validate()
        return cfg

    def for_context(self, *, platform: str | None = None, profile: str | None = None) -> "GizmoConfig":
        """Return this config with default and platform profile overlays applied."""
        names = ["default"]
        requested = _normalize_profile_key(profile or platform)
        resolved = requested if requested in self.profiles else _profile_name(requested)
        if resolved and resolved != "default":
            names.append(resolved)
        overlays = [self.profiles[name] for name in names if name in self.profiles]
        if not overlays:
            return self

        raw = asdict(self)
        raw["anthropic"] = asdict(self.anthropic)
        raw["profiles"] = self.profiles
        for overlay in overlays:
            _merge_profile_overlay(raw, overlay)
        return GizmoConfig.from_mapping(raw)

    @property
    def always_exclude(self) -> list[str]:
        """User-facing alias for disabled_tools."""
        return self.disabled_tools

    def validate(self) -> None:
        if self.mode not in VALID_MODES:
            raise ValueError(f"Invalid gizmo.mode {self.mode!r}; expected one of {sorted(VALID_MODES)}")
        if not isinstance(self.top_k, int) or isinstance(self.top_k, bool) or not math.isfinite(self.top_k):
            raise ValueError("gizmo.top_k must be a finite integer")
        if self.top_k < 0:
            raise ValueError("gizmo.top_k must be >= 0")
        if not isinstance(self.min_total_tools, int) or isinstance(self.min_total_tools, bool) or not math.isfinite(self.min_total_tools):
            raise ValueError("gizmo.min_total_tools must be a finite integer")
        if self.min_total_tools < 0:
            raise ValueError("gizmo.min_total_tools must be >= 0")
        if not isinstance(self.min_estimated_reduction_percent, (int, float)) or isinstance(self.min_estimated_reduction_percent, bool) or not math.isfinite(self.min_estimated_reduction_percent):
            raise ValueError("gizmo.min_estimated_reduction_percent must be finite")
        if self.min_estimated_reduction_percent < 0:
            raise ValueError("gizmo.min_estimated_reduction_percent must be >= 0")
        if not isinstance(self.min_score, (int, float)) or isinstance(self.min_score, bool) or not math.isfinite(self.min_score):
            raise ValueError("gizmo.min_score must be finite")
        if self.min_score < 0:
            raise ValueError("gizmo.min_score must be >= 0")
        if not isinstance(self.rrf_k, (int, float)) or isinstance(self.rrf_k, bool) or not math.isfinite(self.rrf_k) or self.rrf_k <= 0:
            raise ValueError("gizmo.rrf_k must be a finite number > 0")
        if not isinstance(self.progressive_max_loaded, int) or isinstance(self.progressive_max_loaded, bool) or not math.isfinite(self.progressive_max_loaded):
            raise ValueError("gizmo.progressive_max_loaded must be a finite integer")
        if self.progressive_max_loaded < 0:
            raise ValueError("gizmo.progressive_max_loaded must be >= 0")
        if not isinstance(self.progressive_ttl_seconds, int) or isinstance(self.progressive_ttl_seconds, bool) or not math.isfinite(self.progressive_ttl_seconds):
            raise ValueError("gizmo.progressive_ttl_seconds must be a finite integer")
        if self.progressive_ttl_seconds < 0:
            raise ValueError("gizmo.progressive_ttl_seconds must be >= 0")


def _normalize_string_list(value: Any, field_name: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value if item is not None]
    raise ValueError(f"gizmo.{field_name} must be a string or list")


def _normalize_aliases(value: Any) -> dict[str, list[str]]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("gizmo.aliases must be a mapping")
    aliases: dict[str, list[str]] = {}
    for key, values in value.items():
        aliases[str(key)] = _normalize_string_list(values, f"aliases.{key}")
    return aliases


def _normalize_profiles(value: Any) -> dict[str, dict[str, Any]]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("gizmo.profiles must be a mapping")
    profiles: dict[str, dict[str, Any]] = {}
    for name, profile_raw in value.items():
        if profile_raw is None:
            continue
        if not isinstance(profile_raw, dict):
            raise ValueError(f"gizmo.profiles.{name} must be a mapping")
        profile = dict(profile_raw)
        if "always_exclude" in profile and "disabled_tools" not in profile:
            profile["disabled_tools"] = profile["always_exclude"]
        anthropic_raw = profile.pop("anthropic", None)
        normalized = _normalize_mapping(profile, GizmoConfig.__dataclass_fields__, _LIST_FIELDS, _BOOL_FIELDS)
        if isinstance(anthropic_raw, dict):
            normalized["anthropic"] = _normalize_mapping(
                anthropic_raw,
                AnthropicConfig.__dataclass_fields__,
                _ANTHROPIC_LIST_FIELDS,
                _ANTHROPIC_BOOL_FIELDS,
                allow_none_booleans=True,
            )
        profile.pop("two_pass", None)  # removed 2026-07-15; tolerated in old profiles
        profiles[_normalize_profile_key(str(name)) or str(name)] = normalized
    return profiles


def _normalize_profile_key(value: str | None) -> str | None:
    if not value:
        return None
    return str(value).strip().lower().replace("-", "_")


def _profile_name(value: str | None) -> str | None:
    normalized = _normalize_profile_key(value)
    if not normalized:
        return None
    return _PROFILE_ALIASES.get(normalized, normalized)


def _merge_profile_overlay(raw: dict[str, Any], overlay: dict[str, Any]) -> None:
    for key, value in overlay.items():
        if key == "anthropic" and isinstance(value, dict):
            anthropic = raw.get("anthropic")
            if not isinstance(anthropic, dict):
                anthropic = {}
            raw["anthropic"] = {**anthropic, **value}
        elif key == "two_pass":
            continue  # removed 2026-07-15; tolerated in old overlays
        elif key == "aliases" and isinstance(value, dict):
            aliases = raw.get("aliases")
            if not isinstance(aliases, dict):
                aliases = {}
            raw["aliases"] = {**aliases, **value}
        elif key in {"disabled_tools", "disabled_toolsets"} and isinstance(value, list):
            current = raw.get(key)
            if not isinstance(current, list):
                current = []
            raw[key] = _dedupe_strings([*current, *value])
        elif key != "profiles":
            raw[key] = value


def _normalize_mapping(
    raw: dict[str, Any],
    allowed_fields: Collection[str],
    list_fields: set[str],
    bool_fields: set[str],
    *,
    allow_none_booleans: bool = False,
) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in raw.items():
        if key not in allowed_fields:
            continue
        if key in list_fields:
            normalized[key] = _normalize_string_list(value, key)
        elif key == "aliases":
            normalized[key] = _normalize_aliases(value)
        elif key in bool_fields:
            if value is None and allow_none_booleans:
                normalized[key] = None
            elif isinstance(value, bool):
                normalized[key] = value
            else:
                raise ValueError(f"gizmo.{key} must be a boolean")
        else:
            normalized[key] = value
    return normalized


def _dedupe_strings(values: list[Any]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value)
        if text not in seen:
            out.append(text)
            seen.add(text)
    return out


def hermes_home() -> Path:
    return Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes")).expanduser()


def config_path() -> Path:
    return Path(os.environ.get("HERMES_CONFIG", hermes_home() / "config.yaml")).expanduser()


def load_config(path: str | Path | None = None, *, strict: bool = False) -> GizmoConfig:
    target = Path(path).expanduser() if path else config_path()
    if not target.is_file():
        return GizmoConfig()
    try:
        data = yaml.safe_load(target.read_text()) or {}
    except yaml.YAMLError as exc:
        if strict:
            raise ValueError(f"Could not parse gizmo config: {target}") from exc
        return GizmoConfig()
    if not isinstance(data, dict):
        if strict:
            raise ValueError(f"gizmo config must be a mapping: {target}")
        return GizmoConfig()
    section = data.get("gizmo", data if "mode" in data else {})
    if not isinstance(section, dict):
        if strict:
            raise ValueError(f"gizmo section must be a mapping: {target}")
        return GizmoConfig()
    return GizmoConfig.from_mapping(section)
