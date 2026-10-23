#!/usr/bin/env python3
"""
🌍⚡ EARTH EPAS SHIELD DASHBOARD — Live Planetary Ionosphere Visualiser ⚡🌍
═══════════════════════════════════════════════════════════════════════════════

Real-time visualisation of the Earth-scale EPAS second ionosphere simulation.
Uses live VSOP87 planetary positions → cosmic field → 3 shield layers → 6 phases.

Usage:
    python aureon_earth_shield_dashboard.py
    Then open: http://localhost:8785

Port: 8785 (Earth Shield)
"""

import sys
import os

# Windows UTF-8 fix
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import io
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                                          errors='replace', line_buffering=True)
        if hasattr(sys.stderr, 'buffer'):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8',
                                          errors='replace', line_buffering=True)
    except Exception:
        pass

import json
from datetime import datetime

try:
    from aiohttp import web
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    print("aiohttp not available — pip install aiohttp")
    sys.exit(1)

# Import the simulation engine
sys.path.insert(0, os.path.dirname(__file__))
from aureon.decoders.emerald_spec import (
    simulate_earth_epas,
    EarthEPASSimulation,
    _PHASE_LABELS,
    _SIGMA_COHERENCE_TARGET,
    PHI,
    SCHUMANN_FUNDAMENTAL,
    EARTH_RADIUS_M,
    F_REGION_ALT_M,
    F_REGION_ELECTRON_DENSITY,
    F_REGION_SHELL_VOLUME_M3,
    F_REGION_SHELL_AREA_M2,
    VOLUMETRIC_CONCENTRATION_FACTOR,
)

DASHBOARD_PORT = 8785

# ═══════════════════════════════════════════════════════════════════════════════
# INLINE HTML DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>EARTH EPAS SHIELD — Live Planetary Dashboard</title>
<style>
:root {
  --bg-deep: #030712;
  --bg-panel: #0f172a;
  --bg-card: #1e293b;
  --border: #334155;
  --glow-green: #22c55e;
  --glow-cyan: #06b6d4;
  --glow-amber: #f59e0b;
  --glow-red: #ef4444;
  --glow-purple: #a855f7;
  --glow-blue: #3b82f6;
  --text: #e2e8f0;
  --text-dim: #94a3b8;
  --text-bright: #f8fafc;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace;
  background: var(--bg-deep);
  color: var(--text);
  min-height: 100vh;
  overflow-x: hidden;
}

/* ── Header ───────────────────────────── */
.header {
  text-align: center;
  padding: 24px 16px 12px;
  border-bottom: 1px solid var(--border);
  background: linear-gradient(180deg, #0c1524 0%, var(--bg-deep) 100%);
}
.header h1 {
  font-size: 1.6em;
  letter-spacing: 0.15em;
  color: var(--glow-cyan);
  text-shadow: 0 0 30px rgba(6,182,212,0.4);
}
.header .sub {
  font-size: 0.78em;
  color: var(--text-dim);
  margin-top: 4px;
}
.shield-status-banner {
  display: inline-block;
  margin-top: 10px;
  padding: 6px 28px;
  border-radius: 6px;
  font-size: 1.3em;
  font-weight: 700;
  letter-spacing: 0.1em;
  animation: pulse-glow 2s ease-in-out infinite alternate;
}
@keyframes pulse-glow {
  from { filter: brightness(1); }
  to   { filter: brightness(1.25); }
}
.shield-up    { background: rgba(34,197,94,0.15); color: var(--glow-green); border: 2px solid var(--glow-green); text-shadow: 0 0 20px var(--glow-green); }
.shield-stress{ background: rgba(245,158,11,0.15); color: var(--glow-amber); border: 2px solid var(--glow-amber); text-shadow: 0 0 20px var(--glow-amber); }
.shield-fail  { background: rgba(239,68,68,0.15); color: var(--glow-red); border: 2px solid var(--glow-red); text-shadow: 0 0 20px var(--glow-red); animation: pulse-glow 0.5s ease-in-out infinite alternate; }

/* ── Grid layout ──────────────────────── */
.grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; padding: 16px; max-width: 1600px; margin: 0 auto; }
.panel {
  background: var(--bg-panel);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 14px;
  position: relative;
  overflow: hidden;
}
.panel::before {
  content: '';
  position: absolute; top: 0; left: 0; right: 0; height: 2px;
}
.panel-green::before  { background: linear-gradient(90deg, transparent, var(--glow-green), transparent); }
.panel-cyan::before   { background: linear-gradient(90deg, transparent, var(--glow-cyan), transparent); }
.panel-amber::before  { background: linear-gradient(90deg, transparent, var(--glow-amber), transparent); }
.panel-red::before    { background: linear-gradient(90deg, transparent, var(--glow-red), transparent); }
.panel-purple::before { background: linear-gradient(90deg, transparent, var(--glow-purple), transparent); }
.panel-blue::before   { background: linear-gradient(90deg, transparent, var(--glow-blue), transparent); }

.panel h2 {
  font-size: 0.75em;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-dim);
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--border);
}
.span-2 { grid-column: span 2; }
.span-3 { grid-column: span 3; }

