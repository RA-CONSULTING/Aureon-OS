# Binance Pool Mapping and Miner Setup

This repo’s CPU miner supports SHA‑256 pools (BTC/BCH). Other coins require different algorithms and dedicated miners.

## Pool Endpoints by Coin

- BTC (SHA‑256)
  - Hosts: `sha256.poolbinance.com`
  - Ports: `443`, `1800`, `3333`
  - Worker: `youraccount.001`

- BCH (SHA‑256)
  - Hosts: `bch.poolbinance.com`
  - Ports: `443`, `1800`, `3333`
  - Worker: `youraccount.001`

- ETHW (Etchash) — not supported by this CPU miner
  - Hosts: `ethw.poolbinance.com`
  - Ports: `1800`, `25`, `443`

- ZEC (Equihash) — not supported by this CPU miner
  - Hosts: `zec.poolbinance.com`
  - Ports: `5300`, `5400`, `5500`

- ETC (Etchash) — not supported by this CPU miner
  - Hosts: `etc.poolbinance.com`
  - Ports: `1800`, `25`, `443`

- DASH (X11) — not supported by this CPU miner
  - Hosts: `dash.poolbinance.com`
  - Ports: `443`, `1800`, `3333`

- KAS (kHeavyHash) — not supported by this CPU miner
  - Hosts: `kas.poolbinance.com`
  - Ports: `443`, `1800`, `3333`

## Quick start (BTC via SHA‑256)

Use environment variables to launch the built‑in miner against Binance BTC pool:

```bash
export MINING_POOL_HOST=sha256.poolbinance.com
export MINING_POOL_PORT=443
export MINING_WORKER="youraccount.001"   # format: account.worker
export MINING_PASSWORD="123456"
export MINING_THREADS=4
python3 aureon_miner.py
```

For BCH, change the host:

```bash
export MINING_POOL_HOST=bch.poolbinance.com
export MINING_POOL_PORT=443
export MINING_WORKER="youraccount.001"
export MINING_PASSWORD="123456"
export MINING_THREADS=4
python3 aureon_miner.py
```

Alternatively, run the helper:

```bash
chmod +x mine_live.sh
./mine_live.sh
```

It will prompt for `MINING_WORKER` and default to Binance.

## Earnings Tracking (optional)

Set Binance API keys to enable live wallet reads in the miner’s banner:

```bash
export BINANCE_API_KEY=... 
export BINANCE_API_SECRET=...
```

Then launch as above. The miner will display starting BTC balance and session stats.
