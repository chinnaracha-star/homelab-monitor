# Changelog

All notable changes to HomeLab Monitor Toolkit are documented here.

## [1.0.0-rc1] — 2026-09-10

First release candidate. Package, API, and dashboard version strings report
`1.0.0-rc1`. Agent protocol compatibility remains `0.1.0` unless operators raise
`HOMELAB_MINIMUM_AGENT_VERSION`.

### Added

- Ubuntu agent with outbound HTTPS reports, local retry queue, and systemd units
- FastAPI control plane with SQLite history, JWT dashboard auth, and RBAC
- React dashboard (Overview, Agents, Groups, Alerts, Alert Rules, Users, Settings)
- Analytics, trends, capacity, insights, and predictions pages
- Alert timeline, incidents, Notification Center, and production health
- Photo Services (Immich, QuMagie, QNAP storage) and Backup observer pages
- Configurable alert rules and alert stability windows
- Telegram delivery worker with in-memory queue, 10s batching, three retries
- Notification delivery history and metrics APIs (process memory)
- Docker Compose stack (API + nginx dashboard), PWA, Tailscale Serve notes
- Bootstrap passwords via `HOMELAB_BOOTSTRAP_*_PASSWORD` (no shipped defaults)

### Changed

- Alert engine enqueues Telegram jobs instead of calling the multi-channel
  dispatcher on the live path
- Notification Center loads delivery history and metrics from dedicated endpoints
- Production Compose uses `backend` plus `egress` networks (API egress, dashboard
  internal to the API)
- README and operator docs describe v1.0.0-rc1 instead of early Phase 8 status

### Fixed

- Reverse-proxy compose test matches the backend + egress layout
- Production no longer seeds `admin123` / `operator123` / `viewer123`
- Version strings aligned across pyproject, API health/OpenAPI, and dashboard PWA

### Security

- Dashboard users must be created from environment bootstrap passwords
- Known insecure default passwords are rejected in `production`
- JWT secret and registration key remain required; examples are placeholders only
- Dashboard published on loopback; API is not published on the host

### Known Limitations

See [docs/known-limitations.md](docs/known-limitations.md). Summary: in-memory
notification queue and delivery history; Discord/Slack/email not on the live
alert path; infrastructure mock defaults to on; SQLite backup is host scripts
not Compose snapshots.

[1.0.0-rc1]: docs/release-notes-v1.0.0-rc1.md
