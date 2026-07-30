# Changelog

## Unreleased

### Added

- Added `gizmo.native_tool_search_policy` (`"skip"` default, `"compose"`; per-profile overridable). Under `compose`, when the Hermes native tool_search bridge is active Gizmo no longer stands down: it slims the visible core/plugin schemas that native tiered disclosure never defers, re-attaches the untouched bridge stubs on every schema-returning path, and restores its recovery schemas (ACP-style) so slimmed-away tools stay recoverable via `gizmo_request_full_tools`. Motivation: native tiered disclosure activates the bridge whenever any deferrable tool exists, so the former unconditional skip disabled slimming on effectively every turn (observed 2026-07-29: 68 tools / ~34k schema tokens shipped untrimmed per turn on the default CLI profile; compose cut it to ~9.7k).
- Kanban worker turns (detected via `HERMES_KANBAN_TASK`, the same signal decision contexts use) are now routed to the `kanban_worker` config profile overlay instead of the `cli` overlay their platform string would select, so worker lanes can stay on `skip` while interactive CLI/TUI profiles opt into `compose`.
- Added `gizmo.full_tools_grant_iterations` (default 0 = legacy, per-profile overridable): bounds the `gizmo_request_full_tools` grant to the calling iteration plus N assistant turns. Agentic runs carry a single user message, so the legacy user-retry expiry kept the full catalog for the entire remainder of the run (observed 2026-07-30: one fallback call at iteration ~3 shipped 70 tools/~32k tokens for 14+ further iterations). The selection query's recent-mentions boost keeps just-used tools in the re-trimmed set after expiry.
- Reworded the injected fallback instruction to steer models toward the native `tool_search`/`tool_call` bridge for deferred tools before reaching for `gizmo_request_full_tools` (observed models discovering a deferred MCP tool via `tool_search` and then requesting the full catalog instead of dispatching through `tool_call`).

### Changed

- Completed the Hermes Gizmo hard rename across the Python distribution and namespace, plugin discovery, tools, commands, config/state paths, dashboard routes, scripts, documentation, and tests.
- The `min_estimated_reduction_percent` reduction floor now applies uniformly to all selection modes (the former two-pass carve-out is gone).

### Deprecated

### Removed

- Retired MCP-schema selection (2026-07-27). Gizmo never ranks or drops MCP schemas anymore: native Hermes tool_search owns MCP disclosure (tiered progressive disclosure always defers MCP/plugin tools), so eligible MCP schemas pass through every selection untouched and are reported as `mcp_passthrough` in decision metrics. The `include_mcp_tools` config key was removed and is ignored with a logged warning; `disabled_tools`/`disabled_toolsets` still apply to MCP schemas. In the `anthropic_tool_search` lane MCP tools are now always deferred (never hot-picked by relevance). Core-tool slimming, the skills lane, recovery tools, and telemetry are unchanged.
- Removed the former compatibility package, plugin, command, dashboard, and runtime registration aliases.
- Removed the experimental `two_pass` selection mode, the `gizmo_hydrate_tools` tool, the `two_pass` config section, and the in-memory hydrated-tool session cache. Hermes native Tool Search covers the lazy-loading use case; Gizmo detects the native bridge and composes with it. Configs still setting `mode: two_pass` fall back to `keyword` with a logged warning; stale `two_pass:` sections are ignored; historical decision-log rows with `two_pass_*` fields remain readable.

### Fixed

- Restricted advisor rollback to backups under the Hermes Gizmo backup directory and kept advisor config backups/restores private on disk.
- Isolated the pytest suite from the operator's real `HERMES_HOME`/`HERMES_CONFIG` so local plugin settings cannot contaminate test results.
- Kept malformed platform profile overlays inside the selector hook's fail-open path.
- Wrote decision logs, session-loaded state, and persisted tool indexes with private file permissions.

### Security

- Hardened dashboard advisor rollback against arbitrary readable-file-to-config overwrite by resolving backup paths and requiring them to remain under the plugin backup directory.

## 0.7.0 - 2026-06-06

### Added

- Added public open-source maintenance files: support policy, code of conduct, issue templates, and pull request template.
- Added `NOTICE` with upstream attribution and MIT license-preservation notes.

### Changed

