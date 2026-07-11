# Hermes Gizmo Performance Review Plan

Created: 2026-06-25 09:29:33 America/New_York
Workspace: `/home/openclaw/dev/hermes-stuff/plugins/hermes-gizmo`
Mode: planning only — no implementation, config mutation, deployment, service restart, push, or external action authorized.

## Goal

Review Hermes Gizmo performance since the latest settings change with quantifiable evidence, separating:

1. **Efficiency** — schema-token reduction and selector latency.
2. **Safety / tool availability** — whether required tools remain accessible and recovery paths work.
3. **Task quality** — whether real work still completes correctly, safely, and without extra user friction.
4. **Platform readiness** — whether WebUI, Desktop/TUI, Discord, CLI, cron, and other platforms have enough platform-specific evidence for their configured mode.

The review must not treat token savings as safety evidence. Savings, recovery, and task-quality evidence are separate gates.

## Current context snapshot

Read-only checks from the active default profile showed:

- Active config: `/home/openclaw/.hermes/config.yaml`
- Config mtime used as default review boundary: `2026-06-25T00:07:32.332118-04:00`
- Plugin enabled list includes `gizmo`.
- Base Gizmo config:
  - `enabled: true`
  - `mode: keyword`
  - `top_k: 8`
  - `dry_run: true`
  - `fail_open: true`
  - `progressive_enabled: true`
  - `progressive_max_loaded: 20`
- Active profile overrides currently exist for: `webui`, `tui`, `discord`.

Resolved effective config from `hermes_gizmo.config.load_config(...).for_context(...)`:

| Platform key | Enabled | Dry-run | Mode | Progressive | Notes |
|---|---:|---:|---|---:|---|
| `webui` | true | false | keyword | true | Active schema slimming. |
| `tui` | true | false | keyword | true | Configured active; likely Desktop if Desktop reports as `tui`. |
| `desktop` | true | true | keyword | true | No explicit profile; diagnostic/dry-run only if Desktop reports literal `desktop`. |
| `discord` | true | false | keyword | true | Configured active. |
| `cli` | true | true | keyword | true | Diagnostic/dry-run by default. |
| `api_server` | true | true | keyword | true | Diagnostic/dry-run by default. |

Decision-log snapshot at time of planning:

- Decision log: `/home/openclaw/.hermes/gizmo/decisions.jsonl`
- Total events: ~87k
- Post-config-boundary events: 686
- Post-config platform counts: `webui` 551, `cli` 132, `cron` 3
- WebUI post-boundary events are all `dry_run: false`.
- No post-boundary `tui` or `discord` events were observed in that snapshot.
- Literal `desktop` had no observed events in the decision log.

Earlier pre/post metric snapshot using the same config-mtime boundary showed:

| Metric | Post-boundary | Equal-length pre-boundary |
|---|---:|---:|
| Events | 617 | 1082 |
| Median estimated schema reduction | 77.9% | 76.3% |
| p95 selector latency | 125.8 ms | 167.7 ms |
| Skip rate | 1.62% | 3.14% |
| `full_tools_requested` rate | 1.13% | 2.40% |
| `below_min_estimated_reduction_percent` rate | 0.49% | 0.74% |
| `session_loaded_injected` events | 0 | 0 |

Interpretation: WebUI efficiency evidence is promising, but safety/recovery and Desktop/TUI coverage still need targeted evidence.

## Research and review principles consulted

### Agent QA / Gizmo rollout readiness

Use the rollout-readiness distinction:

- **Effectiveness evidence**: schema bytes/tokens saved, selected tool count, selector latency, per-platform coverage.
- **Safety evidence**: required tools were not lost, recovery tools remained exposed, hydration/full-schema recovery worked, platform canaries passed, rollback is immediate.

A platform can show strong savings and still be unsafe for non-dry-run if recovery and task-quality evidence are missing.

### EnterpriseClawBench-style evaluation protocol

Adopt protocol concepts only, not upstream benchmark data/code:

- Convert real sessions into self-contained evaluation tasks only with explicit privacy/provenance controls.
- Preserve fixture/source context and reject reasons.
- Run deterministic hard delivery checks before semantic scoring.
- Use modality-aware artifact review; never silently fall back from visual artifact scoring to text-only scoring.
- Record cost/runtime/tool-call/evidence-warning telemetry.
- Distinguish harness/model/platform interactions from model capability.

### AFTER / procedural-memory transfer framing

For skill/progressive-tool behavior and platform-specific settings:

- Do not promote a setting based on a single local success.
- Evaluate specificity vs generality: did the setting help the source platform, and does evidence transfer to Desktop/TUI/Discord?
- Watch for negative transfer between platforms.
- Prefer platform profiles/adapters over broad global changes when evidence is platform-specific.

