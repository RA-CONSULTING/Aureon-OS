# Runtime ownership and scaling boundary: terminal HOLD

No economic, operator, frontend, metrics, or autonomous runtime is deployed by
the current manifests. DigitalOcean specifications contain zero components.
Compose services are non-networked terminal preflights, Supervisor/systemd
programs run only fixed HOLD targets with retries disabled, and the Procfile has
one release-phase HOLD command.

Therefore the current control is stronger than a singleton topology: there is
no authorized writer process to scale. Do not add replicas, workers,
auto-restart, or autoscaling as a substitute for release authority.

Before any future writer count can exceed one, evidence must prove **leader election with fencing**, **globally unique idempotency** at the provider boundary,
**shared provider-aware rate limits** and nonce coordination, partition/failover
tests, and provider-side topology read-back. **Local static validation is not provider read-back.**
