"""A supervisor respawn must give radar/workspace organs the launcher's env.

unity_supervisor is itself launched with SUPPRESSION_ENV (it uses
_launch_env), and it re-imports organ_registry every cycle. The radar and
workspace organ envs are snapshots of os.environ taken at that import, so
without a scrub they inherited AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS=1 and
AUREON_AUDIT_MODE=1 from the supervisor. aureon/launch/master.py builds these
children from its own environment plus the spec env, which carries neither.

Only variable names are asserted; no env values other than the two
suppression flags are read or printed.
"""

import importlib
import os
import tempfile
import unittest
from unittest import mock

SUPPRESS = "AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS"
AUDIT = "AUREON_AUDIT_MODE"


class SupervisorRespawnEnvTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace = tempfile.TemporaryDirectory(prefix="aureon-respawn-env-")
        parent_env = {
            "SERO_WORKSPACE": cls.workspace.name,
            SUPPRESS: "1",
            AUDIT: "1",
        }
        # Import the registry the way the supervisor does: inside a process
        # whose own environment carries the suppression flags.
        with mock.patch.dict(os.environ, parent_env, clear=True):
            registry = importlib.import_module("aureon_fusion.organ_registry")
            registry = importlib.reload(registry)
            cls.organs = {name: dict(spec.get("env") or {}) for name, spec in registry.ORGANS.items()}
            cls.radar_env = registry._radar_env()
            cls.workspace_env = registry._workspace_env()
            cls.launch_env = registry._launch_env()
            cls.radar_explicit = registry._radar_env({SUPPRESS: "1", AUDIT: "1"})
            cls.suppression = dict(registry.SUPPRESSION_ENV)
        # Leave the module as a clean-env import for any later test.
        with mock.patch.dict(os.environ, {"SERO_WORKSPACE": cls.workspace.name}, clear=True):
            importlib.reload(registry)

    @classmethod
    def tearDownClass(cls):
        cls.workspace.cleanup()

    def test_kill_chain_respawn_env_drops_inherited_suppression(self):
        env = self.organs["orca_unified_kill_chain"]
        self.assertNotIn(SUPPRESS, env)
        self.assertNotIn(AUDIT, env)

    def test_all_plain_radar_and_workspace_organs_drop_inherited_suppression(self):
        for name in (
            "_portfolio_writer_loop",
            "_temporal_refresh_loop",
            "_world_digest_loop",
            "_harmonic_seed_loop",
            "global_energy_aggregator",
            "flight_recorder",
            "bus_bridge",
        ):
            with self.subTest(organ=name):
                env = self.organs[name]
                self.assertNotIn(SUPPRESS, env)
                self.assertNotIn(AUDIT, env)

    def test_helpers_drop_inherited_suppression(self):
        for env in (self.radar_env, self.workspace_env):
            self.assertNotIn(SUPPRESS, env)
            self.assertNotIn(AUDIT, env)

    def test_explicit_entry_values_still_win(self):
        self.assertEqual(self.radar_explicit[SUPPRESS], "1")
        self.assertEqual(self.radar_explicit[AUDIT], "1")
        for name in ("orca_command_center", "unified_market_trader"):
            with self.subTest(organ=name):
                env = self.organs[name]
                self.assertEqual(env[SUPPRESS], "0")
                self.assertEqual(env[AUDIT], "0")

    def test_activation_wave_organs_keep_suppression_env(self):
        self.assertEqual(self.suppression, {SUPPRESS: "1", AUDIT: "1"})
        for key, value in self.suppression.items():
            self.assertEqual(self.launch_env[key], value)
            self.assertEqual(self.organs["unity_supervisor"][key], value)


if __name__ == "__main__":
    unittest.main()
