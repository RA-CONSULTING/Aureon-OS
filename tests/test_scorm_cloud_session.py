from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from aureon.autonomous.aureon_governed_desktop_gateway import (
    GovernedDesktopGateway,
    WindowInfo,
)
from aureon.operator import scorm_cloud_session as session_module
from aureon.operator.scorm_cloud_session import (
    EdgeProfileSpec,
    EdgeWindowRecord,
    LaunchedEdgeProcess,
    PsutilProcessInspector,
    SCORMCloudSessionError,
    SCORMCloudSessionRunner,
    SCORMEvidenceLedger,
    SubprocessEdgeLauncher,
    build_scorm_cloud_edge_plan,
    detect_scorm_access_blocker,
)

SECRET = b"scorm-window-session-secret-at-least-32-bytes"
SCORM_URL = "https://cloud.scorm.com/launch/course?token=signed-value-123"
TITLE = "Workplace Safety - SCORM Cloud - Microsoft Edge"
TITLE_PATTERN = r"^.+ - SCORM Cloud - Microsoft Edge$"


class FakeClock:
    def __init__(self) -> None:
        self.current = datetime(2026, 8, 16, 12, 0, tzinfo=UTC)
        self.tick = 10.0

    def now(self) -> datetime:
        return self.current

    def monotonic(self) -> float:
        return self.tick

    def sleep(self, seconds: float) -> None:
        self.tick += seconds
        self.current += timedelta(seconds=seconds)


class FakeWindowController:
    def __init__(self, records: list[EdgeWindowRecord] | None = None) -> None:
        self.records = list(records or [])
        self.foreground: WindowInfo | None = None
        self.foreground_calls: list[WindowInfo] = []
        self.close_calls: list[WindowInfo] = []

    def snapshot_windows(self) -> list[EdgeWindowRecord]:
        return list(self.records)

    def foreground_exact(self, window: WindowInfo) -> WindowInfo:
        assert any(record.window == window for record in self.records)
        self.foreground_calls.append(window)
        self.foreground = window
        return window

    def foreground_window(self) -> EdgeWindowRecord:
        assert self.foreground is not None
        matching = [record for record in self.records if record.window == self.foreground]
        assert len(matching) == 1
        return matching[0]

    def close_exact(self, window: WindowInfo) -> bool:
        matching = [record for record in self.records if record.window.handle == window.handle]
        if not matching:
            return False
        assert len(matching) == 1
        assert matching[0].window == window
        self.close_calls.append(window)
        self.records.remove(matching[0])
        if self.foreground == window:
            self.foreground = None
        return True


class FakeGatewayBackend:
    def __init__(self, controller: FakeWindowController) -> None:
        self.controller = controller

    def foreground_window(self) -> WindowInfo:
        assert self.controller.foreground is not None
        return self.controller.foreground


class FakeLauncher:
    def __init__(self, on_launch, *, process_id: int = 9000) -> None:
        self.on_launch = on_launch
        self.process_id = process_id
        self.plans = []
        self.cleanup_calls: list[tuple[LaunchedEdgeProcess, bool]] = []

    def launch(self, plan):
        self.plans.append(plan)
        self.on_launch()
        return LaunchedEdgeProcess(
            process_id=self.process_id,
            launched_at_utc="2026-08-16T12:00:00Z",
        )

    def cleanup(
        self,
        launched: LaunchedEdgeProcess,
        *,
        terminate_owned_process: bool,
    ) -> None:
        self.cleanup_calls.append((launched, terminate_owned_process))


class FakeProcessInspector:
    def __init__(
        self,
        parents: dict[int, int | None],
        *,
        executable: str = "",
        profile_matches: bool = True,
    ) -> None:
        self.parents = parents
        self.executable = executable
        self.profile_matches = profile_matches

    def is_same_process_or_descendant(
        self,
        process_id: int,
        *,
        ancestor_process_id: int,
    ) -> bool:
        current: int | None = process_id
        seen: set[int] = set()
        while current is not None and current not in seen:
            if current == ancestor_process_id:
                return True
            seen.add(current)
            current = self.parents.get(current)
        return False

    def process_executable(self, process_id: int) -> str:
        assert process_id in self.parents
        return self.executable

    def process_profile_matches(
        self,
        process_id: int,
        *,
        user_data_dir: str,
        profile_directory: str,
    ) -> bool:
        assert process_id in self.parents
        assert user_data_dir
        assert profile_directory
        return self.profile_matches


def edge_executable(tmp_path: Path) -> Path:
    executable = tmp_path / "msedge.exe"
    executable.write_bytes(b"hermetic-edge-fixture")
    return executable


def test_plan_accepts_exact_google_chrome_executable(tmp_path: Path) -> None:
    executable = tmp_path / "chrome.exe"
    executable.write_bytes(b"exact-chrome-binary")

    plan = build_scorm_cloud_edge_plan(
        exact_url=SCORM_URL,
        edge_executable=executable,
        profile=EdgeProfileSpec.isolated(tmp_path / "fresh-chrome-profile"),
        local_model="qwen2.5vl:3b",
        local_model_endpoint="http://127.0.0.1:11434",
        expected_initial_title_regex=r"^Hazardous Waste Awareness - Google Chrome$",
        allowed_title_regex=r"^Hazardous Waste Awareness - Google Chrome$",
    )

    assert plan.edge_executable == str(executable.resolve())


