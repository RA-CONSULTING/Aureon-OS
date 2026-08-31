import base64
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
EXCHANGES_DIR = REPO_ROOT / "aureon" / "exchanges"
if str(EXCHANGES_DIR) not in sys.path:
    sys.path.insert(0, str(EXCHANGES_DIR))

import unified_market_status_server as status_server


class UnifiedMarketStatusServerFlightTestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state_root = Path(self.tmp.name)
        self.old_status_path = status_server.STATUS_PATH
        self.old_intent_path = status_server.MARKET_INTENT_PATH
        self.old_env_path = status_server.ENV_PATH
        self.old_env_update_intent_path = status_server.ENV_UPDATE_INTENT_PATH
        self.old_hnc_packet_evidence_path = status_server.HNC_PACKET_EVIDENCE_PATH
        status_server.STATUS_PATH = self.state_root / "unified_runtime_status.json"
        status_server.MARKET_INTENT_PATH = self.state_root / "aureon_market_reboot_intent.json"
        status_server.ENV_PATH = self.state_root / ".env"
        status_server.ENV_UPDATE_INTENT_PATH = self.state_root / "aureon_env_update_intent.json"
        status_server.HNC_PACKET_EVIDENCE_PATH = self.state_root / "aureon_hnc_quantum_packet_last_run.json"
        self.old_secret_env = {
            key: os.environ.get(key)
            for key in (
                "KRAKEN_API_KEY",
                "KRAKEN_API_SECRET",
                "BINANCE_API_KEY",
                "BINANCE_API_SECRET",
                "ALPACA_API_KEY",
                "ALPACA_SECRET_KEY",
                "CAPITAL_API_KEY",
                "CAPITAL_IDENTIFIER",
                "CAPITAL_PASSWORD",
                "AUREON_HNC_PACKET_MASTER_KEY",
                "HNC_PACKET_MASTER_KEY",
            )
        }
        self.old_env = {
            key: os.environ.get(key)
            for key in (
                "AUREON_MARKET_DOWNTIME_DAYS",
                "AUREON_MARKET_DOWNTIME_START_LOCAL",
                "AUREON_MARKET_DOWNTIME_END_LOCAL",
            )
        }
        os.environ["AUREON_MARKET_DOWNTIME_DAYS"] = "*"
        os.environ["AUREON_MARKET_DOWNTIME_START_LOCAL"] = "00:00"
        os.environ["AUREON_MARKET_DOWNTIME_END_LOCAL"] = "23:59"

    def tearDown(self):
        status_server.STATUS_PATH = self.old_status_path
        status_server.MARKET_INTENT_PATH = self.old_intent_path
        status_server.ENV_PATH = self.old_env_path
        status_server.ENV_UPDATE_INTENT_PATH = self.old_env_update_intent_path
        status_server.HNC_PACKET_EVIDENCE_PATH = self.old_hnc_packet_evidence_path
        for key, value in self.old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        for key, value in self.old_secret_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tmp.cleanup()

    def _write_status(self, open_positions: int, stale: bool = False):
        payload = {
            "ok": not stale,
            "trading_ready": True,
            "data_ready": True,
            "stale": stale,
            "combined": {"open_positions": open_positions},
            "exchanges": {"kraken_ready": True, "capital_ready": True},
        }
        status_server.STATUS_PATH.write_text(json.dumps(payload), encoding="utf-8")

    def _write_pending_intent(self):
        payload = {"status": "pending", "surface": "market", "reason": "test"}
        status_server.MARKET_INTENT_PATH.write_text(json.dumps(payload), encoding="utf-8")

    def test_flight_test_holds_restart_when_open_positions_exist(self):
        self._write_status(open_positions=2)
        self._write_pending_intent()

        flight = status_server._flight_test()

        self.assertTrue(flight["checks"]["pending_restart"])
        self.assertTrue(flight["checks"]["open_positions"])
        self.assertFalse(flight["reboot_advice"]["can_reboot_now"])
        self.assertEqual(flight["reboot_advice"]["reason"], "open_positions_reported")

    def test_flight_test_reports_stale_tick_with_open_positions_as_position_monitor_hold(self):
        self._write_status(open_positions=2, stale=True)

        flight = status_server._flight_test()

        self.assertFalse(flight["checks"]["tick_fresh"])
        self.assertTrue(flight["checks"]["heartbeat_fresh_but_tick_stale"])
        self.assertFalse(flight["reboot_advice"]["can_reboot_now"])
        self.assertEqual(flight["reboot_advice"]["decision"], "hold_monitor_positions")
        self.assertEqual(flight["reboot_advice"]["reason"], "runtime_tick_stale_with_open_positions")
        self.assertEqual(
            flight["reboot_advice"]["recovery_action"],
            "preserve_position_monitoring_and_defer_restart_until_flat_downtime",
        )

    def test_flight_test_allows_pending_restart_when_flat_in_window(self):
        self._write_status(open_positions=0)
        self._write_pending_intent()

        flight = status_server._flight_test()

        self.assertTrue(flight["checks"]["downtime_window"])
        self.assertFalse(flight["checks"]["open_positions"])
        self.assertTrue(flight["reboot_advice"]["can_reboot_now"])

    def test_env_credentials_status_reports_presence_without_secret_values(self):
        status_server.ENV_PATH.write_text(
            "KRAKEN_API_KEY=kraken-key\nKRAKEN_API_SECRET=kraken-secret-value\n",
            encoding="utf-8",
        )

        status = status_server._env_credentials_status()

        self.assertTrue(status["exchanges"]["kraken"]["present"])
        self.assertEqual(status["exchanges"]["kraken"]["keys"]["KRAKEN_API_SECRET"]["length"], len("kraken-secret-value"))
        self.assertNotIn("kraken-secret-value", json.dumps(status))
        self.assertEqual(status["secret_policy"], "metadata_only_no_values_returned")

    def test_env_credential_update_writes_env_and_marks_restart_required(self):
        os.environ.pop("AUREON_HNC_PACKET_MASTER_KEY", None)
        os.environ.pop("HNC_PACKET_MASTER_KEY", None)
        updates = status_server._extract_env_updates(
            "kraken",
            {"krakenApiKey": "new-kraken-key", "krakenApiSecret": "new-kraken-secret"},
        )
        result = status_server._write_env_updates(updates)
        intent = status_server._record_env_update_intent("kraken", result["updated_keys"])

        env_text = status_server.ENV_PATH.read_text(encoding="utf-8")
        status = status_server._env_credentials_status()

        self.assertIn("KRAKEN_API_KEY=new-kraken-key", env_text)
        self.assertIn("KRAKEN_API_SECRET=new-kraken-secret", env_text)
        self.assertEqual(intent["status"], "pending")
        self.assertTrue(status["restart_required"])
        self.assertTrue(status_server.MARKET_INTENT_PATH.exists())
        self.assertNotIn("new-kraken-secret", json.dumps(status))

    def test_env_credential_update_packet_encrypts_when_hnc_master_key_present(self):
        os.environ["AUREON_HNC_PACKET_MASTER_KEY"] = (
            base64.urlsafe_b64encode(b"U" * 32).decode("ascii").rstrip("=")
        )
        updates = status_server._extract_env_updates(
            "kraken",
            {"krakenApiKey": "packet-kraken-key", "krakenApiSecret": "packet-kraken-secret"},
        )
        result = status_server._write_env_updates(updates)

        env_text = status_server.ENV_PATH.read_text(encoding="utf-8")
        status = status_server._env_credentials_status()

        self.assertIn("KRAKEN_API_KEY=hncqp1:", env_text)
        self.assertIn("KRAKEN_API_SECRET=hncqp1:", env_text)
        self.assertNotIn("packet-kraken-secret", env_text)
        self.assertEqual(result["hnc_packet_encrypted_keys"], ["KRAKEN_API_KEY", "KRAKEN_API_SECRET"])
        self.assertTrue(status["hnc_packet_encryption"]["enabled"])
        self.assertTrue(status["hnc_packet_encryption"]["master_key_valid"])
        self.assertEqual(status["hnc_packet_encryption"]["encoded_key_count"], 2)
        self.assertTrue(status_server.HNC_PACKET_EVIDENCE_PATH.exists())

    def test_env_status_does_not_report_malformed_hnc_key_as_enabled(self):
        os.environ["AUREON_HNC_PACKET_MASTER_KEY"] = "not a canonical base64url key"

        status = status_server._env_credentials_status()
        encryption = status["hnc_packet_encryption"]

        self.assertTrue(encryption["master_key_present"])
        self.assertFalse(encryption["master_key_valid"])
        self.assertFalse(encryption["enabled"])
        self.assertEqual(encryption["configuration_error"], "hnc_master_key_invalid")
        self.assertNotIn(os.environ["AUREON_HNC_PACKET_MASTER_KEY"], json.dumps(status))

    def test_flight_test_treats_env_update_as_pending_restart(self):
        self._write_status(open_positions=0)
        status_server._record_env_update_intent("binance", ["BINANCE_API_KEY"])

        flight = status_server._flight_test()

        self.assertTrue(flight["checks"]["pending_restart"])
        self.assertTrue(flight["reboot_advice"]["can_reboot_now"])
        self.assertEqual(flight["env_update_intent"]["exchange"], "binance")


if __name__ == "__main__":
    unittest.main()
