#!/usr/bin/env python3
"""
Cron-friendly agent health monitor.

Exits 0 when the agent is healthy, 2 when unhealthy (hung / dead / stale),
and runs an optional --on-fail command for alerting.

Examples:
    python3 monitor.py --heartbeat /tmp/agent.hb --max-age 120
    python3 monitor.py --heartbeat /tmp/agent.hb --max-age 120 \
        --on-fail "curl -fsS -X POST https://health.example.com/alert?agent=a"
    python3 monitor.py --pidfile /tmp/agent.pid --max-age 1800
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

from heartbeat_lib import check_heartbeat, _pid_alive


def check_pidfile(path: str, max_age: int) -> tuple[bool, str]:
    try:
        pid = int(open(path).read().strip())
    except (OSError, ValueError):
        return False, f"pidfile {path} missing or unreadable"
    if not _pid_alive(pid):
        return False, f"pid {pid} is not running"
    age = time.time() - os.path.getmtime(path)
    if age > max_age:
        return False, f"process {pid} alive but pidfile age {age:.0f}s > {max_age}s"
    return True, f"process {pid} alive, age {age:.0f}s"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--heartbeat", help="heartbeat file path")
    ap.add_argument("--pidfile", help="pid file path (alternative check)")
    ap.add_argument("--max-age", type=int, required=True,
                    help="max allowed age in seconds")
    ap.add_argument("--on-fail", default="", help="shell command on unhealthy")
    args = ap.parse_args()
    if not (args.heartbeat or args.pidfile):
        ap.error("provide --heartbeat or --pidfile")

    if args.heartbeat:
        healthy, age = check_heartbeat(args.heartbeat, args.max_age)
        detail = f"heartbeat age {age}s (max {args.max_age}s)"
    else:
        healthy, detail = check_pidfile(args.pidfile, args.max_age)

    if healthy:
        print(f"[OK] {detail}")
        return 0
    print(f"[UNHEALTHY] {detail}", file=sys.stderr)
    if args.on_fail:
        try:
            subprocess.run(args.on_fail, shell=True, check=False,  # noqa: S602
                           timeout=30)
        except subprocess.TimeoutExpired:
            print("on-fail command timed out", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
