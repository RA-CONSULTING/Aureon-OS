"""The live CI job stays off mainnet and does not arm trading."""

from pathlib import Path


def test_live_sandbox_workflow_never_arms_mainnet():
    text = Path(".github/workflows/live-sandbox.yml").read_text(encoding="utf-8")
    assert 'AUREON_LIVE_TRADING: "0"' in text
    assert 'AUREON_DISABLE_REAL_ORDERS: "1"' in text
    assert "https://api.kraken.com" not in text.split("banned")[0]
    assert "https://testnet.binance.vision" in text
    assert "https://api.sandbox.kraken.com" in text
    assert "https://paper-api.alpaca.markets" in text
    assert "-m live" in text
