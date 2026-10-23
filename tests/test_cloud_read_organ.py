"""No real organ starts: verify hold binding and owner checks with isolated peers."""
import contextlib
import importlib.util
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

DIRECTORY = Path(__file__).parents[1] / "deployment/google-cloud"
sys.path.insert(0, str(DIRECTORY))
spec = importlib.util.spec_from_file_location("cloud_read_organ", DIRECTORY / "cloud_read_organ.py")
organ = importlib.util.module_from_spec(spec)
spec.loader.exec_module(organ)

PROVIDER_CONFIG = {
    "NASA_API_KEY": "offline_nasa_" + "n" * 32,
    "NOAA_API_KEY": "offline_noaa_" + "o" * 32,
    "USGS_API_KEY": "offline_usgs_" + "u" * 32,
    "OLLAMA_API_KEY": "offline_ollama_" + "m" * 32,
    "AUREON_LLM_BASE_URL": "https://ollama.com/v1",
    "AUREON_LLM_MODEL": "gpt-oss:120b-cloud",
}


def registry_and_gate():
    registry = SimpleNamespace(
        ORGANS={"unified_market_trader": {"module": "fixture", "env": {"AUREON_LIVE_TRADING": "1", "UNIFIED_CAPITAL_TICK_TIMEOUT_SEC": "5"}}},
        _release_granted=lambda: False,
    )
    gate = SimpleNamespace(release_authorized=lambda: False,
                           _check_verdict=lambda action: {"allowed": False, "deployment_hold": True})
    return registry, gate


def test_actual_hold_contract_and_selected_environment_are_required():
    registry, gate = registry_and_gate()
    old = registry.ORGANS["unified_market_trader"]
    organ.configure(registry, gate, "unified_market_trader", dict(organ.HOLDS))
    configured = registry.ORGANS["unified_market_trader"]
    assert configured is not old
    assert old["env"]["AUREON_LIVE_TRADING"] == "1"
    assert configured["env"]["UNIFIED_CAPITAL_TICK_TIMEOUT_SEC"] == "5"
    assert all(configured["env"][key] == value for key, value in organ.HOLDS.items())
    gate._check_verdict = lambda action: {"allowed": False}  # label-only/missing implementation
    with pytest.raises(organ.ReleaseError, match="contract_not_enforced"):
        organ.configure(registry, gate, "unified_market_trader", dict(organ.HOLDS))


@pytest.mark.parametrize("key", sorted(organ.HOLDS))
def test_any_missing_action_hold_blocks_configuration(key):
    registry, gate = registry_and_gate()
    environment = dict(organ.HOLDS)
    environment.pop(key)
    with pytest.raises(organ.ReleaseError, match="all_cloud_action_holds"):
        organ.configure(registry, gate, "unified_market_trader", environment)


def test_unity_and_duplicate_http_registry_services_are_not_allowed():
    registry, gate = registry_and_gate()
    for name in ("unity_supervisor", "operator_gateway", "frontend_vite", "aureon_radar_suite"):
        registry.ORGANS[name] = {}
        with pytest.raises(organ.ReleaseError, match="outside_selected"):
            organ.configure(registry, gate, name, dict(organ.HOLDS))


def test_selected_provider_organs_receive_only_validated_memory_bundle():
    for name in sorted(organ.PROVIDER_CONFIG_ORGANS):
        registry, gate = registry_and_gate()
        registry.ORGANS[name] = {
            "module": "fixture",
            "env": {"NASA_API_KEY": "stale-parent-value", "ORGAN_SETTING": "retained"},
        }
        environment = {**organ.HOLDS, "NASA_API_KEY": "untrusted-service-value"}
        organ.configure(registry, gate, name, environment, PROVIDER_CONFIG)
        configured = registry.ORGANS[name]["env"]
        assert configured["ORGAN_SETTING"] == "retained"
        assert configured["PYTHON_DOTENV_DISABLED"] == "1"
        assert configured[organ.PINNED_PROVIDER_ENV_VARS_ENV] == ",".join(
            organ.OWNER_PROVIDER_KEYS
        )
        assert {key: configured[key] for key in organ.OWNER_PROVIDER_KEYS} == PROVIDER_CONFIG
        assert all(configured[key] == value for key, value in organ.HOLDS.items())