## Plan structure

This plan is structured as an **evidence-gated rollout review**, not a generic benchmark. Each platform must pass separate gates for runtime alignment, efficiency, safety/recovery, and task quality.

## Step-by-step plan

### Phase 1 — Runtime and config alignment

Purpose: prove that the reviewed telemetry comes from the intended Gizmo runtime and config.

Collect and preserve:

1. Redacted config snapshot:
   - `gizmo` / `gizmo` section only.
   - plugin enabled state.
   - platform profiles.
2. Runtime status:
   - `hermes gizmo status`
   - `hermes gizmo doctor`
3. Package/import identity:
   - Python module path for `hermes_gizmo`.
   - package version if installed metadata exists.
   - current repo git commit.
4. Live schema snapshots:
   - platform label
   - schema/tool count
   - checksum
   - updated time
   - session presence, without leaking session IDs.
5. Selector-hook status:
   - whether Hermes core advertises/supports `select_tool_schemas`.
   - whether native Hermes Tool Search is available/active.

Metrics / gates:

| Gate | Required result |
|---|---|
| Config parses | pass |
| Plugin enabled | pass |
| `fail_open` | true |
| Decision logging | true or explicit blocker |
| Recovery tools visible | 100% for active platforms |
| Runtime path | intended checkout/install |
| Native Tool Search overlap | documented skip/interaction behavior |

Artifact target:

```text
~/.hermes/artifacts/gizmo-performance-review/<timestamp>/01-runtime-alignment.json
```

### Phase 2 — Decision-log pre/post analysis

Purpose: quantify operational behavior since the settings change and compare to a pre-change baseline.

Default boundary:

```text
/home/openclaw/.hermes/config.yaml mtime
```

If a more precise settings-change timestamp or backup file is identified, rerun the analysis using that boundary.

Aggregate globally and by `(platform, dry_run)`:

- event count
- first/last timestamp
- platform counts
- provider/model counts, if useful and non-sensitive
- mode counts
- median/p90/p95/max selection latency
- median/p90/p95/max selected tools
- median/p90/p95/max total tools
- median/p90/p95 estimated schema reduction
- median/p90/p95 approximate tokens saved
- skip rate and skip reasons
- `full_tools_requested` rate
- `below_min_estimated_reduction_percent` rate
- selector fail-open / exception evidence, if logged
- `session_loaded_injected` count/rate
- `recovery_meta_injected` count/rate
- two-pass hydration metrics, if present
- native Tool Search skip metrics, if present

Core formulas:

```text
estimated_reduction_percent = (schema_bytes_before - schema_bytes_after) / schema_bytes_before * 100
approx_tokens = serialized_schema_json_bytes / 4
skip_rate = skipped_events / total_events
full_tools_request_rate = full_tools_requested_events / total_events
active_event_rate = dry_run_false_events / total_events
```

Minimum summary tables:

1. Pre vs post overall.
2. Post by platform.
3. Post active-only (`dry_run=false`) by platform.
4. Post dry-run-only (`dry_run=true`) by platform.
5. Top selected tools and top skip reasons.

Interpretation gates:

| Metric | Healthy target |
|---|---:|
| WebUI active post-boundary events | >= 500 |
| Median schema reduction on large catalogs | >= 70% |
| p95 selector latency | < 150 ms preferred; < 250 ms acceptable |
| Skip rate | < 5%, unless explained by tiny catalogs/cron |
| `full_tools_requested` rate | < 3%, no rising trend |
| Selector exceptions not fail-open | 0 |
| Recovery-tool absence on active platform | 0 |

Artifact targets:

```text
~/.hermes/artifacts/gizmo-performance-review/<timestamp>/02-decision-log-summary.json
~/.hermes/artifacts/gizmo-performance-review/<timestamp>/03-pre-post-comparison.md
```

### Phase 3 — Platform exposure audit

Purpose: answer which surfaces are actually active versus dry-run.

Required platform classifications:

| Platform | Classification rule |
|---|---|
| WebUI | Active only if resolved `dry_run=false` and decision logs show `platform=webui`, `dry_run=false`. |
| Desktop/TUI | Determine whether Desktop reports as `tui`, `desktop`, or another platform key. |
| Discord | Active only if profile resolves `dry_run=false` and fresh events/canaries confirm. |
| CLI | Current expected state is dry-run unless a profile says otherwise. |
| API server | Current expected state is dry-run unless explicitly profiled. |
| Cron | Usually conservative; tiny tool catalogs may skip/produce low savings. |