/* ── Solar system orbital ring ────────── */
.orbit-container {
  position: relative;
  width: 100%;
  max-width: 360px;
  aspect-ratio: 1;
  margin: 0 auto;
}
.orbit-ring {
  position: absolute;
  border-radius: 50%;
  border: 1px solid rgba(51,65,85,0.5);
  top: 50%; left: 50%;
  transform: translate(-50%, -50%);
}
.earth-core {
  position: absolute;
  top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  width: 28px; height: 28px;
  border-radius: 50%;
  background: radial-gradient(circle, #3b82f6, #1e40af);
  box-shadow: 0 0 20px rgba(59,130,246,0.6);
  z-index: 10;
}
.earth-label {
  position: absolute;
  top: 50%; left: 50%;
  transform: translate(-50%, 20px);
  font-size: 0.6em;
  color: var(--glow-blue);
  z-index: 11;
}
.planet-dot {
  position: absolute;
  width: 10px; height: 10px;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  z-index: 12;
  transition: all 0.8s ease;
}
.planet-label {
  position: absolute;
  font-size: 0.55em;
  color: var(--text-dim);
  transform: translate(-50%, 8px);
  white-space: nowrap;
  z-index: 13;
}

/* ── Aspect list ──────────────────────── */
.aspect-row {
  display: flex;
  justify-content: space-between;
  padding: 3px 0;
  font-size: 0.72em;
  border-bottom: 1px solid rgba(51,65,85,0.3);
}
.aspect-positive { color: var(--glow-green); }
.aspect-negative { color: var(--glow-red); }
.aspect-name { color: var(--text-dim); min-width: 80px; }
.aspect-score { font-weight: 600; min-width: 55px; text-align: right; }

/* ── Layer cards ──────────────────────── */
.layer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.layer-status {
  padding: 2px 10px;
  border-radius: 4px;
  font-size: 0.7em;
  font-weight: 700;
  letter-spacing: 0.08em;
}
.status-good    { background: rgba(34,197,94,0.2); color: var(--glow-green); }
.status-warn    { background: rgba(245,158,11,0.2); color: var(--glow-amber); }
.status-danger  { background: rgba(239,68,68,0.2); color: var(--glow-red); }
.metric-row {
  display: flex;
  justify-content: space-between;
  padding: 2px 0;
  font-size: 0.72em;
}
.metric-label { color: var(--text-dim); }
.metric-value { color: var(--text-bright); font-weight: 600; }

/* ── Phase bars ───────────────────────── */
.phase-row {
  display: flex;
  align-items: center;
  margin-bottom: 5px;
}
.phase-label {
  width: 110px;
  font-size: 0.7em;
  color: var(--text-dim);
}
.phase-bar-bg {
  flex: 1;
  height: 18px;
  background: var(--bg-card);
  border-radius: 3px;
  overflow: hidden;
  position: relative;
}
.phase-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.8s ease, background 0.8s ease;
}
.phase-score {
  width: 50px;
  text-align: right;
  font-size: 0.7em;
  font-weight: 600;
  margin-left: 8px;
}
.phase-status-tag {
  width: 90px;
  text-align: center;
  font-size: 0.6em;
  letter-spacing: 0.05em;
  margin-left: 6px;
}

/* ── Coherence gauge ──────────────────── */
.gauge-container {
  text-align: center;
  padding: 10px 0;
}
.gauge-ring {
  position: relative;
  width: 180px; height: 180px;
  margin: 0 auto;
}
.gauge-ring svg { width: 100%; height: 100%; transform: rotate(-90deg); }
.gauge-bg { fill: none; stroke: var(--bg-card); stroke-width: 12; }
.gauge-fill { fill: none; stroke-width: 12; stroke-linecap: round; transition: stroke-dashoffset 1s ease, stroke 0.5s ease; }
.gauge-center {
  position: absolute;
  top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
}
.gauge-value { font-size: 2em; font-weight: 700; }
.gauge-label { font-size: 0.65em; color: var(--text-dim); margin-top: 2px; }

/* ── Power ────────────────────────────── */
.power-value {
  font-size: 1.6em;
  font-weight: 700;
  color: var(--glow-purple);
  text-shadow: 0 0 15px rgba(168,85,247,0.4);
}
.power-unit { font-size: 0.55em; color: var(--text-dim); }

/* ── Footer ───────────────────────────── */
.footer {
  text-align: center;
  padding: 12px;
  font-size: 0.65em;
  color: var(--text-dim);
  border-top: 1px solid var(--border);
}
.refresh-indicator {
  display: inline-block;
  width: 8px; height: 8px;
  border-radius: 50%;
  background: var(--glow-green);
  margin-right: 6px;
  animation: blink 1s infinite;
}
@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

/* ── Responsive ───────────────────────── */
@media (max-width: 1100px) { .grid { grid-template-columns: 1fr 1fr; } .span-3 { grid-column: span 2; } }
@media (max-width: 700px) { .grid { grid-template-columns: 1fr; } .span-2, .span-3 { grid-column: span 1; } }

/* ── Relay world map ──────────────── */
.relay-map {
  position: relative;
  width: 100%;
  height: 320px;
  background: var(--bg-card);
  border-radius: 6px;
  border: 1px solid var(--border);
  overflow: hidden;
}
.relay-map svg { position: absolute; top:0; left:0; width:100%; height:100%; }
#relayDots {
  position: absolute; top:0; left:0; width:100%; height:100%; z-index:2;
}
.relay-dot {
  position: absolute;
  width: 12px; height: 12px;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  cursor: pointer;
  z-index: 3;
  transition: all 0.5s ease;
}
.relay-dot:hover { transform: translate(-50%, -50%) scale(1.6); z-index: 10; }
.relay-dot.active    { background: var(--glow-green); box-shadow: 0 0 12px var(--glow-green); }
.relay-dot.resonating { background: var(--glow-cyan); box-shadow: 0 0 12px var(--glow-cyan); }
.relay-dot.dormant   { background: var(--glow-amber); box-shadow: 0 0 8px var(--glow-amber); opacity: 0.7; }
.relay-dot.offline   { background: var(--glow-red); box-shadow: 0 0 6px var(--glow-red); opacity: 0.4; }

/* ── Relay table ──────────────────── */
.relay-table { width: 100%; border-collapse: collapse; font-size: 0.7em; }
.relay-table th {
  text-align: left; color: var(--text-dim); padding: 4px 8px;
  border-bottom: 1px solid var(--border); font-weight: 600; letter-spacing: 0.05em;
}
.relay-table td { padding: 3px 8px; border-bottom: 1px solid rgba(51,65,85,0.3); }
.relay-civ {
  font-size: 0.85em; padding: 1px 6px; border-radius: 3px; letter-spacing: 0.03em;
}
</style>
</head>
<body>

<div class="header">
  <h1>EARTH EPAS SECOND IONOSPHERE</h1>
  <div class="sub">Live Planetary Shield Simulation &middot; VSOP87 Engine &middot; F-Region Scale</div>
  <div id="shieldBanner" class="shield-status-banner shield-stress">LOADING...</div>
</div>

