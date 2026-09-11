# Roadmap — v1.1

Recommended work after **v1.0.0-rc1**. None of this is required to operate RC1
on a trusted LAN with Tailscale Serve.

## Must-have for v1.1

1. **Durable notification outbox** — persist alert jobs (and optionally delivery
   history) so `docker compose restart api` does not drop Telegram activate /
   recover messages.
2. **Mock-off operator path** — first-boot wizard or clearer Settings so Immich,
   QNAP, and backup observer are live without hunting env vars.
3. **Disable or gate OpenAPI** in `HOMELAB_ENVIRONMENT=production` (`/docs`,
   `/redoc`, `/openapi.json`).
4. **Ship 10.3.3–10.3.5** on `main` and rebuild images so nginx PWA headers,
   Compose port 18081, and backup scripts match the running host.

## Should-have

- Scheduled Telegram reports: default operator schedule documented; hourly still
  opt-in.
- Production-health Dashboard probe that does not fight Telegram’s public URL
  (separate internal probe URL).
- Discord / Slack / email on the live alert path **or** remove those Settings
  fields.
- Compose-native SQLite snapshot (optional sidecar) in addition to host scripts.
- Agent protocol version aligned with product version, or an explicit
  compatibility matrix in the UI.
- Dashboard bundle code-splitting (build warns >500 kB).

## Could-have / later

- PostgreSQL, Prometheus/Grafana, Kubernetes.
- Agent auto-update.
- UPS monitoring.
- Write/control of NAS or backup jobs (out of scope for a read-only observer).
- inotify for local disks (not for CIFS Photo Monitor).

## Explicitly not in v1.1 unless product direction changes

- Public Funnel / WAN port-forward of the dashboard.
- A second reporting service alongside `TelegramReportService`.
- Replacing CIFS poll with inotify on NAS shares.
