import ast
from pathlib import Path


def test_btc_v2_provider_defaults_are_removed_and_paths_fail_closed():
    source = (Path(__file__).resolve().parents[1] / 'aureon' / 'trading' / 'aureon_btc_v2.py').read_text(encoding='utf-8')
    ast.parse(source)
    assert 'ticker.get(\'lastPrice\', 91000)' not in source
    for field in ('priceChangePercent', 'quoteVolume', 'lastPrice'):
        assert f"ticker.get('{field}', 0)" not in source
    assert "if btc_price is None:\n            return False" in source
    assert "if btc_price is None:\n            return" in source