<div class="grid">

  <!-- ─── Solar System Orbital ────────────── -->
  <div class="panel panel-blue">
    <h2>Solar System — Live Ecliptic Positions</h2>
    <div class="orbit-container" id="orbitVis">
      <div class="earth-core"></div>
      <div class="earth-label">Earth</div>
    </div>
    <div style="text-align:center;margin-top:8px">
      <span style="font-size:0.65em;color:var(--text-dim)" id="aspectSummary"></span>
    </div>
  </div>

  <!-- ─── Aspects ─────────────────────────── -->
  <div class="panel panel-cyan">
    <h2>Active Planetary Aspects</h2>
    <div id="aspectList" style="max-height:340px;overflow-y:auto"></div>
  </div>

  <!-- ─── Coherence Gauge ─────────────────── -->
  <div class="panel panel-green">
    <h2>Shield Coherence &Gamma;</h2>
    <div class="gauge-container">
      <div class="gauge-ring">
        <svg viewBox="0 0 200 200">
          <circle class="gauge-bg" cx="100" cy="100" r="85"/>
          <circle class="gauge-fill" id="gaugeFill" cx="100" cy="100" r="85"
                  stroke-dasharray="534" stroke-dashoffset="534"/>
        </svg>
        <div class="gauge-center">
          <div class="gauge-value" id="gaugeValue">—</div>
          <div class="gauge-label">coverage <span id="gaugePct">—</span>%</div>
        </div>
      </div>
      <div style="margin-top:8px;font-size:0.7em;color:var(--text-dim)">
        Target: &Gamma; &ge; <span id="sigmaTarget"></span> (Sigma Coherence)
      </div>
    </div>
  </div>

  <!-- ─── Layer 1 ─────────────────────────── -->
  <div class="panel panel-amber">
    <h2>Layer 1 — EM Deflection</h2>
    <div class="layer-header">
      <span style="font-size:0.72em;color:var(--text-dim)">Harmonic Field Filter</span>
      <span class="layer-status" id="l1Status"></span>
    </div>
    <div class="metric-row"><span class="metric-label">Incoming threats</span><span class="metric-value" id="l1Threats">—</span></div>
    <div class="metric-row"><span class="metric-label">Field score</span><span class="metric-value" id="l1Score">—</span></div>
    <div class="metric-row"><span class="metric-label">Cosmic field (raw)</span><span class="metric-value" id="cosmicRaw">—</span></div>
    <div class="metric-row"><span class="metric-label">Schumann-modulated</span><span class="metric-value" id="cosmicMod">—</span></div>
  </div>

  <!-- ─── Layer 2 ─────────────────────────── -->
  <div class="panel panel-purple">
    <h2>Layer 2 — Plasma Ablation</h2>
    <div class="layer-header">
      <span style="font-size:0.72em;color:var(--text-dim)">F-Region Density Guard</span>
      <span class="layer-status" id="l2Status"></span>
    </div>
    <div class="metric-row"><span class="metric-label">Electron density</span><span class="metric-value" id="l2Density">—</span></div>
    <div class="metric-row"><span class="metric-label">Shell volume</span><span class="metric-value" id="l2Volume">—</span></div>
    <div class="metric-row"><span class="metric-label">Total electrons</span><span class="metric-value" id="l2Electrons">—</span></div>
    <div class="metric-row"><span class="metric-label">Plasma frequency</span><span class="metric-value" id="l2PlasmaFreq">—</span></div>
    <div class="metric-row"><span class="metric-label">Density score</span><span class="metric-value" id="l2Score">—</span></div>
  </div>

  <!-- ─── Layer 3 ─────────────────────────── -->
  <div class="panel panel-red">
    <h2>Layer 3 — Shield Phased Harmonics</h2>
    <div class="layer-header">
      <span style="font-size:0.72em;color:var(--text-dim)">Acoustic Fragmentation</span>
      <span class="layer-status" id="l3Status"></span>
    </div>
    <div class="metric-row"><span class="metric-label">Schumann phase</span><span class="metric-value" id="l3Phase">—</span></div>
    <div class="metric-row"><span class="metric-label">Schumann modulator</span><span class="metric-value" id="l3Modulator">—</span></div>
    <div class="metric-row"><span class="metric-label">Harmonic coherence</span><span class="metric-value" id="l3Coherence">—</span></div>
    <div class="metric-row"><span class="metric-label">L3 score</span><span class="metric-value" id="l3Score">—</span></div>
  </div>

  <!-- ─── Six Phases ──────────────────────── -->
  <div class="panel panel-green span-2">
    <h2>Six Illumination Phases — Earth Scale</h2>
    <div id="phaseContainer"></div>
  </div>

  <!-- ─── Power Budget ────────────────────── -->
  <div class="panel panel-purple">
    <h2>Earth Power Budget</h2>
    <div style="text-align:center;margin:12px 0">
      <div class="power-value" id="pwrRF">—</div>
      <div class="power-unit">Earth RF Power (Watts)</div>
    </div>
    <div class="metric-row"><span class="metric-label">Power density</span><span class="metric-value" id="pwrDensity">—</span></div>
    <div class="metric-row"><span class="metric-label">Output voltage</span><span class="metric-value" id="pwrVoltage">—</span></div>
    <div class="metric-row"><span class="metric-label">Concentration</span><span class="metric-value" id="pwrConcentration">—</span></div>
    <div style="margin-top:12px;font-size:0.65em;color:var(--text-dim);text-align:center">
      EPOS 50 W &times; concentration factor &rarr; planetary scale
    </div>
  </div>

  <!-- ─── Summary ─────────────────────────── -->
  <div class="panel panel-cyan span-3">
    <h2>Planetary Verdict</h2>
    <div id="verdictText" style="font-size:0.78em;line-height:1.6;word-break:break-word"></div>
  </div>

  <!-- ─── Relay World Map ─────────────────── -->
  <div class="panel panel-blue span-3">
    <h2>Historical Relay Network — Sacred Site Ground Transducers</h2>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
      <span style="font-size:0.7em;color:var(--text-dim)" id="relayNetSummary"></span>
      <span style="font-size:0.7em" id="relayNetCoverage"></span>
    </div>
    <div class="relay-map" id="relayMap">
      <svg viewBox="0 0 360 180" preserveAspectRatio="none">
        <line x1="0" y1="90" x2="360" y2="90" stroke="rgba(51,65,85,0.6)" stroke-width="0.5" stroke-dasharray="4,4"/>
        <line x1="0" y1="66.5" x2="360" y2="66.5" stroke="rgba(51,65,85,0.3)" stroke-width="0.3" stroke-dasharray="2,4"/>
        <line x1="0" y1="113.5" x2="360" y2="113.5" stroke="rgba(51,65,85,0.3)" stroke-width="0.3" stroke-dasharray="2,4"/>
        <line x1="180" y1="0" x2="180" y2="180" stroke="rgba(51,65,85,0.4)" stroke-width="0.3" stroke-dasharray="4,4"/>
        <line x1="0" y1="45" x2="360" y2="45" stroke="rgba(51,65,85,0.15)" stroke-width="0.3" stroke-dasharray="2,6"/>
        <line x1="0" y1="135" x2="360" y2="135" stroke="rgba(51,65,85,0.15)" stroke-width="0.3" stroke-dasharray="2,6"/>
        <line x1="90" y1="0" x2="90" y2="180" stroke="rgba(51,65,85,0.2)" stroke-width="0.3" stroke-dasharray="2,6"/>
        <line x1="270" y1="0" x2="270" y2="180" stroke="rgba(51,65,85,0.2)" stroke-width="0.3" stroke-dasharray="2,6"/>
        <text x="2" y="88" fill="rgba(148,163,184,0.5)" font-size="4">Equator</text>
        <text x="2" y="64" fill="rgba(148,163,184,0.3)" font-size="3">Tropic of Cancer</text>
        <text x="2" y="116" fill="rgba(148,163,184,0.3)" font-size="3">Tropic of Capricorn</text>
      </svg>
      <div id="relayDots"></div>
    </div>
  </div>

  <!-- ─── Relay Table ─────────────────────── -->
  <div class="panel panel-cyan span-3">
    <h2>Relay Site Status — Live Metrics</h2>
    <div style="max-height:400px;overflow-y:auto" id="relayTableContainer"></div>
  </div>

  <!-- ═══ NATURAL IONOSPHERE PROFILER ═══════════════════════════════ -->

  <!-- ─── Ionosphere Header Banner ────────── -->
  <div class="panel panel-blue span-3">
    <h2>Natural Ionosphere &mdash; &ldquo;Know Our Own Before We Make a New&rdquo;</h2>
    <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:12px">
      <div>
        <span style="font-size:0.7em;color:var(--text-dim)">Solar Zenith:</span>
        <span style="font-size:0.85em;font-weight:700" id="ionoZenith">—</span>
        &nbsp;&nbsp;
        <span style="font-size:0.7em;color:var(--text-dim)">Day/Night:</span>
        <span style="font-size:0.85em;font-weight:700" id="ionoDayNight">—</span>
      </div>
      <div>
        <span style="font-size:0.7em;color:var(--text-dim)">Health:</span>
        <span class="layer-status" id="ionoHealth" style="font-size:0.85em"></span>
        &nbsp;&nbsp;
        <span style="font-size:0.7em;color:var(--text-dim)">EPAS Readiness:</span>
        <span style="font-size:0.85em;font-weight:700" id="ionoReady">—</span>
      </div>
      <div>
        <span style="font-size:0.7em;color:var(--text-dim)">foF2:</span>
        <span style="font-size:0.85em;font-weight:700;color:var(--glow-cyan)" id="ionoFoF2">—</span>
        &nbsp;&nbsp;
        <span style="font-size:0.7em;color:var(--text-dim)">TEC:</span>
        <span style="font-size:0.85em;font-weight:700;color:var(--glow-purple)" id="ionoTEC">—</span>
      </div>
    </div>
  </div>

  <!-- ─── Chapman Layers ──────────────────── -->
  <div class="panel panel-cyan span-2">
    <h2>Chapman Layer Model &mdash; Altitude Density Profile</h2>
    <div id="ionoLayerBars"></div>
  </div>

  <!-- ─── Aluminum Harmonic Fluid ─────────── -->
  <div class="panel panel-purple">
    <h2>Aluminum Harmonic Fluid</h2>
    <div style="text-align:center;margin:12px 0">
      <div style="font-size:0.65em;color:var(--text-dim)">Ionosphere &rarr; Aluminum metallicity ratio</div>
      <div class="power-value" id="fluidPeak" style="font-size:1.3em">—</div>
      <div class="power-unit">peak harmonic fluid ratio</div>
    </div>
    <div class="metric-row"><span class="metric-label">Mean ratio</span><span class="metric-value" id="fluidMean">—</span></div>
    <div class="metric-row"><span class="metric-label">Classification</span><span class="metric-value" id="fluidClass">—</span></div>
    <div style="margin-top:10px;font-size:0.6em;color:var(--text-dim);text-align:center">
      Drude model: &epsilon;(&omega;) = 1 &minus; &omega;<sub>p</sub>&sup2; / (&omega;&sup2; + i&gamma;&omega;)<br>
      Aluminum &omega;<sub>p</sub> = 3.57 PHz &bull; Ionosphere &omega;<sub>p</sub> &asymp; 3&ndash;9 MHz
    </div>
  </div>

  <!-- ─── FFS Spectral Analysis ───────────── -->
  <div class="panel panel-amber span-2">
    <h2>FFS Full Frequency Spectrum &mdash; Spectral Analysis</h2>
    <div style="display:flex;gap:16px;margin-bottom:8px">
      <div><span style="font-size:0.7em;color:var(--text-dim)">Opaque below:</span>
        <span style="font-size:0.8em;font-weight:700;color:var(--glow-red)" id="ffsOpaque">—</span></div>
      <div><span style="font-size:0.7em;color:var(--text-dim)">Transparent above:</span>
        <span style="font-size:0.8em;font-weight:700;color:var(--glow-green)" id="ffsTransparent">—</span></div>
    </div>
    <div style="max-height:280px;overflow-y:auto" id="ffsTable"></div>
  </div>

  <!-- ─── Lighthouse Mapping ──────────────── -->
  <div class="panel panel-green">
    <h2>Lighthouse Mapping</h2>
    <div style="text-align:center;margin:8px 0">
      <div style="font-size:2em;font-weight:700;color:var(--glow-green)" id="lhLocked">—</div>
      <div style="font-size:0.7em;color:var(--text-dim)">probes LOCKED</div>
    </div>
    <div class="metric-row"><span class="metric-label">Mean foF2</span><span class="metric-value" id="lhMeanFoF2">—</span></div>
    <div class="metric-row"><span class="metric-label">Mean TEC</span><span class="metric-value" id="lhMeanTEC">—</span></div>
    <div style="margin-top:8px;max-height:180px;overflow-y:auto" id="lhProbeList"></div>
  </div>

