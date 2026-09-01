# Aureon Operator deployment status: terminal HOLD

The Operator and Cognition implementations remain available for source review
and offline tests. No supported launcher currently starts their Python module,
WSGI process, mesh registration, HTTP listener, mobile page, model-provider
connection, or tool route.

Verify the fixed targets only:

```bash
python -I -S -B scripts/bootstrap/protected_bootstrap_v05.py --target-id operator
python -I -S -B scripts/bootstrap/protected_bootstrap_v05.py --target-id operator-wsgi
```

Both commands must exit non-zero with a registered, target-specific receipt
containing `decision: HOLD` and `process_start_authorized: false`. Do not inject
model keys, bearer tokens, proxy configuration, or hosting credentials for this
check. No HTTP response, tunnel, phone route, SSE stream, or health endpoint is
expected.

A future release requires native process containment, exact target-source
measurement, a shared production limiter where applicable, externally anchored
HNC evidence, an authenticated deployment receipt, and provider-side read-back.
None is claimed by the current local HOLD.
