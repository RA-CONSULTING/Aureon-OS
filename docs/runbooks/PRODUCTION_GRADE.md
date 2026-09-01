# Production-grade program: current HOLD boundary

The repository contains product, operator, SaaS, research, and deployment
implementations plus offline tests. It is not currently certified as a
production operating system.

The checked-in deployment images are minimal terminal preflights: they do not
install application dependencies, copy target source, start Waitress/nginx,
expose ports, or claim `/healthz`. Compose, Supervisor, systemd, package, and
installer routes likewise have retries disabled and start no Aureon target.

Useful implementation checks remain:

```bash
ruff check aureon/operator/ aureon/saas/
mypy aureon/operator/ aureon/saas/
AUREON_LLM_OFFLINE=1 pytest tests/test_operator_*.py tests/test_saas_*.py -q
python -I -S -B scripts/bootstrap/protected_bootstrap_v05.py --target-id operator-wsgi
```

The last command must return a target-specific non-zero HOLD. Lint, type, and
test passes are quality evidence only; they do not authorize a runtime release.
Production status requires native containment, measured release provenance,
external HNC head anchoring, complete census closure, and provider read-back.
