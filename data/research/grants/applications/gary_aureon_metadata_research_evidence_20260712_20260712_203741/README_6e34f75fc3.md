# Kimi Agent Aureon Research Bundle (2026-04-08)

Source file (local):

- `C:\Users\ayman kattan\Downloads\Kimi_Agent_Aureon.zip`

Extracted into this folder on **2026-04-08** so it can be versioned and shared across terminals.

## Contents

This bundle is primarily **research artifacts** (reports, JSON analyses, images) plus an `ionospheric_data/` folder containing scripts and sample data.

## Intentionally Not Committed

The upstream ZIP also contained an embedded snapshot of this repository:

- `aureon-trading.zip`
- `aureon-trading-main/` (extracted copy)

The raw archive (`aureon-trading.zip`) is **not committed** because it includes `.env*` (live credentials) and is not safe to publish.

## Embedded Snapshot (Sanitized, Committed)

To preserve the snapshot for multi-terminal use without leaking secrets, a **sanitized extraction** is committed here:

- `imports/Kimi_Agent_Aureon_20260408/aureon-trading-main-snapshot/`

Sanitization performed:

- Removed `aureon-trading-main-snapshot/.env1.txt` (contained live credentials).