</div>

<div class="footer">
  <span class="refresh-indicator"></span>
  <span id="footerTs">Connecting...</span>
  &nbsp;&middot;&nbsp; Auto-refresh every 5 s &nbsp;&middot;&nbsp; VSOP87 Engine &nbsp;&middot;&nbsp; Aureon Emerald Decoder
</div>

<script>
const PLANET_COLORS = {
  Sun:'#fbbf24', Moon:'#e2e8f0', Mercury:'#a3a3a3', Venus:'#fb923c',
  Mars:'#ef4444', Jupiter:'#f59e0b', Saturn:'#d4a574', Uranus:'#67e8f9',
  Neptune:'#818cf8', Pluto:'#a78bfa'
};
const PLANET_SIZES = {
  Sun:14, Moon:8, Mercury:6, Venus:8, Mars:7, Jupiter:12, Saturn:11,
  Uranus:9, Neptune:9, Pluto:5
};

function sci(n, d) { return n != null ? Number(n).toExponential(d || 2) : '—'; }
function fix(n, d) { return n != null ? Number(n).toFixed(d || 4) : '—'; }

function statusClass(s) {
  const good = ['CLEAR','INTACT','COHERENT','SHIELDS_UP','PRIMED','RESONANT','ACTIVE','AMPLIFYING','STABLE','DELIVERING'];
  const warn = ['DEFLECTING','ABLATING','CRACKING','SHIELDS_STRESSED','SPARKING','COUPLING','FLUCTUATING','MIXING','STABILIZING','CHARGING'];
  if (good.includes(s)) return 'status-good';
  if (warn.includes(s)) return 'status-warn';
  return 'status-danger';
}

