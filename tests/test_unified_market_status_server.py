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

    def test_env_credential_writer_holds_before_plaintext_or_intent_write(self):
        os.environ.pop("AUREON_HNC_PACKET_MASTER_KEY", None)
        os.environ.pop("HNC_PACKET_MASTER_KEY", None)
        updates = status_server._extract_env_updates(
            "kraken",
            {"krakenApiKey": "new-kraken-key", "krakenApiSecret": "new-kraken-secret"},
        )

        with self.assertRaisesRegex(
            status_server.HNCPacketError,
            status_server.CREDENTIAL_UPDATE_FILESYSTEM_HOLD,
        ):
            status_server._write_env_updates(updates)

        self.assertFalse(status_server.ENV_PATH.exists())
        self.assertFalse(status_server.ENV_UPDATE_INTENT_PATH.exists())
        self.assertFalse(status_server.MARKET_INTENT_PATH.exists())
        self.assertFalse(status_server.HNC_PACKET_EVIDENCE_PATH.exists())

    def test_public_credential_status_holds_before_reading_sources(self):
        captured = {}

        class FakeHandler:
            path = "/api/env-credentials"

            def _json(self, status, payload):
                captured.update({"status": status, "payload": payload})

        original = status_server._env_credentials_status
        status_server._env_credentials_status = lambda: self.fail(
            "public credential status inspected a credential source"
        )
        try:
            status_server.StatusHandler.do_GET(FakeHandler())
        finally:
            status_server._env_credentials_status = original

        self.assertEqual(captured["status"], 403)
        self.assertEqual(
            captured["payload"],
            {"ok": False, "error": status_server.CREDENTIAL_STATUS_READ_HOLD},
        )

    def test_cors_never_grants_nonlocal_or_prefix_confusion_origin(self):
        class FakeHandler:
            def __init__(self, origin):
                self.headers = {"Origin": origin}
                self.emitted = []

            def send_header(self, key, value):
                self.emitted.append((key, value))

        for origin in (
            "https://attacker.invalid",
            "http://localhost.attacker.invalid",
            "http://127.0.0.1.attacker.invalid",
        ):
            handler = FakeHandler(origin)
            status_server.StatusHandler._cors(handler)

            self.assertNotIn(
                "Access-Control-Allow-Origin",
                {key for key, _ in handler.emitted},
            )

    def test_env_credential_writer_holds_before_encrypted_or_evidence_write(self):
        os.environ["AUREON_HNC_PACKET_MASTER_KEY"] = (
            base64.urlsafe_b64encode(b"U" * 32).decode("ascii").rstrip("=")
        )
        updates = status_server._extract_env_updates(
            "kraken",
            {"krakenApiKey": "packet-kraken-key", "krakenApiSecret": "packet-kraken-secret"},
        )

        with self.assertRaisesRegex(
            status_server.HNCPacketError,
            status_server.CREDENTIAL_UPDATE_FILESYSTEM_HOLD,
        ):
            status_server._write_env_updates(updates)

        self.assertFalse(status_server.ENV_PATH.exists())
        self.assertFalse(status_server.HNC_PACKET_EVIDENCE_PATH.exists())

    def test_packetize_env_updates_is_pure_and_metadata_only(self):
        os.environ["AUREON_HNC_PACKET_MASTER_KEY"] = (
            base64.urlsafe_b64encode(b"U" * 32).decode("ascii").rstrip("=")
        )
        updates = {
            "KRAKEN_API_KEY": "packet-kraken-key",
            "KRAKEN_API_SECRET": "packet-kraken-secret",
        }

        stored, encrypted_keys, evidence = status_server._packetize_env_updates(updates)
        rendered = json.dumps(evidence, sort_keys=True)

        self.assertEqual(encrypted_keys, ["KRAKEN_API_KEY", "KRAKEN_API_SECRET"])
        self.assertTrue(all(status_server.is_env_packet(token) for token in stored.values()))
        self.assertNotIn("packet-kraken-key", json.dumps(stored))
        self.assertNotIn("packet-kraken-secret", json.dumps(stored))
        self.assertNotIn("packet-kraken-key", rendered)
        self.assertNotIn("packet-kraken-secret", rendered)
        self.assertTrue(all(token not in rendered for token in stored.values()))
        self.assertFalse(status_server.ENV_PATH.exists())
        self.assertFalse(status_server.HNC_PACKET_EVIDENCE_PATH.exists())
        encryption = status_server._env_credentials_status()["hnc_packet_encryption"]
        self.assertFalse(encryption["enabled"])
        self.assertTrue(encryption["packetization_available"])
        self.assertFalse(encryption["filesystem_write_released"])
        self.assertEqual(
            encryption["release_hold"],
            status_server.CREDENTIAL_UPDATE_FILESYSTEM_HOLD,
        )

    def test_packetize_env_updates_requires_valid_hnc_key_without_raw_fallback(self):
        os.environ.pop("AUREON_HNC_PACKET_MASTER_KEY", None)
        os.environ.pop("HNC_PACKET_MASTER_KEY", None)

        with self.assertRaisesRegex(
            status_server.HNCPacketError,
            "credential_update_requires_valid_hnc_master_key",
        ):
            status_server._packetize_env_updates(
                {"KRAKEN_API_SECRET": "must-not-return-raw"}
            )

        self.assertFalse(status_server.ENV_PATH.exists())
        self.assertFalse(status_server.HNC_PACKET_EVIDENCE_PATH.exists())

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
