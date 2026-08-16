"""Tests for the heartbeat primitives (pid_lock, touch/check_heartbeat)."""

from __future__ import annotations

import os
import time

import heartbeat_lib as hb
import pytest


def test_pid_lock_acquires_and_serializes(tmp_path) -> None:
    lock = tmp_path / "job.lock"
    hb.pid_lock(str(lock))
    assert lock.exists()
    assert int(lock.read_text().strip()) == os.getpid()
    with pytest.raises(SystemExit):
        hb.pid_lock(str(lock))  # a second worker must be refused


def test_pid_lock_steals_stale_lock(tmp_path) -> None:
    lock = tmp_path / "job.lock"
    lock.write_text("999999999")  # pid that will not be alive
    mtime = os.path.getmtime(lock) - 5000  # force age > stale_after
    os.utime(lock, (mtime, mtime))
    hb.pid_lock(str(lock), stale_after=3600)
    assert int(lock.read_text().strip()) == os.getpid()


def test_pid_lock_fresh_lock_with_live_pid_raises(tmp_path) -> None:
    lock = tmp_path / "job.lock"
    lock.write_text(str(os.getpid()))
    with pytest.raises(SystemExit):
        hb.pid_lock(str(lock), stale_after=3600)


def test_touch_and_check_heartbeat_roundtrip(tmp_path) -> None:
    hb_file = tmp_path / "agent.hb"
    hb.touch_heartbeat(str(hb_file))
    healthy, age = hb.check_heartbeat(str(hb_file), max_age=60)
    assert healthy is True
    assert 0 <= age < 2


def test_check_heartbeat_missing_is_unhealthy(tmp_path) -> None:
    healthy, age = hb.check_heartbeat(str(tmp_path / "nope.hb"), max_age=60)
    assert healthy is False
    assert age == float("inf")


def test_check_heartbeat_stale_stamp_is_unhealthy(tmp_path) -> None:
    hb_file = tmp_path / "agent.hb"
    hb_file.write_text(str(int(time.time()) - 120))
    healthy, age = hb.check_heartbeat(str(hb_file), max_age=60)
    assert healthy is False
    assert age >= 119


def test_check_heartbeat_corrupt_stamp_is_unhealthy(tmp_path) -> None:
    hb_file = tmp_path / "agent.hb"
    hb_file.write_text("not-a-number")
    healthy, age = hb.check_heartbeat(str(hb_file), max_age=60)
    assert healthy is False
    assert age == float("inf")