def test_plan_rejects_non_chromium_executable(tmp_path: Path) -> None:
    executable = tmp_path / "firefox.exe"
    executable.write_bytes(b"not-a-supported-browser")

    with pytest.raises(
        SCORMCloudSessionError,
        match="exact_chromium_executable_required",
    ):
        build_scorm_cloud_edge_plan(
            exact_url=SCORM_URL,
            edge_executable=executable,
            profile=EdgeProfileSpec.isolated(tmp_path / "fresh-firefox-profile"),
            local_model="qwen2.5vl:3b",
            local_model_endpoint="http://127.0.0.1:11434",
            expected_initial_title_regex=TITLE_PATTERN,
            allowed_title_regex=TITLE_PATTERN,
        )


def edge_window(executable: Path, *, handle: int = 200, process_id: int = 9000) -> EdgeWindowRecord:
    return EdgeWindowRecord(
        window=WindowInfo(
            handle=handle,
            title=TITLE,
            process_id=process_id,
            left=10,
            top=20,
            width=1200,
            height=800,
        ),
        executable=str(executable.resolve()),
    )


def isolated_plan(tmp_path: Path, *, session_id: str = "scorm-test-run"):
    executable = edge_executable(tmp_path)
    profile = EdgeProfileSpec.isolated(tmp_path / "fresh-profile")
    plan = build_scorm_cloud_edge_plan(
        exact_url=SCORM_URL,
        edge_executable=executable,
        profile=profile,
        local_model="qwen3:8b",
        local_model_endpoint="http://127.0.0.1:11434",
        expected_initial_title_regex=TITLE_PATTERN,
        allowed_title_regex=TITLE_PATTERN,
        session_id=session_id,
    )
    return executable, plan


def owner_existing_plan(
    tmp_path: Path,
    *,
    session_id: str = "owner-existing-run",
):
    executable = edge_executable(tmp_path)
    root = tmp_path / "owner-edge"
    (root / "Default").mkdir(parents=True)
    profile = EdgeProfileSpec.owner_existing(
        root,
        owner_edge_process_id=5000,
    )
    plan = build_scorm_cloud_edge_plan(
        exact_url=SCORM_URL,
        edge_executable=executable,
        profile=profile,
        local_model="qwen3:8b",
        local_model_endpoint="http://127.0.0.1:11434",
        expected_initial_title_regex=TITLE_PATTERN,
        allowed_title_regex=TITLE_PATTERN,
        session_id=session_id,
    )
    return executable, root, plan


def make_runner(
    tmp_path: Path,
    *,
    plan,
    controller: FakeWindowController,
    launcher: FakeLauncher,
    inspector: FakeProcessInspector,
    clock: FakeClock,
):
    ledger = SCORMEvidenceLedger(
        tmp_path / "scorm-evidence.jsonl",
        run_id=plan.session_id,
        utc_now=clock.now,
    )
    gateway = GovernedDesktopGateway(
        backend=FakeGatewayBackend(controller),  # type: ignore[arg-type]
        evidence_path=tmp_path / "gateway-evidence.jsonl",
        utc_now=clock.now,
    )
    runner = SCORMCloudSessionRunner(
        launcher=launcher,
        window_controller=controller,
        process_inspector=inspector,
        gateway=gateway,
        ledger=ledger,
        signing_secret=SECRET,
        utc_now=clock.now,
        monotonic=clock.monotonic,
        sleeper=clock.sleep,
    )
    return runner, gateway, ledger


def test_plan_preserves_exact_scorm_url_and_binds_loopback_model(tmp_path: Path) -> None:
    _executable, plan = isolated_plan(tmp_path)

    assert plan.command[-1] == SCORM_URL
    assert plan.exact_url == SCORM_URL
    assert plan.local_model_endpoint == "http://127.0.0.1:11434"
    assert plan.audit_dict()["url_sha256"] == hashlib.sha256(SCORM_URL.encode()).hexdigest()
    assert SCORM_URL not in repr(plan)
    assert len(plan.plan_sha256) == 64


@pytest.mark.parametrize(
    "url,code",
    [
        ("http://cloud.scorm.com/launch", "https_required"),
        ("https://evil.example/launch", "host_not_allowed"),
        ("https://cloud.scorm.com.evil.example/launch", "host_not_allowed"),
        ("https://CLOUD.SCORM.COM/launch", "host_not_allowed"),
        ("https://cloud.scorm.com:443/launch", "host_not_allowed"),
        ("https://user@cloud.scorm.com/launch", "host_not_allowed"),
        (" https://cloud.scorm.com/launch", "not_exact"),
    ],
)
def test_plan_rejects_every_non_exact_scorm_authority(
    tmp_path: Path,
    url: str,
    code: str,
) -> None:
    executable = edge_executable(tmp_path)
    profile = EdgeProfileSpec.isolated(tmp_path / "fresh-profile")

    with pytest.raises(SCORMCloudSessionError, match=code):
        build_scorm_cloud_edge_plan(
            exact_url=url,
            edge_executable=executable,
            profile=profile,
            local_model="qwen3:8b",
            local_model_endpoint="http://127.0.0.1:11434",
            expected_initial_title_regex=TITLE_PATTERN,
            allowed_title_regex=TITLE_PATTERN,
        )


