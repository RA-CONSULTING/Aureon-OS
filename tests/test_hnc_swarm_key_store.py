import shutil
import subprocess

import pytest

from aureon.vault import hnc_swarm_key_store as key_store
from aureon.vault.hnc_swarm_key_store import ensure_dpapi_swarm_keys, load_dpapi_swarm_agent_keys

pytestmark = pytest.mark.skipif(
    shutil.which("powershell.exe") is None and shutil.which("powershell") is None,
    reason="Windows PowerShell is required for DPAPI swarm key storage",
)


def test_dpapi_swarm_key_store_round_trips_metadata_only(tmp_path):
    manifest = ensure_dpapi_swarm_keys(("seer", "lyra"), store_dir=tmp_path)
    loaded = load_dpapi_swarm_agent_keys(("seer", "lyra"), store_dir=tmp_path)

    assert manifest["secret_policy"] == "metadata_only_no_raw_keys"
    assert manifest["agent_count"] == 2
    assert set(loaded) == {"seer", "lyra"}
    assert loaded["seer"] != loaded["lyra"]
    assert "seer" not in (tmp_path / "seer.dpapi").read_text(encoding="utf-8")
    assert loaded["seer"] not in (tmp_path / "manifest.json").read_text(encoding="utf-8")


def test_powershell_launcher_scrubs_polluted_module_path_without_exposing_stdin(tmp_path, monkeypatch):
    inherited_module_path = str(tmp_path / "powershell-7-inherited-modules")
    override_module_path = str(tmp_path / "powershell-7-override-modules")
    target = str(tmp_path / "agent.dpapi")
    secret = "synthetic-secret-kept-on-stdin"
    captured = {}

    monkeypatch.setenv("PSModulePath", inherited_module_path)
    monkeypatch.setattr(key_store, "_powershell", lambda: "powershell.exe")

    def fake_run(args, **kwargs):
        captured["args"] = args
        captured.update(kwargs)
        return subprocess.CompletedProcess(args, 0, stdout="ok\n", stderr="")

    monkeypatch.setattr(key_store.subprocess, "run", fake_run)

    output = key_store._run_powershell(
        "Write-Output ok",
        stdin=secret,
        env={
            "AUREON_DPAPI_TARGET": target,
            "pSmOdUlEpAtH": override_module_path,
        },
    )

    assert output == "ok\n"
    assert key_store.os.environ["PSModulePath"] == inherited_module_path
    assert all(name.casefold() != "psmodulepath" for name in captured["env"])
    assert captured["env"]["AUREON_DPAPI_TARGET"] == target
    assert captured["input"] == secret
    assert all(secret not in argument for argument in captured["args"])
    assert all(secret not in value for value in captured["env"].values())
    assert captured["capture_output"] is True
    assert captured["text"] is True
    assert captured["check"] is False


def test_powershell_failure_never_exposes_child_output(monkeypatch):
    secret = "synthetic-decrypted-secret"
    monkeypatch.setattr(key_store, "_powershell", lambda: "powershell.exe")
    monkeypatch.setattr(
        key_store.subprocess,
        "run",
        lambda args, **kwargs: subprocess.CompletedProcess(
            args,
            1,
            stdout=f"stdout:{secret}",
            stderr=f"stderr:{secret}:polluted-module-path",
        ),
    )

    with pytest.raises(RuntimeError, match="^powershell_failed$") as exc_info:
        key_store._run_powershell("throw 'failure'", stdin=secret)

    assert secret not in str(exc_info.value)
    assert "polluted-module-path" not in str(exc_info.value)
