# Archive: Auris Real-Time Validator Setup

Status: Historical/experimental reference. For the unified ecosystem and current run path, see [README.md](README.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Overview
The Auris system now includes a complete real-time validation pipeline with Python backend processing for intent broadcast verification using Earth data streams.

## Components

### 1. Python Validator (`validator_auris.py`)
Real-time processor that computes validation metrics using exact mathematical formulas:
- **Coherence Score**: Energy concentration on Schumann harmonics
- **Schumann Lock**: Harmonic-weighted resonance alignment  
- **TSV Gain**: Time-source-vector amplitude with soft clipping
- **Prime Alignment**: Spectral energy on prime-indexed FFT bins
- **Phase Error**: Circular deviation from Happiness (10Hz) and Love (8.25Hz) pulses
- **10-9-1 Concordance**: Energy distribution matching Unity:Flow:Anchor bands

### 2. Stream Exporter (`src/lib/auris-stream-exporter.ts`)
Formats React data for Python validator consumption:
- Generates realistic signal samples based on intent
- Converts intents to 10-9-1 vectors
- Outputs newline-delimited JSON format
- Provides console streaming and file download

### 3. Enhanced UI (`src/components/AurisSymbolicCompiler.tsx`)
Real-time compilation with Python integration:
- Live validation every 1.2 seconds
- Stream control buttons (Start/Stop/Download)
- Real-time waveform visualization
- Earth data integration (solar wind, geomagnetic field)

## Usage Instructions

### Step 1: Install Python Dependencies
```bash
pip install numpy pandas
```

### Step 2: Start the React Application
```bash
npm run dev
```

### Step 3: Enable Python Stream
1. Open the Auris Symbolic Compiler
2. Click "Start Stream" in the Python Validator section
3. Open browser console to see JSON output

### Step 4: Run Python Validator
```bash
# Pipe browser console output to validator
python validator_auris.py < auris_stream.jsonl

# Or for real-time processing:
tail -f auris_stream.jsonl | python validator_auris.py
```

### Step 5: Monitor Results
- Python validator outputs validation scores to stderr
- Metrics are saved to `auris_metrics.csv`
- Real-time status shows ✅ VALIDATED or 🔄 OPTIMIZING

## Expected JSON Format
```json
{
  "ts": "2025-08-31T10:58:12.431Z",
  "site_id": "EARTH-01", 
  "lattice_id": "Φ•Gaia•02111991•10:9:1",
  "sr": 200,
  "samples": [0.1, -0.2, 0.3, ...],
  "gain": 1.0,
  "intent": [10, 9, 1],
  "targets_hz": [7.83, 14.3, 20.8, 27.3, 33.8]
}
```

## Validation Metrics Output
The validator computes and logs:
- Coherence: 0.0-1.0 (energy on Schumann frequencies)
- Schumann Lock: 0.0-1.0 (harmonic weighting)
- TSV Gain: 0.0-1.0 (amplitude with tanh clipping)
- Prime Alignment: 0.0-1.0 (spectral energy on primes)
- Phase Errors: radians (deviation from target pulses)
- 10-9-1 Concordance: 0.0-1.0 (band energy distribution)

## Real-Time Operation
The system runs continuously:
1. React generates intent signals every 1.2s
2. Stream exporter formats data for Python
3. Python validator computes exact metrics
4. Results logged to CSV for analysis
5. UI shows live validation status

This creates a complete real-time validation loop for intent broadcast monitoring with mathematical precision.