def test_plan_rejects_remote_model_endpoint_and_unanchored_title(tmp_path: Path) -> None:
    executable = edge_executable(tmp_path)
    profile = EdgeProfileSpec.isolated(tmp_path / "fresh-profile")
    common = {
        "exact_url": SCORM_URL,
        "edge_executable": executable,
        "profile": profile,
        "local_model": "qwen3:8b",
        "expected_initial_title_regex": TITLE_PATTERN,
        "allowed_title_regex": TITLE_PATTERN,
    }

    with pytest.raises(SCORMCloudSessionError, match="must_be_loopback"):
        build_scorm_cloud_edge_plan(
            **common,
            local_model_endpoint="https://api.example.com/v1",
        )
    with pytest.raises(SCORMCloudSessionError, match="must_be_anchored"):
        build_scorm_cloud_edge_plan(
            **{**common, "expected_initial_title_regex": "SCORM Cloud"},
            local_model_endpoint="http://localhost:11434",
        )


def test_owner_existing_profile_is_used_in_place_without_cookie_read_or_copy(tmp_path: Path) -> None:
    executable = edge_executable(tmp_path)
    root = tmp_path / "owner-edge"
    default = root / "Default"
    default.mkdir(parents=True)
    cookie = default / "Cookies"
    cookie.write_bytes(b"owner-signed-cookie-database")
    before = hashlib.sha256(cookie.read_bytes()).hexdigest()

    profile = EdgeProfileSpec.owner_existing(
        root,
        owner_edge_process_id=5000,
    )
    plan = build_scorm_cloud_edge_plan(
        exact_url=SCORM_URL,
        edge_executable=executable,
        profile=profile,
        local_model="qwen3:8b",
        local_model_endpoint="http://localhost:11434",
        expected_initial_title_regex=TITLE_PATTERN,
        allowed_title_regex=TITLE_PATTERN,
        session_id="owner-profile-run",
    )

    baseline = edge_window(executable, handle=100, process_id=5000)
    launched_window = edge_window(executable, handle=101, process_id=5000)
    controller = FakeWindowController([baseline])
    launcher = FakeLauncher(lambda: controller.records.append(launched_window), process_id=6000)
    clock = FakeClock()
    runner, gateway, _ledger = make_runner(
        tmp_path,
        plan=plan,
        controller=controller,
        launcher=launcher,
        inspector=FakeProcessInspector(
            {5000: None, 6000: None},
            executable=str(executable.resolve()),
        ),
        clock=clock,
    )

    active = runner.start(plan)

    assert active.initial_binding.window == launched_window.window
    assert gateway.require_single_target_binding_id() == active.initial_binding.binding_id
    assert hashlib.sha256(cookie.read_bytes()).hexdigest() == before
    assert list(default.iterdir()) == [cookie]

    active.close()

    assert controller.close_calls == [launched_window.window]
    assert [record.window for record in controller.records] == [baseline.window]
    assert launcher.cleanup_calls[0][1] is False
    assert root.is_dir()
    assert hashlib.sha256(cookie.read_bytes()).hexdigest() == before


def test_owner_existing_without_visible_baseline_captures_only_new_descendant(
    tmp_path: Path,
) -> None:
    executable, root, plan = owner_existing_plan(tmp_path)
    created = edge_window(executable, handle=301, process_id=5001)
    controller = FakeWindowController()
    launcher = FakeLauncher(
        lambda: controller.records.append(created),
        process_id=6000,
    )
    clock = FakeClock()
    runner, gateway, _ledger = make_runner(
        tmp_path,
        plan=plan,
        controller=controller,
        launcher=launcher,
        inspector=FakeProcessInspector(
            {5000: None, 5001: 5000, 6000: None},
            executable=str(executable.resolve()),
        ),
        clock=clock,
    )

    active = runner.start(plan)

    assert active.initial_binding.window == created.window
    assert controller.foreground_calls == [created.window]
    assert gateway.require_single_target_binding_id() == active.initial_binding.binding_id

    active.close()

    assert controller.close_calls == [created.window]
    assert launcher.cleanup_calls == [(active.launched_process, False)]
    assert root.is_dir()


@pytest.mark.parametrize(
    ("executable_matches", "profile_matches", "error"),
    [
        (False, True, "owner_edge_process_executable_mismatch"),
        (True, False, "owner_edge_process_profile_mismatch"),
    ],
)
def test_owner_existing_without_visible_baseline_requires_exact_process_identity(
    tmp_path: Path,
    executable_matches: bool,
    profile_matches: bool,
    error: str,
) -> None:
    executable, root, plan = owner_existing_plan(tmp_path)
    controller = FakeWindowController()
    launcher = FakeLauncher(lambda: None, process_id=6000)
    inspector = FakeProcessInspector(
        {5000: None, 6000: None},
        executable=(
            str(executable.resolve())
            if executable_matches
            else str((tmp_path / "unrelated" / "msedge.exe").resolve())
        ),
        profile_matches=profile_matches,
    )
    clock = FakeClock()
    runner, gateway, _ledger = make_runner(
        tmp_path,
        plan=plan,
        controller=controller,
        launcher=launcher,
        inspector=inspector,
        clock=clock,
    )

    with pytest.raises(SCORMCloudSessionError, match=error):
        runner.start(plan)

    assert launcher.plans == []
    assert launcher.cleanup_calls == []
    assert controller.close_calls == []
    assert gateway.status()["binding_count"] == 0
    assert root.is_dir()


