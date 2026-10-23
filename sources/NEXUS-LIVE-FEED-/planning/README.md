# Wheel Planning Utilities

Python utilities for modelling and simulating the 21-node "Wheel" roadmap.

## Files

- `plan.py` – canonical node definitions and dependency graph data.
- `ops.py` – graph analytics: critical path, dependency pressure, phase burndown.
- `viz.py` – Matplotlib helpers for readiness and dependency visuals.
- `sim.py` – Monte Carlo readiness simulation helpers.
- `requirements.txt` – Python dependencies for the utilities.

## Quickstart

```bash
pip install -r planning/requirements.txt
python -m planning.viz  # prints health summary and shows plots
python -m planning.sim  # runs a default simulation and prints stats
```

Each module can also be imported to integrate the plan with other tooling.
