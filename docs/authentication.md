# Authentication

HomeLab Monitor uses separate credentials for agents and dashboard users.

Agents continue to authenticate with a one-time hashed bearer token issued at
registration. Dashboard users authenticate with a username, password, and a
short-lived JWT access token.

## Roles

| Role | Purpose |
| --- | --- |
| `admin` | Full dashboard operator. Seeded by default in development. |
| `operator` | Day-to-day monitoring access. |
| `viewer` | Read-only dashboard access. |

Sprint 5.1 grants all active roles access to the protected read APIs. Finer
role checks can be added later without changing the login contract.

## Login flow

1. Submit `POST /api/v1/auth/login` with a JSON username and password.
2. The API verifies the bcrypt password hash and returns a JWT.
3. The dashboard stores the token in `localStorage`.
4. Subsequent dashboard API calls send `Authorization: Bearer <token>`.
5. `GET /api/v1/auth/me` returns the current user for the navbar.
6. Logout deletes the stored token and returns to `/login`.

Default seeded administrator (change after first login in any shared environment):

- username: `admin`
- password: `admin123`

## JWT

Tokens are signed with HS256 using `HOMELAB_JWT_SECRET`. Expiry is controlled by
`HOMELAB_JWT_EXPIRE_MINUTES`. Expired or malformed tokens return HTTP 401.
Inactive users return HTTP 403.

## Protected APIs

These routes require a dashboard JWT:

- `GET /api/v1/dashboard/*`
- `GET /api/v1/agents`
- `GET /api/v1/agents/{agent_id}`
- `GET /api/v1/agents/{agent_id}/latest-report`
- `GET /api/v1/agents/{agent_id}/reports`
- `GET /api/v1/alerts/*`
- `GET /api/v1/auth/me`

These routes remain available without a dashboard JWT:

- `GET /health`
- `POST /api/v1/auth/login`
- `POST /api/v1/agents/register` (registration key)
- `POST /api/v1/agent/check-ins` (agent token)
- `POST /api/v1/agent/reports` (agent token)

## Security notes

- Passwords are hashed with bcrypt through passlib. Plain passwords are never stored.
- Do not commit `HOMELAB_JWT_SECRET` or production passwords.
- Replace the seeded `admin123` password before exposing the dashboard beyond a
  trusted HomeLab network.
- The dashboard JWT is stored in `localStorage` in v1. Treat the browser as a
  trusted operator workstation.
