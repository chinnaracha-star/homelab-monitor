# Sprint 10.3.3 Regression Report

Date: 2026-09-09

## Scope

Reverse-proxy and Compose hardening only. No API route, authentication flow,
database schema, WebSocket event type, notification provider, or Tailscale
deployment was changed.

## Verified behavior

| Area | Result | Evidence |
| --- | --- | --- |
| Tailnet endpoint | Pass | `GET https://home-srv-01.tail1ea57f.ts.net/health` returned HTTP 200, service `healthy`, database `up` |
| nginx structure | Pass | Both Docker and systemd configurations parsed; only runtime include files were unavailable on the Windows test host |
| REST proxy | Pass | Dedicated `/api/` regression assertions verify standard HTTP forwarding without upgrade headers |
| WebSocket proxy | Pass | Both `/api/v1/ws/` and backward-compatible `/ws/` retain upgrade headers, disabled buffering, keepalive, and bounded timeouts |
| Security headers | Pass | Regression assertions cover CSP, nosniff, frame denial, referrer policy, and permissions policy |
| Compression/cache | Pass | Regression assertions cover gzip manifest MIME support, immutable hashed assets, and non-cacheable SPA/PWA entry files |
| Compose isolation | Pass | YAML parsed successfully; dashboard and API share internal `backend`, API alone joins `egress`, and only dashboard loopback ports are published |
| Dashboard lint | Pass with one pre-existing warning | `npm run lint`; warning remains in `SettingsPage.tsx` for synchronous state update in an effect |
| Dashboard tests | Pass | `npm run test` |
| Dashboard build | Pass | `npm run build` |
| Python lint/format | Pass | `ruff check .` and `ruff format --check .` |
| Sprint regression tests | Pass | `pytest tests/deployment/test_reverse_proxy_config.py` (6 tests) |

## Environment limitation

The complete Python suite was attempted on Windows. Existing API fixtures use
the Linux path `/tmp`, which resolves to protected `C:\tmp` on this host, and
three existing Ubuntu collector tests require `os.getloadavg`, which Windows
does not provide. The attempt reached 13 passing tests before those platform
failures. No production or test code outside this sprint was changed to mask
the limitation; CI remains the authoritative Linux full-suite gate.

Docker and nginx executables are not installed on this host, so `docker compose
config` and native `nginx -t` could not run. YAML was loaded directly and nginx
was parsed structurally as substitutes; deployment should still run both native
commands before rebuilding the production image.
