"""Isolated process-control tests. Every child launch and live probe is mocked."""
import contextlib
import importlib
import os
import sys
from pathlib import Path
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest import mock


class RegistryStartTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module_workspace = tempfile.TemporaryDirectory(prefix="aureon-registry-import-")
        # Import-time path creation and captured child environments stay inside
        # the test workspace and never inspect runtime credentials.
        with mock.patch.dict(os.environ, {"SERO_WORKSPACE": cls.module_workspace.name}, clear=True):
            cls.registry = importlib.import_module("aureon_fusion.organ_registry")
            cls.supervisor = importlib.import_module("aureon_fusion.unity_supervisor")

    @classmethod
    def tearDownClass(cls):
        cls.module_workspace.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="aureon-registry-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.spec = {"script": "test-only-worker.py", "args": [], "cwd": str(self.root),
                     "mode": "test-only", "log": str(self.root / "worker.log")}
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        patches = {
            "REGISTRY_FILE": self.root / "registry.json", "FUSION_STATE": self.root,
            "ORGANS": {"test_worker": self.spec},
            "_find_running_pid": mock.Mock(return_value=None),
            "_pid_alive": mock.Mock(side_effect=lambda pid, spec=None: pid == 123456),
            "_process_creation_time": mock.Mock(return_value=1234567890.0),
            "_release_granted": mock.Mock(return_value=False),
        }
        for name, value in patches.items():
            self.stack.enter_context(mock.patch.object(self.registry, name, value))
        self.stack.enter_context(mock.patch.object(self.registry.events, "publish_event"))
        self.stack.enter_context(mock.patch.object(self.registry.events, "chirp"))
        self.popen = self.stack.enter_context(mock.patch.object(self.registry.subprocess, "Popen"))
        # No real process API may escape a test, including error paths whose
        # broad exception handler could otherwise hide an accidental probe.
        import psutil
        self.process_guards = []
        for name in ("process_iter", "Process", "pid_exists", "wait_procs"):
            guard = self.stack.enter_context(mock.patch.object(psutil, name,
                side_effect=AssertionError(f"unexpected live psutil.{name} call")))
            self.process_guards.append(guard)
        self.process_guards.append(self.stack.enter_context(mock.patch.object(
            self.registry.subprocess, "run", side_effect=AssertionError("unexpected process command"))))
        # The test exercises atomic replacement and advisory locking, not disk
        # durability. Antivirus/storage flush latency must not decide whether
        # a competing thread reaches its synchronization point.
        self.stack.enter_context(mock.patch.object(self.registry.os, "fsync"))

    def tearDown(self):
        for guard in self.process_guards:
            guard.assert_not_called()

    def test_concurrent_starts_publish_one_pid_and_spawn_one_child(self):
        first_spawned = threading.Event()
        release_spawn = threading.Event()
        second_lock_attempted = threading.Event()
        duplicate_spawn = threading.Event()
        owner = []
        real_acquire = self.registry._acquire_registry_lock

        def acquire(timeout_s=10.0):
            if owner and threading.get_ident() != owner[0]:
                second_lock_attempted.set()
            return real_acquire(timeout_s)

        def spawn(*args, **kwargs):
            if owner:
                duplicate_spawn.set()
            else:
                owner.append(threading.get_ident())
            first_spawned.set()
            if not release_spawn.wait(60):
                raise AssertionError("test spawn was not released")
            return SimpleNamespace(pid=123456)

        self.popen.side_effect = spawn
        with mock.patch.object(self.registry, "_acquire_registry_lock", side_effect=acquire):
            with ThreadPoolExecutor(max_workers=2) as pool:
                first = pool.submit(self.registry.start, "test_worker")
                try:
                    reached_spawn = first_spawned.wait(30)
                    self.assertTrue(reached_spawn, str(first.result()) if first.done() else "mock spawn not reached")
                    second = pool.submit(self.registry.start, "test_worker")
                    self.assertTrue(second_lock_attempted.wait(30), "second start never attempted the registry lock")
                    self.assertFalse(duplicate_spawn.is_set())
                finally:
                    release_spawn.set()
                results = [first.result(timeout=10), second.result(timeout=10)]
        self.assertEqual(self.popen.call_count, 1)
        self.assertEqual({result["state"] for result in results}, {"started", "already_running"})
        self.assertEqual({result["pid"] for result in results}, {123456})
        self.assertEqual(self.registry._read_registry_file()["organs"]["test_worker"]["pid"], 123456)

    def test_lock_conflict_returns_without_scanning_or_spawning(self):
        @contextlib.contextmanager
        def unavailable_lock(*args, **kwargs):
            yield False

        with mock.patch.object(self.registry, "_registry_lock", unavailable_lock), \
                mock.patch.object(self.registry, "_load_registry") as load:
            result = self.registry.start("test_worker")
        self.assertEqual(result["state"], "registry_busy")
        self.assertFalse(result["ok"])
        self.popen.assert_not_called()
        load.assert_not_called()

    def test_load_lock_conflict_returns_snapshot_without_reconciling_or_writing(self):
        @contextlib.contextmanager
        def unavailable_lock(*args, **kwargs):
            yield False

        snapshot = {"organs": {"test_worker": {"pid": 123456}}}
        with mock.patch.object(self.registry, "_registry_lock", unavailable_lock), \
                mock.patch.object(self.registry, "_read_registry_file", return_value=snapshot), \
                mock.patch.object(self.registry, "_save_registry") as save:
            result = self.registry._load_registry()
        self.assertEqual(result["organs"]["test_worker"], {"pid": 123456, "mode": "test-only"})
        self.registry._find_running_pid.assert_not_called()
        self.registry._pid_alive.assert_not_called()
        self.popen.assert_not_called()
        save.assert_not_called()

        with mock.patch.object(self.registry, "_registry_lock", unavailable_lock), \
                mock.patch.object(self.registry, "_read_registry_file", return_value={"organs": {}}), \
                mock.patch.object(self.registry, "_save_registry") as save:
            result = self.registry._load_registry()
        self.assertEqual(result["organs"]["test_worker"], {"mode": "test-only"})
        save.assert_not_called()

    def test_capital_release_and_dormant_gates_still_refuse_spawn(self):
        self.spec["requires_release"] = True
        self.assertEqual(self.registry.start("test_worker")["state"], "held")
        self.spec["dormant"] = True
        self.assertEqual(self.registry.start("test_worker")["state"], "dormant")
        self.popen.assert_not_called()

    def test_windows_wait_denial_rechecks_terminated_process(self):
        import psutil
        process = mock.Mock()
        process.children.return_value = []
        process.create_time.return_value = 1.0
        process.is_running.return_value = False
        with mock.patch.object(psutil, "Process", return_value=process), \
                mock.patch.object(psutil, "wait_procs", side_effect=psutil.AccessDenied(123456)):
            self.assertTrue(self.registry._kill_tree(123456))
        process.terminate.assert_called_once()
        process.kill.assert_not_called()

    def test_windows_wait_denial_does_not_report_unknown_process_dead(self):
        import psutil
        process = mock.Mock()
        process.children.return_value = []
        process.create_time.return_value = 1.0
        process.is_running.side_effect = psutil.AccessDenied(123456)
        with mock.patch.object(psutil, "Process", return_value=process), \
                mock.patch.object(psutil, "wait_procs", side_effect=psutil.AccessDenied(123456)):
            self.assertFalse(self.registry._kill_tree(123456))
        process.kill.assert_called_once()

    def test_supervisor_termination_preserves_independent_children(self):
        import psutil
        process = mock.Mock()
        process.create_time.return_value = 1.0
        with mock.patch.object(psutil, "Process", return_value=process), \
                mock.patch.object(psutil, "wait_procs", return_value=([], [])) as wait:
            self.assertTrue(self.registry._kill_tree(123456, preserve_children=True))
        process.children.assert_not_called()
        process.terminate.assert_called_once()
        process.kill.assert_not_called()
        self.assertEqual(wait.call_args_list[0].args[0], [process])

    def test_supervisor_taskkill_fallback_omits_tree_flag(self):
        with mock.patch.object(self.registry.subprocess, "run") as run, \
                mock.patch.object(self.registry, "_pid_alive", return_value=False):
            self.assertTrue(self.registry._taskkill(123456, preserve_children=True))
        self.assertEqual(run.call_args.args[0], ["taskkill", "/PID", "123456", "/F"])

    def test_process_name_prefilter_does_not_read_unrelated_command_lines(self):
        import psutil
        unrelated = mock.Mock(pid=111, info={"name": "unrelated-windows-process.exe"})
        excluded = mock.Mock(pid=222, info={"name": "python.exe"})
        worker = mock.Mock(pid=333, info={"name": "python.exe"})
        worker.cmdline.return_value = ["python.exe", "-m", "test.worker"]
        different_module = mock.Mock(pid=444, info={"name": "python.exe"})
        different_module.cmdline.return_value = ["python.exe", "-m", "test.worker_other"]
        with mock.patch.object(self.registry, "_excluded_pids", return_value={222}), \
                mock.patch.object(psutil, "process_iter", return_value=[unrelated, excluded, worker, different_module]) as scan:
            self.assertEqual(self.registry._iter_matching_pids({"module": "test.worker"}), [333])
        scan.assert_called_once_with(["name"])
        unrelated.cmdline.assert_not_called()
        excluded.cmdline.assert_not_called()

    def test_prune_duplicate_supervisor_preserves_registered_descendants(self):
        fake_receipts = SimpleNamespace(log_intrusion=mock.Mock())
        package = importlib.import_module("aureon_fusion")
        with mock.patch.object(self.registry, "ORGANS", {"unity_supervisor": self.spec}), \
                mock.patch.object(self.registry, "_load_registry", return_value={"organs": {"unity_supervisor": {"pid": 123456}}}), \
                mock.patch.object(self.registry, "_iter_matching_pids", return_value=[123456, 654321]), \
                mock.patch.object(self.registry, "_kill_tree", return_value=True) as kill, \
                mock.patch.object(package, "receipts", fake_receipts, create=True), \
                mock.patch.dict(sys.modules, {"aureon_fusion.receipts": fake_receipts}):
            result = self.registry.prune()
        kill.assert_called_once_with(654321, preserve_children=True)
        self.assertEqual(result["unity_supervisor"]["kept"], 123456)
        self.assertEqual(result["unity_supervisor"]["killed"], [654321])
        fake_receipts.log_intrusion.assert_called_once()

    def test_supervisor_stale_snapshot_never_stops_a_newly_started_process(self):
        supervisor = self.supervisor
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(supervisor.importlib, "reload", side_effect=lambda module: module))
            stack.enter_context(mock.patch.object(supervisor, "FUSION_STATE", self.root))
            stack.enter_context(mock.patch.object(supervisor, "SUPERVISOR_STATE_FILE", self.root / "supervisor.json"))
            stack.enter_context(mock.patch.object(self.registry, "status_data", return_value={"test_worker": {"state": "stopped", "pid": None}}))
            start = stack.enter_context(mock.patch.object(self.registry, "start", return_value={"ok": True, "organ": "test_worker", "pid": 123456, "state": "already_running"}))
            restart = stack.enter_context(mock.patch.object(self.registry, "restart", side_effect=AssertionError("must not stop a process from a stale snapshot")))
            stop = stack.enter_context(mock.patch.object(self.registry, "stop", side_effect=AssertionError("must not stop a process from a stale snapshot")))
            result = supervisor._supervise_cycle()
        start.assert_called_once_with("test_worker")
        restart.assert_not_called()
        stop.assert_not_called()
        self.assertEqual(result["fleet"][0]["status"], "running")
        self.assertEqual(result["restarts_this_cycle"], [])
        self.assertEqual(result["decisions"][0]["action"], "ensure_running")


class RestartFailureTests(unittest.TestCase):
    def test_failed_stop_never_starts_or_adopts_stale_process(self):
        registry = importlib.import_module("aureon_fusion.organ_registry")
        failed = {"ok": False, "state": "stop_failed", "pid": 123456}
        with mock.patch.object(registry, "stop", return_value=failed), \
                mock.patch.object(registry, "start") as start:
            self.assertEqual(registry.restart("frontend_vite"), failed)
            start.assert_not_called()


if __name__ == "__main__":
    unittest.main()