- Updated public docs and package metadata toward the Hermes Gizmo community fork URL while retaining the compatibility layer used during that release.
- Expanded CI/release validation to include mypy, canonical dashboard plugin compilation, package build, wheel asset checks, and temp install smoke.
- Adopted an explicit SemVer release policy and bumped the community-preview line to `0.7.0`.

## 0.6.4 - 2026-05-30

Installer environment override repair.

### Fixed

- Installer, updater, self-heal, and troubleshooting scripts now treat an environment-provided `HERMES_BIN` as an explicit trusted binary, matching the documented `HERMES_BIN=... bash ...` install flow and avoiding fallback to `command -v hermes`.

## 0.6.3 - 2026-05-30

Security hardening release.

### Fixed

- Enforces disabled tool, disabled toolset, MCP/native origin, and malformed-schema policy consistently across keyword, two-pass, Anthropic Tool Search, full-tool fallback, and guardrail skip paths.
- Keeps global disabled-tool policy when applying platform profiles or Guided Setup recommendations.
- Restricts model-callable `gizmo_select` so it no longer reads live/indexed catalogs unless explicitly opted in and no longer accepts `mode: eager`.
- Stops logging prompt-derived expanded query tokens; decision logs now store only the expanded-query token count.
- Redacts live snapshot summaries returned to the dashboard and refuses stale live-schema snapshots by default.
- Avoids fixed `/tmp/hermes-gizmo` installer commands in docs, prevents installer raw-decision output, and hardens self-heal systemd unit generation.

## 0.6.1 - 2026-05-30

Install and support diagnostics repair release.

### Added

- `hermes gizmo diagnostics` emits a sanitized GitHub-issue support report without raw prompts, environment secrets, or session IDs.
- Dashboard API exposes the same sanitized diagnostics at `/diagnostics`.

### Fixed

- Installer-based dashboard/user-plugin installs now include a bundled `src/hermes_gizmo` fallback so the dashboard can import the matching plugin package even when Hermes dashboard runs under a different Python launcher.
- Normal install docs and doctor messages now point users back to the installer compatibility patcher instead of asking them to manually apply the upstream Hermes core patch artifact.

## 0.6.0 - 2026-05-29

Experimental two-pass schema hydration release.

### Added

- Experimental `mode: two_pass` with compact deterministic tool catalogs, batched schema hydration through `gizmo_hydrate_tools`, session-scoped hydrated-tool caching, decision-log metrics, CLI/doctor/status visibility, and dashboard diagnostics.

## 0.5.3 - 2026-05-29

Dashboard git-install repair release.

### Fixed

- Dashboard git installs now include the root dashboard bundle assets expected by Hermes' `/dashboard-plugins/gizmo/dist/...` static routes.
- Git-installed dashboard/API loading can import the repo-local `src/hermes_gizmo` package before the repair installer has installed the Python package into the Hermes venv.

## 0.5.2 - 2026-05-28

Hermes update repair release.

### Added

- `scripts/update-hermes-and-repair-gizmo.sh` to run `hermes update --yes`, preserve Hermes' normal backup behavior by default, rerun Gizmo repair, and restart services after Hermes updates.
- `scripts/self-heal-gizmo.sh` with an optional user systemd unit for guarded boot/login repair when Gizmo is enabled but the Hermes selector hook is missing.

### Tested

- Verified Hermes Agent update from v0.14.0 to v0.15.0 with default backup behavior and noninteractive `--yes` prompt handling.
- Verified post-update Gizmo repair on Hermes v0.15.0 and all-pass doctor after gateway/dashboard restart.
- Verified the self-heal systemd unit installs, starts, exits cleanly in healthy no-op mode, and leaves gateway/dashboard active.

## 0.5.1 - 2026-05-28

Live snapshot clarity release.

### Added

- Per-platform live schema snapshots for TUI, Slack, Telegram, and API server turns.
- Dashboard and CLI status context explaining which live request snapshot populated the persisted index.
- Dashboard snapshot chips so users can see why Hermes TUI and Gizmo counts may differ by entry point.

### Tested

- Verified TUI, Slack, Telegram, and API server turns against live Hermes with full-tool fallback available.
- Smoke-tested a clean Hermes install on a disposable exe.dev VM, including installer patching, doctor, status, and eval.

## 0.5.0 - 2026-05-27

Guided setup and profile tuning release.

### Added

