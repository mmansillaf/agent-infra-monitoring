# Agent Infra Monitoring

Tiny, dependency-free utilities for keeping long-running **AI agents and
background jobs** healthy: heartbeat checks, hung-process detection, timeouts
and alerting.

> A hung agent is worse than a failed one: it fails *silently*. This is the
> toolkit you reach for when you run agents, scrapers or batch workers on a
> server and need to know they are actually progressing.

## The problems this solves

| Problem | Symptom | Fix here |
|---|---|---|
| Agent hung (deadlock, waiting on a blocked call) | Process alive, no progress | `monitor.py --heartbeat <file>` |
| Long job never finished | Cron re-spawns duplicates | `--max-age` + stale lock detection |
| Silent crash | No logs, no alert | Exit-code + heartbeat age checks |
| Duplicate workers racing | Two instances of the same job | PID lock file |

## Files

| File | Purpose |
|---|---|
| `monitor.py` | CLI that checks a heartbeat file / process age and exits non-zero when unhealthy (cron-friendly: alert on non-zero exit) |
| `heartbeat_lib.py` | Small importable library: `touch_heartbeat()`, `check_heartbeat()`, `pid_lock()` |
| `cron.example` | Example crontab entries wiring the monitor to a health endpoint |

## Quickstart

```python
# in your agent loop
from heartbeat_lib import touch_heartbeat, pid_lock

with pid_lock("/tmp/my-agent.lock"):      # prevents duplicate workers
    while work_remaining():
        step()
        touch_heartbeat("/tmp/my-agent.hb")   # stamp: still alive
```

```bash
# every 5 minutes, from cron: alert if heartbeat older than 2 minutes
*/5 * * * * cd /opt/my-agent && python3 monitor.py \
    --heartbeat /tmp/my-agent.hb --max-age 120 \
    --on-fail "curl -fsS -X POST https://health.example.com/alert?agent=my-agent"
```

`monitor.py` exits `0` when healthy and `2` when unhealthy — pipe it to any
notification (curl, mail, ntfy, healthchecks.io).

## Design principles

1. **Zero dependencies** — stdlib only; drop into any server.
2. **Cron-friendly** — exit codes, not daemons. The OS supervises.
3. **Fail loudly** — if it cannot determine health, it reports unhealthy.
4. **Idempotent** — safe to run repeatedly, no state beyond the heartbeat file.

## License

MIT
