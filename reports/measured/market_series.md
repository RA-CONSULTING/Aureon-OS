# Public market series

Read-only bars for the brain proof. No exchange key was read. No order was sent. Live autonomy stays off. This is not a claim that the system is conscious or alive.

Verdict: **loaded**. Evidence tag `measured`.
Key group `public:kraken`. Key material `none`.
Source `https://api.kraken.com/0/public/OHLC` symbol `XBTUSD` interval `1h` venue interval `60`.
OHLC time range `2026-10-29T19:00:00Z` to `2026-11-05T19:00:00Z` (168 closed bars). ohlc bar open time; end is the last kept bar open time plus the interval
Spread source `https://api.kraken.com/0/public/Spread`. Spread time range `2026-11-05T19:41:24Z` to `2026-11-05T19:41:53Z` (250 prints). This is the venue's recent spread window, not a print for every OHLC bar.
The last venue bar is dropped because the public candle response includes the in-progress bar.

Fetch attempts, public endpoints only:
- `binance` `https://api.binance.com/api/v3/klines` status `451` used `False` error `HTTPError`.
- `kraken` `https://api.kraken.com/0/public/OHLC` status `200` used `True` error `None`.
- `kraken` `https://api.kraken.com/0/public/Spread` status `200` used `True` error `None`.

Auris inputs are one window texture, not a substitute for a missing node:
- `volatility` `0.0057184012087201355` tag `measured`. mean of (high - low) / ((high + low) / 2) over the closed bars. Clock: ohlc window.
- `momentum` `-0.05910772427954495` tag `measured`. (last close - first close) / first close. Clock: ohlc window, first close to last close.
- `volume` `0.2448478811568242` tag `measured`. last bar base volume / max base volume in the closed window. Clock: ohlc window.
- `spread` `4.9876097274178236e-05` tag `measured`. (ask - bid) / ((ask + bid) / 2) of the latest print. Clock: latest public bid/ask print, not an OHLC bar.

Per-bar `range_fraction` and `return` are on the bars. The first bar has no return. Nothing missing is filled with zero.
Filled trade outcomes are not in this pack. Brain proof derives paper labels from these bar returns. Signal-in-noise labels: **HOLD**. Release boundary: **HOLD**.

JSON is the harness input. The CSV files are the same bars and the same spread prints.

Live fetch, public endpoints only:

```bash
AUREON_DISABLE_REAL_ORDERS=1 PYTHONPATH=. python3 -m aureon.evaluation.market_series --out reports/measured
```

Check the file already on disk, without fetching:

```bash
PYTHONPATH=. python3 -m aureon.evaluation.market_series --check --out reports/measured
```