def test_provider_values_are_stripped_from_unselected_child():
    registry, gate = registry_and_gate()
    registry.ORGANS["unified_market_trader"]["env"].update(PROVIDER_CONFIG)
    organ.configure(registry, gate, "unified_market_trader", {**organ.HOLDS, **PROVIDER_CONFIG})
    configured = registry.ORGANS["unified_market_trader"]["env"]
    assert not set(organ.OWNER_PROVIDER_KEYS) & set(configured)
    with pytest.raises(organ.ReleaseError, match="outside_selected"):
        organ.configure(registry, gate, "unified_market_trader", dict(organ.HOLDS), PROVIDER_CONFIG)


def test_every_child_scrubs_exchange_authority_and_dotenv_controls():
    registry, gate = registry_and_gate()
    contaminated = {
        **organ.HOLDS,
        **{key: "ambient-secret" for key in organ.CLOUD_EXCHANGE_CREDENTIAL_ENV_VARS},
        **{key: "unsafe" for key in organ.CLOUD_EXCHANGE_MODE_ENV_VARS},
        **{key: "/private/env" for key in organ.CLOUD_ENV_LOADER_CONTROL_VARS},
    }
    registry.ORGANS["unified_market_trader"]["env"].update(contaminated)
    organ.configure(registry, gate, "unified_market_trader", contaminated)
    configured = registry.ORGANS["unified_market_trader"]["env"]
    assert not set(organ.CLOUD_EXCHANGE_CREDENTIAL_ENV_VARS) & set(configured)
    assert not set(organ.CLOUD_ENV_LOADER_CONTROL_VARS) & set(configured)
    assert configured["PYTHON_DOTENV_DISABLED"] == "1"
    assert configured[organ.CLOUD_CREDENTIAL_ISOLATION_ENV] == "1"
    assert configured[organ.CLOUD_EXCHANGE_CREDENTIALS_PINNED_ENV] == "1"
    assert str(DIRECTORY) == configured["PYTHONPATH"].split(os.pathsep)[0]
    assert {
        key: configured[key] for key in organ.CLOUD_OPERATOR_SAFE_MODE_ENV
    } == organ.CLOUD_OPERATOR_SAFE_MODE_ENV


def test_selected_provider_reference_is_complete_and_pinned_by_loader():
    captured = []

    def loader(project, secret, version):
        captured.append((project, secret, version))
        return dict(PROVIDER_CONFIG)

    assert organ.owner_provider_config(
        "hnc_live_daemon", "fixture-project", "owner-provider", "9", loader
    ) == PROVIDER_CONFIG
    assert captured == [("fixture-project", "owner-provider", "9")]
    with pytest.raises(organ.ReleaseError, match="reference_required"):
        organ.owner_provider_config("hnc_live_daemon", "fixture-project", "", "9", loader)
    with pytest.raises(organ.ReleaseError, match="outside_selected"):
        organ.owner_provider_config(
            "unified_market_trader", "fixture-project", "owner-provider", "9", loader
        )


def test_an_existing_process_is_never_adopted_or_stopped():
    registry = SimpleNamespace(start=Mock(return_value={"state": "already_running", "pid": 111}), stop=Mock())
    factory = Mock()
    with pytest.raises(organ.ReleaseError, match="did_not_start_new_owned"):
        organ.start_owned(registry, "hnc_core", factory, lambda pid: b"fixture")
    factory.assert_not_called()
    registry.stop.assert_not_called()


def test_started_process_must_belong_to_own_cgroup():
    registry = SimpleNamespace(start=Mock(return_value={"state": "started", "pid": 111}), stop=Mock())
    process = SimpleNamespace(pid=111, create_time=lambda: 123)
    with pytest.raises(organ.ReleaseError, match="not_in_owned_systemd_cgroup"):
        organ.start_owned(registry, "hnc_core", lambda pid: process,
                          lambda pid: b"foreign" if pid == 111 else b"this-unit")
    registry.stop.assert_not_called()


def test_stop_cannot_target_replacement_registry_owner_or_reused_pid():
    state = {"organs": {"hnc_core": {"pid": 222}}}
    registry = SimpleNamespace(_registry_lock=lambda: contextlib.nullcontext(True),
                               _load_registry=lambda: state, stop=Mock())
    process = SimpleNamespace(pid=111, is_running=lambda: True, create_time=lambda: 123)
    organ.stop_owned(registry, "hnc_core", process, 123, lambda pid: b"same")
    registry.stop.assert_not_called()
    state["organs"]["hnc_core"]["pid"] = 111
    organ.stop_owned(registry, "hnc_core", process, 122, lambda pid: b"same")
    registry.stop.assert_not_called()
    organ.stop_owned(registry, "hnc_core", process, 123, lambda pid: b"same")
    registry.stop.assert_called_once_with("hnc_core")
