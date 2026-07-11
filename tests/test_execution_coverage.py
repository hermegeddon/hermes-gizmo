import argparse
import json
import sqlite3

from hermes_gizmo.cli import handle_cli, setup_argparse
from hermes_gizmo.execution_coverage import execution_coverage_report


def _append_decision(path, *, session_id, platform="cli", execution_kind="kanban_worker", profile="default"):
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "timestamp": 1782440000.0,
        "context": {
            "session_id": session_id,
            "platform": platform,
            "execution_kind": execution_kind,
            "active_profile": profile,
            "dry_run": True,
        },
        "metrics": {"selected_tools": 20, "total_tools": 100},
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event) + "\n")


def _create_board_run(home, *, board, profile, session_id, run_id=1):
    db_path = home / "kanban" / "boards" / board / "kanban.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE task_runs (
            id INTEGER,
            task_id TEXT,
            profile TEXT,
            status TEXT,
            outcome TEXT,
            started_at REAL,
            metadata TEXT,
            error TEXT
        )
        """
    )
    conn.execute(
        "INSERT INTO task_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            run_id,
            "t_worker",
            profile,
            "done",
            "completed",
            1782440000.0,
            json.dumps({"worker_session_id": session_id}),
            None,
        ),
    )
    conn.commit()
    conn.close()
    return db_path


def test_execution_coverage_scans_default_and_profile_decision_logs(tmp_path):
    _append_decision(tmp_path / "gizmo" / "decisions.jsonl", session_id="root-session", profile="default")
    _append_decision(
        tmp_path / "profiles" / "frontend-eng" / "gizmo" / "decisions.jsonl",
        session_id="profile-session",
        profile="frontend-eng",
    )

    report = execution_coverage_report(tmp_path)

    log_profiles = {item["profile"] for item in report["decision_logs"]}
    assert log_profiles == {"default", "frontend-eng"}
    assert report["decision_index"]["session_count"] == 2
    assert report["decision_index"]["events"] == 2


def test_execution_coverage_joins_kanban_worker_session_ids_to_decisions(tmp_path):
    _append_decision(
        tmp_path / "profiles" / "frontend-eng" / "gizmo" / "decisions.jsonl",
        session_id="20260625_173453_ead4ff",
        profile="frontend-eng",
    )
    _create_board_run(
        tmp_path,
        board="navigator",
        profile="frontend-eng",
        session_id="20260625_173453_ead4ff",
    )
    _create_board_run(
        tmp_path,
        board="research",
        profile="reviewer",
        session_id="20260625_153603_9d71fc",
        run_id=2,
    )

    report = execution_coverage_report(tmp_path)
    kanban = report["kanban"]

    assert kanban["live_board_db_count"] == 2
    assert kanban["total_runs"] == 2
    assert kanban["runs_with_session_id"] == 2
    assert kanban["runs_with_session_id_matched_to_decision_log"] == 1
    assert kanban["runs_with_session_id_unmatched"] == 1
    by_profile = {item["profile"]: item for item in kanban["runs_by_profile"]}
    assert by_profile["frontend-eng"]["matched_runs"] == 1
    assert by_profile["frontend-eng"]["sid_match_rate_pct"] == 100.0
    assert by_profile["reviewer"]["unmatched_sid_runs"] == 1


def test_execution_coverage_cli_outputs_report(tmp_path, capsys):
    _append_decision(tmp_path / "gizmo" / "decisions.jsonl", session_id="root-session", profile="default")
    parser = argparse.ArgumentParser()
    setup_argparse(parser)
    args = parser.parse_args(["execution-coverage", "--home", str(tmp_path)])

    assert handle_cli(args) == 0

    output = json.loads(capsys.readouterr().out)
    assert output["home"] == str(tmp_path)
    assert output["decision_index"]["session_count"] == 1
