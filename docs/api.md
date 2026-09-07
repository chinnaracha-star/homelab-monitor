# API development guide

## Start the API

Copy `.env.example` to `.env` and replace the registration key. Then install the
project, apply migrations, and start Uvicorn as described in the root README.

## Register an agent

With the API running, execute this from the repository root. The snippet reads
`HOMELAB_REGISTRATION_KEY` directly from `.env`; it does not require exporting
the key into the shell:

```bash
AGENT_TOKEN="$(
  .venv/bin/python - <<'PY'
import socket

import httpx
from dotenv import dotenv_values

config = dotenv_values(".env")
registration_key = config.get("HOMELAB_REGISTRATION_KEY")
if not registration_key:
    raise SystemExit("HOMELAB_REGISTRATION_KEY is missing from .env")

response = httpx.post(
    "http://127.0.0.1:8000/api/v1/agents/register",
    headers={"X-Registration-Key": registration_key},
    json={
        "name": socket.gethostname(),
        "hostname": socket.gethostname(),
        "version": "0.1.0",
        "capabilities": ["ubuntu"],
    },
)
response.raise_for_status()
print(response.json()["agent_token"])
PY
)"
```

The one-time token is now available as `AGENT_TOKEN` in the current shell
without being printed. Store it in the agent environment file with mode `0600`;
the server does not return it again.

## Upload a report

```bash
curl --request POST http://127.0.0.1:8000/api/v1/agent/reports \
  --header "Authorization: Bearer AGENT_TOKEN" \
  --header "Content-Type: application/json" \
  --data '{
    "report_id": "home-server-000001",
    "schema_version": "1.0",
    "observed_at": "2026-09-07T05:00:00Z",
    "config_revision": 1,
    "modules": [{
      "module": "system",
      "status": "healthy",
      "summary": "System resources are within thresholds",
      "metrics": {
        "cpu_percent": 12.5,
        "memory_percent": 44.0
      }
    }]
  }'
```

Retrying an identical `report_id` and payload is idempotent. Reusing the ID with
different content returns HTTP `409`.

Interactive OpenAPI documentation is available at `/docs`.

## Ubuntu agent integration

The packaged agent implements check-in and report upload automatically. Configure
it with the one-time registration token and run:

```bash
.venv/bin/homelab-agent --env-file ./agent.env run
```

The current agent sends a full system report each cycle. Buffered retries retain
the original `report_id`, so the API's existing idempotency contract prevents
duplicate database rows.
