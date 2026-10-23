import unittest

from alfie_thruster import ALFIEThrusterController


PROMPT = "Maintain 500N vertical thrust with maximum efficiency and coherence."
INTENT = "love + pride"


class TestALFIEThrusterController(unittest.TestCase):
    def setUp(self) -> None:
        self.controller = ALFIEThrusterController()

    def test_love_pride_stabilization(self) -> None:
        report = self.controller.execute_prompt(PROMPT, INTENT)

        self.assertTrue(report.ok)
        gamma_delta = report.details["gamma_delta"]
        self.assertAlmostEqual(gamma_delta, 0.04, delta=0.01)
        self.assertLess(report.details["thrust_ripple_percent"], 1.5)
        self.assertEqual(report.details["target_thrust"], 500.0)

    def test_thermal_derating_drill(self) -> None:
        self.controller.execute_prompt(PROMPT, INTENT)
        report = self.controller.simulate_thermal_derating(coil_temperature_c=95.0)

        self.assertTrue(report.ok)
        self.assertLess(report.details["response_time_ms"], 10.0)
        self.assertLess(report.details["derated_thrust"], 500.0)
        self.assertIn("coil_T", report.notes[0])

    def test_communication_loss(self) -> None:
        self.controller.execute_prompt(PROMPT, INTENT)
        report = self.controller.simulate_communication_drop(outage_ms=300)

        self.assertTrue(report.ok)
        self.assertLess(report.details["max_deviation_percent"], 1.0)
        log = self.controller.export_log()
        self.assertTrue(any("Communication drop" in entry for entry in log))
        self.assertTrue(any("Link restored" in entry for entry in log))


if __name__ == "__main__":
    unittest.main()