def test_psutil_owner_identity_probe_accepts_exact_descendant_profile_flags(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executable = edge_executable(tmp_path).resolve()
    profile_root = tmp_path / "owner-edge"
    (profile_root / "Default").mkdir(parents=True)

    class MissingProcess(Exception):
        pass

    class DeniedProcess(Exception):
        pass

    class FakeProcess:
        def __init__(
            self,
            process_id: int,
            command: list[str],
            children: list[FakeProcess] | None = None,
        ) -> None:
            self.pid = process_id
            self._command = command
            self._children = children or []

        def exe(self) -> str:
            return str(executable)

        def children(self, *, recursive: bool) -> list[FakeProcess]:
            assert recursive is True
            return list(self._children)

        def cmdline(self) -> list[str]:
            return list(self._command)

    child = FakeProcess(
        5001,
        [
            str(executable),
            f"--user-data-dir={profile_root.resolve()}",
            "--profile-directory=Default",
        ],
    )
    root_process = FakeProcess(5000, [str(executable), "--no-startup-window"], [child])
    fake_psutil = SimpleNamespace(
        Process=lambda process_id: root_process if process_id == 5000 else child,
        AccessDenied=DeniedProcess,
        NoSuchProcess=MissingProcess,
    )
    monkeypatch.setitem(sys.modules, "psutil", fake_psutil)
    inspector = PsutilProcessInspector()

    assert inspector.process_executable(5000) == str(executable)
    assert inspector.process_profile_matches(
        5000,
        user_data_dir=str(profile_root.resolve()),
        profile_directory="Default",
    )


def test_psutil_owner_identity_probe_rejects_mismatched_descendant_profile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executable = edge_executable(tmp_path).resolve()
    profile_root = tmp_path / "owner-edge"
    (profile_root / "Default").mkdir(parents=True)
    other_root = tmp_path / "other-edge"
    (other_root / "Default").mkdir(parents=True)

    class MissingProcess(Exception):
        pass

    class DeniedProcess(Exception):
        pass

    class FakeProcess:
        pid = 5000

        def children(self, *, recursive: bool) -> list[FakeProcess]:
            assert recursive is True
            return []

        def cmdline(self) -> list[str]:
            return [str(executable), f"--user-data-dir={other_root.resolve()}"]

    fake_process = FakeProcess()
    monkeypatch.setitem(
        sys.modules,
        "psutil",
        SimpleNamespace(
            Process=lambda _process_id: fake_process,
            AccessDenied=DeniedProcess,
            NoSuchProcess=MissingProcess,
        ),
    )

    assert not PsutilProcessInspector().process_profile_matches(
        5000,
        user_data_dir=str(profile_root.resolve()),
        profile_directory="Default",
    )


@pytest.mark.parametrize("descendant_readable", [True, False])
def test_psutil_owner_identity_probe_rejects_unreadable_root_cmdline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    descendant_readable: bool,
) -> None:
    executable = edge_executable(tmp_path).resolve()
    profile_root = tmp_path / "owner-edge"
    (profile_root / "Default").mkdir(parents=True)

    class MissingProcess(Exception):
        pass

    class DeniedProcess(Exception):
        pass

    class FakeProcess:
        def __init__(self, process_id: int, *, root: bool) -> None:
            self.pid = process_id
            self.root = root

        def children(self, *, recursive: bool) -> list[FakeProcess]:
            assert recursive is True
            return [child] if self.root else []

        def cmdline(self) -> list[str]:
            if self.root or not descendant_readable:
                raise DeniedProcess
            return [str(executable), f"--user-data-dir={profile_root.resolve()}"]

    child = FakeProcess(5001, root=False)
    root_process = FakeProcess(5000, root=True)
    monkeypatch.setitem(
        sys.modules,
        "psutil",
        SimpleNamespace(
            Process=lambda process_id: root_process if process_id == 5000 else child,
            AccessDenied=DeniedProcess,
            NoSuchProcess=MissingProcess,
        ),
    )

    with pytest.raises(
        SCORMCloudSessionError,
        match="local_process_profile_root_cmdline_unavailable",
    ):
        PsutilProcessInspector().process_profile_matches(
            5000,
            user_data_dir=str(profile_root.resolve()),
            profile_directory="Default",
        )


def test_owner_root_cmdline_inspection_failure_prevents_launch(tmp_path: Path) -> None:
    executable, root, plan = owner_existing_plan(tmp_path)
    controller = FakeWindowController()
    launcher = FakeLauncher(lambda: None, process_id=6000)

    class UnreadableOwnerInspector(FakeProcessInspector):
        def process_profile_matches(
            self,
            process_id: int,
            *,
            user_data_dir: str,
            profile_directory: str,
        ) -> bool:
            raise SCORMCloudSessionError(
                "local_process_profile_root_cmdline_unavailable"
            )

    clock = FakeClock()
    runner, gateway, _ledger = make_runner(
        tmp_path,
        plan=plan,
        controller=controller,
        launcher=launcher,
        inspector=UnreadableOwnerInspector(
            {5000: None, 6000: None},
            executable=str(executable.resolve()),
        ),
        clock=clock,
    )

    with pytest.raises(
        SCORMCloudSessionError,
        match="owner_edge_process_inspection_failed",
    ):
        runner.start(plan)

    assert launcher.plans == []
    assert controller.close_calls == []
    assert gateway.status()["binding_count"] == 0
    assert root.is_dir()


