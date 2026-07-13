# System Landscape Overview

This workspace now hosts multiple concurrent subsystems that together compose the extended AUREON environment. The sections below map each codebase, its purpose, and its integration state.

## 1. Core AUREON Web Platform (`src/`)
- **Type:** Vite + React + TypeScript application.
- **Purpose:** Primary operator console for the AUREON Quantum Trading System (AQTS).
- **Key Modules:**
  - `src/core/masterEquation.ts`: Master Equation orchestration with Earth and Nexus influence blending.
  - `src/core/earthAureonBridge.ts`: Earth electromagnetic field ingestion.
  - `src/core/nexusLiveFeedBridge.ts`: Harmonic Nexus Stargate feed normalization.
  - `src/components/` + `src/pages/`: UI panels (coherence dashboards, scheduling, analytics, etc.).
  - `src/lib/`: Domain libraries (Schumann mappings, harmonic engines, utilities).
- **Supporting Scripts:** `scripts/testEarthIntegration.ts`, `scripts/testNexusIntegration.ts` executed via `npm run test:earth` / `npm run test:nexus`.

## 2. Earth Field Ingestion Stack
- **Location:** `src/lib/earth-streams.ts`, `src/lib/schumann-emotional-mapping.ts`, `docs/EARTH_AUREON_INTEGRATION.md`, `docs/EARTH_QUICKSTART.md`.
- **Purpose:** Converts Schumann resonance, geomagnetic data, and solar wind telemetry into coherence modifiers for the Master Equation.
- **Runtime Hooks:** `MasterEquation.enableEarthSync`, `MasterEquation.setEarthStreams`.
- **Edge Scripts:** `server/earth-live-data-server.js` streams live CSV data for local dev.

## 3. Nexus Stargate Integration
- **Location:** `src/core/nexusLiveFeedBridge.ts`, `docs/NEXUS_LIVE_FEED_INTEGRATION.md`, `scripts/testNexusIntegration.ts`.
- **External Bundle:** `NEXUS-LIVE-FEED--main/` contains the original Node/SSE service, Python tooling, and Next.js hosting templates.
- **Purpose:** Normalizes harmonic resonance, quantum coherence, rainbow spectrum, and consciousness signals; `MasterEquation` applies the composite boost to coherence.

## 4. Legacy AQTS Bundle (`Aueron-Trading-Quantum-Quackers-War-Ready-Version--alert-autofix-gl1/`)
- **Contents:** Full historical AQTS distribution (React UI, scripts, Unity assets, data exports) recovered from the `earth-live-data-1 (10).zip` archive.
- **Status:** Serves as reference material; not currently wired into the live Vite project but sources inform component and library ports.
- **Notable Assets:** Unity C# scripts under `Assets/Scripts/Nexus/`, comprehensive documentation (`docs/`, `README_*.md`), and prior Node/TypeScript services under `core/` and `scripts/`.

## 5. Rainbow & Validation Research Bundles
- **`RAINBOW-main/`**: Archive containing Rainbow project documentation and additional earth data packages.
- **`VERIFICATION AND VALIDATION/`**: Evidence packages (PDF/DOCX) outlining harmonic nexus validation methodology.
- **Purpose:** Reference artifacts for compliance, research traceability, and legacy protocol documentation.

## 6. Edge Infrastructure & Services
- **Supabase Functions:** Located under `supabase/functions/` (edge functions and migrations).
- **Server Utilities:** `server/earth-live-data-server.js`, `aura_validator.py`, `validator_auris.py`, `validation_bridge.py` provide data streaming and audit tooling.
- **Cloud Manifests:** `manifest.json`, `manifest_modules.json`, `netlify/functions/` supply deployment metadata.

## 7. Documentation & Knowledge Base
- **Primary Spec:** `README.md` (AQTS full specification).
- **Integration Guides:** `docs/EARTH_AUREON_INTEGRATION.md`, `docs/NEXUS_LIVE_FEED_INTEGRATION.md`, other domain knowledge inside `docs/`.
- **Additional READMEs:** `README_AURIS_VALIDATOR.md`, `README_HARMONIC_NEXUS.md`, `README_TEST_VALIDATION.md`, `README_VALIDATION.md` supply subsystem context.

## 8. Remaining Archives / Data Packs
- Archives kept for provenance: `earth-live-data-1.zip`, `earth-live-data-3 (7).zip`, `earth-live-data-3 (8).zip`, `RAINBOW-main.zip`, `NEXUS-LIVE-FEED--main.zip`, `Aueron-Trading-Quantum-Quackers-War-Ready-Version--alert-autofix-gl1.zip`, `VERIFICATION AND VALIDATION-20250916T213737Z-1-001.zip`.
- Consider moving these into an `archives/` folder (or removing once version-controlled) to declutter the workspace.

## Suggested Next Steps
1. **Consolidate Legacy Sources:** Curate what portions of the legacy AQTS bundle should be merged into the modern `src/` codebase vs. archived.
2. **UI Surfacing:** Add a dedicated dashboard tile that visualizes `LambdaState.nexusInfluence` alongside Earth metrics for operators.
3. **Archive Hygiene:** Relocate or remove redundant `.zip` files now that contents are extracted to avoid accidental edits.
4. **Dependency Audit:** Run `npm audit fix` (per npm install output) to address flagged vulnerabilities.
5. **Testing Matrix:** Extend script coverage to ensure Earth and Nexus boosts are exercised in integration tests (e.g., Jest/Vitest harness).
