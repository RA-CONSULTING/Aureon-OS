# Aureon and Flameborn integration status

The integration implementation remains available for source review, but every
supported start, runtime, desktop, terminal, sandbox, Cloudflare, and deployment
route is on terminal **HOLD**.

Use either platform wrapper only to verify the fixed boundary:

```bash
bash scripts/start_aureon_with_flameborn.sh
```

```powershell
.\scripts\start_aureon_with_flameborn.ps1
```

The expected result is a non-zero exit and a registered `flameborn-runtime`
receipt with `process_start_authorized: false`. Neither command loads `.env`,
creates directories or logs, starts Python or Node target code, opens a network
listener, mounts a Docker socket, enables a host terminal, performs Cloudflare
deployment, or authorizes economic action.

Releasing this integration requires a reviewed Node/native outer boundary,
target-source measurement, least-privilege sandbox isolation, durable HNC
evidence with external head anchoring, and an authenticated provider read-back.
