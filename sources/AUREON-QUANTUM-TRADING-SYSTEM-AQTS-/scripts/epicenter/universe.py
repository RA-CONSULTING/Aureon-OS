import os
import requests

TESTNET = os.getenv('BINANCE_TESTNET', 'false').lower() == 'true'
BASE_URL = "https://testnet.binance.vision/api" if TESTNET else "https://api.binance.com/api"


def fetch_spot_universe(quote_whitelist=None, min_volume_usdt: float = 1000000.0, limit: int = 50):
    """Discover tradable spot symbols filtered by 24h quote volume and quote asset.

    Returns list of symbols sorted by 24h quote volume desc.
    """
    try:
        info = requests.get(f"{BASE_URL}/v3/exchangeInfo", timeout=15).json()
        symbols = [s for s in info.get('symbols', []) if s.get('status') == 'TRADING' and s.get('isSpotTradingAllowed', True)]
        out = []
        for s in symbols:
            sym = s.get('symbol')
            quote = s.get('quoteAsset')
            if quote_whitelist and quote not in quote_whitelist:
                continue
            # 24hr stats
            try:
                t = requests.get(f"{BASE_URL}/v3/ticker/24hr", params={'symbol': sym}, timeout=5)
                if t.status_code == 200:
                    data = t.json()
                    qvol = float(data.get('quoteVolume', '0'))
                    if qvol >= min_volume_usdt:
                        out.append((sym, qvol))
            except Exception:
                pass
        out.sort(key=lambda x: x[1], reverse=True)
        return [s for s,_ in out[:limit]]
    except Exception:
        return []
