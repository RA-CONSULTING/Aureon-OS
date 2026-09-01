# Aureon operational script status

The repository contains historical, diagnostic, simulation, ingest, trading,
and launcher scripts. Their presence is not a production authorization.

All canonical shell start routes, Windows launcher wrappers, cloud/deployment
routes, desktop packagers, and named live runners are currently terminal
`HOLD` surfaces. They either enter the fixed isolated protected bootstrap or
emit a non-mutating machine-readable HOLD receipt. They do not import the
target, inspect credentials, start a child or listener, write state, access the
network, or execute an order.

Unregistered source elsewhere in the checkout remains research or historical
input and is outside the executable release. It must not be invoked directly.
The whole-repository protection census remains authoritative: a local file or
test pass cannot override unresolved source blockers, missing native
containment, or the missing external HNC ledger-head anchor.

Current release decision: `HOLD`.