Special Desktop question:

- If Desktop emits `platform=tui`, current config makes it active.
- If Desktop emits `platform=desktop`, current config leaves it dry-run.
- If Desktop emits another key, map it explicitly and decide whether to add a profile only after canary evidence.

Metrics / gates:

| Gate | Required result |
|---|---|
| Active platform names known | 100% for targeted surfaces |
| Active/dry-run classification matches config | 100% |
| Fresh event or canary per active platform | required before readiness claim |
| Recovery tools exposed per active platform | 100% |

Artifact target:

```text
~/.hermes/artifacts/gizmo-performance-review/<timestamp>/04-platform-exposure-audit.md
```

### Phase 4 — Historical-session replay benchmark

Purpose: detect hidden-tool misses that pure decision logs cannot prove.

Construct a private replay set from authorized local Hermes data only. Do not publish raw prompts, session IDs, secrets, local private paths, or artifacts.

Candidate sources:

- decision logs,
- live schema snapshots,
- sanitized session excerpts where authorized,
- task artifacts with explicit provenance,
- prior dry-run periods where full schemas remained available.

Task packet fields:

```yaml
id:
source_ref:
platform:
timestamp:
prompt_redacted:
schema_snapshot_ref:
selected_tools:
actual_tools_used:
expected_any:
expected_all:
forbidden_tools:
authority_boundary:
fixtures:
hard_rules:
semantic_rubric:
privacy_notes:
```

Sampling targets:

| Source class | Target count |
|---|---:|
| WebUI active post-change | 30-50 |
| CLI dry-run/control | 20-30 |
| TUI/Desktop fresh events | 10-20 after platform confirmation |
| Discord fresh events | 10-20 after canaries/traffic |
| Cron/subagent edge cases | 5-10 if relevant |
| All `full_tools_requested` events | include all feasible cases |

Replay metrics:

| Metric | Definition | Target |
|---|---|---:|
| `tool_recall@turn` | expected/actual needed tool present in selected set | >= 99% |
| `critical_tool_recall` | file/shell/search/patch/browser/web/memory/recovery tools present when required | 100% |
| `toolset_recall` | expected toolset represented | >= 99.5% |
| `false_reduction_rate` | request slimmed despite expected tool absent and no recovery | <= 0.5% |
| `recovery_success_rate` | fallback/hydration/details made missing tool available | 100% in canaries; inspect real events |
| `extra_turns_due_to_recovery` | added turns before progress resumes | median <= 1 |
| `unresolved_missing_tool_rate` | hidden tool caused failure/stall | 0 |
| `authority_boundary_preserved` | no unsafe workaround due to hidden tool | 100% |

Artifact targets:

```text
~/.hermes/artifacts/gizmo-performance-review/<timestamp>/05-replay-task-packets.jsonl
~/.hermes/artifacts/gizmo-performance-review/<timestamp>/06-replay-results.json
~/.hermes/artifacts/gizmo-performance-review/<timestamp>/07-replay-summary.md
```

### Phase 5 — Deterministic canary suite

Purpose: exercise tool-selection and recovery paths intentionally, including tools that normal traffic may not cover.

Build 60-100 canaries. Do not rely on the repo's current two-prompt demo eval as sufficient evidence.

Canary classes:

| Class | Count | Purpose |
|---|---:|---|
| File/repo operations | 10-15 | `read_file`, `search_files`, `patch`, `write_file`, `terminal` |
| Browser/web tasks | 8-12 | browser vs web search/extract distinctions |
| Git/build/test tasks | 8-12 | terminal + file/code workflow |
| Scheduling/cron tasks | 5-8 | `cronjob` selection and safe exclusions |
| Memory/skill tasks | 8-12 | `skill_view`, `skills_list`, `skill_manage`, memory/session search |
| Design/media/productivity | 5-8 | lower-frequency but important tools |
| MCP/platform tools | 5-10 | namespaced/verbose schemas |
| Recovery-only canaries | 10-15 | request-full/hydrate/details/load tools |
| Desktop/TUI canaries | 5-10 | confirm actual Desktop platform key and active/dry-run behavior |
| Discord canaries | 5-10 | confirm active profile behavior and recovery exposure |

Canary schema:

```yaml
name:
platform:
prompt:
required_any:
required_all:
forbidden:
expected_recovery_allowed:
authority_boundary:
hard_rules:
expected_notes:
```

Canary metrics / gates:

| Metric | Target |
|---|---:|
| Expected-tool hard checks | >= 99%; ideally 100% |
| Recovery canaries | 100% |
| Critical recovery tools present | 100% |
| Forbidden tools selected | 0 |
| Median schema reduction | >= 60-70% for large catalogs |
| p95 selector latency | < 150 ms preferred; < 250 ms acceptable |
| Selector exception fail-open | 100% |

