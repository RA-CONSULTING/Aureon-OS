# Aureon quick start — terminal HOLD

There is no approved runtime quick start in this checkout. Canonical launch,
cloud, packaging, desktop, operational, trading, UI, and data-ingest entrypoints
are routed to the fixed isolated bootstrap or a non-mutating HOLD receipt.

The one supported evaluation route is the guarded `./install.sh --smoke` in
[`EVALUATE.md`](EVALUATE.md). It binds loopback-only listeners on
`127.0.0.1` in guarded mode with live trading off, and it is not a runtime
quick start. Apart from that route, do not install dependencies for
production, copy credentials, start a listener, invoke a direct subsystem
module, activate an exchange client, or run a provider deployment from this
repository. Offline tests and benchmarks may check
source contracts, but they do not authorize operation and are not a validation
of the release.

The release stays on `HOLD`. Receipt 1, a measured native zero-network cold
boot, does not clear it. Receipts 2–5 remain open: exact target-source
provenance, an external monotonic HNC head anchor
(`external_head_anchor_attested` stays false), source-boundary census closure,
and an authenticated provider read-back. Signed packaging is not a clearance
in this checkout. The orange release-boundary badge stays HOLD.

The live routes are active, and they are not on hold. With exchange keys in
`.env`, the launcher boots into live trading. There is no verified live track
record. The public default is full mode (`AUREON_AUTONOMY_MODE` unset). That
boot is not a go-live clearance and not production-ready.

Canonical launcher paths, still unapproved and not a start command:
`scripts/launchers/AUREON_PRODUCTION_LIVE.cmd`,
`scripts/launchers/AUREON_WAKE_UP_FULL_AUTONOMOUS.ps1`,
`scripts/launchers/AUREON_DATA_OCEAN.cmd`.