function phaseBarColor(score) {
  if (score >= 0.65) return 'var(--glow-green)';
  if (score >= 0.42) return 'var(--glow-amber)';
  return 'var(--glow-red)';
}

function gaugeColor(gamma) {
  if (gamma >= 0.70) return 'var(--glow-green)';
  if (gamma >= 0.42) return 'var(--glow-amber)';
  return 'var(--glow-red)';
}

function renderOrbits(positions) {
  const container = document.getElementById('orbitVis');
  // Remove old dots/labels/rings
  container.querySelectorAll('.planet-dot,.planet-label,.orbit-ring').forEach(el => el.remove());

  const bodies = Object.entries(positions).sort((a,b) => a[1] - b[1]);
  const cx = 50, cy = 50; // percent
  const ringRadii = [15, 20, 25, 30, 35, 38, 42, 45, 47, 49]; // percent of container

  // Draw orbit rings
  ringRadii.forEach(r => {
    const ring = document.createElement('div');
    ring.className = 'orbit-ring';
    ring.style.width = ring.style.height = (r*2) + '%';
    container.appendChild(ring);
  });

  bodies.forEach(([name, lon], idx) => {
    const r = ringRadii[Math.min(idx, ringRadii.length-1)];
    const rad = (lon - 90) * Math.PI / 180; // -90 so 0° is top
    const px = cx + r * Math.cos(rad);
    const py = cy + r * Math.sin(rad);

    const dot = document.createElement('div');
    dot.className = 'planet-dot';
    const sz = PLANET_SIZES[name] || 7;
    dot.style.width = sz + 'px';
    dot.style.height = sz + 'px';
    dot.style.background = PLANET_COLORS[name] || '#94a3b8';
    dot.style.boxShadow = '0 0 8px ' + (PLANET_COLORS[name] || '#94a3b8');
    dot.style.left = px + '%';
    dot.style.top = py + '%';
    dot.title = name + ': ' + Number(lon).toFixed(2) + '°';
    container.appendChild(dot);

    const lbl = document.createElement('div');
    lbl.className = 'planet-label';
    lbl.textContent = name.substring(0, 3);
    lbl.style.left = px + '%';
    lbl.style.top = py + '%';
    container.appendChild(lbl);
  });
}

function renderAspects(aspects) {
  const container = document.getElementById('aspectList');
  if (!aspects || !aspects.length) { container.innerHTML = '<div style="color:var(--text-dim);font-size:0.75em">No active aspects</div>'; return; }
  const sorted = [...aspects].sort((a,b) => Math.abs(b.score) - Math.abs(a.score));
  container.innerHTML = sorted.map(a => {
    const cls = a.score >= 0 ? 'aspect-positive' : 'aspect-negative';
    return `<div class="aspect-row ${cls}">
      <span>${a.body1}–${a.body2}</span>
      <span class="aspect-name">${a.aspect} ${a.separation}°</span>
      <span>orb ${a.orb}°</span>
      <span>h=${a.harmonic_value >= 0 ? '+' : ''}${a.harmonic_value}</span>
      <span>&phi;=${a.phi_resonance}</span>
      <span class="aspect-score">${a.score >= 0 ? '+' : ''}${a.score}</span>
    </div>`;
  }).join('');
}

const CIV_COLORS = {
  'Egyptian':'#fbbf24', 'Maya':'#22c55e', 'Celtic':'#3b82f6', 'Mogollon':'#f97316',
  'Khmer':'#a855f7', 'Javanese':'#ec4899', 'Neolithic':'#94a3b8', 'Inca':'#14b8a6',
  'Nazca':'#f43f5e', 'Tiwanaku':'#06b6d4', 'Micronesian':'#10b981',
  'Rapa Nui':'#e879f9', 'Shona':'#fb923c', 'Aboriginal':'#ef4444'
};

function renderRelayMap(sites) {
  const container = document.getElementById('relayDots');
  container.innerHTML = '';
  if (!sites) return;
  sites.forEach(s => {
    const x = ((s.longitude + 180) / 360) * 100;
    const y = ((90 - s.latitude) / 180) * 100;
    const dot = document.createElement('div');
    dot.className = 'relay-dot ' + s.relay_status.toLowerCase();
    dot.style.left = x + '%';
    dot.style.top = y + '%';
    const civClr = CIV_COLORS[s.civilisation] || '#94a3b8';
    dot.style.border = '2px solid ' + civClr;
    dot.title = s.name + ' (' + s.civilisation + ')\n'
      + s.harmonic_role + '\n'
      + 'Status: ' + s.relay_status + '\n'
      + 'Strength: ' + (s.relay_strength * 100).toFixed(1) + '%\n'
      + 'Geo-coupling: ' + s.geomagnetic_coupling.toFixed(4) + '\n'
      + 'Power: ' + sci(s.power_share_w, 2) + ' W';
    container.appendChild(dot);
  });
}