def test_owner_existing_without_visible_baseline_ignores_unrelated_new_pid(
    tmp_path: Path,
) -> None:
    executable, root, plan = owner_existing_plan(tmp_path)
    unrelated = edge_window(executable, handle=302, process_id=7000)
    controller = FakeWindowController()
    launcher = FakeLauncher(
        lambda: controller.records.append(unrelated),
        process_id=6000,
    )
    clock = FakeClock()
    runner, gateway, _ledger = make_runner(
        tmp_path,
        plan=plan,
        controller=controller,
        launcher=launcher,
        inspector=FakeProcessInspector(
            {5000: None, 6000: None, 7000: None},
            executable=str(executable.resolve()),
        ),
        clock=clock,
    )

    with pytest.raises(SCORMCloudSessionError, match="scorm_new_window_not_observed"):
        runner.start(plan)

    assert controller.close_calls == []
    assert controller.records == [unrelated]
    assert launcher.cleanup_calls[0][1] is False
    assert gateway.status()["binding_count"] == 0
    assert root.is_dir()


def test_owner_existing_ambiguity_closes_every_exact_post_launch_delta(
    tmp_path: Path,
) -> None:
    executable, root, plan = owner_existing_plan(tmp_path)
    first = edge_window(executable, handle=303, process_id=5001)
    second = edge_window(executable, handle=304, process_id=5002)
    controller = FakeWindowController()
    launcher = FakeLauncher(
        lambda: controller.records.extend([first, second]),
        process_id=6000,
    )
    clock = FakeClock()
    runner, gateway, _ledger = make_runner(
        tmp_path,
        plan=plan,
        controller=controller,
        launcher=launcher,
        inspector=FakeProcessInspector(
            {5000: None, 5001: 5000, 5002: 5000, 6000: None},
            executable=str(executable.resolve()),
        ),
        clock=clock,
    )

    with pytest.raises(SCORMCloudSessionError, match="scorm_new_window_ambiguous"):
        runner.start(plan)

    assert controller.close_calls == [second.window, first.window]
    assert controller.records == []
    assert launcher.cleanup_calls[0][1] is False
    assert gateway.status()["binding_count"] == 0
    assert root.is_dir()


def test_owner_existing_title_mismatch_closes_exact_new_descendant(
    tmp_path: Path,
) -> None:
    executable, root, plan = owner_existing_plan(tmp_path)
    created = edge_window(executable, handle=305, process_id=5001)
    created = replace(created, window=replace(created.window, title="Unrelated - Microsoft Edge"))
    controller = FakeWindowController()
    launcher = FakeLauncher(
        lambda: controller.records.append(created),
        process_id=6000,
    )
    clock = FakeClock()
    runner, gateway, _ledger = make_runner(
        tmp_path,
        plan=plan,
        controller=controller,
        launcher=launcher,
        inspector=FakeProcessInspector(
            {5000: None, 5001: 5000, 6000: None},
            executable=str(executable.resolve()),
        ),
        clock=clock,
    )

    with pytest.raises(SCORMCloudSessionError, match="scorm_new_window_title_not_allowed"):
        runner.start(plan)

    assert controller.close_calls == [created.window]
    assert launcher.cleanup_calls[0][1] is False
    assert gateway.status()["binding_count"] == 0
    assert root.is_dir()


def test_runner_waits_for_transient_chromium_title_before_binding(
    tmp_path: Path,
) -> None:
    executable, plan = isolated_plan(tmp_path)
    loading = edge_window(executable)
    loading = replace(
        loading,
        window=replace(loading.window, title="New tab - Microsoft Edge"),
    )
    ready = replace(loading, window=replace(loading.window, title=TITLE))
    controller = FakeWindowController()

    class TitleTransitionClock(FakeClock):
        def sleep(self, seconds: float) -> None:
            super().sleep(seconds)
            controller.records = [ready]

    clock = TitleTransitionClock()
    runner, gateway, _ledger = make_runner(
        tmp_path,
        plan=plan,
        controller=controller,
        launcher=FakeLauncher(lambda: controller.records.append(loading)),
        inspector=FakeProcessInspector({9000: None}),
        clock=clock,
    )

    active = runner.start(plan)

    assert active.initial_binding.window == ready.window
    assert gateway.require_single_target_binding_id() == active.initial_binding.binding_id

    active.close()

    assert controller.close_calls == [ready.window]


def test_runner_captures_new_exact_window_foregrounds_once_and_starts_governed_session(
    tmp_path: Path,
) -> None:
    executable, plan = isolated_plan(tmp_path)
    initial = edge_window(executable)
    controller = FakeWindowController()
    launcher = FakeLauncher(lambda: controller.records.append(initial))
    clock = FakeClock()
    runner, gateway, ledger = make_runner(
        tmp_path,
        plan=plan,
        controller=controller,
        launcher=launcher,
        inspector=FakeProcessInspector({9000: None}),
        clock=clock,
    )

    active = runner.start(plan)

    assert launcher.plans == [plan]
    assert controller.foreground_calls == [initial.window]
    assert active.initial_binding.window == initial.window
    assert gateway.require_single_target_binding_id() == active.initial_binding.binding_id
    assert active.control_manifest.control_grant_sha256 == active.control_grant_sha256
    assert (
        active.control_manifest.verify(
            SECRET,
            plan=plan,
            policy_sha256=active.initial_binding.policy_sha256,
            now=clock.now(),
        )
        is active.control_manifest
    )
    assert active.control_manifest.launch_plan_sha256 == plan.plan_sha256
    assert active.control_manifest.launch_url_sha256 == plan.url_sha256
    assert active.control_manifest.allowed_actions == plan.allowed_gui_actions
    assert set(active.control_manifest.signed_payload()) == {
        "allowed_actions",
        "expires_at_unix",
        "issued_at_unix",
        "launch_plan_sha256",
        "launch_url_sha256",
        "policy_sha256",
        "schema_version",
        "session_id",
    }
    assert active.control_manifest.schema_version == (
        "aureon-scorm-neutral-control-manifest-v2"
    )
    assert (Path(plan.profile.user_data_dir) / "Default").is_dir()
    raw_evidence = ledger.path.read_text(encoding="utf-8")
    assert SCORM_URL not in raw_evidence
    assert "signed-value-123" not in raw_evidence
    events = [json.loads(row)["event"] for row in raw_evidence.splitlines()]
    assert events == [
        "launch_plan_accepted",
        "window_baseline_captured",
        "isolated_profile_created",
        "browser_launch_authorized",
        "browser_process_started",
        "browser_window_captured",
        "browser_window_foregrounded",
        "governed_window_session_authorized",
        "scorm_session_started",
    ]

    active.close()

    assert controller.close_calls == [initial.window]
    assert launcher.cleanup_calls[0][1] is True
    assert not Path(plan.profile.user_data_dir).exists()
    assert gateway.status()["binding_count"] == 0


