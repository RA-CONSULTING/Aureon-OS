"""Both live venue clients must rate-limit and cache — checked against their REAL interfaces.

Two defects were in the TEST, not the clients:

* ``test_binance_has_rate_and_cache`` called ``get_binance_client()`` without ever importing
  it — a NameError on every run, so the Binance half never actually ran.
* ``test_kraken_has_rate_and_cache`` asserted Binance's attribute names (``_rate_limiter`` /
  ``_request_cache``) against Kraken. Kraken's protection is real and richer — a tier-based
  dual token bucket (``_private_bucket`` / ``_public_bucket`` mirroring Kraken's decaying
  counter model) plus purpose-specific TTL caches (``_pairs_cache``, ``_balance_cache``) —
  it just never used Binance's names. The assertion produced a permanent false alarm that
  read as "Kraken ships unratelimited", which an audit briefly believed.

The assertions now check the mechanisms each client actually has, and the behaviour that
matters: a cached call must not re-hit the network.
"""
from aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import unittest

from binance_client import BinanceClient, get_binance_client
from kraken_client import KrakenClient, get_kraken_client

assert BinanceClient and KrakenClient  # imported for interface visibility


class TestClientsRateAndCache(unittest.TestCase):
    def test_binance_has_rate_and_cache(self):
        b = get_binance_client()
        if b is None:  # get_binance_client returns Optional — no client is a skip, not a pass
            self.skipTest("Binance client unavailable in this environment")
        self.assertTrue(hasattr(b, '_rate_limiter'))
        self.assertTrue(hasattr(b, '_request_cache'))
        # Monkeypatch session.request to count calls
        calls = {'count': 0}
        def fake_request(method, url, params=None, data=None, timeout=5, **kwargs):
            calls['count'] += 1
            class R:
                status_code = 200
                def json(self):
                    return {'symbols': []}
            return R()
        b.session.request = fake_request
        # First call should call session.request
        b.exchange_info()
        # Second call should be cached (same symbol None) and not call again within TTL
        b.exchange_info()
        self.assertEqual(calls['count'], 1)

    def test_kraken_has_rate_and_cache(self):
        k = get_kraken_client()
        # Kraken's rate limiting: tier-based private/public token buckets. The attributes
        # must exist; the buckets themselves are None only when the rate_limiter lib is
        # absent, in which case the honest check is the attribute contract, not the bucket.
        self.assertTrue(hasattr(k, '_private_bucket'))
        self.assertTrue(hasattr(k, '_public_bucket'))
        self.assertTrue(hasattr(k, '_min_call_interval'))
        # Kraken's caching: purpose-specific TTL caches.
        self.assertTrue(hasattr(k, '_pairs_cache'))
        self.assertTrue(hasattr(k, '_balance_cache'))
        # Behaviour: a cached pairs load must not re-hit the network.
        calls = {'count': 0}
        def fake_get(url, params=None, timeout=20, **kwargs):
            calls['count'] += 1
            class R:
                status_code = 200
                def raise_for_status(self):
                    return
                def json(self):
                    return {'result': {'XXBTZUSD': {'altname': 'XBTUSD', 'wsname': 'XBT/USD'}}}
            return R()
        k.session.get = fake_get
        k._load_asset_pairs(force=True)
        k._load_asset_pairs(force=False)
        self.assertEqual(calls['count'], 1)


if __name__ == '__main__':
    unittest.main()
