# Sprint 10.3.4 Regression Report

## Architecture

Production health is an additive read-only layer. `ProductionHealthService` composes the existing
SQLite session, Mission Control agent runtime, notification records, realtime hub, and Tailscale
service with host-level `psutil` and optional Docker CLI probes. The dashboard uses the existing
authenticated REST client and one 30-second live-polling cycle; no WebSocket protocol types or
database tables were added.

## Endpoints

- `GET /api/v1/system/health` — component status, latency, health score, and diagnostics
- `GET /api/v1/system/runtime` — agent, Docker, Telegram, and Tailscale runtime details
- `GET /api/v1/system/storage` — filesystem, database, logs, disk IO, and IO wait
- `GET /api/v1/system/network` — LAN/Tailscale addressing, gateway, connectivity, DNS, and counters

All endpoints retain the existing admin/operator/viewer read policy and return `unknown` or
`unavailable` data when an optional host integration cannot be inspected.

## Compatibility

- No database migration
- No authentication changes
- No existing response model changes
- No new WebSocket event types
- Existing `/health` and `/api/v1/system/remote-access` routes remain unchanged
- Docker and Tailscale probes are read-only and fail closed without raising API errors

## Verification

Verification completed on 9 September 2026:

- `ruff check .` — passed
- `ruff format --check .` — passed (164 files formatted)
- `pytest` — passed on Ubuntu (208 tests)
- `npm run lint` — passed with five pre-existing React advisory warnings
- `npm run test` — passed (147 tests)
- `npm run build` — passed; PWA service worker and 19-entry precache generated
- `docker compose config -q` — passed on Ubuntu

The Windows backend run reached 204 passing tests but retained three Linux-specific
`os.getloadavg` failures and one scheduler timing failure. The authoritative Ubuntu run passed all
208 tests. The shared fixture now uses the platform temporary directory and disposes SQLite before
cleanup, so API tests are portable and do not leave a locked database file.

## Deployment observations

- Docker details intentionally report unavailable when the CLI/socket is not exposed to the API.
- Tailscale details intentionally remain read-only; unknown optional fields do not fail the page.
- Dashboard probing uses `HOMELAB_DASHBOARD_HEALTH_URL`, defaulting to the Compose service URL.
