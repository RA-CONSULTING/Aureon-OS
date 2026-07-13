# 🔭 Aureon Quantum Telescope: Bot Shape Scanner

This module allows you to "see" the shape of algorithmic actors in the market by breaking down trade volume and order book layering into spectral frequencies (Hz).

## Components

1. **Scanner Engine (`aureon_bot_shape_scanner.py`)**
    - **Role:** The backend "Telescope".
    - **Function:** Connects to Binance WebSocket (Trades + Depth), performs FFT (Fast Fourier Transform), and identifies periodic bot loops.
    - **Output:** Generates `bot_shape_snapshot.json` every 5 seconds.

2. **3D Viewer (`bot_shape_viewer.py`)**
    - **Role:** The "3D Printer" Frontend.
    - **Function:** Reads the snapshot and renders an interactive 3D scatter plot.
    - **Output:** Creates `bot_shapes.html` (Open in your browser).
    - **Visuals:**
        - **X-Axis:** Asset (Reality Branch)
        - **Y-Axis:** Frequency (The "Loop Speed" - e.g., 2Hz = 2 trades/sec pattern)
        - **Z-Axis:** Amplitude (Magnitude of the bot's volume)
        - **Color:** Bot Class (HFT, Spoofing, Accumulation)

3. **ML Bridge (`aureon_bridge_ml.py`)**
    - **Role:** The Intelligence Collector.
    - **Function:** Watches for new snapshots and appends them to a CSV dataset.
    - **Output:** `bot_shape_training_data.csv` (used to train the Queen).

4. **Historical Census (`aureon_historical_bot_census.py`)**
    - **Role:** The Historian.
    - **Function:** Scans the last 365 days of 1H candles to find persistent macro-bots (24h, Weekly, Funding Rate algos).
    - **Output:** `bot_census_registry.json`.

## How to Run

### Step 1: Historical Census (One-Time)

Identify the permanent residents of the market:

```bash
python aureon_historical_bot_census.py
```

*This generates the "Bot Registry" of verified whales.*

### Step 2: Start the Live Scanner

In a terminal, run:

```bash
python aureon_bot_shape_scanner.py
```

*Wait for it to connect to Binance streams and start creating snapshots.*

### Step 2: Start the Visualization

In a **separate** terminal, run:

```bash
python bot_shape_viewer.py
```

*This will continually update `bot_shapes.html`.*

### Step 3: View Results

Open `bot_shapes.html` in your web browser. Refresh the page to see the latest "shape" of the market bots.

### Step 4: Record Data for ML (Optional)

In a **separate** terminal, run:

```bash
python aureon_bridge_ml.py
```

## Interpreting the Shapes

- **High Frequency (> 1.0Hz)**: HFT Algos. Often arbitrage or market making.
- **Mid Frequency (0.1 - 1.0Hz)**: "Spoofing" or Layering bots. Re-posting orders to move price.
- **Low Frequency (< 0.1Hz)**: Accumulation/Iceberg bots. Large players buying slowly.
