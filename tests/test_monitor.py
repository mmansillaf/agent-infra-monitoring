"""Tests for the monitor CLI (exit codes, pidfile check, on-fail command)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import heartbeat_lib as hb
from monitor import check_pidfile

REPO_ROOT = Path(__file__).resolve().parent.parent


def run_monitor(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "monitor.py", *args],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,  # returncode is asserted by the caller
    )


def test_monitor_healthy_exits_0(tmp_path) -> None:
    hb_file = tmp_path / "agent.hb"
    hb.touch_heartbeat(str(hb_file))
    out = run_monitor("--heartbeat", str(hb_file), "--max-age", "60")
    assert out.returncode == 0
    assert "[OK]" in out.stdout


def test_monitor_missing_heartbeat_exits_2(tmp_path) -> None:
    out = run_monitor("--heartbeat", str(tmp_path / "missing.hb"), "--max-age", "60")
    assert out.returncode == 2
    assert "[UNHEALTHY]" in out.stderr


def test_monitor_on_fail_runs_without_shell(tmp_path) -> None:
    marker = tmp_path / "alerted"
    out = run_monitor(
        "--heartbeat",
        str(tmp_path / "missing.hb"),
        "--max-age",
        "60",
        "--on-fail",
        f"touch {marker}",
    )
    assert out.returncode == 2
    assert marker.exists()


def test_check_pidfile_live_process(tmp_path) -> None:
    pidfile = tmp_path / "job.pid"
    pidfile.write_text(str(os.getpid()))
    ok, msg = check_pidfile(str(pidfile), max_age=60)
    assert ok is True
    assert "alive" in msg


def test_check_pidfile_dead_process(tmp_path) -> None:
    pidfile = tmp_path / "job.pid"
    pidfile.write_text("999999999")
    ok, msg = check_pidfile(str(pidfile), max_age=60)
    assert ok is False
    assert "not running" in msg
