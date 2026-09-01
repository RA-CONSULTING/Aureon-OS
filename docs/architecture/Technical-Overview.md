# Technical overview

Aureon is a large research and prototyping repository containing exchange,
strategy, orchestration, UI, deployment, HNC, and validation source. Source
presence is not the same as an approved or protected production runtime.

## Current runtime boundary

Supported launch and deployment surfaces are routed to the fixed isolated
protected bootstrap. That boundary returns `HOLD` and does not import the target,
start a child, write a file, invoke Git, or access the network. Legacy launchers
that cannot safely enter that boundary have been replaced with non-mutating HOLD
receipts.

## Unresolved production requirements

- Complete source-boundary coverage with no unresolved census blockers.
- Native process containment outside the Python interpreter.
- Durable HNC evidence whose monotonic ledger head is externally attested.
- Credential custody and provider-specific authorization/read-back.
- Recovery, rollback, incident-response, and operational qualification evidence.

Until those requirements are satisfied and independently reviewed, no exchange,
listener, autonomous worker, cloud deployment, or live execution path is
production-ready. Configuration flags, simulations, and local tests cannot
override this terminal release `HOLD`.
