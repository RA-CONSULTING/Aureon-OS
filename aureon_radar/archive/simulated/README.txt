SIMULATED DATA ARCHIVE — NOT REAL PERFORMANCE
==============================================

sniper_million_model.json
-------------------------
This file is SIMULATED reference data produced by the synthetic training
simulator bots/sniper_million_trainer.py (random.gauss synthetic prices,
"exit only on confirmed profit" rule). Its headline stats
(~209,000 trades, 0 losses, 100% win rate) are artifacts of the
simulation's no-loss exit rule and synthetic price generation. They are
NOT live trading performance and must never be ingested as truth by any
live trading or research logic.

Live decision code must not load this file as performance truth.
It may be consulted only as clearly-labeled simulated reference data.

Archived: 2026-09-06 (moved out of aureon_radar/ root so live processes
can no longer pick it up from the working directory).
