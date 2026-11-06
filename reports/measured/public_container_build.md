# Public container build

Local build of the root guarded preflight. This is not a claim that a live
Aureon instance exists, and it is not a claim that the system is alive.

Verdict: **measured_hold**.
Release boundary: **HOLD**. Orange badge: unchanged.
Go-live: **HOLD**.
Production ready: false. Validation claim: none.
Receipt 5 (authenticated deployment receipt and provider-side read-back): **HOLD**.
This file is not receipt 5. Provider read-back: false. Registry publish: false.

## Image

Tag `aureon-protection-preflight:local` (measured). Id `sha256:027bd66cd686a79aef520dcf333e5825a8650db2edef951006e172a3d0559dd3`.
Size 43286941 bytes. Created `2026-11-05T20:43:56.829569504Z`.
User `aureon`. Exposed ports: None.
Repo digests: ['aureon-protection-preflight@sha256:027bd66cd686a79aef520dcf333e5825a8650db2edef951006e172a3d0559dd3']. Login attempted: false. Push attempted: false.

## Run

Command was `docker run` with network none, a read-only root, and every capability dropped.
Exit code 1 (measured). Network mode `none`.
Port bindings {}. Listeners opened: false.
Bootstrap sha256 matches the checkout: True.

## Preflight

decision `HOLD`. target_imported False.
network_accessed False. production_ready False.
target_id `docker-runtime`.

## Still HOLD

- Receipt 2: exact target-source measurement and immutable release provenance — HOLD
- Receipt 3: durable HNC evidence with an external monotonic head anchor — HOLD
- Receipt 4: complete source-boundary census closure — HOLD
- Receipt 5: authenticated deployment receipt and provider-side read-back — HOLD

A public GHCR push was not done. It needs Gary's own yes and a token. Neither was used.
Claims recorded here: cloud_go_live=False, listeners_opened=False, production_ready=False, receipt_5=False, registry_publish=False, system_alive=False, validated=False.

Git HEAD at measurement: `08f04936088689e29b7995d89530b21b425c35f9`.
The UTC stamp is this machine's clock. It is not receipt 3.
