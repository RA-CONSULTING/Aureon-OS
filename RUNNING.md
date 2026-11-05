# Running Aureon — terminal HOLD

There is currently no approved production start command. The fixed isolated
bootstrap measures its own boundary, emits a causal `HOLD` receipt, and does
not import or call the selected target, start a process, write a file, invoke
Git, access the network, or execute an order.

Historical direct runner commands are withdrawn. Test and benchmark commands
may check source contracts offline, but their success does not authorize a
runtime and is not a validation of the release. Production operation requires
zero unresolved source-boundary blockers, native outer containment, externally
anchored HNC evidence, signed packaging, credential custody, and authenticated
provider read-back.

A measured native zero-network cold boot is go-live receipt 1. It does not
approve a production start. Receipts 2–5 remain HOLD. The orange
release-boundary badge stays HOLD.

The live routes are active, and they are not on hold. With exchange keys in
`.env`, the launcher boots into live trading. There is no verified live track
record. The public default is full mode (`AUREON_AUTONOMY_MODE` unset). That
boot is not a go-live clearance and not production-ready.

Canonical launcher paths remain on HOLD and are not an approved start:
`scripts/launchers/AUREON_PRODUCTION_LIVE.cmd`,
`scripts/launchers/AUREON_WAKE_UP_FULL_AUTONOMOUS.ps1`,
`scripts/launchers/AUREON_DATA_OCEAN.cmd`,
`scripts/launchers/AUREON_DATA_OCEAN.ps1`.
