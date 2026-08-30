from aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import unittest
from datetime import datetime, timezone
from alpaca_client import AlpacaClient

class TestAlpacaQuoteFallback(unittest.TestCase):
    def test_crypto_fallback_when_stock_empty(self):
        c = AlpacaClient()
        # Monkeypatch _request to simulate stock endpoint returning empty and crypto endpoint
        # returning quotes. The real _request now also takes request_type= (rate-bucket
        # discriminator), so the fake must swallow extra kwargs or every call TypeErrors,
        # gets caught by get_last_quote's broad except, and the test fails on {}.
        def fake_request(method, endpoint, params=None, json=None, base_url=None, **kwargs):
            if endpoint.startswith('/v2/stocks/'):
                return {}  # simulate 404/no-data
            if endpoint.startswith('/v1beta3/crypto'):
                # mimic the crypto quotes payload
                observed_at = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
                return {'BTC/USD': {'bp': 97000.0, 'ap': 97100.0, 't': observed_at}}
            return {}
        c._request = fake_request
        res = c.get_last_quote('BTCUSD')
        self.assertIn('last', res)
        self.assertAlmostEqual(res['last']['price'], 97050.0)

    def test_stock_quote_uses_stock_endpoint(self):
        c = AlpacaClient()
        def fake_request(method, endpoint, params=None, json=None, base_url=None, **kwargs):
            if endpoint.startswith('/v2/stocks/'):
                observed_at = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
                return {'quote': {'bp': 100.0, 'ap': 102.0, 't': observed_at}}
            return {}
        c._request = fake_request
        res = c.get_last_quote('AAPL')
        self.assertIn('last', res)
        self.assertAlmostEqual(res['last']['price'], 101.0)

if __name__ == '__main__':
    unittest.main()
