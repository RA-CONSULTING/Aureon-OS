"""Offline cache-provenance guard coverage for the real-price fallback."""

import importlib.util
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "aureon" / "observer" / "real_price_fallback.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("_test_real_price_fallback", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _cache(source_timestamp, received_at, *, generated_values=False):
    return {
        "source_timestamp": source_timestamp,
        "received_at": received_at,
        "generated_values": generated_values,
        "data": [{"symbol": "BTC", "current_price": 100.0}],
    }


def test_coingecko_cache_requires_fresh_non_generated_provider_timestamp(tmp_path, monkeypatch):
    fallback = _load_module()
    cache_path = tmp_path / "coingecko_market_cache.json"
    monkeypatch.setattr(fallback, "_COINGECKO_CACHE_PATHS", (cache_path,))
    monkeypatch.setattr(fallback.time, "time", lambda: 1000.0)

    def read(cache):
        cache_path.write_text(json.dumps(cache), encoding="utf-8")
        return fallback._src_coingecko_cache(["BTC"], max_age=10.0)

    assert read(_cache(995.0, 999.0)) == {"BTC/USD": 100.0}
    assert read(_cache(None, 999.0)) == {}
    assert read(_cache(989.9, 999.0)) == {}
    assert read(_cache("malformed", 999.0)) == {}
    assert read(_cache(1006.0, 999.0)) == {}
    assert read(_cache(995.0, 999.0, generated_values=True)) == {}