function renderRelayTable(sites) {
  const c = document.getElementById('relayTableContainer');
  if (!sites || !sites.length) { c.innerHTML = '<div style="color:var(--text-dim);font-size:0.75em">No relay data</div>'; return; }
  const rows = sites.map(s => {
    const sc = s.relay_status==='ACTIVE'||s.relay_status==='RESONATING' ? 'status-good' :
               s.relay_status==='DORMANT' ? 'status-warn' : 'status-danger';
    const cc = CIV_COLORS[s.civilisation] || '#94a3b8';
    return '<tr>'
      + '<td style="font-weight:600">' + s.name + '</td>'
      + '<td><span class="relay-civ" style="background:'+cc+'22;color:'+cc+'">' + s.civilisation + '</span></td>'
      + '<td>' + s.harmonic_role + '</td>'
      + '<td>' + s.latitude.toFixed(2) + '\u00b0, ' + s.longitude.toFixed(2) + '\u00b0</td>'
      + '<td>' + s.geomagnetic_coupling.toFixed(4) + '</td>'
      + '<td style="font-weight:700;color:' + phaseBarColor(s.relay_strength) + '">' + (s.relay_strength*100).toFixed(1) + '%</td>'
      + '<td><span class="layer-status '+sc+'" style="font-size:0.85em">' + s.relay_status + '</span></td>'
      + '<td>' + sci(s.power_share_w, 2) + ' W</td>'
      + '</tr>';
  }).join('');
  c.innerHTML = '<table class="relay-table">'
    + '<thead><tr><th>Site</th><th>Civilisation</th><th>Role</th><th>Coordinates</th><th>Geo-Coupling</th><th>Strength</th><th>Status</th><th>Power</th></tr></thead>'
    + '<tbody>' + rows + '</tbody></table>';
}

function renderPhases(phases) {
  const container = document.getElementById('phaseContainer');
  if (!phases) return;
  container.innerHTML = phases.map(p => {
    const pct = (p.score * 100).toFixed(1);
    const clr = phaseBarColor(p.score);
    return `<div class="phase-row">
      <span class="phase-label">${p.phase}</span>
      <div class="phase-bar-bg">
        <div class="phase-bar-fill" style="width:${pct}%;background:${clr}"></div>
      </div>
      <span class="phase-score" style="color:${clr}">${p.score.toFixed(4)}</span>
      <span class="phase-status-tag ${statusClass(p.status)}" style="padding:1px 6px;border-radius:3px">${p.status}</span>
    </div>`;
  }).join('');
}

const LAYER_COLORS = {
  'D':'#ef4444', 'E':'#f59e0b', 'F1':'#22c55e', 'F2':'#06b6d4', 'Topside':'#a855f7'
};

function fmtFreq(hz) {
  if (hz >= 1e9) return (hz/1e9).toFixed(2) + ' GHz';
  if (hz >= 1e6) return (hz/1e6).toFixed(2) + ' MHz';
  if (hz >= 1e3) return (hz/1e3).toFixed(2) + ' kHz';
  return hz.toFixed(1) + ' Hz';
}

function renderIonoLayers(layers) {
  const c = document.getElementById('ionoLayerBars');
  if (!layers || !layers.length) { c.innerHTML = '<div style="color:var(--text-dim)">No layer data</div>'; return; }
  const maxN = Math.max(...layers.map(l => l.peak_density_m3));
  c.innerHTML = layers.map(l => {
    const pct = maxN > 0 ? (l.peak_density_m3 / maxN * 100).toFixed(1) : 0;
    const clr = LAYER_COLORS[l.name] || '#94a3b8';
    return '<div style="margin-bottom:6px">'
      + '<div style="display:flex;justify-content:space-between;font-size:0.72em">'
      + '<span style="color:'+clr+';font-weight:700">'+l.name+' ('+l.base_alt_km+'-'+l.top_alt_km+' km)</span>'
      + '<span style="color:var(--text-bright)">N<sub>m</sub>='+sci(l.peak_density_m3)+' m<sup>-3</sup></span>'
      + '</div>'
      + '<div class="phase-bar-bg" style="height:14px">'
      + '<div class="phase-bar-fill" style="width:'+pct+'%;background:'+clr+'"></div>'
      + '</div>'
      + '<div style="display:flex;justify-content:space-between;font-size:0.6em;color:var(--text-dim)">'
      + '<span>f<sub>p</sub>='+fmtFreq(l.plasma_freq_hz)+'</span>'
      + '<span>&sigma;='+sci(l.conductivity_s_m,2)+' S/m</span>'
      + '<span>&delta;='+Number(l.skin_depth_m).toLocaleString()+' m</span>'
      + '<span>&epsilon;\'='+l.drude_epsilon_real.toFixed(4)+'</span>'
      + '</div></div>';
  }).join('');
}

function renderFFSTable(bands) {
  const c = document.getElementById('ffsTable');
  if (!bands || !bands.length) { c.innerHTML = '<div style="color:var(--text-dim)">No FFS data</div>'; return; }
  const show = bands.filter((b,i) => i % 2 === 0 || !b.penetrates);
  const rows = show.map(b => {
    const reflect = b.penetrates ? '<span style="color:var(--glow-green)">TRANSPARENT</span>'
      : '<span style="color:var(--glow-red)">REFLECTS @ '+b.reflection_alt_km+' km</span>';
    return '<tr>'
      + '<td style="color:var(--glow-amber)">'+b.band_name+'</td>'
      + '<td>'+fmtFreq(b.freq_hz)+'</td>'
      + '<td>'+reflect+'</td>'
      + '<td>'+b.absorption_db_km.toFixed(4)+' dB/km</td>'
      + '<td>'+b.phase_velocity_ratio.toFixed(4)+'c</td>'
      + '</tr>';
  }).join('');
  c.innerHTML = '<table class="relay-table"><thead><tr>'
    + '<th>Band</th><th>Freq</th><th>Propagation</th><th>Absorption</th><th>V<sub>phase</sub></th>'
    + '</tr></thead><tbody>'+rows+'</tbody></table>';
}