- Platform profiles for Telegram, Slack, CLI/TUI, cron, and webhook entry points.
- Advisor recommendations with plain-English setup checklist, recommended YAML, safe apply, config backups, and rollback support.
- Dashboard Guided Setup card with one-click recommended config apply and backup visibility.
- Low-information query handling so greetings, pings, thanks, and numeric nudges do not fill `top_k` with unrelated task tools.
- Beginner-friendly setup docs and an agent-install prompt for users who do not want to run shell commands manually.

### Changed

- `always_exclude` is accepted as a user-facing alias for `disabled_tools`.
- Dashboard status now exposes disabled tools, disabled toolsets, aliases, and profiles for easier troubleshooting.

## 0.4.7 - 2026-05-20

Missing skill-tool fallback release.

### Fixed

- Full-tool fallback now survives the first user retry after `gizmo_request_full_tools`, covering the common chat flow where the model asks the user to send another message before retrying.
- Ambiguous retry messages now use recent assistant/tool mentions of known tool names, so a follow-up like `12` can still expose a recently requested tool such as `skill_view`.
- Skill companion tools are kept together: selecting `skill_manage` or skill-context requests also keeps `skill_view` and `skills_list` available when present.

## 0.4.6 - 2026-05-19

Dashboard git-install compatibility release.

### Changed

- The repository root now includes the Hermes runtime plugin entry point and dashboard files, matching Hermes dashboard git-install expectations.
- Git checkouts installed at `$HERMES_HOME/plugins/gizmo` now stay clean after repair, so the dashboard can show `Source: git` and keep using `git pull`.
- Mypy configuration now uses explicit package bases so the root Hermes plugin entry point can coexist with the `src/` Python package layout.

## 0.4.5 - 2026-05-19

Dashboard installer compatibility release.

### Changed

- The installer now supports being run from an in-place dashboard git checkout at `$HERMES_HOME/plugins/gizmo` by overlaying the runtime plugin files without deleting the checkout, preserving future `git pull` updates from the plugin page.
- Plugin and dashboard manifest versions now track the package release version.

## 0.4.4 - 2026-05-19

Dashboard index reliability release.

### Fixed

- Dashboard "Rebuild From Hermes Tools" now chooses the largest available runtime catalog between Hermes tool definitions and the last live request snapshot.
- Dashboard rebuild now preserves an existing larger index instead of replacing it with a smaller standalone catalog, preventing full gateway catalogs from shrinking after cron/subagent snapshots or incomplete standalone `model_tools` discovery.

## 0.4.3 - 2026-05-19

Installer reliability release.

### Changed

- Prefer the Hermes virtualenv launcher at `$HOME/.hermes/hermes-agent/venv/bin/hermes` when install and troubleshooting scripts need a Hermes executable.
- Document the venv launcher path for Hermes Agent-assisted installs and repairs.
- Run the troubleshooting script through `bash` from the installer so executable-bit restrictions do not block the final health report.

## 0.2.0 - 2026-05-15

Dashboard and operations release.

### Added

- Hermes dashboard plugin with status, health checks, recent selection decisions, selected-tool visibility, and estimated schema-token savings.
- Dashboard backend API routes for Gizmo status, session-filtered summaries, full audit summaries, and raw recent events.
- Durable JSONL decision logging under `$HERMES_HOME/gizmo/decisions.jsonl`.
- One-command local installer/repair script and deterministic troubleshooting report script.
- GitHub Actions test workflow plus README badges and professional README hero image.

### Changed

- Dashboard headline totals now exclude probe/test events without a Hermes `session_id`; full audit totals remain available as `all_summary`.
- README and docs now clearly label savings as estimated schema-token savings, not guaranteed billable-token savings.

### Tested

- Added tests for decision logging, session-filtered summary accounting, dashboard API routes, and existing selector/provider behavior.

## 0.1.0 - 2026-05-03

Initial public release.

### Added

- Hermes plugin entry point `gizmo`.
- Deterministic tokenizer, corpus builder, local BM25 ranker, and selector.
- Config loader for `gizmo` settings in Hermes config files.
- CLI commands for status, doctor, index, select, benchmark, and config recommendations.
- Slash command and JSON tool handlers.
- Metrics for schema byte/token reduction estimates.
- Anthropic Tool Search helpers with explicit provider capability gating.
- JSON index store with checksum-based rebuilds.
- Upstreamable Hermes core selector-hook patch artifact.
- Documentation, examples, and unit tests.
