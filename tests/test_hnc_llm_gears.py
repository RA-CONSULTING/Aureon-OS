"""The HNC gears turn on an Aureon reply without calling another model."""

import os
import tempfile
import unittest

from aureon.core.aureon_thought_bus import ThoughtBus
from aureon.core.hnc_llm_gears import attach_gears, parse_hnc_object, turn_gears


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

    def tearDown(self):
        os.environ.pop("AUREON_HNC_TRACE_PATH", None)
        try:
            os.remove(self._trace.name)
        except OSError:
            pass

    def test_all_three_gears_turn_on_salad(self):
        receipt = turn_gears("signature_validuamuasham", bus=ThoughtBus())
        names = [gear["name"] for gear in receipt["gears"]]
        self.assertEqual(names, ["parse", "field", "auris"])
        self.assertTrue(receipt["all_turned"])
        self.assertFalse(receipt["parsed"])
        by_name = {gear["name"]: gear for gear in receipt["gears"]}
        self.assertFalse(by_name["parse"]["engaged"])
        self.assertTrue(by_name["field"]["turned"])
        self.assertFalse(by_name["field"]["engaged"])
        self.assertTrue(by_name["auris"]["engaged"])
        self.assertEqual(by_name["auris"]["total"], 9)

    def test_parse_engages_on_json(self):
        receipt = turn_gears('{"claim_class": "C5"}', bus=ThoughtBus())
        self.assertTrue(receipt["parsed"])
        self.assertTrue(receipt["gears"][0]["engaged"])

    def test_attach_keeps_the_reply_text(self):
        body = attach_gears(
            {"choices": [{"message": {"content": "salad"}}]},
            "salad",
            bus=ThoughtBus(),
        )
        self.assertEqual(body["choices"][0]["message"]["content"], "salad")
        self.assertTrue(body["hnc_gears"]["all_turned"])


if __name__ == "__main__":
    unittest.main()
