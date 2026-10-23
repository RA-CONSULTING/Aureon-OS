"""The live CI job stays off mainnet and does not arm trading."""

from pathlib import Path


def test_live_sandbox_workflow_never_arms_mainnet():
    text = Path(".github/workflows/live-sandbox.yml").read_text(encoding="utf-8")
    configured = text.split("steps:", 1)[0]
    assert 'AUREON_LIVE_TRADING: "0"' in configured
    assert 'AUREON_DISABLE_REAL_ORDERS: "1"' in configured
    assert "https://api.kraken.com" not in configured
    assert "https://api.binance.com" not in configured
    assert "https://api.alpaca.markets" not in configured
    assert "https://testnet.binance.vision" in configured
    assert "https://api.sandbox.kraken.com" in configured
    assert "https://paper-api.alpaca.markets" in configured
    assert "-m live" in text
    assert 'if [ "$code" -eq 5 ]' in text
