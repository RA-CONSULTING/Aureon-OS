# Aureon release preflight — terminal HOLD

This repository is not approved for production deployment or live trading.
Historical compatibility checks, simulations, local tests, symbolic shield
claims, and source-level gates are not production protection evidence.

## Required evidence before this HOLD may be reviewed

- A native outer process boundary that prevents unmeasured runtime execution.
- A complete source-boundary census with zero unresolved protection blockers.
- Durable HNC denial and admission evidence with an externally attested,
  monotonic ledger head.
- Provider-side deployment receipts and authenticated live read-back from an
  explicitly authorized deployment.
- Credential custody, network exposure, rollback, incident response, and
  recovery evidence reviewed by the system owner.
- Exchange-specific paper or test execution evidence before any separate live
  trading authorization is considered.

## Current preflight decision

`HOLD`

Do not provision a host, copy credentials, enable services, expose listeners,
or execute trades from this checkout. The legacy deployment and setup scripts
now terminate at the fixed isolated bootstrap or emit a machine-readable HOLD
receipt. A test pass does not override this release decision.
