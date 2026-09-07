# Architecture

## Version 1 boundary

HomeLab Monitor Toolkit uses an agent-server architecture. Bash agents collect
host-local information while the central server owns persistence, policy,
history, alert transitions, Telegram delivery, and the dashboard.

```text
Ubuntu host                         Central server
┌────────────────────┐             ┌───────────────────────────┐
│ Bash CLI and agent │ HTTPS POST  │ FastAPI                   │
│ System checks      ├────────────►│ Authentication            │
│ Docker checks      │             │ Config service            │
│ Immich checks      │◄────────────┤ Metrics and health score  │
│ QNAP adapter       │  Control    │ Alerts and Telegram       │
└────────────────────┘  response   │ SQLite and history        │
                                   │ React dashboard           │
                                   └───────────────────────────┘
```

## Communication model

Agents initiate outbound HTTPS requests every 60 seconds by default. The server
does not initiate connections to agents, and agents expose no network listener.
This works across normal LAN firewalls and avoids distributing TLS server
credentials to every monitored host.

Each accepted report response includes:

- next reporting interval
- current configuration revision and changed configuration
- minimum and latest supported agent versions
- reserved command metadata

Agent auto-update is not part of version 1.

## Trust boundaries

- The bootstrap registration key only authorizes registration.
- Registration returns a high-entropy agent token exactly once.
- Only a SHA-256 digest of the high-entropy token is stored.
- Each subsequent agent request uses its bearer token.
- Dashboard authentication is separate from agent authentication.
- Integration credentials must not be included in metric payloads or API responses.

The intended deployment boundary for version 1 is a trusted HomeLab LAN with
HTTPS termination. Internet-facing and multi-site operation are version 2 work.

## Persistence

SQLite is the version 1 database. Foreign keys and WAL mode are enabled. Alembic
owns schema changes. PostgreSQL is intentionally deferred until multi-site or
higher-write-volume requirements justify it.

Reports use a client-generated report ID and server-computed content hash.
Replaying the same report is safe; reusing an ID with different content is
rejected.