Artifact targets:

```text
~/.hermes/artifacts/gizmo-performance-review/<timestamp>/08-canary-suite.yaml
~/.hermes/artifacts/gizmo-performance-review/<timestamp>/09-canary-results.json
~/.hermes/artifacts/gizmo-performance-review/<timestamp>/10-canary-summary.md
```

### Phase 6 — End-to-end task-quality audit

Purpose: verify that active slimming did not degrade actual outcomes.

Use hard delivery checks before semantic scoring, following the EnterpriseClawBench-style lesson.

Audit dimensions:

| Dimension | Examples |
|---|---|
| Hard completion | requested files/artifacts exist, commands/tests ran, artifact readable |
| Correct tool use | needed tool present or recovered; no fake substitute workflow |
| No fabricated work | no invented command output, file contents, APIs, or success claims |
| Safety | approvals, destructive/external boundaries, secrets, profile boundaries preserved |
| Friction | user retries/corrections attributable to missing tools; extra recovery turns |
| Artifact quality | parse/openability, diff sanity, citations, screenshots/visual checks when relevant |

Sample target:

- 30-50 WebUI tasks post-change.
- 20 CLI dry-run/control tasks.
- 10-20 Desktop/TUI tasks after platform confirmation.
- 10-20 Discord tasks after fresh canaries/traffic.
- All `full_tools_requested` events that can be safely inspected.

Task-quality metrics / gates:

| Metric | Target |
|---|---:|
| Hard-rule task success | >= 95% overall; 100% for simple/safety-critical tasks |
| Hidden-tool suspected failures | 0 |
| User correction attributable to missing tool | <= 1% |
| Unsupported/fabricated completion claims | 0 |
| Authority-boundary violations | 0 |
| Artifact parse/openability failures caused by missing tool | 0 |

Artifact target:

```text
~/.hermes/artifacts/gizmo-performance-review/<timestamp>/11-task-quality-audit.md
```

### Phase 7 — Verdict and rollout decision

Produce a final verdict by platform, not a single blanket result.

Verdict categories:

```text
PASS_ACTIVE
PASS_DRY_RUN_ONLY
NEEDS_MORE_EVIDENCE
REVISION_REQUIRED
ROLLBACK_OR_PAUSE
```

Platform verdict table:

| Platform | Efficiency | Safety/recovery | Task quality | Verdict | Recommendation |
|---|---|---|---|---|---|
| WebUI | evidence-backed | pending replay/canary | pending audit | TBD | likely continue active if gates pass |
| Desktop/TUI | configured if `tui`; unknown if `desktop` | needs fresh canaries | needs traffic | TBD | identify platform key first |
| Discord | configured active | needs fresh post-change evidence | needs traffic | TBD | canary before readiness claim |
| CLI | dry-run | can serve as control | n/a | dry-run | keep as diagnostic unless separately approved |
| API server | dry-run | sparse logs | n/a | dry-run | no promotion without evidence |
| Cron | conservative/tiny catalog | special-case | n/a | TBD | likely keep conservative |

Final report sections:

1. Boundary and scope.
2. Config/runtime proof.
3. Pre/post headline metrics.
4. Platform exposure audit.
5. Replay results.
6. Canary results.
7. Task-quality audit.
8. Risks and blockers.
9. Per-platform verdicts.
10. Safe next action and rollback path.

Artifact target:

```text
~/.hermes/artifacts/gizmo-performance-review/<timestamp>/12-final-verdict.md
```

## Acceptance gates

### WebUI can remain active if all pass

| Gate | Threshold |
|---|---:|
| Active WebUI post-change events | >= 500 |
| Median schema reduction | >= 70% |
| p95 selector latency | < 150 ms preferred; < 250 ms acceptable |
| Skip rate | < 5%, explained if higher |
| `full_tools_requested` rate | < 3%, no rising trend |
| Replay tool recall | >= 99% |
| Critical tool recall | 100% |
| Recovery canaries | 100% |
| Hidden-tool task failures | 0 |
| Recovery tools visible | 100% |
| Selector errors fail open | 100% |

### Desktop/TUI readiness gate

Before claiming Desktop is active and safe:

1. Determine actual platform key emitted by Desktop.
2. If key is `tui`, verify fresh non-dry-run events or run canaries.
3. If key is `desktop`, add no config change until a proposal/canary plan is approved; current effective config is dry-run.
4. Recovery tools must be visible in Desktop's effective schema set.
5. Run Desktop-specific canaries covering file/search/browser/recovery/progressive paths.

