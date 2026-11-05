# Public container distribution

Status: local build and CI build. Not published. Go-live: **HOLD**.

The root `Dockerfile` is the guarded non-live default. Its entrypoint is the
isolated bootstrap with target id `docker-runtime`. That process returns
`HOLD` and does not import the target. Official installers, including
`scripts/linux/install-linux.sh`, still stop at that same HOLD before target
import. This document does not switch them on.

The image is not a supported cloud go-live. It is not production ready. It is
not a validation. The orange release-boundary badge stays HOLD.

`README.md` is unchanged. Receipt 1 pins its bytes in
`reports/measured/native_process_containment.json`. The badge in that file
stays the orange HOLD badge.

The committed build receipt records the image id from the build that wrote
it. A later build can produce a different id. That id is a local image id,
not a registry digest.

## What the image is

The image environment sets:

- `AUREON_AUTONOMY_MODE=guarded`
- `AUREON_LIVE_TRADING=0`
- `AUREON_LLM_OFFLINE=1`
- `AUREON_DISABLE_LLM_HTTP=1`
- `AUREON_DISABLE_REAL_ORDERS=1`
- `AUREON_DISABLE_EXCHANGE_MUTATIONS=1`

The process user is `aureon`. The Dockerfile does not declare `EXPOSE`.
`docker-compose.yml` does not set an environment block, an env file, a
secret, a published port, or a volume. The service network mode is `none`,
the root filesystem is read-only, and capabilities are dropped. Compose does
not inject credentials.

`deploy/plug/` is a separate optional checkout stack. It is not this
distribution path, and this path does not publish its listeners.

## Local build

From the repository root, with Docker Compose v2:

```bash
docker compose build
docker compose run --rm protection-preflight
```

Expect exit status 1 and one JSON object whose `decision` is `HOLD`. Exit 1
is the terminal HOLD. It is not a successful go-live. `target_imported` is
false. `production_ready` is false.

To record a measured receipt of that build:

```bash
python3 scripts/validation/measure_public_container.py
```

The command builds the image, runs it with no network and no published port,
and writes `reports/measured/public_container_build.json` and
`reports/measured/public_container_build.md` only after that build and run.
If the image does not build, the command writes nothing. A hand-written
stand-in is not a receipt.

## CI

`.github/workflows/public-container.yml` checks out the tree, builds the same
image, and runs the same no-network preflight (`--check`, so CI does not
rewrite the receipt). The workflow permissions are `contents: read`. It does
not log in to a registry and it does not publish an image.

## Registry

This change does not push to GHCR or to any other registry. A public GHCR
publish needs Gary's own yes and a token. Both are absent here. A local image
id is not a published digest and is not provider-side read-back.

That is not receipt 5. Receipt 5 remains the authenticated deployment receipt
and provider-side read-back, and it stays HOLD.

## What this is not

- not a supported cloud go-live
- not production ready
- not a validation of Aureon
- not a listener, and not a bypass of the zero-network containment default
- not a claim that the system is alive
- not a clear of the orange release-boundary badge
