# Self-hosted Aureon OS

Hosting is the end user's choice. These two commands start the same stack on the machine in front of you. Live trading stays off. `may_act` stays false. No provider credential is required.

The loopback bearer token is `local-selfhost-token`. It is not a provider key. The local Postgres password `local_only` is a throwaway for the compose database.

## Without Docker

Requires Python 3.12, Postgres, Redis, and nginx on the PATH.

```bash
make up
```

That runs `scripts/selfhost_up.py`. It applies the row-level-security migration to a local database named `aureon`, starts Redis if it is not already answering, and supervises:

- two API replicas on `127.0.0.1:8765` and `127.0.0.1:8766`
- the frontend HTTP profile on `127.0.0.1:5173`
- the local error sink on `127.0.0.1:8088`
- nginx on `http://127.0.0.1:8080`, load-balancing the two APIs and rate-limiting `/api/`

Stop it with `make down`.

## With Docker

```bash
make compose
```

That builds `deploy/selfhost/docker-compose.yml` and waits until every service is healthy. The edge is published on `http://127.0.0.1:8080`. Postgres and Redis stay on the compose network. Each service has a health check and `restart: unless-stopped`.

## Smoke

```bash
make smoke
```

`scripts/selfhost_smoke.py` checks the console, the frontend profile, auth, Redis, both API replicas, the nginx 429, the error sink, Postgres RLS (`anon` denied, `service_role` allowed), and the eleven flight-recorder faculties. A faculty that cannot be fed from a real public or read-only source is `blocked` with a reason. Nothing synthetic is written in its place.

Set `AUREON_SELFHOST_MODE=local` when the stack was started with `make up`. The default mode is `compose`.