### Discord readiness gate

Before making a post-change readiness claim:

1. Generate fresh Discord events or canaries after the settings boundary.
2. Verify `dry_run=false` on those events.
3. Verify recovery tools are present.
4. Verify no hidden-tool misses in canaries.

## Rollback / pause triggers

Immediate rollback to dry-run or pause active slimming for a platform if any occur:

- Recovery tool absent from an active platform.
- Critical tool hidden with no successful recovery path.
- Hidden-tool miss causes task failure, unsafe workaround, or unsupported success claim.
- Selector exception does not fail open.
- p95 selector latency > 500 ms sustained.
- `full_tools_requested` > 10% over a meaningful active window.
- Repeated user corrections show missing-tool failures.
- Progressive mode injects stale/incorrect tools.
- Native Hermes Tool Search and Gizmo both actively slim the same request unexpectedly.

Rollback path should be platform-scoped when possible:

```yaml
gizmo:
  profiles:
    <platform>:
      dry_run: true
```

Do not globally disable Gizmo unless the failure is global or selector fail-open is compromised.

## Files likely to change during the review

Plan mode changes only this file.

If the review is executed later, expected review artifacts should live outside source code, e.g.:

```text
~/.hermes/artifacts/gizmo-performance-review/<timestamp>/
```

Potential source-repo additions only if separately authorized:

- expanded canary/eval prompt pack under `examples/` or `tests/fixtures/`,
- analysis script under `scripts/`,
- docs report under `docs/reports/`,
- tests for any discovered metric/config bug.

## Tests / validation for the review work

For the review artifact itself:

- Verify every JSON/JSONL output parses.
- Verify every metric in the final report maps to a source file/command/artifact.
- Verify no raw session IDs, raw prompts, secrets, or private paths leak into shareable summaries.
- Verify all platform names are literal observed config/log values.
- Verify final verdict distinguishes source facts from inference.

For any later code/doc changes caused by findings:

```bash
ruff check .
python -m compileall -q src tests dashboard-plugin/gizmo dashboard-plugin/gizmo
pytest -q
```

If canary fixtures are added:

- Add unit tests for expected-tool selection.
- Add regression tests for recovery tools and platform-profile resolution.
- Add a focused test for the misleading dry-run diagnostic if confirmed: diagnostic hook should resolve platform context or avoid claiming dry-run when the selector will use `dry_run=false`.

## Risks and tradeoffs

1. **Token savings can mask tool misses.**
   - Mitigation: separate replay/canary safety gates from efficiency metrics.
2. **Actual tool-call logs undercount hidden-tool failures.**
   - Mitigation: use counterfactual replay and hard expected-tool canaries.
3. **Desktop platform key is ambiguous.**
   - Mitigation: classify observed platform key before changing config.
4. **Private transcript leakage risk.**
   - Mitigation: redacted packets, no raw prompts/session IDs in shareable report, local-only artifacts unless explicitly approved.
5. **Platform-specific negative transfer.**
   - Mitigation: per-platform verdicts; prefer profiles over global config changes.
6. **Progressive mode may be untested.**
   - Mitigation: explicit progressive load/unload/hydration canaries.
7. **Native Hermes Tool Search overlap.**
   - Mitigation: audit skip behavior and bridge-tool presence; no double-slimming.

## Open questions

1. What exact event should define “last settings change” if not `/home/openclaw/.hermes/config.yaml` mtime?
2. What platform key does Desktop actually emit in the live runtime: `tui`, `desktop`, or something else?
3. Should the review create repo-owned reusable canary fixtures, or keep all review artifacts under `~/.hermes/artifacts/`?
4. Should WebUI remain active during replay/canaries, or should a parallel dry-run/control profile be created for comparison?
5. Which platforms are in scope for a final readiness verdict: WebUI + Desktop only, or also Discord/CLI/cron/subagents?

## Definition of done

The review is complete when:

- Runtime/config alignment is proven for the intended Gizmo instance.
- Pre/post decision-log metrics are computed and preserved.
- Platform active/dry-run status is explicitly classified.
- WebUI has efficiency, safety/recovery, and task-quality evidence.
- Desktop/TUI has an observed platform-key classification and fresh canary evidence.
- Discord is either fresh-canary reviewed or explicitly marked insufficient evidence.
- Recovery tools are verified for every active platform in scope.
- Replay/canary/task-quality findings are mapped to proof artifacts.
- Final verdict names per-platform recommendations and rollback triggers.
- No raw private prompts, session IDs, secrets, or unauthorized external data are leaked.
