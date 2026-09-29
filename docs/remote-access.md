# Remote access (Tailscale)

HomeLab Monitor is reachable from outside the home through a Tailscale tailnet
only. Do not publish dashboard or API ports on the LAN router. Do not add
Cloudflare Tunnel, Traefik, or Caddy in front of this path. The MagicDNS HTTPS
route is Tailscale Serve alone. Android clients that do not use MagicDNS use a
separate host Nginx listener bound only to the Tailscale IPv4 address.

Local access on the server continues to work:

```text
http://localhost:18081
```

Remote access uses Tailscale HTTPS:

```text
https://<machine>.<tailnet>.ts.net
```

Dashboard login is unchanged (JWT). Viewer, operator, and admin use the same
accounts as on the LAN.

```text
Internet
    │
    ▼
Tailscale Network
    │
    ▼
Ubuntu Server (tailscaled + Serve)
    │
    ▼
Docker Compose
 ├── Dashboard  127.0.0.1:18081
 ├── API        (compose network only)
 └── SQLite
```

## Installing Tailscale

On the Ubuntu host (not inside the API container):

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

Confirm the CLI is present:

```bash
tailscale version
tailscale status
```

## Login

```bash
sudo tailscale login
sudo tailscale up
```

Use the printed URL on a phone or laptop that can complete the Tailscale login.
The node should appear in the Tailscale admin console.

## MagicDNS

In the Tailscale admin console:

1. Open DNS.
2. Enable MagicDNS.
3. Note the tailnet name (for example `tailnet.ts.net`).

The host should then have a name such as
`homelab-monitor.tailnet.ts.net`. Confirm:

```bash
tailscale status --json | python3 -c "import json,sys; print(json.load(sys.stdin)['Self']['DNSName'])"
```

## Enable HTTPS

In the Tailscale admin console:

1. Open DNS.
2. Enable HTTPS Certificates.

This issues certificates for MagicDNS names. HomeLab Monitor does not store
those certificates. Tailscale Serve presents them.

## Enable Serve

Bind Serve to the loopback dashboard port. Example with Compose overlay
`docker-compose.tailscale.yml` (host port `18081`):

```bash
export HOMELAB_DASHBOARD_PORT=18081
docker compose -f docker-compose.yml -f docker-compose.tailscale.yml up -d --build
sudo tailscale serve --bg 18081
```

If the dashboard is already on `http://127.0.0.1:18081`:

```bash
sudo tailscale serve --bg http://127.0.0.1:18081
```

Do **not** run `tailscale funnel`. Funnel would publish the dashboard on the
public internet. This project expects `funnel_enabled: false` and
`public: false`.

Confirm Serve is proxying `/` only on the tailnet:

```bash
tailscale serve status
```

## Verify

On the Ubuntu host:

```bash
curl -fsS http://127.0.0.1:18081/health
curl -fsS http://127.0.0.1:18081/
tailscale status
tailscale serve status
```

From another device on the same tailnet:

```text
https://<machine>.<tailnet>.ts.net
```

Log in with an existing dashboard user. JWT cookies/tokens are the same as
local use.

Optional Compose overlay mounts the host Tailscale socket read-only so the API
can report status at `GET /api/v1/system/remote-access`. If the socket is not
mounted, the dashboard still works over Serve; Mission Control shows
`not_installed` for detection only.

## Android access without MagicDNS

Phones that keep Private DNS on `one.one.one.one` and leave Tailscale DNS off
cannot resolve `*.ts.net`. They can still open the dashboard over the tailnet
by using the server Tailscale IPv4 directly.

Current production path:

```text
Android (Tailscale ON)
    |
    v
http://100.84.30.100:18082
    |
    v
Host Nginx, bound only to 100.84.30.100:18082
    |
    v
http://127.0.0.1:18081
    |
    v
HomeLab Dashboard
```

The existing MagicDNS route stays in place for clients that can resolve it:

```text
https://home-srv-01.tail1ea57f.ts.net
    -> Tailscale Serve
    -> http://127.0.0.1:18081
```

Telegram uses `HOMELAB_DASHBOARD_PUBLIC_URL=http://100.84.30.100:18082` for the
Dashboard button. That value is the only production setting recorded here.

Security boundaries:

- Port `18082` listens only on `100.84.30.100`. Do not bind it to `0.0.0.0`
  or a LAN address.
- The dashboard container stays on `127.0.0.1:18081`.
- Tailscale off makes `http://100.84.30.100:18082` unreachable.
- UFW was not changed for this path. Do not add `18082/tcp` for Anywhere.
- `http://100.84.30.100:18082` is HTTP at the application layer. Tailscale
  carries it inside the WireGuard tunnel between tailnet peers. That is not
  the same as the HTTPS MagicDNS route.

