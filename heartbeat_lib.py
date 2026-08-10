#!/usr/bin/env python3
"""
Minimal agent/background-job health library (stdlib only).

Three primitives:
  * pid_lock()          — prevent duplicate workers (with stale-lock recovery)
  * touch_heartbeat()   — stamp "I am alive" from inside the worker
  * check_heartbeat()   — ask "was the worker alive recently?"
"""
from __future__ import annotations

import os
import time
from pathlib import Path


def pid_lock(lock_path: str, stale_after: int = 3600) -> Path:
    """
    Acquire an exclusive lock. If an existing lock is older than
    `stale_after` seconds (process died without cleanup), steal it.

    Usage:
        with pid_lock("/tmp/job.lock"):
            ... do work ...
    """
    lock = Path(lock_path)
    now = int(time.time())
    if lock.exists():
        try:
            old_pid = int(lock.read_text().strip())
        except ValueError:
            old_pid = -1
        age = now - lock.stat().st_mtime
        if age < stale_after and _pid_alive(old_pid):
            raise SystemExit(f"another worker is running (pid {old_pid}, "
                             f"lock age {age}s)")
        # stale lock: remove and take over
        lock.unlink(missing_ok=True)

    lock.write_text(str(os.getpid()))
    return lock


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)  # signal 0 = existence probe, no signal sent
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # exists but owned by another user
    return True


def touch_heartbeat(path: str) -> None:
    """Stamp the current time into the heartbeat file."""
    Path(path).write_text(str(int(time.time())))


def check_heartbeat(path: str, max_age: int) -> tuple[bool, float]:
    """
    Return (healthy, age_seconds). Unhealthy when the file is missing,
    unreadable, or older than max_age seconds.
    """
    hb = Path(path)
    if not hb.exists():
        return False, float("inf")
    try:
        stamp = int(hb.read_text().strip())
    except (ValueError, OSError):
        return False, float("inf")
    age = time.time() - stamp
    return age <= max_age, round(age, 1)
