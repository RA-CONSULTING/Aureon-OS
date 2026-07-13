# Validation System Test Guide

## Quick 60-Second Go/No-Go Check

### Setup (3 terminals)

1. **Terminal 1 - Schumann Validator**
```bash
python validator_auris.py
```

2. **Terminal 2 - Aura Validator** 
```bash
python aura_validator.py
```

3. **Terminal 3 - Test Emitters**
```bash
# For Schumann lattice stream
python emit_test_stream.py | python validator_auris.py

# For aura biometric stream (separate terminal)
python emit_test_stream_aura.py | python aura_validator.py
```

### Expected Results

**CSV Files Generated:**
- `validation/auris_metrics.csv` (updates ~0.5s intervals)
- `validation/aura_features.csv` (updates ~1s intervals)

**During "intent" blocks you should see:**
- `coherence_score` ≥ 0.65
- `schumann_lock` ≥ 0.65  
- `calm_index` ↑ (rising)
- `prime_concordance_10_9_1` ↑ (rising)
- `aura_hue_deg` → ~60° (alpha-dominant region)

### Test Data Phases

**emit_test_stream.py (Schumann):**
- Baseline (10s): Low coherence ~0.3-0.5
- Intent Grounding (10s): Enhanced coherence + envelopes
- Nudge +0.05Hz (10s): Frequency lock test

**emit_test_stream_aura.py (Biometric):**
- Baseline (10s): Normal alpha/theta, moderate HRV
- Intent (10s): ↑ alpha, ↓ beta, ↑ HRV, resp→6bpm
- Nudge (10s): Sustained calm state

### Troubleshooting

**UI crashes on .toFixed():**
- Fixed with null safety: `(value || 0).toFixed(3)`

**Flat coherence_score:**
- Verify `fund_hz`, `harmonics`, `gain` in JSON packets

**CSVs not updating:**
- Check validators are running and receiving piped data
- Ensure `validation/` directory exists

### Success Criteria

✅ Both CSV files updating with realistic metrics
✅ Coherence/lock rise during intent phases  
✅ Calm index increases with better alpha/theta ratios
✅ Prime concordance tracks 10-9-1 alignment
✅ Aura hue shifts toward alpha-dominant (~60°)

The validation system is battle-ready for live proof protocols.