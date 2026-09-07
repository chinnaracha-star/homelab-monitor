# Real-time dashboard

The dashboard receives live updates over a JWT-authenticated WebSocket. REST
read APIs are unchanged. HTTP polling remains as a fallback whenever the socket
is not connected.

## Endpoint

`GET /api/v1/ws/dashboard`

Authenticate with a dashboard access token as `?token=` or
`Authorization: Bearer`. Unauthenticated or inactive users are closed with code
`4401`.

## Events

Every message includes `id`, `type`, `timestamp`, and `payload`.

| Type | When |
| --- | --- |
| `connection` | After accept (`status: connected`) and on server heartbeat (`status: heartbeat`) |
| `overview_updated` | Successful agent check-in, report upload, or offline evaluation that changed state |
| `agent_updated` | Same ingest paths, including online/offline status changes |
| `alert_updated` | Alert evaluation after ingest, offline evaluation, or alert acknowledgement |

Payload fields:

- `reason`: `check_in`, `report`, `report_duplicate`, `offline_evaluation`, `acknowledge`, `connected`, or `heartbeat`
- `agent_id`: present when the change is tied to one agent
- `status`: connection lifecycle only

## Connection manager

The API keeps an in-memory `ConnectionManager`:

- `connect` accepts the socket and sends the initial `connection` event
- `disconnect` removes the client and closes the socket
- `broadcast` sends JSON to every subscriber and drops dead sockets
- a 20-second heartbeat loop broadcasts `connection` / `heartbeat`

Ingest paths publish through `RealtimeHub`, which schedules broadcasts on the
application event loop so synchronous FastAPI routes stay unchanged.

## Dashboard client

`useDashboardSocket` opens one connection per authenticated layout:

- auto-connect when a JWT is present
- reconnect with exponential backoff (1s, doubling to 30s)
- client heartbeat pings every 20 seconds
- duplicate event IDs are ignored
- Overview, Agents, Agent Detail, and Alerts refetch immediately on matching events
- navbar shows 🟢 Connected, 🟡 Connecting, or 🔴 Disconnected
- on disconnect, existing data stays on screen, a banner is shown, and 30-second polling resumes until the socket reconnects
