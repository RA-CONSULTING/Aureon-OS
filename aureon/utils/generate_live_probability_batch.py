#!/usr/bin/env python3
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import time
import json
from datetime import datetime
import numpy as np

os.environ.setdefault('LIVE','1')

from aureon.exchanges.binance_client import BinanceClient, get_binance_client
from aureon.strategies.hnc_probability_matrix import HNCProbabilityIntegration

# 🔶 COMPREHENSIVE BINANCE SYMBOLS (70+)
DEFAULT_SYMBOLS = [
    # === TOP TIER ===
    'BTCUSDC', 'ETHUSDC', 'SOLUSDC', 'XRPUSDC', 'ADAUSDC', 'AVAXUSDC', 'BNBUSDC',
    'DOTUSDC', 'ATOMUSDC', 'NEARUSDC', 'ICPUSDC', 'APTUSDC', 'SUIUSDC', 'SEIUSDC', 'TIAUSDC',
    # === LAYER 2s ===
    'ARBUSDC', 'OPUSDC', 'MATICUSDC', 'STXUSDC', 'IMXUSDC',
    # === DEFI ===
    'UNIUSDC', 'AAVEUSDC', 'LINKUSDC', 'CRVUSDC', 'SNXUSDC', 'LDOUSDC', 'PENDLEUSDC',
    'MKRUSDC', 'COMPUSDC', 'DYDXUSDC', 'GRTUSDC', 'ENSUSDC',
    # === AI & DATA ===
    'FETUSDC', 'RENDERUSDC', 'INJUSDC', 'WLDUSDC', 'PYTHUSDC', 'JTOUSDC', 'ONDOUSDC',
    # === GAMING ===
    'AXSUSDC', 'MANAUSDC', 'SANDUSDC', 'GALAUSDC', 'FLOWUSDC', 'GMTUSDC',
    # === MEMECOINS ===
    'DOGEUSDC', 'SHIBUSDC', 'PEPEUSDC', 'BONKUSDC', 'FLOKIUSDC', 'WIFUSDC', 'TRUMPUSDC',
    # === MID CAPS ===
    'LTCUSDC', 'ETCUSDC', 'FILUSDC', 'ALGOUSDC', 'XLMUSDC', 'TRXUSDC', 'HBARUSDC',
    'QNTUSDC', 'KAVAUSDC', 'RUNEUSDC', 'MOVEUSDC', 'JUPUSDC',
    # === EMERGING ===
    'APEUSDC', 'CHZUSDC', 'MASKUSDC', 'JASMYUSDC', 'ZRXUSDC',
]

def collect_baseline(client: BinanceClient, symbol: str, samples: int = 5, interval: float = 0.2):
    prices = []
    for _ in range(samples):
        t = client.get_24h_ticker(symbol)
        p = float(t.get('lastPrice', 0))
        prices.append(p)
        time.sleep(interval)
    start, end = prices[0], prices[-1]
    momentum = ((end - start) / start) * 100 if start > 0 else 0.0
    phi = (1 + 5 ** 0.5) / 2
    ratio = end / start if start > 0 else 1.0
    freq = max(256.0, min(963.0, 432.0 * (ratio ** phi)))
    std = float(np.std(prices))
    coherence = max(0.2, min(0.95, 1.0 / (1.0 + std / max(1.0, end))))
    is_harmonic = abs(freq - 528) < 25
    return end, freq, momentum, coherence, is_harmonic


def main():
    client = get_binance_client()
    integration = HNCProbabilityIntegration()

    symbols = DEFAULT_SYMBOLS
    results = []

    print(f"\nGenerating probability matrices for {len(symbols)} symbols...")
    for i, symbol in enumerate(symbols, start=1):
        try:
            price, freq, momentum, coherence, is_harmonic = collect_baseline(client, symbol)
            matrix = integration.update_and_analyze(symbol, price, freq, momentum, coherence, is_harmonic)
            signal = integration.get_trading_signal(symbol)
            results.append({
                'symbol': symbol,
                'probability': float(signal['probability']),
                'confidence': float(signal['confidence']),
                'action': signal['action'],
                'modifier': signal['modifier'],
                'reason': signal['reason'],
                'frequency': float(matrix.hour_plus_1.avg_frequency),
                'state': matrix.hour_plus_1.state.value,
            })
            print(f"[{i}/{len(symbols)}] {symbol}: {signal['action']} | prob={float(signal['probability']):.2%} conf={float(signal['confidence']):.2%}")
        except Exception as e:
            print(f"[{i}/{len(symbols)}] {symbol}: ERROR {e}")
            continue

    # Aggregate top opportunities
    results.sort(key=lambda r: (r['probability'], r['confidence']), reverse=True)

    print("\nTop Opportunities:")
    for r in results[:10]:
        print(f"  {r['symbol']:10s} | {r['action']:12s} | prob={r['probability']:.0%} conf={r['confidence']:.0%} | {r['state']:12s} | {r['frequency']:.0f}Hz")

    # Save report
    report = {
        'generated_at': datetime.now().isoformat(),
        'count': len(results),
        'top_10': results[:10],
        'all': results,
    }
    out_path = 'probability_batch_report.json'
    with open(out_path, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"\nSaved report -> {out_path}")


if __name__ == '__main__':
    main()
