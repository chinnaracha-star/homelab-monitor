# Job engine

**Sprint:** 13.5  
**Status:** Registry only. `operations.factories` still starts the same asyncio loops.

## Current architecture

Application startup builds six coroutines and schedules them itself:

| Job | Loop |
| --- | --- |
| offline_monitor | `run_offline_monitor` |
| infrastructure_monitor | `run_infrastructure_monitor` |
| telegram_reports | `run_telegram_reports` |
| notification_worker | `run_notification_worker` |
| photo_watcher | `run_photo_watcher` |
| sqlite_backup | `run_sqlite_backup` |

Intervals, enable flags, and sleep calls stay in those modules. The job engine is not imported by startup.

## Target architecture

```text
Job Engine
    ↓
Job Registry (metadata)
    ↓
Existing loop (still owns execution)
```

Later, the engine may start and stop the same coroutines. Until that sprint, `JobEngine` only registers and describes jobs.

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

1. Keep this metadata registry unused by startup.
2. Have startup read the registry and still call the same coroutines.
3. Move start and stop into the engine without changing intervals.
4. Replace the separate loops with one scheduler only after intervals and enable flags match current behavior in tests.

## Future scheduler replacement

One coordinator can own the six loops. It must keep `alert_evaluation_interval_seconds`, `infrastructure_refresh_seconds`, the 60-second report tick, the notification poll, the photo scan interval, and the backup delay. Removing a loop before that parity check would change runtime behavior.
