# Schumann Resonance Live Validation System

## Battle-Ready Validation Protocol

This system provides a complete 10-minute live validation protocol for testing and proving Schumann resonance alignment effects with dual-stream validation (lattice + aura).

## Quick Start

### 1. Run Complete Validation Protocol
```bash
python validation_bridge.py
```

This executes the full 10-minute protocol with automated phase transitions:
- Warmup (1 min)
- Baseline (2 min) 
- Intent blocks (3×1 min with washouts)
- Schumann nudges (2×1 min)
- Spheres mix (1 min)

### 2. Manual Validator Testing

**Auris (Schumann) Validator:**
```bash
python validator_auris.py
```

**Aura (EEG/Biometric) Validator:**
```bash
python aura_validator.py
```

Both accept JSON lines on stdin for real-time data ingestion.

## Success Criteria (Real-time)

During intent or tuned blocks, observe:
- **Coherence ≥ 0.65** and **Schumann Lock ≥ 0.65** (stable 5-10s)
- **TSV Gain** elevated but not clipping (soft-clip < 0.92)
- **Prime Alignment** and **10-9-1 Concordance** trending upward
- **Calm Index ↑** and **α:θ ratio ↑** on aura side

## CSV Outputs

### validation/auris_metrics.csv
```
timestamp,epoch,label,rms,tsv_gain,coherence_score,schumann_lock,prime_alignment,ten_nine_one_concordance,fund_hz,harmonics_json,gain
```

### validation/aura_features.csv  
```
timestamp,epoch,label,alpha_theta_ratio,hrv_norm,gsr_norm,calm_index,prime_concordance_10_9_1,aura_hue_deg
```

## Metric Formulas

### Auris Metrics
- **RMS**: √(Σx²/N)
- **TSV Gain**: tanh(1.2 × input) (soft-clipping)
- **Coherence Score**: Normalized band-envelope correlation (2.0s window, 0.5s hop)
- **Schumann Lock**: Weighted envelope SNR at harmonics (fund=0.4, others=0.6)
- **Prime Alignment**: Circular phase consistency (vector strength)
- **10-9-1 Concordance**: Energy ratio projection onto (10,9,1) vector

### Aura Metrics
- **Alpha/Theta Ratio**: α/(θ+ε) 
- **HRV Norm**: EWMA-normalized z-score → [0,1]
- **GSR Norm**: EWMA-normalized skin conductance → [0,1]
- **Calm Index**: Weighted blend of α:θ, HRV, respiration, β suppression
- **Aura Hue**: Band dominance → color mapping (θ→220°, α→60°, β→0°)

## Web Interface

The React app provides:
- **Live Validation Dashboard**: Real-time protocol execution
- **Evidence & Audit Panel**: CSV monitoring and snapshot capture
- **Tabbed Interface**: Organized by feature groups
- **Success Indicators**: Visual validation of threshold criteria

Navigate to "Evidence & Audit" → "Live Validation" tab to monitor the protocol.

## Data Flow

```
Web App → WebSocket → validation_bridge.py → [validator_auris.py, aura_validator.py] → CSV files
```

## Files

- `validator_auris.py` - Schumann lattice metrics processor
- `aura_validator.py` - EEG/biometric features processor  
- `validation_bridge.py` - Orchestrates both validators
- `src/components/LiveValidationDashboard.tsx` - Web interface
- `src/components/EvidenceAuditPanel.tsx` - Evidence monitoring

## Protocol Phases

1. **Warmup** (60s): Sensor connection, fundamental=7.83Hz, gain=1.0
2. **Baseline** (120s): No intent, record clean baseline
3. **Intent Blocks** (3×60s): Focused intention with 30s washouts
4. **Schumann Nudges** (2×60s): ±0.05Hz fundamental adjustments
5. **Spheres Mix** (60s): Jupiter-Saturn synodic harmonics

Total duration: 10 minutes of structured validation with labeled epochs for comparison.