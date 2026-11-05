# Auris coherence

Source `aureon.utils.aureon_queen_hive_mind.QueenHiveMind.get_auris_coherence`. Loaded 168 closed 1h bars of XBTUSD from public:kraken (https://api.kraken.com/0/public/OHLC), 2026-10-29T19:00:00Z to 2026-11-05T19:00:00Z. Spread input clock: latest public bid/ask print, not an OHLC bar. The four inputs are the measured window statistics in the pack. Key material was not read. No order was sent.
Coherence `0.5023340603593964`. Status `⛔ COHERENCE BREAK - Do not trade`.
Nodes without a reading when the four market fields are present as 0: none.
Series nodes without a reading: none.
Trade readiness: **fail**. paper trade-outcome labels: 166 next-bar close-to-close returns from public:kraken XBTUSD; the prices are measured and the outcomes are paper; filled outcomes: 0; Clownfish readings 166 of 166; Owl readings 166 of 166; nodes without a reading on a labelled bar: Deer; ready-to-trade paper entries: 0; entries with a higher next close: 0; entries without a higher next close: 0; a spread print is used only when its time is at or before the decision close; window call status: ⛔ COHERENCE BREAK - Do not trade; measured fail: get_auris_coherence did not mark any labelled bar ready to trade; release boundary stays HOLD
This coherence is the method's return. It is not a hit rate. Paper labels, when present, are next-bar closes and are not fills.
Release boundary stays HOLD. No order was sent. This is not a claim that the system is alive.
