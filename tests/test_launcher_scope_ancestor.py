"""An inherited launcher scope is trusted only from our own session root.

No launcher is started, no cgroup or systemd unit is created: the scope
set-up calls are replaced with fakes.
"""

from __future__ import annotations

import os

import pytest

from aureon.launch import session_scope as ss

_LEAK = {
    ss.SCOPE_ENV: "aureon-launcher-live",
    ss.CGROUP_ENV: "/sys/fs/cgroup/fake/aureon-launcher-live",
    ss.INSIDE_ENV: "1",
    ss.PROBE_STARTED_ENV: "1",
}


@pytest.fixture
def no_real_scope(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    calls: dict[str, object] = {}
    monkeypatch.setattr(ss, "_try_systemd_reexec", lambda argv, unit: calls.setdefault("reexec_unit", unit) and False)
    monkeypatch.setattr(ss, "_try_cgroup", lambda unit: calls.setdefault("cgroup_unit", unit) and False)
    monkeypatch.setattr(ss, "_become_subreaper", lambda: None)
    monkeypatch.setattr(ss, "_start_setsid_probe", lambda: None)
    monkeypatch.setattr(ss, "_unit_name", lambda: "aureon-launcher-fresh")
    monkeypatch.setattr(ss.os, "name", "posix")
    return calls


def _leak(monkeypatch: pytest.MonkeyPatch, root: int) -> None:
    for key, value in _LEAK.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv(ss.ROOT_ENV, str(root))


def test_scope_from_an_unrelated_root_is_not_trusted(monkeypatch, no_real_scope) -> None:
    # pid 2 is never this process or one of its ancestors (kthreadd / not ours).
    _leak(monkeypatch, 2)
    assert ss.inherited_scope_is_ours() is False
    ss.enter_session([])
    assert no_real_scope.get("reexec_unit") == "aureon-launcher-fresh"
    assert os.environ.get(ss.CGROUP_ENV, "") == ""
    assert os.environ[ss.ROOT_ENV] == str(os.getpid())
    assert ss.current_session()["root_pid"] == os.getpid()


def test_missing_or_bad_root_is_not_trusted(monkeypatch) -> None:
    for key, value in _LEAK.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv(ss.ROOT_ENV, raising=False)
    assert ss.inherited_scope_is_ours() is False
    monkeypatch.setenv(ss.ROOT_ENV, "not-a-pid")
    assert ss.inherited_scope_is_ours() is False


def test_own_pid_is_trusted(monkeypatch, no_real_scope) -> None:
    _leak(monkeypatch, os.getpid())
    assert ss.inherited_scope_is_ours() is True
    ss.enter_session([])
    assert "reexec_unit" not in no_real_scope
    assert os.environ[ss.CGROUP_ENV] == _LEAK[ss.CGROUP_ENV]


def test_parent_launcher_is_trusted(monkeypatch) -> None:
    _leak(monkeypatch, os.getppid())
    assert ss.inherited_scope_is_ours() is True


def test_reexec_stamps_its_own_pid_as_root(monkeypatch) -> None:
    seen: dict[str, object] = {}

    class _Done:
        returncode = 0

    monkeypatch.setattr(ss, "_systemd_user_works", lambda: True)
    monkeypatch.setattr(ss.subprocess, "run", lambda *a, **k: _Done())

    def fake_exec(file, cmd, env):
        seen["env"] = env
        raise OSError("not really exec'ing")

    monkeypatch.setattr(ss.os, "execvpe", fake_exec)
    monkeypatch.setenv(ss.ROOT_ENV, "2")
    assert ss._try_systemd_reexec([], "aureon-launcher-x") is False
    env = seen["env"]
    assert env[ss.INSIDE_ENV] == "1"
    assert env[ss.ROOT_ENV] == str(os.getpid())