def test_runner_initial_foreground_tolerates_title_and_rect_drift(tmp_path: Path) -> None:
    executable, plan = isolated_plan(tmp_path)
    initial = edge_window(executable)
    drifted_initial = replace(
        initial,
        window=replace(
            initial.window,
            left=17,
            top=33,
            width=1024,
            height=720,
        ),
    )

    class DriftingWindowController(FakeWindowController):
        def foreground_exact(self, window: WindowInfo) -> WindowInfo:
            matching = [
                record
                for record in self.records
                if record.window.handle == window.handle
                and record.window.process_id == window.process_id
            ]
            assert len(matching) == 1
            self.foreground_calls.append(window)
            self.records = [
                replace(record, window=drifted_initial.window)
                if record.window == window
                else record
                for record in self.records
            ]
            self.foreground = drifted_initial.window
            return drifted_initial.window

    controller = DriftingWindowController([])
    runner, gateway, _ledger = make_runner(
        tmp_path,
        plan=plan,
        controller=controller,
        launcher=FakeLauncher(lambda: controller.records.append(initial)),
        inspector=FakeProcessInspector({9000: None}),
        clock=FakeClock(),
    )

    active = runner.start(plan)

    assert active.initial_binding.window == drifted_initial.window
    assert gateway.require_single_target_binding_id() == active.initial_binding.binding_id

    active.close()

    assert controller.foreground_calls == [initial.window]
    assert controller.close_calls == [drifted_initial.window]


def test_public_preview_control_manifest_tamper_and_context_fail_closed(
    tmp_path: Path,
) -> None:
    executable, plan = isolated_plan(tmp_path)
    initial = edge_window(executable)
    controller = FakeWindowController()
    clock = FakeClock()
    runner, _gateway, _ledger = make_runner(
        tmp_path,
        plan=plan,
        controller=controller,
        launcher=FakeLauncher(lambda: controller.records.append(initial)),
        inspector=FakeProcessInspector({9000: None}),
        clock=clock,
    )
    active = runner.start(plan)

    with pytest.raises(SCORMCloudSessionError, match="signature_invalid"):
        active.control_manifest.verify(
            b"different-scorm-session-secret-at-least-32-bytes",
            plan=plan,
            policy_sha256=active.initial_binding.policy_sha256,
            now=clock.now(),
        )
    with pytest.raises(SCORMCloudSessionError, match="context_mismatch"):
        active.control_manifest.verify(
            SECRET,
            plan=plan,
            policy_sha256="f" * 64,
            now=clock.now(),
        )


def test_control_grant_matches_exact_observation_and_rejects_credential_typing(tmp_path: Path) -> None:
    executable, plan = isolated_plan(tmp_path)
    initial = edge_window(executable)
    controller = FakeWindowController()
    clock = FakeClock()
    runner, _gateway, _ledger = make_runner(
        tmp_path,
        plan=plan,
        controller=controller,
        launcher=FakeLauncher(lambda: controller.records.append(initial)),
        inspector=FakeProcessInspector({9000: None}),
        clock=clock,
    )
    active = runner.start(plan)
    rect = SimpleNamespace(left=10, top=20, width=1200, height=800)
    observation = SimpleNamespace(
        window_handle=200,
        window_process_id=9000,
        window_title_sha256=hashlib.sha256(TITLE.encode()).hexdigest(),
        window_rect=rect,
    )

    assert len(active.control_grant_sha256) == 64
    assert active.authorize_control(
        observation,
        SimpleNamespace(name="left_click", params={"x": 10, "y": 20}),
    )
    assert not active.authorize_control(
        observation,
        SimpleNamespace(name="type_text", params={"text_class": "credential"}),
    )
    assert not active.authorize_control(replace_namespace(observation, window_handle=201))


def replace_namespace(namespace: SimpleNamespace, **changes) -> SimpleNamespace:
    return SimpleNamespace(**{**vars(namespace), **changes})


