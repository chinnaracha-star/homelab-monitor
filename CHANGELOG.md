# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project will use [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Initial FastAPI service and health endpoint.
- SQLite persistence managed by Alembic.
- One-time agent credential issuance with hashed token storage.
- Authenticated agent check-in, configuration sync, and idempotent metrics upload.
- Structured request logging, API tests, and GitHub Actions quality gates.
- Python Ubuntu agent with `run` and `collect` commands.
- CPU, memory, filesystem, load-average, uptime, OS, hostname, and optional
  temperature collection.
- Server-controlled reporting intervals and threshold configuration sync.
- Bounded exponential retry and persistent SQLite offline report queue.
- Graceful SIGINT/SIGTERM shutdown and hardened systemd service example.
- Agent collector, transport, authentication, buffering, restart, and retry tests.
- Read-only Dashboard API for overview counts, agent lists, agent details, and
  latest metric reports.
- Persisted alert-state engine for CPU, memory, disk, temperature, and offline
  agent detection.
- Reusable Telegram Bot API notifier for new and reopened alert transitions,
  with environment configuration and duplicate-notification suppression.
- Dashboard user accounts, bcrypt password hashing, and HS256 JWT access tokens.
- `POST /api/v1/auth/login` and `GET /api/v1/auth/me`.
- JWT protection for dashboard, agent-read, and alert-read APIs.
- React login page, route guards, logout, and navbar session display.
- Role-based access control with a reusable `require_roles` dependency.
- Admin-only user listing and admin/operator alert acknowledgement.
- Dashboard navigation and route gates driven by a single `can()` helper.
- Default `admin`, `operator`, and `viewer` accounts seeded by migration `0003`,
  with missing defaults created at API startup without overwriting existing users.
- Admin-only user management APIs and a Users page for create, edit, password
  reset, enable/disable, and delete, with last-admin and self-account protections.
- JWT-authenticated dashboard WebSocket at `GET /api/v1/ws/dashboard`.
- Real-time broadcasts for agent check-in, report upload, alert changes, and
  agent online/offline transitions.
- Dashboard socket client with reconnect, heartbeat, connection status, and
  polling fallback while disconnected.
- `metric_history` table and Alembic migration `0004_add_metric_history`.
- `GET /api/v1/history/agents/{agent_id}` time-series API with interval
  aggregation and CSV export.
- Agent Detail history charts for CPU, memory, disk, and temperature.
- Docker images and Compose files for the API and nginx dashboard.
- systemd units for the API and dashboard, plus SQLite/log/config backup scripts.
- Agent groups (`agent_groups`, `agent_group_members`) and Alembic migration
  `0005_add_agent_groups`.
- Group CRUD, membership, and summary APIs, plus overview `groups` and
  `group_stats` fields.
- Groups and Group Detail pages, group filter on Agents, bulk assign dialog,
  and overview group cards.
- Notification dispatcher with Telegram, Discord, Slack, and email providers.
- Alembic migration `0006_add_notifications` plus delivery history and
  dashboard notification settings.
- Configurable alert rules (`alert_rules`) and Alembic migration
  `0007_add_alert_rules`.
- Alert Rules page for create, edit, delete, enable/disable, search, and filter.
- Read-only infrastructure connectors (QNAP, Docker, Immich, QuMagie, backup)
  with mock mode, aggregated snapshots, and an Infrastructure dashboard page.
- Read-only Photo Services snapshots (Immich, QuMagie, QNAP storage) with live
  GET collectors when configured, aggregated statistics, and a Photo Services
  dashboard page.
- Read-only Backup monitoring for a TS-253 Pro target (`GET /api/v1/backup`),
  Backup page, Overview backup cards, Backup Progress, and Backup History.
- Photo Services Storage History and Photo Growth, plus `ops_snapshots`
  (Alembic `0008`) for live trend windows.
