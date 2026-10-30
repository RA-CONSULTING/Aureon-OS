# Aureon OS — capability demonstration

The live capability demonstration is on HOLD. The current command does not boot the operator app, does not exercise routes, providers, suites, or Tier-A checks, and does not establish that any capability class passed. An older write-up of this page quoted a pass. That write-up is not a current measured result, and those figures are not repeated here.

What the command is designed to do, once a production release exists, is boot the operator app in-process, exercise the capability surface (reasoning, operator, the MCP boundary, connection probes, the SaaS telemetry surface, and frontend-to-backend parity), then roll up the existing self-tests. That path is not what runs today.

The held preflight is read-only in this sense: it does not arm a flag, record an approval, move money, or place a trade.

## Status

**Status: HOLD.** No capability class was exercised. No suite result and no Tier-A result are quoted.

## Reproduce the preflight

```bash
AUREON_LLM_OFFLINE=1 AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS=1 \
  python -m aureon.saas.capability_demo --report docs/reports/CAPABILITY_DEMO.md
```

This writes the held preflight. It is not a measured capability result.