def test_explicit_child_popup_handoff_foregrounds_then_atomically_rebinds(tmp_path: Path) -> None:
    executable, plan = isolated_plan(tmp_path)
    initial = edge_window(executable)
    controller = FakeWindowController()
    clock = FakeClock()
    inspector = FakeProcessInspector({9000: None, 9001: 9000})
    runner, gateway, ledger = make_runner(
        tmp_path,
        plan=plan,
        controller=controller,
        launcher=FakeLauncher(lambda: controller.records.append(initial)),
        inspector=inspector,
        clock=clock,
    )
    active = runner.start(plan)
    popup = replace(
        initial,
        window=replace(initial.window, handle=201, process_id=9001, title="Assessment - SCORM Cloud - Microsoft Edge"),
    )
    controller.records.append(popup)

    rebound = active.handoff(target_handle=201)

    assert rebound.window == popup.window
    assert rebound.generation == 1
    assert controller.foreground_calls == [initial.window, popup.window]
    assert gateway.require_single_target_binding_id() == rebound.binding_id
    assert [json.loads(row)["event"] for row in ledger.path.read_text().splitlines()][-2:] == [
        "window_handoff_authorized",
        "window_handoff_committed",
    ]


def test_dynamic_binding_supplier_fresh_authorizes_and_unique_handoff_uses_foreground(
    tmp_path: Path,
) -> None:
    executable, plan = isolated_plan(tmp_path)
    initial = edge_window(executable)
    controller = FakeWindowController()
    clock = FakeClock()
    runner, gateway, _ledger = make_runner(
        tmp_path,
        plan=plan,
        controller=controller,
        launcher=FakeLauncher(lambda: controller.records.append(initial)),
        inspector=FakeProcessInspector({9000: None, 9001: 9000}),
        clock=clock,
    )
    active = runner.start(plan)
    assert active.authorize_binding_id() == active.initial_binding.binding_id
    authorized = active.authorize_binding()
    assert (authorized.binding_id, authorized.generation) == (
        active.initial_binding.binding_id,
        0,
    )

    popup = replace(
        initial,
        window=replace(
            initial.window,
            handle=202,
            process_id=9001,
            title="Assessment - SCORM Cloud - Microsoft Edge",
        ),
    )
    controller.records.append(popup)
    controller.foreground = popup.window

    binding_id = active.handoff_unique_changed_window()

    assert binding_id != active.initial_binding.binding_id
    assert gateway.require_single_target_binding_id() == binding_id
    assert active.authorize_binding_id() == binding_id
    assert active.authorize_binding().generation == 1
    assert active.window_session.active_binding is not None
    assert active.window_session.active_binding.window == popup.window


def test_same_hwnd_navigation_updates_owned_identity_and_closes_current_window(
    tmp_path: Path,
) -> None:
    executable, plan = isolated_plan(tmp_path)
    initial = edge_window(executable)
    controller = FakeWindowController()
    clock = FakeClock()
    runner, gateway, _ledger = make_runner(
        tmp_path,
        plan=plan,
        controller=controller,
        launcher=FakeLauncher(lambda: controller.records.append(initial)),
        inspector=FakeProcessInspector({9000: None}),
        clock=clock,
    )
    active = runner.start(plan)
    navigated = replace(
        initial,
        window=replace(
            initial.window,
            title="Assessment - SCORM Cloud - Microsoft Edge",
            left=24,
            top=32,
            width=1100,
            height=760,
        ),
    )
    controller.records[:] = [navigated]
    controller.foreground = navigated.window

    binding_id = active.handoff_unique_changed_window()

    assert binding_id != active.initial_binding.binding_id
    assert active.authorize_binding().window == navigated.window
    assert gateway.require_single_target_binding_id() == binding_id

    active.close()

    assert controller.close_calls == [navigated.window]
    assert controller.records == []


def test_unique_handoff_rejects_an_owner_window_that_predated_the_launch(tmp_path: Path) -> None:
    executable = edge_executable(tmp_path)
    root = tmp_path / "owner-edge"
    (root / "Default").mkdir(parents=True)
    profile = EdgeProfileSpec.owner_existing(root, owner_edge_process_id=5000)
    plan = build_scorm_cloud_edge_plan(
        exact_url=SCORM_URL,
        edge_executable=executable,
        profile=profile,
        local_model="qwen3:8b",
        local_model_endpoint="http://127.0.0.1:11434",
        expected_initial_title_regex=TITLE_PATTERN,
        allowed_title_regex=TITLE_PATTERN,
        session_id="preexisting-owner-window-run",
    )
    preexisting = edge_window(executable, handle=100, process_id=5000)
    initial = edge_window(executable, handle=101, process_id=5000)
    controller = FakeWindowController([preexisting])
    clock = FakeClock()
    runner, _gateway, _ledger = make_runner(
        tmp_path,
        plan=plan,
        controller=controller,
        launcher=FakeLauncher(lambda: controller.records.append(initial), process_id=6000),
        inspector=FakeProcessInspector(
            {5000: None, 6000: None},
            executable=str(executable.resolve()),
        ),
        clock=clock,
    )
    active = runner.start(plan)
    controller.foreground = preexisting.window

    with pytest.raises(SCORMCloudSessionError, match="preexisting_window_not_owned"):
        active.handoff_unique_changed_window()

    assert active.authorize_binding_id() == active.initial_binding.binding_id


