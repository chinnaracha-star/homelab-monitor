# Scheduler consolidation plan

**Sprint:** 13.2 plan; Phases 13.12–13.15 complete through Photo Watcher interval ownership
**Status:** Execution ownership is wrapped. Backup, report, and Photo Watcher interval ownership are separated from their lifecycle loops. Phase 6 is not started.

## Current loops

`operations.factories` still returns the six coroutines. `JobExecutionWrapper` registers them at startup:

| Task | Loop |
| --- | --- |
| `offline_monitor` | Marks agents offline from check-in age |
| `infrastructure_monitor` | Polls connector snapshots |
| `telegram_reports` | `run_telegram_reports` loop calls `run_report_clock`: one 60-second sleep, then one tick |
| `notification_worker` | Drains the notification queue |
| `photo_watcher` | Scans NAS folders on the photo scan interval |
| `sqlite_backup` | `run_sqlite_backup` loop calls `run_backup_clock`, then `run_backup_once`. Logs `sqlite_backup_scheduler_started` |

`restart_scheduler` in Operations Center restarts the backup loop only. Photo scan interval, report due times, and the backup clock do not share a timetable. There is no second OS scheduler for these jobs.

## Future Job Engine

This section is the later scheduler, not Phase 13.12. The wrapper does not own sleep or overlap. One in-process engine would own sleep, overlap, and shutdown.

```text
API lifespan
    ↓
JobEngine
    ↓
Job: id, interval or cron, run(), overlap policy
```

The engine calls the current `run_*` functions. It does not move their business rules. Shutdown cancels the engine, which cancels the jobs, matching today's lifespan cancel.

## Migration phases

1. **Inventory.** This document is that list. Done.
2. **Wrapper.** Done in Phase 13.12 under [RFC-0002](rfc/RFC-0002-job-engine-execution-wrapper.md), commit `f9e1375`. `JobExecutionWrapper` starts and stops the same six factories. `factories` still returns six callables, not one task. Each loop still owns its interval. Production soak passed `2026-09-28T05:13:17Z`.
3. **Backup clock.** Done in Phase 13.13 under [RFC-0003](rfc/RFC-0003-backup-clock-ownership.md), commit `477a355`. `run_sqlite_backup` remains the loop. `run_backup_clock` is one wait, then `run_backup_once`. No seventh job. Natural backup passed at `2026-09-28T19:00:04Z` (`2026-09-29 02:00` Asia/Bangkok), one execution, then `sqlite_backup_sleep seconds=86396` toward `2026-09-30 02:00` Asia/Bangkok, still in the same process. One lifecycle is inferred, not taken from an asyncio dump. `restart_scheduler` still restarts `sqlite_backup` only.
4. **Report clock.** Done in Phase 13.14 under [RFC-0004](rfc/RFC-0004-report-clock-ownership.md), commit `ab23831`. `run_telegram_reports` remains the loop. `run_report_clock` is one 60-second sleep, then one tick. No seventh job. Controlled deploy `2026-09-29T05:07:37Z`. Natural 13:00 Asia/Bangkok hourly report `cbb105d3-c470-4f59-91f0-feb3722f5a24` at `2026-09-29 06:01:06` UTC, status `sent`, one row. The 14:00 slot also sent once at `2026-09-29 07:00:30` UTC. Hourly `last_sent` advanced to `2026-09-29T07:00:07.045860+00:00`. A later API recreate did not duplicate the 14:00 slot.
5. **Photo interval.** Done in Phase 13.15 under [RFC-0005](rfc/RFC-0005-photo-watcher-interval-ownership.md), commit `5940ad9`. `run_photo_watcher` remains the lifecycle loop. `run_photo_watcher_interval` is one normal scan/flush, dynamic-delay sleep, then return. The first scan remains immediate, batch state can shorten sleep, baseline and notification behavior remain unchanged, failure recovery remains 5 seconds, and registry/factories remain six. Production image `sha256:02ea247ed246d1c0865b39817b9a7608e177f04dc856d59c90f9ad637f8b1290` showed startup tick before first sleep and three natural 10-second sleeps. API stayed healthy with restart count 0.
6. **Retire private loops** only after each later phase has run in production for a release without missed jobs. Not started. Accepted [RFC-0006](rfc/RFC-0006-retire-private-loops.md) prepares timing extraction for `offline_monitor` and `infrastructure_monitor` only. It does not retire lifecycle loops and does not complete this phase.

Phases 3–6 each need their own accepted RFC. Phase 2 does not make the scheduler refactor complete.

## Compatibility strategy

Job names stay `offline_monitor`, `infrastructure_monitor`, `telegram_reports`, `notification_worker`, `photo_watcher`, and `sqlite_backup`. Health and logs keep those names. No new REST route describes the engine in the first wrapper sprint.
