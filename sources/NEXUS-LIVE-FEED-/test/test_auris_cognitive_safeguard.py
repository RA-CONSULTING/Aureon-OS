import unittest
from auris_cognitive_safeguard import CognitiveCoherenceFilter

class TestCognitiveCoherenceFilter(unittest.TestCase):

    def test_no_hazard(self):
        safeguard = CognitiveCoherenceFilter(
            hazard_threshold_kw_per_s=25.0,
            dampening_factor=1.0,
            authorized_temporal_id="alpha",
        )
        sample_data = [
            {"temporal_id": "alpha", "output_power_kw": 0.0, "simulation_time_s": 0.0},
            {"temporal_id": "alpha", "output_power_kw": 10.0, "simulation_time_s": 1.0},
            {"temporal_id": "alpha", "output_power_kw": 20.0, "simulation_time_s": 2.0},
        ]
        processed_data = list(safeguard.process_stream(sample_data))
        self.assertEqual(len(processed_data), 3)
        for point in processed_data:
            self.assertTrue(point["is_stable"])
            self.assertFalse(point["cognitive_safeguard_active"])

    def test_hazard_dampening(self):
        safeguard = CognitiveCoherenceFilter(
            hazard_threshold_kw_per_s=25.0,
            dampening_factor=0.5,
            authorized_temporal_id="alpha",
        )
        sample_data = [
            {"temporal_id": "alpha", "output_power_kw": 10.0, "simulation_time_s": 0.0},
            {"temporal_id": "alpha", "output_power_kw": 60.0, "simulation_time_s": 1.0}, # 50 kW/s change
        ]
        processed_data = list(safeguard.process_stream(sample_data))
        self.assertEqual(len(processed_data), 2)
        self.assertTrue(processed_data[0]["is_stable"])
        self.assertFalse(processed_data[1]["is_stable"])
        self.assertTrue(processed_data[1]["cognitive_safeguard_active"])
        # Expected dampened power = 10.0 + 0.5 * 25.0 * 1.0 * 1 = 22.5
        self.assertEqual(processed_data[1]["output_power_kw"], 22.5)

    def test_unauthorized_temporal_id(self):
        safeguard = CognitiveCoherenceFilter(authorized_temporal_id="alpha")
        sample_data = [
            {"temporal_id": "alpha", "output_power_kw": 10.0, "simulation_time_s": 0.0},
            {"temporal_id": "beta", "output_power_kw": 20.0, "simulation_time_s": 1.0},
        ]
        processed_data = list(safeguard.process_stream(sample_data))
        self.assertEqual(len(processed_data), 1)
        self.assertEqual(processed_data[0]["temporal_id"], "alpha")

    def test_missing_keys(self):
        safeguard = CognitiveCoherenceFilter(authorized_temporal_id="alpha")
        sample_data = [
            {"temporal_id": "alpha", "output_power_kw": 10.0}, # missing simulation_time_s
            {"temporal_id": "alpha", "simulation_time_s": 1.0}, # missing output_power_kw
        ]
        processed_data = list(safeguard.process_stream(sample_data))
        self.assertEqual(len(processed_data), 0)

if __name__ == '__main__':
    unittest.main()