def test_runner_rejects_ambiguous_new_windows_without_foreground_or_binding(tmp_path: Path) -> None:
    executable, plan = isolated_plan(tmp_path)
    first = edge_window(executable, handle=200)
    second = edge_window(executable, handle=201)
    controller = FakeWindowController()
    clock = FakeClock()
    launcher = FakeLauncher(lambda: controller.records.extend([first, second]))
    runner, gateway, _ledger = make_runner(
        tmp_path,
        plan=plan,
        controller=controller,
        launcher=launcher,
        inspector=FakeProcessInspector({9000: None}),
        clock=clock,
    )

    with pytest.raises(SCORMCloudSessionError, match="new_window_ambiguous"):
        runner.start(plan)

    assert controller.foreground_calls == []
    assert gateway.status()["binding_count"] == 0
    assert launcher.cleanup_calls[0][1] is True
    assert not Path(plan.profile.user_data_dir).exists()


def test_runner_cleans_owned_launch_when_initial_window_is_not_observed(
    tmp_path: Path,
) -> None:
    _executable, plan = isolated_plan(tmp_path)
    controller = FakeWindowController()
    launcher = FakeLauncher(lambda: None)
    clock = FakeClock()
    runner, gateway, ledger = make_runner(
        tmp_path,
        plan=plan,
        controller=controller,
        launcher=launcher,
        inspector=FakeProcessInspector({9000: None}),
        clock=clock,
    )

    with pytest.raises(SCORMCloudSessionError, match="new_window_not_observed"):
        runner.start(plan)

    assert launcher.cleanup_calls[0][1] is True
    assert controller.close_calls == []
    assert gateway.status()["binding_count"] == 0
    assert not Path(plan.profile.user_data_dir).exists()
    events = [json.loads(row)["event"] for row in ledger.path.read_text().splitlines()]
    assert events[-1] == "browser_launch_cleanup_completed"


def test_runner_closes_exact_captured_window_when_foregrounding_fails(
    tmp_path: Path,
) -> None:
    executable, plan = isolated_plan(tmp_path)
    initial = edge_window(executable)

    class FailingForegroundController(FakeWindowController):
        def foreground_exact(self, window: WindowInfo) -> WindowInfo:
            raise RuntimeError(f"cannot foreground {window.handle}")

    controller = FailingForegroundController()
    launcher = FakeLauncher(lambda: controller.records.append(initial))
    clock = FakeClock()
    runner, gateway, _ledger = make_runner(
        tmp_path,
        plan=plan,
        controller=controller,
        launcher=launcher,
        inspector=FakeProcessInspector({9000: None}),
        clock=clock,
    )

    with pytest.raises(SCORMCloudSessionError, match="initial_foreground_failed"):
        runner.start(plan)

    assert controller.close_calls == [initial.window]
    assert launcher.cleanup_calls[0][1] is True
    assert gateway.status()["binding_count"] == 0
    assert not Path(plan.profile.user_data_dir).exists()


def test_subprocess_launcher_releases_exact_handle_and_terminates_only_when_requested(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _executable, plan = isolated_plan(tmp_path)

    class FakePopen:
        def __init__(self, *_args, **_kwargs) -> None:
            self.pid = 45678
            self.running = True
            self.terminate_calls = 0
            self.kill_calls = 0

        def poll(self):
            return None if self.running else 0

        def terminate(self) -> None:
            self.terminate_calls += 1
            self.running = False

        def kill(self) -> None:
            self.kill_calls += 1
            self.running = False

        def wait(self, *, timeout: float):
            assert timeout == 1.0
            return 0

    processes: list[FakePopen] = []

    def fake_popen(*args, **kwargs):
        process = FakePopen(*args, **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(session_module.subprocess, "Popen", fake_popen)
    launcher = SubprocessEdgeLauncher(cleanup_timeout_seconds=1.0)

    terminated = launcher.launch(plan)
    launcher.cleanup(terminated, terminate_owned_process=True)
    assert processes[0].terminate_calls == 1
    assert processes[0].kill_calls == 0

    released = launcher.launch(plan)
    launcher.cleanup(released, terminate_owned_process=False)
    assert processes[1].terminate_calls == 0
    with pytest.raises(SCORMCloudSessionError, match="cleanup_receipt_unknown"):
        launcher.cleanup(released, terminate_owned_process=False)


def test_ledger_detects_tampering_and_never_accepts_sensitive_keys(tmp_path: Path) -> None:
    clock = FakeClock()
    path = tmp_path / "evidence.jsonl"
    ledger = SCORMEvidenceLedger(path, run_id="ledger-run", utc_now=clock.now)
    first = ledger.append("safe_event", {"url_sha256": "a" * 64})
    assert first.sequence == 1

    with pytest.raises(SCORMCloudSessionError, match="sensitive_field"):
        ledger.append("unsafe_event", {"exact_url": SCORM_URL})

    row = json.loads(path.read_text())
    row["data"]["url_sha256"] = "b" * 64
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    with pytest.raises(SCORMCloudSessionError, match="chain_invalid"):
        ledger.append("second_event", {})


@pytest.mark.parametrize(
    "text",
    [
        "SCORM Cloud Sign In",
        "Email address Password",
        "Email Password Continue",
        "Session expired, please try again",
        "401 Unauthorized",
        "ERROR The request could not be satisfied. Generated by cloudfront",
        "Missing Key-Pair-Id query parameter or cookie value",
    ],
)
def test_visible_login_gates_report_owner_cookie_or_sign_in_blocker(text: str) -> None:
    assert detect_scorm_access_blocker(text) == "signed_session_cookie_or_owner_login_required"


def test_normal_course_text_does_not_invent_an_access_blocker() -> None:
    assert (
        detect_scorm_access_blocker("Workplace safety lesson 1 Continue")
        == "access_not_blocked_by_visible_login_gate"
    )
