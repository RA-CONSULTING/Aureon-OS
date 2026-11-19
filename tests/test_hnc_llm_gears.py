"""The HNC gears turn on an Aureon reply without calling another model."""

import json
import os
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from aureon.core.aureon_lambda_engine import LambdaEngine, SubsystemReading
from aureon.core.aureon_thought_bus import ThoughtBus
from aureon.core.hnc_llm_gears import attach_gears, parse_hnc_object, turn_gears
from aureon.gates.panel import PanelReading


class ParseGearTests(unittest.TestCase):
    def test_json_object_parses(self):
        parsed = parse_hnc_object('note {"claim_class": "C5", "confidence": 0.2} tail')
        self.assertEqual(parsed["claim_class"], "C5")

    def test_fenced_json_parses(self):
        parsed = parse_hnc_object('```json\n{"role": "map"}\n```')
        self.assertEqual(parsed["role"], "map")

    def test_salad_does_not_parse(self):
        self.assertIsNone(parse_hnc_object("signature_validuamuasham **+latingproviders"))


class GearTrainTests(unittest.TestCase):
    def setUp(self):
        self._trace = tempfile.NamedTemporaryFile(delete=False)
        self._trace.close()
        os.environ["AUREON_HNC_TRACE_PATH"] = self._trace.name
        self._history_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._history_dir.cleanup)
        self._empty_panel = PanelReading(
            available=True,
            consensus="NEUTRAL",
            confidence=0.3,
            total=9,
            grounded_inputs=0,
            ungrounded_nodes=("Tiger", "Panda"),
        )

    def tearDown(self):
        os.environ.pop("AUREON_HNC_TRACE_PATH", None)
        try:
            os.remove(self._trace.name)
        except OSError:
            pass

    def _history_receipt(self, samples=20):
        path = Path(self._history_dir.name) / f"lambda-history-{samples}.json"
        engine = LambdaEngine(state_path=path)
        provider_id = "provider:test:measurement-1"
        for index in range(samples):
            engine.step(
                [SubsystemReading("test", 0.4 + (index % 5) * 0.05, 0.9, "live")],
                source_receipt_ids=[provider_id],
                auto_persist=False,
            )
        receipt = engine.save_history(source_receipt_ids=[provider_id])
        self.assertIsNotNone(receipt)
        return receipt

    def _field(self, receipt=None, *, available=True, freshness="fresh"):
        return SimpleNamespace(
            available=available,
            memory_receipt_id=receipt["receipt_id"] if receipt else None,
            memory_canonical_hash=receipt["canonical_hash"] if receipt else None,
            receipt_id="hnc:live_field:test",
            freshness_status=freshness,
            lambda_t=1.25,
            coherence_gamma=0.81,
            symbolic_life_score=0.72,
            consciousness_psi=0.66,
            step=receipt["step_count"] if receipt else None,
            source_timestamp=1_786_400_000.0,
        )

    def _turn_with_field(self, field, history):
        with (
            patch("aureon.core.hnc_field.read_canonical_field", return_value=field),
            patch("aureon.gates.panel.auris_panel", return_value=self._empty_panel) as panel,
            patch("aureon.core.hnc_llm_gears._load_hnc_history", return_value=history),
        ):
            receipt = turn_gears('{"verdict": "supported"}', bus=ThoughtBus())
        self.assertIs(panel.call_args.kwargs["canonical"], field)
        return receipt

    def test_all_four_gears_turn_without_live_evidence(self):
        with patch("aureon.gates.panel.auris_panel", return_value=self._empty_panel):
            receipt = turn_gears("signature_validuamuasham", bus=ThoughtBus())
        names = [gear["name"] for gear in receipt["gears"]]
        self.assertEqual(names, ["parse", "field", "auris", "qgita"])
        self.assertTrue(receipt["all_turned"])
        self.assertFalse(receipt["parsed"])
        by_name = {gear["name"]: gear for gear in receipt["gears"]}
        self.assertFalse(by_name["parse"]["engaged"])
        self.assertFalse(by_name["field"]["engaged"])
        self.assertFalse(by_name["auris"]["engaged"])
        self.assertEqual(by_name["auris"]["total"], 9)
        self.assertEqual(by_name["auris"]["grounded_inputs"], 0)
        self.assertFalse(by_name["qgita"]["engaged"])
        self.assertEqual(by_name["qgita"]["blocker"], "fresh_canonical_field_unavailable")

    def test_nine_default_votes_do_not_engage_auris(self):
        receipt = self._turn_with_field(self._field(available=False), None)
        auris = next(gear for gear in receipt["gears"] if gear["name"] == "auris")
        self.assertTrue(auris["turned"])
        self.assertFalse(auris["engaged"])
        self.assertEqual(auris["total"], 9)
        self.assertEqual(auris["evidence_ratio"], 0.0)

    def test_parse_engages_on_json(self):
        with patch("aureon.gates.panel.auris_panel", return_value=self._empty_panel):
            receipt = turn_gears('{"claim_class": "C5"}', bus=ThoughtBus())
        self.assertTrue(receipt["parsed"])
        self.assertTrue(receipt["gears"][0]["engaged"])

    def test_reply_reuses_precaptured_organism_snapshot(self):
        organism = {
            "all_turned": True,
            "gears": [
                {"name": "field", "turned": True, "engaged": True, "receipt_id": "field-before"},
                {"name": "auris", "turned": True, "engaged": True, "grounded_inputs": 3},
                {"name": "qgita", "turned": True, "engaged": True, "receipt_id": "history-before"},
            ],
        }
        with patch(
            "aureon.core.hnc_llm_gears.capture_organism",
            side_effect=AssertionError("reply must not resample the organism"),
        ):
            receipt = turn_gears('{"verdict": "supported"}', organism=organism)
        self.assertTrue(receipt["parsed"])
        self.assertEqual(receipt["gears"][1]["receipt_id"], "field-before")
        self.assertEqual(receipt["gears"][3]["receipt_id"], "history-before")

    def test_qgita_uses_matching_validated_hnc_history(self):
        history = self._history_receipt()
        receipt = self._turn_with_field(self._field(history), history)
        field = next(gear for gear in receipt["gears"] if gear["name"] == "field")
        qgita = next(gear for gear in receipt["gears"] if gear["name"] == "qgita")
        self.assertEqual(field["lambda_t"], 1.25)
        self.assertEqual(field["coherence_gamma"], 0.81)
        self.assertEqual(field["symbolic_life_score"], 0.72)
        self.assertEqual(field["step"], history["step_count"])
        self.assertTrue(qgita["turned"])
        self.assertTrue(qgita["engaged"])
        self.assertEqual(qgita["samples"], 20)
        self.assertEqual(qgita["receipt_id"], history["receipt_id"])
        self.assertEqual(qgita["canonical_hash"], history["canonical_hash"])
        self.assertEqual(qgita["time_basis"], "hnc_step_index")
        self.assertNotIn("signals", qgita)
        self.assertNotIn("regime", qgita)
        self.assertIs(type(qgita["global_R"]), float)
        json.dumps(receipt, allow_nan=False)

    def test_qgita_rejects_receipt_mismatch(self):
        history = self._history_receipt()
        mismatched = self._field(history)
        mismatched.memory_canonical_hash = "0" * 64
        mismatched.memory_receipt_id = f"hnc:lambda_history:{'0' * 64}"
        receipt = self._turn_with_field(mismatched, history)
        qgita = next(gear for gear in receipt["gears"] if gear["name"] == "qgita")
        self.assertFalse(qgita["engaged"])
        self.assertEqual(qgita["blocker"], "hnc_history_receipt_mismatch")
        self.assertNotIn("global_R", qgita)

    def test_qgita_rejects_tampered_history(self):
        history = self._history_receipt()
        tampered = dict(history)
        tampered["history"] = list(history["history"])
        tampered["history"][0] += 1.0
        receipt = self._turn_with_field(self._field(history), tampered)
        qgita = next(gear for gear in receipt["gears"] if gear["name"] == "qgita")
        self.assertFalse(qgita["engaged"])
        self.assertEqual(qgita["blocker"], "invalid_hnc_history_receipt")

    def test_qgita_rejects_stale_field_without_reading_history(self):
        history = self._history_receipt()
        field = self._field(history, available=False, freshness="stale")
        with (
            patch("aureon.core.hnc_field.read_canonical_field", return_value=field),
            patch("aureon.gates.panel.auris_panel", return_value=self._empty_panel),
            patch(
                "aureon.core.hnc_llm_gears._load_hnc_history",
                side_effect=AssertionError("stale field must not load history"),
            ),
        ):
            receipt = turn_gears("salad", bus=ThoughtBus())
        qgita = next(gear for gear in receipt["gears"] if gear["name"] == "qgita")
        self.assertFalse(qgita["engaged"])
        self.assertEqual(qgita["blocker"], "fresh_canonical_field_unavailable")

    def test_qgita_requires_ten_validated_samples(self):
        history = self._history_receipt(samples=9)
        receipt = self._turn_with_field(self._field(history), history)
        qgita = next(gear for gear in receipt["gears"] if gear["name"] == "qgita")
        self.assertFalse(qgita["engaged"])
        self.assertEqual(qgita["blocker"], "insufficient_hnc_history")
        self.assertEqual(qgita["samples"], 9)

    def test_attach_keeps_the_reply_text(self):
        with patch("aureon.gates.panel.auris_panel", return_value=self._empty_panel):
            body = attach_gears(
                {"choices": [{"message": {"content": "salad"}}]},
                "salad",
                bus=ThoughtBus(),
            )
        self.assertEqual(body["choices"][0]["message"]["content"], "salad")
        self.assertTrue(body["hnc_gears"]["all_turned"])


if __name__ == "__main__":
    unittest.main()
