# API development guide

## Start the API

Copy `.env.example` to `.env` and replace the registration key. Then install the
project, apply migrations, and start Uvicorn as described in the root README.

## Register an agent

```bash
curl --request POST http://127.0.0.1:8000/api/v1/agents/register \
  --header "Content-Type: application/json" \
  --header "X-Registration-Key: replace-with-the-registration-key" \
  --data '{
    "name": "home-server",
    "hostname": "home-server.local",
    "version": "0.1.0",
    "capabilities": ["ubuntu", "docker", "immich", "qnap"]
  }'
```

The response contains `agent_token`. Store it with file mode `0600`; the server
does not return it again.

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