Realtime uses the WebSocket at `/api/v1/ws/dashboard`. The host Nginx site
`/etc/nginx/sites-available/homelab-dashboard-tailscale` must forward
`Upgrade` and `Connection`, with `proxy_read_timeout 75s` and
`proxy_buffering off`. The shared map lives in
`/etc/nginx/conf.d/connection-upgrade.conf`:

```nginx
map $http_upgrade $connection_upgrade {
    default upgrade;
    '' close;
}
```

If those headers are missing, normal HTTP pages still load and polling can
show the last data, while the dashboard reports realtime disconnected.

Android setup:

1. Install Tailscale and sign in to the same tailnet.
2. Set Private DNS to `one.one.one.one`.
3. Turn Tailscale on.
4. Open `http://100.84.30.100:18082`, or use the Telegram Dashboard button.

Validation completed on 2026-09-29 from Android on 5G with Private DNS
`one.one.one.one`:

- Tailscale on: dashboard, Telegram button, and realtime passed.
- Tailscale off: `http://100.84.30.100:18082` was unreachable.

Checks:

```bash
tailscale ip -4
tailscale serve status
ss -lnt
sudo nginx -t
sudo systemctl status nginx
curl -fsS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:18081/
curl -fsS -o /dev/null -w '%{http_code}\n' http://100.84.30.100:18082/
curl -fsS -o /dev/null -w '%{http_code}\n' https://home-srv-01.tail1ea57f.ts.net/
```

`ss` must show `100.84.30.100:18082` and `127.0.0.1:18081`. It must not show
`0.0.0.0:18082`, `[::]:18082`, or a LAN address on `18082`.

Rollback, if needed:

1. Set `HOMELAB_DASHBOARD_PUBLIC_URL` back to
   `https://home-srv-01.tail1ea57f.ts.net`.
2. Recreate only the API service so it reloads that variable.
3. Disable the dedicated `18082` Nginx site.
4. Remove `/etc/nginx/conf.d/connection-upgrade.conf` only when no other site
   uses `$connection_upgrade`.
5. Run `sudo nginx -t`, then reload Nginx.
6. Confirm `18082` is no longer listening and the MagicDNS HTTPS route still
   returns HTTP 200.

Do not run this rollback as part of normal operation. Leave Funnel disabled.
The phone must be connected to Tailscale. Cellular alone is not enough.

## Windows access

1. Install Tailscale for Windows.
2. Sign in to the same tailnet.
3. Open the MagicDNS URL in Edge or Chrome over HTTPS.
4. Confirm the padlock and log in as usual.

Do not port-forward 18081 on the Windows host or the Ubuntu router.

## Tablet access

Same as Android or iPad Tailscale: join the tailnet, then open the MagicDNS
HTTPS URL. The dashboard layout is responsive; Settings → Deployment can copy
the URL once you are already on the LAN or tailnet.

## Troubleshooting

### Tailscale missing

Symptom: `GET /api/v1/system/remote-access` returns `"status": "not_installed"`.

- Install Tailscale on the Ubuntu host.
- For Docker status detection, apply `docker-compose.tailscale.yml` so
  `/var/run/tailscale/tailscaled.sock` is visible to the API (read-only).
- The API never installs Tailscale.

### Serve disabled

Symptom: Connection is Connected, Serve is Disabled, HTTPS may still show
Enabled if certificates exist.

```bash
sudo tailscale serve --bg 18081
tailscale serve status
```

If Serve points at the wrong port, stop the previous serve target and bind
`18081` (or `http://127.0.0.1:18081`).

### MagicDNS unavailable

Symptom: Hostname is empty or the browser cannot resolve `*.ts.net`.

- Enable MagicDNS in the admin console.
- Confirm `tailscale status` shows `DNSName`.
- On the client, Tailscale must be connected so MagicDNS works.

### HTTPS certificate

Symptom: Browser warns on HTTP or certificate errors.

- Enable HTTPS Certificates in the Tailscale DNS settings.
- Use `https://` MagicDNS URLs, not `http://100.x.x.x`.
- Wait a minute after enabling certificates, then retry Serve.

### Firewall

- Do not open TCP 80/443/18081 on the router.
- Host firewall may allow loopback and Tailscale (`tailscale0`) only.
- UFW example (optional): allow Tailscale, deny WAN to 18081.

```bash
sudo ufw allow in on tailscale0
sudo ufw deny 18081
```

`docker compose` already binds the dashboard to `127.0.0.1`.

### Funnel accidentally enabled

```bash
tailscale funnel status
```

If Funnel is on, disable it in the Tailscale CLI/admin UI. HomeLab Monitor only
reads Funnel state; it will not turn Funnel off for you.

### JWT / login failures over HTTPS

- `VITE_API_BASE_URL` must stay `/api/v1` (same origin through Serve).
- Clear a stale token issued for `http://localhost:18081` and log in again on
  the HTTPS origin.

### Localhost still required

Keep `http://localhost:18081` (or `HOMELAB_DASHBOARD_PORT`) for on-server
debugging. Serve is additive; it does not replace loopback.
