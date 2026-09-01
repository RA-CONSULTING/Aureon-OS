# Go-live status: terminal HOLD

There is no supported live Aureon instance in the current release. Official
Docker, Compose, Supervisor, systemd, shell, package, desktop, and cloud routes
stop before target import or process start. The cloud manifests define zero
components and no secret bindings.

Do not expose listeners, inject credentials, enable trading, create tunnels, or
use direct module execution as a substitute for the missing release boundary.
Historical listener and environment guidance is withdrawn.

Go-live requires all of the following, none inferred from a local test pass:

- native process containment with a zero-network default;
- exact target-source measurement and immutable release provenance;
- durable HNC evidence with an external monotonic head anchor;
- complete source-boundary census closure;
- authenticated deployment receipt and provider-side read-back.

Until those receipts exist, the correct outcome is `HOLD`, not a partially
configured listener.
