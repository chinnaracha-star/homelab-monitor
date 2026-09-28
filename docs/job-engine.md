# Job engine

**Sprint:** 13.5 registry, 13.12 execution wrapper
**Status:** Metadata registry plus lifespan ownership. Not a generalized scheduler.

## Current architecture

`JobEngine` still only stores `JobDefinition` metadata. `JobExecutionWrapper` in `jobs/execution.py` creates and stops the six background tasks during application lifespan. It checks `operations.factories(settings)` against `default_engine().jobs()` before calling `register_background`. Sleep, due checks, and delivery stay in the existing loops.

| Job | Loop |
| --- | --- |
| offline_monitor | `run_offline_monitor` |
| infrastructure_monitor | `run_infrastructure_monitor` |
| telegram_reports | `run_telegram_reports` |
| notification_worker | `run_notification_worker` |
| photo_watcher | `run_photo_watcher` |
| sqlite_backup | `run_sqlite_backup` |

Lifespan calls `jobs.start(settings)` before `yield`. Shutdown is `hub.stop()`, then `await jobs.stop()`. A second `start()` while that start is active does not create more tasks and does not revive a finished or failed task. `stop()` cancels the tasks from the successful start and the current `runtime_control` task for each of those names, including one replaced by `restart_background`. One running task failure does not cancel the others. There is no `TaskGroup`, retry loop, or persistent scheduler.

If a later registration raises, the exception propagates, the wrapper does not mark itself started, `start()` does not call `stop()`, and earlier tasks from that attempt are not cancelled. That matches [RFC-0002](rfc/RFC-0002-job-engine-execution-wrapper.md).

## Target architecture

```text
Application lifespan
    ↓
JobExecutionWrapper
    ↓
Job registry names checked against operations.factories
    ↓
Existing loop (still owns timing and delivery)
```

A later scheduler that owns intervals is a separate RFC. See [refactor-scheduler.md](refactor-scheduler.md).

## Registry

`default_engine()` registers the six jobs above. Each `JobDefinition` has name, description, category, current implementation, schedule text, enabled flag, and owner. Execution stays in the named function.

## Categories

Every job uses one of:

- Monitoring
- Notification
- Backup
- Reporting
- Maintenance
- Infrastructure

Maintenance is reserved for future work. A new job must use one of these names.

## Lifecycle

Documented states only. The engine does not transition them.

```text
Registered
    ↓
Enabled
    ↓
Running
    ↓
Paused
    ↓
Stopped
    ↓
Disabled
```

Today every factory job is started with the process. Pause, stop, and disable are not implemented here.

## Migration phases

1. Metadata registry. Done in Phase 13.5.
2. Startup checks registry names and still calls the same factories. Done in Phase 13.12 as `JobExecutionWrapper`.
3. Move intervals into one scheduler only after a later accepted RFC. Not started.

## Phase 13.12 production checkpoint

Complete, deployed, and soak passed. Commit `f9e1375`. API image `sha256:a53e9a0b0c0b7453370eb9a33b2eef2874217c84b17a4a4ca8caccc6f8b47b36`, deployed `2026-09-28T04:36:32Z`. Soak at `2026-09-28T05:13:17Z` (about 37 minutes): API healthy, restart count 0, registry 6/6, startup once, no lifecycle traceback. One natural `hourly_report` at `2026-09-28 05:01:02` UTC, status `sent`, with no second row in that window. The notification row does not store the message body.

Live task count is inferred from the health registry, a single startup, and that one report. It was not read from an asyncio task dump. The soak did not call `restart_background`; tests cover shutdown of a replaced task. Photo watcher kept ticking and had no new photo event. Backup logged one start and a sleep of about 51802 seconds, so a backup run was not due. `home-srv-01` stayed online. QNAP stayed healthy as `Chin-HomeNas` / `TS-X53B`, four disks, thresholds 55°C / 60°C, with storage percent, SMART, manufacturer, disk model, and capacity still null. Dashboard stayed on `sha256:0e5486e2f0379c3a3f30b21d16538b518c85427cdc714cec716800472ad201f8`. Rollback image `homelab-monitor-api:rollback-phase13.12-predeploy` is `sha256:27eadf9bfa71e3b53dce7bd6d55e21b72083bede444b4e5a974d99ea6a965916`. Phase 13.11 rollback tags and the QNAP recovery copies under `/tmp/homelab-qnap-recovery` and `~/homelab-qnap-recovery` stay in place. No credential leak was seen in post-deploy logs. No manual report, backup, photo scan, or Docker prune was used for the soak.

## Future scheduler replacement

One coordinator can own the six loops. It must keep `alert_evaluation_interval_seconds`, `infrastructure_refresh_seconds`, the 60-second report tick, the notification poll, the photo scan interval, and the backup delay. Removing a loop before that parity check would change runtime behavior.
