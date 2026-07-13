# Archive: Aureon Trading on Kraken

Status: This document is an older, Kraken-focused guide. For the current unified engine and run instructions, see [README.md](README.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

This bot now supports the Kraken ecosystem! 🐙

## Setup

1.  **Environment Variables**:
    Create a `.env` file or set these variables:
    ```bash
    EXCHANGE=kraken
    KRAKEN_API_KEY=your_api_key
    KRAKEN_API_SECRET=your_api_secret
    # Optional: Set to false for real trading (use with CAUTION)
    BINANCE_DRY_RUN=true 
    ```

2.  **Dry-Run Testing**:
    You can simulate balances in dry-run mode without API keys:
    ```bash
    export EXCHANGE=kraken
    export BINANCE_DRY_RUN=true
    export DRY_RUN_BALANCE_USDC=1000
    export DRY_RUN_BALANCE_ETH=0.5
    
    python aureon_ultimate.py --dry-run --duration 300
    ```

## Features

*   **Market Data**: Fetches real-time tickers from Kraken public API.
*   **Order Execution**: 
    *   **Dry-Run**: Simulates orders and tracks them in logs.
    *   **Live**: Uses Kraken's `AddOrder` endpoint (Market Orders).
*   **Asset Mapping**: Automatically maps Kraken pairs (e.g., `ETH/USDC`) to Aureon's expected format (`ETHUSDC`).

## Notes

*   The bot defaults to `USDC` as the primary quote asset. Ensure you have USDC or configure `PRIMARY_QUOTE` in `aureon_ultimate.py`.
*   Minimum trade size logic respects Kraken's `ordermin` and `costmin` (min notional) filters.
