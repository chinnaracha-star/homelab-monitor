# Scheduler consolidation plan

**Sprint:** 13.2  
**Status:** Plan only. No scheduler is replaced.

## Current loops

`operations.factories` starts six asyncio tasks in the API process:

| Task | Loop |
| --- | --- |
| `offline_monitor` | Marks agents offline from check-in age |
| `infrastructure_monitor` | Polls connector snapshots |
| `telegram_reports` | Wakes and sends hourly, daily, and weekly reports when due |
| `notification_worker` | Drains the notification queue |
| `photo_watcher` | Scans NAS folders on the photo scan interval |
| `sqlite_backup` | Own sleep loop. Logs `sqlite_backup_scheduler_started` |

`restart_scheduler` in Operations Center restarts the backup loop only. Photo scan interval, report due times, and the backup clock do not share a timetable. There is no second OS scheduler for these jobs.

## Future Job Engine

One in-process engine that owns sleep, overlap, and shutdown.

```text
API lifespan
    ↓
JobEngine
    ↓
Job: id, interval or cron, run(), overlap policy
```

The engine calls the current `run_*` functions. It does not move their business rules. Shutdown cancels the engine, which cancels the jobs, matching today's lifespan cancel.

## Migration phases

1. **Inventory.** This document is that list. No code.
2. **Wrapper.** A `JobEngine` starts the same six coroutines and logs start and stop. `factories` returns that one task. Behavior of each loop stays.
3. **Backup clock.** Register the backup sleep loop as a job. `restart_scheduler` restarts that job only, as it does now.
4. **Report clock.** Register report due checks as a job. Due rules stay in `telegram_reports.py`.
5. **Photo interval.** Register the watcher. Scan interval still comes from photo settings.
6. **Retire private loops** only after each wrapper has run in production for a release without missed jobs.

Phases 2–6 need an accepted RFC each. Phase 1 is this sprint.

## Compatibility strategy

Job names stay `offline_monitor`, `infrastructure_monitor`, `telegram_reports`, `notification_worker`, `photo_watcher`, and `sqlite_backup`. Health and logs keep those names. No new REST route describes the engine in the first wrapper sprint.
