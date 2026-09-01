# DigitalOcean deployment protection status

Aureon DigitalOcean deployment is currently **HOLD**.

The repository's Docker, Compose, shell, Supervisor, and systemd entrypoints run only the
fixed, standard-library protection bootstrap. They intentionally start no Aureon module,
network listener, autonomous worker, or trading process. The current receipt is a fail-closed
preflight result, not evidence that the full operating system is protected or production-ready.

## Safe preflight

From an authenticated, owner-controlled checkout:

```bash
python3 -I -S -B scripts/bootstrap/protected_bootstrap_v05.py --target-id cloud-supervisor
docker compose -f docker-compose.autonomous.yml config --quiet
```

The bootstrap must return a target-specific JSON receipt with `decision: HOLD`,
`target_registered: true`, and `process_start_authorized: false`. Exit status 1 is the
expected terminal HOLD. Exit status 2 is an invalid bootstrap/request failure and is not an
acceptable protection receipt.

Do not add exchange credentials, create a droplet, build/push an image, enable a service,
publish a port, or treat an HTTP/process probe as protection evidence while this hold remains.
A future release requires a reviewed native outer boundary, durable authenticated HNC denial
evidence, full source-scope census closure, and provider-side deployment read-back.
