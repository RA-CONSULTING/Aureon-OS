# Nexus Live Feed Integration

The Harmonic Nexus Stargate feed is now wired directly into the AUREON Master Equation. The integration mirrors the Earth sync flow while maintaining its own configurable weighting profile.

## Runtime Behaviour
- `nexusLiveFeedBridge` polls the Nexus feed every ~2 seconds (simulated locally) and normalizes the quantum coherence, harmonic resonance, Schumann proxy, rainbow spectrum, and consciousness metrics.
- The resulting `NexusInfluence` exposes a `compositeBoost` range of `-0.10 .. +0.20`. This boost is added to the coherence output inside `MasterEquation.step`, after Earth influence has been applied.
- Status values (`optimal`, `supportive`, `neutral`, `degraded`) can be surfaced in the UI via the bridge listener API when needed.

## Master Equation Hooks
```
import { nexusLiveFeedBridge } from './nexusLiveFeedBridge';

// Enable / tune at runtime
eq.enableNexusSync(true, { pollingIntervalMs: 1500 });

// LambdaState now contains `nexusInfluence`
const { nexusInfluence } = await eq.step(snapshot);
```

`MasterEquation.enableNexusSync` toggles the bridge or accepts partial `NexusBridgeConfig` overrides (e.g., alternative endpoint, weight adjustments, or a tighter polling cadence).

## Future Extensions
- Replace the simulated generator in `nexusLiveFeedBridge` with an SSE/WebSocket client for the real feed located under `NEXUS-LIVE-FEED--main/src/server.js`.
- Surface the `NexusInfluence.status` in a UI component alongside existing Earth telemetry (`EarthFieldMonitor`).
- Blend the nexus boost into strategy selection heuristics or alerting thresholds.