function renderLHProbes(probes) {
  const c = document.getElementById('lhProbeList');
  if (!probes) return;
  c.innerHTML = probes.map(p => {
    const sc = p.probe_status==='LOCKED' ? 'status-good' :
               p.probe_status==='PARTIAL' ? 'status-warn' : 'status-danger';
    return '<div style="display:flex;justify-content:space-between;font-size:0.65em;padding:2px 0;border-bottom:1px solid rgba(51,65,85,0.3)">'
      + '<span style="min-width:120px">'+p.site_name.substring(0,18)+'</span>'
      + '<span class="layer-status '+sc+'" style="font-size:0.9em">'+p.probe_status+'</span>'
      + '<span>foF2='+fmtFreq(p.local_fof2_hz)+'</span>'
      + '<span>TEC='+p.tec_tecu.toFixed(1)+'</span>'
      + '</div>';
  }).join('');
}

function updateGauge(gamma, pct) {
  const circumference = 534;
  const offset = circumference * (1 - gamma);
  const fill = document.getElementById('gaugeFill');
  const clr = gaugeColor(gamma);
  fill.style.strokeDashoffset = offset;
  fill.style.stroke = clr;
  document.getElementById('gaugeValue').textContent = gamma.toFixed(4);
  document.getElementById('gaugeValue').style.color = clr;
  document.getElementById('gaugePct').textContent = pct.toFixed(1);
}

async function refresh() {
  try {
    const r = await fetch('/api/simulation');
    const d = await r.json();

    // Banner
    const banner = document.getElementById('shieldBanner');
    banner.textContent = d.shield.status + '  ·  ' + d.shield.coverage_pct.toFixed(1) + '% coverage';
    banner.className = 'shield-status-banner ' +
      (d.shield.status === 'SHIELDS_UP' ? 'shield-up' :
       d.shield.status === 'SHIELDS_STRESSED' ? 'shield-stress' : 'shield-fail');

    // Orbits
    renderOrbits(d.solar_system.positions);

    // Aspect summary
    document.getElementById('aspectSummary').textContent =
      d.solar_system.total_aspects + ' aspects  (+' +
      d.solar_system.positive_aspects + ' / \u2212' +
      d.solar_system.negative_aspects + ')';

    // Aspects
    renderAspects(d.active_aspects);

    // Gauge
    updateGauge(d.shield.coherence, d.shield.coverage_pct);
    document.getElementById('sigmaTarget').textContent = d.shield.sigma_target;

    // Layer 1
    document.getElementById('l1Threats').textContent = d.layer1_em_deflection.incoming_threats;
    document.getElementById('l1Score').textContent = fix(d.layer1_em_deflection.field_score);
    const l1s = document.getElementById('l1Status');
    l1s.textContent = d.layer1_em_deflection.status;
    l1s.className = 'layer-status ' + statusClass(d.layer1_em_deflection.status);
    document.getElementById('cosmicRaw').textContent = fix(d.solar_system.cosmic_field_score);
    document.getElementById('cosmicMod').textContent = fix(d.solar_system.schumann_modulated_score);

    // Layer 2
    document.getElementById('l2Density').textContent = sci(d.layer2_plasma_ablation.electron_density_m3, 3) + ' m\u207B\u00B3';
    document.getElementById('l2Volume').textContent = sci(d.layer2_plasma_ablation.shell_volume_m3, 3) + ' m\u00B3';
    document.getElementById('l2Electrons').textContent = sci(d.layer2_plasma_ablation.total_electrons, 3);
    document.getElementById('l2PlasmaFreq').textContent = Number(d.layer2_plasma_ablation.plasma_frequency_hz).toLocaleString() + ' Hz';
    document.getElementById('l2Score').textContent = fix(d.layer2_plasma_ablation.score);
    const l2s = document.getElementById('l2Status');
    l2s.textContent = d.layer2_plasma_ablation.status;
    l2s.className = 'layer-status ' + statusClass(d.layer2_plasma_ablation.status);

    // Layer 3
    document.getElementById('l3Phase').textContent = fix(d.layer3_shield_phased_harmonics.schumann_phase);
    document.getElementById('l3Modulator').textContent = fix(d.layer3_shield_phased_harmonics.schumann_modulator, 6);
    document.getElementById('l3Coherence').textContent = fix(d.layer3_shield_phased_harmonics.harmonic_coherence);
    document.getElementById('l3Score').textContent = fix(d.layer3_shield_phased_harmonics.score);
    const l3s = document.getElementById('l3Status');
    l3s.textContent = d.layer3_shield_phased_harmonics.status;
    l3s.className = 'layer-status ' + statusClass(d.layer3_shield_phased_harmonics.status);

    // Phases
    renderPhases(d.illumination_phases);

    // Power
    document.getElementById('pwrRF').textContent = sci(d.power.earth_rf_power_w, 3);
    document.getElementById('pwrDensity').textContent = sci(d.power.earth_power_density_w_m3, 3) + ' W/m\u00B3';
    document.getElementById('pwrVoltage').textContent = Number(d.power.earth_output_voltage_v).toLocaleString() + ' V';
    document.getElementById('pwrConcentration').textContent = '×' + Number(""" + str(VOLUMETRIC_CONCENTRATION_FACTOR) + r""").toLocaleString();

    // Verdict
    document.getElementById('verdictText').textContent = d.planetary_summary;

    // Relay Network
    if (d.relay_network) {
      const rn = d.relay_network;
      document.getElementById('relayNetSummary').textContent =
        rn.active_count + '/' + rn.total_count + ' relays active';
      const covPct = (rn.network_coverage * 100).toFixed(1);
      const covEl = document.getElementById('relayNetCoverage');
      covEl.textContent = 'Network coverage: ' + covPct + '%';
      covEl.style.color = rn.network_coverage >= 0.35 ? 'var(--glow-green)' :
                           rn.network_coverage >= 0.20 ? 'var(--glow-amber)' : 'var(--glow-red)';
      renderRelayMap(rn.sites);
      renderRelayTable(rn.sites);
    }

    // Natural Ionosphere Profile
    if (d.natural_ionosphere) {
      const ni = d.natural_ionosphere;
      document.getElementById('ionoZenith').textContent = ni.solar_zenith_deg.toFixed(1) + '\u00b0';
      const dn = document.getElementById('ionoDayNight');
      dn.textContent = ni.is_daytime ? '\u2600 DAYTIME' : '\u263e NIGHTTIME';
      dn.style.color = ni.is_daytime ? 'var(--glow-amber)' : 'var(--glow-blue)';
      const hEl = document.getElementById('ionoHealth');
      const hMap = {'ROBUST':'status-good','MODERATE':'status-warn','DEPLETED':'status-danger','STORM':'status-danger'};
      hEl.textContent = ni.assessment.ionosphere_health;
      hEl.className = 'layer-status ' + (hMap[ni.assessment.ionosphere_health] || 'status-warn');
      const rdyPct = (ni.assessment.readiness_for_epas * 100).toFixed(1);
      const rdyEl = document.getElementById('ionoReady');
      rdyEl.textContent = rdyPct + '%';
      rdyEl.style.color = ni.assessment.readiness_for_epas >= 0.6 ? 'var(--glow-green)' :
                           ni.assessment.readiness_for_epas >= 0.3 ? 'var(--glow-amber)' : 'var(--glow-red)';
      document.getElementById('ionoFoF2').textContent = fmtFreq(ni.f2_peak.critical_freq_hz);
      document.getElementById('ionoTEC').textContent = ni.f2_peak.total_electron_content_tecu.toFixed(2) + ' TECU';
      renderIonoLayers(ni.layers);
      // Fluid
      document.getElementById('fluidPeak').textContent = ni.aluminum_harmonic_fluid.peak_ratio.toExponential(4);
      document.getElementById('fluidMean').textContent = ni.aluminum_harmonic_fluid.mean_ratio.toExponential(4);
      document.getElementById('fluidClass').textContent = ni.aluminum_harmonic_fluid.classification;
      // FFS
      document.getElementById('ffsOpaque').textContent = fmtFreq(ni.ffs_spectral.opaque_below_hz);
      document.getElementById('ffsTransparent').textContent = fmtFreq(ni.ffs_spectral.transparent_above_hz);
      renderFFSTable(ni.ffs_spectral.bands);
      // Lighthouse
      const lm = ni.lighthouse_mapping;
      document.getElementById('lhLocked').textContent = lm.locked_count + '/' + lm.probes.length;
      document.getElementById('lhMeanFoF2').textContent = fmtFreq(lm.mean_fof2_hz);
      document.getElementById('lhMeanTEC').textContent = lm.mean_tec_tecu.toFixed(2) + ' TECU';
      renderLHProbes(lm.probes);
    }

    // Footer
    document.getElementById('footerTs').textContent =
      'Updated: ' + d.timestamp + '  ·  ' + d.solar_system.total_aspects + ' aspects  ·  \u0393 = ' + d.shield.coherence.toFixed(4);

  } catch(e) {
    console.error('Refresh error:', e);
    document.getElementById('footerTs').textContent = 'Connection error — retrying...';
  }
}

