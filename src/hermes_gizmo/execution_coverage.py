from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SESSION_ID_RE = re.compile(r"20\d{6}_\d{6}_[0-9a-f]{6}")


def _safe_json_loads(text: str | None) -> Any:
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _profile_from_decision_log(path: Path, home: Path) -> str:
    try:
        rel = path.resolve().relative_to((home / "profiles").resolve())
    except ValueError:
        return "default"
    return rel.parts[0] if rel.parts else "unknown"


def decision_log_paths(home: str | Path) -> list[Path]:
    """Return existing default and profile-local Gizmo decision logs."""

    root = Path(home).expanduser()
    paths: list[Path] = []
    default_log = root / "gizmo" / "decisions.jsonl"
    if default_log.is_file():
        paths.append(default_log)
    profiles_root = root / "profiles"
    if profiles_root.is_dir():
        for profile_home in sorted(child for child in profiles_root.iterdir() if child.is_dir()):
            log = profile_home / "gizmo" / "decisions.jsonl"
            if log.is_file():
                paths.append(log)
    return paths


def _iso_from_timestamp(value: Any) -> str | None:
    if not isinstance(value, int | float):
        return None
    return datetime.fromtimestamp(float(value), timezone.utc).isoformat()


def _safe_percent(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(100.0 * numerator / denominator, 3)


def _read_decision_logs(home: Path, since_ts: float | None = None) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    logs: list[dict[str, Any]] = []
    session_index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for path in decision_log_paths(home):
        profile = _profile_from_decision_log(path, home)
        events = 0
        bad_lines = 0
        sessions: set[str] = set()
        platforms: Counter[str] = Counter()
        execution_kinds: Counter[str] = Counter()
        dry_run_counts: Counter[str] = Counter()
        first_ts: float | None = None
        latest_ts: float | None = None
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line_number, line in enumerate(handle, 1):
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    bad_lines += 1
                    continue
                if not isinstance(event, dict):
                    bad_lines += 1
                    continue
                ts = event.get("timestamp")
                if since_ts is not None and (not isinstance(ts, int | float) or float(ts) < since_ts):
                    continue
                raw_context = event.get("context")
                context: dict[str, Any] = raw_context if isinstance(raw_context, dict) else {}
                events += 1
                if isinstance(ts, int | float):
                    first_ts = float(ts) if first_ts is None else min(first_ts, float(ts))
                    latest_ts = float(ts) if latest_ts is None else max(latest_ts, float(ts))
                platform = context.get("platform")
                if platform:
                    platforms[str(platform)] += 1
                execution_kind = context.get("execution_kind")
                if execution_kind:
                    execution_kinds[str(execution_kind)] += 1
                dry_run_counts[str(context.get("dry_run"))] += 1
                session_id = context.get("session_id")
                if session_id:
                    sid = str(session_id)
                    sessions.add(sid)
                    session_index[sid].append(
                        {
                            "profile": profile,
                            "path": str(path),
                            "line": line_number,
                            "platform": context.get("platform"),
                            "execution_kind": context.get("execution_kind"),
                            "dry_run": context.get("dry_run"),
                        }
                    )
        logs.append(
            {
                "profile": profile,
                "path": str(path),
                "events": events,
                "bad_lines": bad_lines,
                "sessions": len(sessions),
                "platforms": dict(platforms.most_common()),
                "execution_kinds": dict(execution_kinds.most_common()),
                "dry_run_counts": dict(dry_run_counts.most_common()),
                "first_utc": _iso_from_timestamp(first_ts),
                "latest_utc": _iso_from_timestamp(latest_ts),
            }
        )
    return logs, dict(session_index)


def live_kanban_db_paths(home: str | Path) -> list[Path]:
    root = Path(home).expanduser()
    paths: list[Path] = []
    root_db = root / "kanban" / "kanban.db"
    if root_db.is_file():
        paths.append(root_db)
    boards_root = root / "kanban" / "boards"
    if boards_root.is_dir():
        paths.extend(sorted(boards_root.glob("*/kanban.db")))
    return paths


def _session_ids_from_run(row: sqlite3.Row) -> list[str]:
    metadata = row["metadata"] if "metadata" in row.keys() else None
    error = row["error"] if "error" in row.keys() else None
    text = ""
    parsed = _safe_json_loads(metadata)
    if parsed is not None:
        text += json.dumps(parsed, default=str, sort_keys=True)
    elif metadata:
        text += str(metadata)
    if error:
        text += " " + str(error)
    return sorted(set(SESSION_ID_RE.findall(text)))


def _empty_profile_row() -> dict[str, int]:
    return {
        "runs": 0,
        "with_sid": 0,
        "matched_runs": 0,
        "unmatched_sid_runs": 0,
        "no_sid_runs": 0,
        "matched_sids": 0,
    }


def kanban_decision_coverage(home: str | Path, session_index: dict[str, list[dict[str, Any]]], since_ts: float | None = None) -> dict[str, Any]:
    root = Path(home).expanduser()
    by_profile: dict[str, dict[str, int]] = defaultdict(_empty_profile_row)
    by_board: Counter[str] = Counter()
    total_runs = 0
    runs_with_session_id = 0
    matched_runs = 0
    unmatched_sid_runs = 0
    matched_session_id_instances = 0
    examples: list[dict[str, Any]] = []
    unmatched_examples: list[dict[str, Any]] = []

    for db_path in live_kanban_db_paths(root):
        board = "root" if db_path.name == "kanban.db" and db_path.parent.name == "kanban" else db_path.parent.name
        try:
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if "task_runs" not in tables:
                continue
            rows = conn.execute(
                """
                SELECT id, task_id, profile, status, outcome, started_at, metadata, error
                FROM task_runs
                WHERE (? IS NULL OR started_at >= ?)
                ORDER BY started_at DESC, id DESC
                """,
                (since_ts, since_ts),
            ).fetchall()
        except sqlite3.Error:
            continue
        finally:
            try:
                conn.close()
            except Exception:
                pass

        for row in rows:
            total_runs += 1
            by_board[board] += 1
            profile = str(row["profile"] or "null")
            profile_row = by_profile[profile]
            profile_row["runs"] += 1
            sids = _session_ids_from_run(row)
            if not sids:
                profile_row["no_sid_runs"] += 1
                continue
            runs_with_session_id += 1
            profile_row["with_sid"] += 1
            hits = []
            for sid in sids:
                if sid in session_index:
                    hits.append({"session_id": sid, "decision_hits": session_index[sid][:3]})
            if hits:
                matched_runs += 1
                profile_row["matched_runs"] += 1
                matched_session_id_instances += len(hits)
                profile_row["matched_sids"] += len(hits)
                if len(examples) < 10:
                    examples.append(
                        {
                            "board": board,
                            "run_id": row["id"],
                            "task_id": row["task_id"],
                            "profile": profile,
                            "session_ids": sids,
                            "decision_hits": hits,
                        }
                    )
            else:
                unmatched_sid_runs += 1
                profile_row["unmatched_sid_runs"] += 1
                if len(unmatched_examples) < 10:
                    unmatched_examples.append(
                        {
                            "board": board,
                            "run_id": row["id"],
                            "task_id": row["task_id"],
                            "profile": profile,
                            "session_ids": sids,
                        }
                    )

    runs_by_profile = []
    for profile, row in sorted(by_profile.items(), key=lambda item: item[1]["runs"], reverse=True):
        runs_by_profile.append(
            {
                "profile": profile,
                **row,
                "sid_match_rate_pct": _safe_percent(row["matched_runs"], row["with_sid"]),
            }
        )

    return {
        "live_board_db_count": len(live_kanban_db_paths(root)),
        "total_runs": total_runs,
        "runs_with_session_id": runs_with_session_id,
        "runs_with_session_id_matched_to_decision_log": matched_runs,
        "runs_with_session_id_unmatched": unmatched_sid_runs,
        "matched_session_id_instances": matched_session_id_instances,
        "runs_by_profile": runs_by_profile,
        "runs_by_board": [{"board": board, "runs": count} for board, count in by_board.most_common()],
        "matched_examples": examples,
        "unmatched_examples": unmatched_examples,
    }


def execution_coverage_report(home: str | Path, since_ts: float | None = None) -> dict[str, Any]:
    root = Path(home).expanduser()
    logs, session_index = _read_decision_logs(root, since_ts=since_ts)
    return {
        "ok": True,
        "home": str(root),
        "since_utc": _iso_from_timestamp(since_ts) if since_ts is not None else None,
        "privacy": {
            "raw_prompts_included": False,
            "tool_args_included": False,
            "tool_outputs_included": False,
            "decision_context_paths_included": True,
        },
        "decision_logs": logs,
        "decision_index": {
            "events": sum(item["events"] for item in logs),
            "session_count": len(session_index),
            "log_count": len(logs),
        },
        "kanban": kanban_decision_coverage(root, session_index, since_ts=since_ts),
    }


def parse_since(value: str | None) -> float | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        pass
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()
