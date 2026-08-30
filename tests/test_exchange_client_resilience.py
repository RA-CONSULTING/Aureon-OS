import os
import sys
import unittest
from unittest.mock import Mock, patch


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EXCHANGES_DIR = os.path.join(REPO_ROOT, "aureon", "exchanges")
if EXCHANGES_DIR not in sys.path:
    sys.path.insert(0, EXCHANGES_DIR)

import alpaca_client as alpaca_mod
import binance_client as binance_mod
import binance_ws_client as binance_ws_mod
import capital_client as capital_mod


class AlpacaClientResilienceTests(unittest.TestCase):
    @patch.dict(os.environ, {
        "ALPACA_API_KEY": "key",
        "ALPACA_SECRET_KEY": "secret",
        "ALPACA_PAPER": "false",
        "ALPACA_DRY_RUN": "false",
    }, clear=False)
    @patch.object(alpaca_mod.requests.Session, "get", side_effect=alpaca_mod.requests.exceptions.ReadTimeout("slow"))
    def test_explicit_auth_timeout_keeps_client_enabled(self, _mock_get):
        client = alpaca_mod.AlpacaClient()

        self.assertTrue(client.is_authenticated)
        self.assertEqual(client.init_error, "")
        self.assertEqual(client.auth_probe_warning, "")

        verified = client.start_auth_probe(background=False)

        self.assertFalse(verified)
        self.assertTrue(client.is_authenticated)
        self.assertEqual(client.init_error, "")
        self.assertIn("slow", client.auth_probe_warning)


class CapitalClientResilienceTests(unittest.TestCase):
    @patch.dict(os.environ, {
        "CAPITAL_API_KEY": "key",
        "CAPITAL_IDENTIFIER": "user",
        "CAPITAL_PASSWORD": "pass",
        "CAPITAL_DEMO": "0",
    }, clear=False)
    @patch.object(capital_mod.requests, "post", side_effect=capital_mod.requests.exceptions.ReadTimeout("slow"))
    def test_initial_session_timeout_does_not_disable_client(self, _mock_post):
        client = capital_mod.CapitalClient()

        self.assertTrue(client.enabled)
        self.assertIn("slow", client.init_error)

    def test_request_without_session_returns_error_response(self):
        client = capital_mod.CapitalClient.__new__(capital_mod.CapitalClient)
        client.enabled = True
        client.base_url = "https://example.com"
        client.init_error = "session_missing"
        client.cst = None
        client.x_security_token = None
        client.session_start_time = 0.0
        client._rate_limit_until = 0.0
        client._rate_limit_logged = False
        client._session_error_logged = False
        client._next_session_retry_at = 0.0
        client._session_is_expired = lambda: True  # type: ignore[method-assign]
        client._create_session = lambda: None  # type: ignore[method-assign]
        client._get_headers = lambda: {}  # type: ignore[method-assign]

        response = client._request("GET", "/markets")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["errorCode"], "session_unavailable")


class BinanceRestClientResilienceTests(unittest.TestCase):
    @staticmethod
    def _client(balance_result):
        client = binance_mod.BinanceClient.__new__(binance_mod.BinanceClient)
        client.uk_mode = False
        client.dry_run = False
        client.get_free_balance = balance_result
        client._signed_request = Mock(side_effect=AssertionError("MARKET endpoint must not be called"))
        return client

    def test_sell_balance_exception_denies_before_market_dispatch(self):
        client = self._client(Mock(side_effect=RuntimeError("provider unavailable")))

        result = client.place_market_order("ETHUSDT", "SELL", quantity=1.25)

        self.assertTrue(result["rejected"])
        self.assertEqual(result["error"], "balance_check_unavailable")
        self.assertEqual(result["truth_status"], "no_data")
        self.assertEqual(result["decision_status"], "denied")
        self.assertFalse(result["generated_values"])
        client._signed_request.assert_not_called()

    def test_sell_nonfinite_balance_receipt_denies_before_market_dispatch(self):
        client = self._client(Mock(return_value=float("nan")))

        result = client.place_market_order("ETHUSDT", "SELL", quantity=1.25)

        self.assertTrue(result["rejected"])
        self.assertEqual(result["truth_status"], "no_data")
        self.assertEqual(result["decision_status"], "denied")
        client._signed_request.assert_not_called()


@unittest.skipIf(
    binance_ws_mod.websocket is None,
    "websocket-client not installed — production guards this import the same way",
)
class BinanceWebSocketClientTests(unittest.TestCase):
    @patch.dict(os.environ, {"BINANCE_WS_DISABLE": "false"}, clear=False)
    @patch.object(binance_ws_mod.websocket, "WebSocketApp")
    @patch.object(binance_ws_mod.threading, "Thread")
    def test_connect_attempts_real_binance_socket_when_not_disabled(self, mock_thread, mock_ws_app):
        thread_instance = Mock()
        mock_thread.return_value = thread_instance
        client = binance_ws_mod.BinanceWebSocketClient()
        client.subscriptions.add("btcusdt@ticker")

        client._connect()

        mock_ws_app.assert_called_once()
        mock_thread.assert_called_once()
        thread_instance.start.assert_called_once()


if __name__ == "__main__":
    unittest.main()
