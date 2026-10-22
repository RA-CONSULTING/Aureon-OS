import unittest
from unittest.mock import patch

from system_pillar_validator import SystemPillarValidator


class TestSystemPillarValidator(unittest.TestCase):
    @patch("system_pillar_validator.time.sleep", return_value=None)
    def test_all_pillars_active_when_fail_chance_zero(self, _):
        validator = SystemPillarValidator(fail_chance=0.0)
        self.assertTrue(validator.are_all_pillars_active())

    @patch("system_pillar_validator.time.sleep", return_value=None)
    def test_pillars_fail_when_fail_chance_one(self, _):
        validator = SystemPillarValidator(fail_chance=1.0)
        self.assertFalse(validator.are_all_pillars_active())


if __name__ == "__main__":
    unittest.main()