// First fetch + auto-refresh
refresh();
setInterval(refresh, 5000);
</script>
</body>
</html>"""


# ═══════════════════════════════════════════════════════════════════════════════
# API HANDLERS
# ═══════════════════════════════════════════════════════════════════════════════

async def handle_index(request):
    """Serve the main dashboard HTML."""
    return web.Response(text=DASHBOARD_HTML, content_type='text/html')


async def handle_health(request):
    """Health check."""
    return web.json_response({
        'status': 'healthy',
        'service': 'earth-epas-shield-dashboard',
        'timestamp': datetime.now().isoformat(),
    })


async def handle_simulation(request):
    """Run a fresh simulation and return JSON."""
    sim = simulate_earth_epas()
    return web.json_response(sim.to_dict())


# ═══════════════════════════════════════════════════════════════════════════════
# SERVER
# ═══════════════════════════════════════════════════════════════════════════════

def create_app():
    app = web.Application()
    app.router.add_get('/', handle_index)
    app.router.add_get('/api/health', handle_health)
    app.router.add_get('/api/simulation', handle_simulation)
    return app


def main():
    from aureon.core.simulated_boot import random_dashboard_allowed

    if not random_dashboard_allowed():
        return
    print()
    print("=" * 70)
    print(r"""
    ███████╗ █████╗ ██████╗ ████████╗██╗  ██╗
    ██╔════╝██╔══██╗██╔══██╗╚══██╔══╝██║  ██║
    █████╗  ███████║██████╔╝   ██║   ███████║
    ██╔══╝  ██╔══██║██╔══██╗   ██║   ██╔══██║
    ███████╗██║  ██║██║  ██║   ██║   ██║  ██║
    ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝

    ███████╗██████╗  █████╗ ███████╗    ███████╗██╗  ██╗██╗███████╗██╗     ██████╗
    ██╔════╝██╔══██╗██╔══██╗██╔════╝    ██╔════╝██║  ██║██║██╔════╝██║     ██╔══██╗
    █████╗  ██████╔╝███████║███████╗    ███████╗███████║██║█████╗  ██║     ██║  ██║
    ██╔══╝  ██╔═══╝ ██╔══██║╚════██║    ╚════██║██╔══██║██║██╔══╝  ██║     ██║  ██║
    ███████╗██║     ██║  ██║███████║    ███████║██║  ██║██║███████╗███████╗██████╔╝
    ╚══════╝╚═╝     ╚═╝  ╚═╝╚══════╝    ╚══════╝╚═╝  ╚═╝╚═╝╚══════╝╚══════╝╚═════╝
    """)
    print("=" * 70)
    print("  EARTH EPAS SECOND IONOSPHERE — LIVE DASHBOARD")
    print("=" * 70)
    print()
    print(f"   URL:     http://localhost:{DASHBOARD_PORT}")
    print(f"   API:     http://localhost:{DASHBOARD_PORT}/api/simulation")
    print(f"   Health:  http://localhost:{DASHBOARD_PORT}/api/health")
    print(f"   Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("   Auto-refresh: every 5 seconds (live VSOP87 recomputation)")
    print("   Press Ctrl+C to stop")
    print("=" * 70)
    print()

    app = create_app()

    print(f"Starting Earth Shield dashboard on port {DASHBOARD_PORT}...")
    try:
        web.run_app(app, host='0.0.0.0', port=DASHBOARD_PORT, print=None)
    except Exception as e:
        print(f"Server error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
