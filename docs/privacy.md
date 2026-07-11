# Privacy And Logging

Hermes Gizmo does not write raw user prompts to its decision log.

Decision events are stored at `$HERMES_HOME/gizmo/decisions.jsonl` when `gizmo.log_decisions: true`. Each event has three top-level fields:

- `timestamp`
- `metrics`
- `context`

`context` may include provider, model, platform, session ID, dry-run state, and schema count.

`metrics` includes selector mode, tool counts, schema byte/token estimates, selected tool names, always-included tool names, skip/fail-open reasons, selector timing, score details, top candidates, and expanded query tokens.

Dashboard headline totals exclude probe/test events without a `session_id`. Full audit data remains available through the dashboard API and local decision log.

Run this for the exact field inventory in the installed version:

```bash
hermes gizmo privacy
```
