# Nginx

Nginx serves the React dashboard and reverse-proxies the FastAPI process.

## Paths

| Browser path | Upstream |
| --- | --- |
| `/` | SPA (`try_files` → `index.html`) |
| `/assets/` | Hashed Vite files, `Cache-Control: immutable` for one year |
| `/api/` | FastAPI (`/api/v1/...`), including WebSocket upgrades |
| `/ws/` | FastAPI `/api/v1/ws/` |
| `/health` | FastAPI `/health` |

The dashboard WebSocket client uses `/api/v1/ws/dashboard`. The `/api/`
location enables `Upgrade` and `Connection` headers so that socket works
without a separate `/ws` call. The `/ws/` location is provided for the same
upstream path.

## Files

| File | Use |
| --- | --- |
| `deploy/nginx/nginx.conf` | Full nginx config inside `Dockerfile.dashboard` (listen 8080, upstream `api:8000`) |
| `deploy/nginx/nginx.host.conf` | Full nginx config for systemd (`/etc/homelab-monitor/nginx.conf`) |
| `deploy/nginx/homelab-monitor.conf` | Server block for host installs (upstream `127.0.0.1:8000`) |

## Compression and cache

- `gzip` is on for text, JavaScript, JSON, CSS, and SVG
- `/assets/` is cached for 31536000 seconds
- `index.html` and SPA routes use `no-store`

## systemd

```bash
sudo cp deploy/nginx/nginx.host.conf /etc/homelab-monitor/nginx.conf
sudo cp deploy/nginx/homelab-monitor.conf /etc/homelab-monitor/homelab-monitor.conf
sudo nginx -c /etc/homelab-monitor/nginx.conf -t
sudo systemctl enable --now homelab-monitor-dashboard.service
```

Put a TLS terminator in front of port 80 for anything beyond a trusted LAN.
