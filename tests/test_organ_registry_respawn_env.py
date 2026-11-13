"""A supervisor respawn must give radar/workspace organs the launcher's env.

unity_supervisor is itself launched with SUPPRESSION_ENV (it uses
_launch_env), and it re-imports organ_registry every cycle. The radar and
workspace organ envs are snapshots of os.environ taken at that import, so
without a scrub they inherited AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS=1 and
AUREON_AUDIT_MODE=1 from the supervisor. aureon/launch/master.py builds these
children from its own environment plus the spec env, which carries neither.

A launcher started with AUREON_AUDIT_MODE=1 (a safe audit run) must not
lose it on a respawn: _launch_env records the launcher's own values under
AUREON_PARENT_* and the scrub puts those back.

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


def _supervisor_env(launcher_env):
    """The env unity_supervisor gets from a launcher whose env is launcher_env."""
    with mock.patch.dict(os.environ, launcher_env, clear=True):
        registry = importlib.import_module("aureon_fusion.organ_registry")
        registry = importlib.reload(registry)
        return dict(registry.ORGANS["unity_supervisor"]["env"])


class SupervisorRespawnEnvTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace = tempfile.TemporaryDirectory(prefix="aureon-respawn-env-")
        parent_env = _supervisor_env({"SERO_WORKSPACE": cls.workspace.name})
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


class AuditModeRespawnTests(unittest.TestCase):
    """Buzz's #361 case: a crash mid-audit must not turn audit off."""

    @classmethod
    def setUpClass(cls):
        cls.workspace = tempfile.TemporaryDirectory(prefix="aureon-respawn-audit-")
        launcher_env = {"SERO_WORKSPACE": cls.workspace.name, AUDIT: "1"}
        with mock.patch.dict(os.environ, launcher_env, clear=True):
            registry = importlib.import_module("aureon_fusion.organ_registry")
            registry = importlib.reload(registry)
            cls.first_launch = dict(registry.ORGANS["orca_unified_kill_chain"]["env"])
            cls.supervisor = dict(registry.ORGANS["unity_supervisor"]["env"])
        with mock.patch.dict(os.environ, cls.supervisor, clear=True):
            registry = importlib.reload(registry)
            cls.respawn = dict(registry.ORGANS["orca_unified_kill_chain"]["env"])
            cls.nested_launch = registry._launch_env()
        with mock.patch.dict(os.environ, {"SERO_WORKSPACE": cls.workspace.name}, clear=True):
            importlib.reload(registry)

    @classmethod
    def tearDownClass(cls):
        cls.workspace.cleanup()

    def test_first_launch_keeps_launcher_audit_mode(self):
        self.assertEqual(self.first_launch[AUDIT], "1")
        self.assertNotIn(SUPPRESS, self.first_launch)

    def test_supervisor_records_only_what_the_launcher_had(self):
        self.assertEqual(self.supervisor["AUREON_PARENT_" + AUDIT], "1")
        self.assertNotIn("AUREON_PARENT_" + SUPPRESS, self.supervisor)
        self.assertEqual(self.supervisor[AUDIT], "1")
        self.assertEqual(self.supervisor[SUPPRESS], "1")

    def test_kill_chain_respawn_keeps_launcher_audit_mode(self):
        self.assertEqual(self.respawn[AUDIT], "1")
        self.assertNotIn(SUPPRESS, self.respawn)
        self.assertNotIn("AUREON_PARENT_" + AUDIT, self.respawn)
        self.assertNotIn("AUREON_PARENT_ENV_RECORDED", self.respawn)

    def test_nested_launch_env_keeps_the_launcher_record(self):
        self.assertEqual(self.nested_launch["AUREON_PARENT_" + AUDIT], "1")
        self.assertNotIn("AUREON_PARENT_" + SUPPRESS, self.nested_launch)


if __name__ == "__main__":
    unittest.main()
