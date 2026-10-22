"""Real temporary source/backup transactions; all service operations are fixtures."""
from __future__ import annotations

import importlib.util
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path, PurePosixPath
import sys
from types import SimpleNamespace

import pytest

TOOL = Path(__file__).parents[1] / "deployment/google-cloud/release_update.py"
sys.path.insert(0, str(TOOL.parent))
spec = importlib.util.spec_from_file_location("release_update", TOOL)
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)
operator_closure = sys.modules["operator_runtime_closure"]

UNIT = "aureon-organ@hnc_core.service"
REVISION = "a" * 40
OLD_REVISION = "0" * 40
IAP_ADMIN_EMAIL_SHA256 = "9" * 64
OWNER_SUBJECT = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
OWNER_EMAIL_SHA256 = "c" * 64
TREE = "b" * 40
BOOT_HASH = "f" * 64
CERTIFICATE_FIXTURE_TIME = datetime.now(UTC)
MINIMAL_PACKAGE_TREE = {
    "aureon-os-upstream/aureon/__init__.py",
    "aureon-os-upstream/aureon/operator/__init__.py",
    "aureon-os-upstream/aureon/operator/operator_server.py",
}


def vm_runtime_sources(package_tree=MINIMAL_PACKAGE_TREE):
    return sorted(set(package_tree) | set(operator_closure.OPERATOR_COMPANION_SOURCES))


def vm_runtime_manifest(rows, package_tree=MINIMAL_PACKAGE_TREE):
    indexed = {row["path"]: row for row in rows}
    sources = vm_runtime_sources(package_tree)
    selected = [indexed[path] for path in sources]
    return {
        "schema": "aureon.vm-python-runtime-closure.v1",
        "source_git_tree": TREE,
        "sources": sources,
        "files": len(sources),
        "payload_sha256": release.manifest_payload_sha256(selected),
    }


def component_manifest(rows, required, schema):
    indexed = {row["path"]: row for row in rows}
    sources = sorted(required)
    return {
        "schema": schema,
        "source_git_tree": TREE,
        "sources": sources,
        "files": len(sources),
        "payload_sha256": release.manifest_payload_sha256(
            [indexed[path] for path in sources]
        ),
    }


def broker_identity():
    return {
        "project": release.GCP_PROJECT,
        "zone": "europe-west1-b",
        "instance": "aureon-sero-20260906",
        "email": release.BROKER_SERVICE_ACCOUNT,
        "scopes": [release.BROKER_SCOPE],
    }


def bridge_certificate_evidence(now=None):
    observed = now or CERTIFICATE_FIXTURE_TIME
    return {
        "receipt_sha256": "d" * 64,
        "fingerprint_sha256": "c" * 64,
        "required_ip_sans": ["10.40.0.2"],
        "not_before": (observed - timedelta(days=1)).isoformat(),
        "not_after": (observed + timedelta(days=30)).isoformat(),
        "minimum_remaining_validity_seconds": 86_400,
    }


def authority_receipt(tmp_path):
    path = tmp_path / "authority-receipt.json"
    image_receipt_sha256 = "e" * 64
    authority_image = (
        "europe-west1-docker.pkg.dev/aureon-trading/aureon-web/"
        "aureon-trading-authority@sha256:" + "1" * 64
    )
    public_image = (
        "europe-west1-docker.pkg.dev/aureon-trading/aureon-web/"
        "aureon-public-entry@sha256:" + "2" * 64
    )
    service_names = (
        "aureon-trade-controller",
        "aureon-trade-review",
        "aureon-trade-dispatch",
        "aureon-trade-executor",
        "aureon-trade-receipt",
        "aureon-fusion-web",
        "aureon-fusion-operator",
    )
    certificate = bridge_certificate_evidence()
    provider = {
        "schema": "aureon.gcp.cloud-run-staged-provider-readback.v1",
        "project": release.GCP_PROJECT,
        "region": "europe-west1",
        "contract_sha256": "d" * 64,
        "source_revision": REVISION,
        "image_build_receipt_sha256": image_receipt_sha256,
        "public_bridge_certificate": certificate,
        "services": [
            {
                "name": name,
                "revision": f"{name}-r{REVISION[:12]}",
                "latest_ready_revision": f"{name}-prior",
                "traffic": [
                    {
                        "revision": f"{name}-prior",
                        "percent": 100,
                        "tag": None,
                    }
                ],
                "image": (
                    public_image
                    if name.startswith("aureon-fusion-")
                    else authority_image
                ),
                "configuration_sha256": "3" * 64,
            }
            for name in service_names
        ],
        "secret_values_recorded": False,
        "release_authority": False,
        "mutation_authority": False,
    }
    path.write_text(
        json.dumps(
            {
                "schema": release.AUTHORITY_RECEIPT_SCHEMA,
                "status": "staged_attested",
                "phase": "staged-revision-attestation",
                "recorded_at": datetime.now(UTC).isoformat(),
                "contract_sha256": "d" * 64,
                "source_revision": REVISION,
                "provider_readback_ok": True,
                "provider_readback": provider,
                "provider_readback_sha256": release.digest(
                    json.dumps(
                        provider, sort_keys=True, separators=(",", ":")
                    ).encode("ascii")
                ),
                "immutable_image_build_receipt_sha256": (
                    image_receipt_sha256
                ),
                "public_bridge_certificate": certificate,
                "provider_error_codes": [],
                "vm_readback_deferred_to_release_receipt": True,
                "cloud_run_staged_without_traffic": True,
                "cloud_run_traffic_changed": False,
                "secret_payloads_requested": False,
                "sensitive_environment_values_returned": False,
                "release_authority": False,
                "mutation_authority": False,
            }
        ),
        encoding="utf-8",
    )
    return path, release.digest(path.read_bytes())


def test_authority_receipt_accepts_old_latest_ready_for_no_traffic_stage(tmp_path):
    path, receipt_sha256 = authority_receipt(tmp_path)

    value = release.validate_authority_receipt(
        path, receipt_sha256, REVISION
    )

    assert value["cloud_run_staged_without_traffic"] is True
    assert value["cloud_run_traffic_changed"] is False


def test_authority_receipt_rejects_target_revision_with_nonzero_traffic(tmp_path):
    path, _receipt_sha256 = authority_receipt(tmp_path)
    value = json.loads(path.read_text(encoding="utf-8"))
    target = value["provider_readback"]["services"][0]
    target["traffic"] = [
        {
            "revision": target["revision"],
            "percent": 100,
            "tag": None,
        }
    ]
    value["provider_readback_sha256"] = release.digest(
        json.dumps(
            value["provider_readback"],
            sort_keys=True,
            separators=(",", ":"),
        ).encode("ascii")
    )
    path.write_text(json.dumps(value), encoding="utf-8")

    with pytest.raises(
        release.ReleaseError,
        match="authority_receipt_provider_binding_invalid",
    ):
        release.validate_authority_receipt(
            path, release.digest(path.read_bytes()), REVISION
        )


def broker_token_receipts():
    observed = datetime.now(UTC)
    expires = observed + timedelta(minutes=20)
    return [
        {
            "workload": name,
            "target_service_account": account,
            "token_path": path,
            "schema": release.TOKEN_SCHEMA,
            "owner_uid": 0,
            "owner_gid": index + 1000,
            "reader_uid": index + 2000,
            "reader_gid": index + 1000,
            "mode": "0640",
            "expires_at": expires.isoformat(),
            "observed_at": observed.isoformat(),
            "readback_sha256": f"{index + 1:064x}",
            "secret_value_recorded": False,
        }
        for index, (name, account, _user, path) in enumerate(release.BROKER_WORKLOADS)
    ]


def held_health(unit, revision):
    role = release.HTTP_UNITS.get(unit)
    if role is None:
        return None
    return {
        "schema": "aureon.cloud-http-health.v1",
        "revision": revision,
        "role": role,
        "ready": True,
        "deployment_hold": True,
        "release_authority": False,
        "tenant_auth_ready": True,
        "response_sha256": "a" * 64,
    }


class Services:
    def __init__(self, units, active=True):
        self.units, self.active, self.enablement, self.events = units, {UNIT: active}, {UNIT: True}, []

    def snapshot(self, unit):
        exists = (self.units / unit).exists()
        active = self.active.get(unit, False) if exists else False
        return {
            "exists": exists,
            "active": active,
            "enabled": self.enablement.get(unit, False) if exists else False,
            "main_pid": 100 if active else 0,
            "user": release.service_identity(unit) if exists else None,
        }

    def stop(self, unit):
        self.events.append(("stop", unit))
        self.active[unit] = False

    def start(self, unit):
        assert (self.units / unit).exists()
        self.events.append(("start", unit))
        self.active[unit] = True

    def reload(self):
        self.events.append(("reload",))

    def restart(self, unit):
        assert (self.units / unit).exists()
        self.events.append(("restart", unit))
        self.active[unit] = True

    def enabled(self, unit, value):
        self.events.append(("enabled", unit, value))
        self.enablement[unit] = value


def bootstrap_and_quiesce(staged, services):
    release.bootstrap_broker(staged, services)
    return release.quiesce_for_identity_cutover(staged, services)


def fixture(tmp_path, monkeypatch, *, new_file=False):
    workspace, units, bundle, releases = [tmp_path / name for name in ("workspace", "units", "bundle", "releases")]
    for path in (workspace, units, bundle / "files", releases):
        path.mkdir(parents=True)
    source = "aureon_fusion/reader.py"
    target = workspace / source
    target.parent.mkdir(parents=True)
    if not new_file:
        target.write_bytes(b"VALUE = 1\n")
    runtime = workspace / "aureon_fusion/state/approvals.json"
    runtime.parent.mkdir()
    runtime.write_text('{"fixture_approval":"untouched"}')
    (units / UNIT).write_text("original unit\n")
    data = b"VALUE = 2\n"
    source_data = {source: data}
    for relative in set(vm_runtime_sources()) | set(release.READ_ORGAN_REQUIRED_SOURCES):
        source_data.setdefault(relative, b"VALUE = 2\n")
    rows = []
    for relative, content in source_data.items():
        payload = bundle / "files" / relative
        payload.parent.mkdir(parents=True, exist_ok=True)
        payload.write_bytes(content)
        rows.append(
            {"path": relative, "sha256": release.digest(content), "size": len(content)}
        )
    manifest = {"schema": release.SCHEMA, "revision": REVISION,
                "release_id": "20260911T230000Z-aaaaaaaa",
                "files": rows}
    manifest.update({
        "source_git_revision": REVISION,
        "source_git_tree": TREE,
        "payload_sha256": release.manifest_payload_sha256(manifest["files"]),
        "frontend_dist": None,
        "vm_python_runtime": vm_runtime_manifest(rows),
    })
    (bundle / "manifest.json").write_text(json.dumps(manifest))
    renderer = release.render_unit
    # Exercise actual Linux unit generation even while temp filesystem tests run on Windows.
    monkeypatch.setattr(release, "render_unit", lambda unit, root, *args: renderer(unit, PurePosixPath("/srv/aureon/runtime/workspace"), *args))
    services = Services(units)
    return workspace, units, bundle, releases, target, runtime, services


def prepared(tmp_path, monkeypatch, **kwargs):
    workspace, units, bundle, releases, target, runtime, services = fixture(tmp_path, monkeypatch, **kwargs)
    staged = release.prepare(bundle, workspace, releases, units, [UNIT], services)
    return staged, target, runtime, services


def test_success_commits_only_source_and_preserves_runtime(tmp_path, monkeypatch):
    staged, target, runtime, services = prepared(tmp_path, monkeypatch)
    original_runtime = runtime.read_bytes()
    assert target.read_bytes() == b"VALUE = 1\n" and not services.events
    health_calls = []
    def health(unit, revision):
        assert target.read_bytes() == b"VALUE = 2\n"
        if not health_calls:
            assert services.events[0] == ("enabled", UNIT, False)
            assert services.enablement[UNIT] is False
            assert services.events.index(("stop", UNIT)) < services.events.index(("reload",))
        health_calls.append(unit)
        assert revision == REVISION
    result = release.apply(
        staged,
        services,
        health,
        identity_snapshot=broker_identity,
        boot_id=lambda: BOOT_HASH,
    )
    assert result["phase"] == "committed"
    assert release.check(staged)["phase"] == "committed"
    assert runtime.read_bytes() == original_runtime
    assert result["runtime_state_restored"] is False and result["release_authority"] is False
    assert health_calls == [UNIT, UNIT]
    assert result["vm_release_receipt"]["sha256"] == release.digest(
        (staged / "vm-release-receipt.json").read_bytes()
    )
    assert (staged / "backup/0").read_bytes() == b"VALUE = 1\n"
    assert target.stat().st_uid == json.loads((staged / "journal.json").read_text())["entries"][0]["owner"][0]


def test_failed_health_rolls_source_back_but_keeps_new_runtime(tmp_path, monkeypatch):
    staged, target, runtime, services = prepared(tmp_path, monkeypatch)
    def failure(*args):
        runtime.write_text('{"new_runtime_receipt":"must survive rollback"}')
        raise RuntimeError("fixture health failure")
    with pytest.raises(release.ReleaseError, match="source_rolled_back"):
        release.apply(staged, services, failure, boot_id=lambda: BOOT_HASH)
    assert target.read_bytes() == b"VALUE = 1\n"
    assert "new_runtime_receipt" in runtime.read_text()
    assert services.active[UNIT] is True
    assert release.check(staged)["phase"] == "rolled_back"


def test_failed_new_source_is_removed_without_recursive_cleanup(tmp_path, monkeypatch):
    staged, target, runtime, services = prepared(tmp_path, monkeypatch, new_file=True)
    with pytest.raises(release.ReleaseError, match="source_rolled_back"):
        release.apply(
            staged,
            services,
            lambda *args: (_ for _ in ()).throw(ValueError()),
            boot_id=lambda: BOOT_HASH,
        )
    assert not target.exists() and runtime.exists()


def test_manifest_tampering_is_refused_before_service_operations(tmp_path, monkeypatch):
    workspace, units, bundle, releases, target, runtime, services = fixture(tmp_path, monkeypatch)
    (bundle / "files/aureon_fusion/reader.py").write_bytes(b"VALUE = 99\n")
    with pytest.raises(release.ReleaseError, match="manifest_hash"):
        release.prepare(bundle, workspace, releases, units, [UNIT], services)
    assert not services.events and target.read_bytes() == b"VALUE = 1\n"


@pytest.mark.parametrize("which", ["target", "staged"])
def test_change_after_prepare_refuses_before_stopping(tmp_path, monkeypatch, which):
    staged, target, runtime, services = prepared(tmp_path, monkeypatch)
    changed = target if which == "target" else staged / "staged/0"
    changed.write_bytes(b"VALUE = 99\n")
    with pytest.raises(release.ReleaseError, match="changed_after_prepare|staged_source_hash"):
        release.apply(staged, services)
    assert services.events == []


def test_interruption_recovery_restores_source_without_replaying_state(tmp_path, monkeypatch):
    staged, target, runtime, services = prepared(tmp_path, monkeypatch)
    journal = json.loads((staged / "journal.json").read_text())
    journal["phase"] = "installing"
    release.save_journal(staged, journal)
    target.write_bytes((staged / "staged/0").read_bytes())
    services.active[UNIT] = False
    runtime.write_text('{"decision":"newer than deployment"}')
    with pytest.raises(release.ReleaseError, match="only_prepared"):
        release.apply(staged, services)
    with pytest.raises(release.ReleaseError, match="interrupted"):
        release.check(staged)
    release.rollback(staged, services)
    assert target.read_bytes() == b"VALUE = 1\n"
    assert "newer than deployment" in runtime.read_text()
    assert services.active[UNIT]


def test_backup_corruption_and_newer_source_block_rollback(tmp_path, monkeypatch):
    staged, target, runtime, services = prepared(tmp_path, monkeypatch)
    release.apply(
        staged,
        services,
        lambda *args: None,
        identity_snapshot=broker_identity,
        boot_id=lambda: BOOT_HASH,
    )
    events = list(services.events)
    target.write_bytes(b"VALUE = 3\n")
    with pytest.raises(release.ReleaseError, match="external_or_newer_source"):
        release.rollback(staged, services)
    assert services.events == events and target.read_bytes() == b"VALUE = 3\n"
    target.write_bytes(b"VALUE = 2\n")
    (staged / "backup/0").write_bytes(b"damaged")
    with pytest.raises(release.ReleaseError, match="backup_hash"):
        release.rollback(staged, services)
    assert services.events == events


def test_explicit_rollback_disables_boot_before_restoring_source(tmp_path, monkeypatch):
    staged, target, runtime, services = prepared(tmp_path, monkeypatch)
    release.apply(
        staged,
        services,
        lambda *args: None,
        identity_snapshot=broker_identity,
        boot_id=lambda: BOOT_HASH,
    )
    services.events.clear()
    release.rollback(staged, services)
    assert services.events[:2] == [("enabled", UNIT, False), ("stop", UNIT)]
    assert services.enablement[UNIT] is True
    assert target.read_bytes() == b"VALUE = 1\n"


@pytest.mark.parametrize("path", [
    "../escape.py", "/root/escape.py", "aureon_fusion/../../escape.py", "aureon_fusion\\escape.py",
    "aureon_fusion/C:/escape.py", "aureon_fusion/state/approvals.json", "aureon-os-upstream/.env",
    "aureon-os-upstream/provider_keys.json", "aureon-os-upstream/brain_predictions_history.json",
    "aureon_fusion/coding_decisions.json", "deployment/elsewhere.py", "aureon_fusion/private/key.txt",
])
def test_unsafe_or_private_paths_are_rejected(path):
    with pytest.raises(release.ReleaseError):
        release.source_path(path)


def test_source_subdirectories_are_not_confused_with_runtime_state():
    for path in ("aureon-os-upstream/frontend/src/state/newsEmotionStore.ts", "aureon-os-upstream/aureon/autonomy/reader.py",
                 "solar_system_collector.py", "real_time_data_feeder.py", "sero_mind/reader.py",
                 "deployment/google-cloud/public-entry/public_entry.py"):
        assert release.source_path(path) == path


def test_invalid_python_is_not_imported_or_installed(tmp_path, monkeypatch):
    workspace, units, bundle, releases, target, runtime, services = fixture(tmp_path, monkeypatch)
    bad = b"def broken(:\n"
    (bundle / "files/aureon_fusion/reader.py").write_bytes(bad)
    manifest = json.loads((bundle / "manifest.json").read_text())
    manifest["files"][0].update(sha256=release.digest(bad), size=len(bad))
    manifest["payload_sha256"] = release.manifest_payload_sha256(manifest["files"])
    (bundle / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(SyntaxError):
        release.prepare(bundle, workspace, releases, units, [UNIT], services)
    assert not services.events and target.read_bytes() == b"VALUE = 1\n"


def test_http_units_enforce_all_holds_and_distinct_shims():
    for unit, shim in (("aureon-cloud-operator.service", "cloud_operator.py"), ("aureon-cloud-ui.service", "cloud_ui_gateway.py")):
        body = release.render_unit(unit, PurePosixPath("/srv/aureon/runtime/workspace"), REVISION, "fixture-project", "http-bearer", "7",
                                   "supabase-tenant", "3", "owner-provider", "9",
                                   OWNER_SUBJECT, OWNER_EMAIL_SHA256).decode()
        assert shim in body and "KillMode=control-group" in body
        assert "--secret-version 7" in body and "--revision " + REVISION in body
        for key, value in release.HOLDS.items():
            assert "Environment=" + key + "=" + value in body
        if unit == "aureon-cloud-operator.service":
            assert "--tenant-secret supabase-tenant --tenant-secret-version 3" in body
            assert "--provider-secret owner-provider --provider-secret-version 9" in body
            for expected in ("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS=1", "AUREON_AUDIT_MODE=1",
                             "AUREON_LLM_ALLOW_HTTP_IN_AUDIT=1", "AUREON_LLM_REQUEST_TIMEOUT_S=15",
                             "AUREON_OPERATOR_TIMEOUT_S=15", "AUREON_OPERATOR_MAX_RETRIES=0",
                             "AUREON_COGNITION_MAX_MODEL_CALLS=3"):
                assert "Environment=" + expected in body
            assert "User=aureon-operator" in body
            assert "Group=aureon-operator" in body
            assert "Environment=AUREON_KEYSTORE_DIR=/var/lib/aureon-operator/keystore" in body
            assert (
                "Environment=AUREON_OPERATOR_INTENT_LEDGER="
                + release.OPERATOR_INTENT_LEDGER_PATH
            ) in body
            assert "Environment=AUREON_SUPABASE_OWNER_SUBJECT=" + OWNER_SUBJECT in body
            assert "Environment=AUREON_SUPABASE_OWNER_EMAIL_SHA256=" + OWNER_EMAIL_SHA256 in body
            assert "StateDirectory=aureon-operator" in body
            assert "StateDirectoryMode=0700" in body
            assert "SupplementaryGroups=aureon-control-readers" in body
            assert release.RELEASE_LEDGER_DIR in next(
                line for line in body.splitlines() if line.startswith("ReadWritePaths=")
            )
            assert release.TRADE_READBACK_DIR in next(
                line for line in body.splitlines() if line.startswith("ReadOnlyPaths=")
            )
        else:
            assert "User=aureon-ui" in body and "Group=aureon-ui" in body
            assert "--provider-secret" not in body
            assert "AUREON_KEYSTORE_DIR" not in body
            assert "StateDirectory=aureon-ui" in body
        assert "Requires=aureon-cloud-token-broker.service" in body
        assert "After=network-online.target aureon-cloud-token-broker.service" in body
        assert "ProtectProc=invisible" in body and "ProcSubset=pid" in body
        for address in release.METADATA_ADDRESSES:
            assert "IPAddressDeny=" + address in body
        assert "ReadOnlyPaths=/srv/aureon/runtime/workspace" in body
        assert "/srv/aureon/runtime/workspace" not in next(
            line for line in body.splitlines() if line.startswith("ReadWritePaths=")
        )
        assert "Environment=PYTHON_DOTENV_DISABLED=1" in body
        assert "Environment=AUREON_CLOUD_CREDENTIAL_ISOLATION=1" in body
        assert "Environment=AUREON_CLOUD_EXCHANGE_CREDENTIALS_PINNED=1" in body
        assert "PYTHONPATH=/srv/aureon/runtime/workspace/deployment/google-cloud:" in body
        assert "Environment=DRY_RUN=true" in body
        assert "Environment=CONFIRM_LIVE=no" in body
        unset = next(line for line in body.splitlines() if line.startswith("UnsetEnvironment="))
        for name in (*release.ENV_LOADER_CONTROL_VARS, *release.EXCHANGE_CREDENTIAL_ENV_VARS):
            assert name in unset
        inaccessible = next(
            line for line in body.splitlines() if line.startswith("InaccessiblePaths=")
        )
        for path in (
            "/srv/aureon/runtime/workspace/.env",
            "/srv/aureon/runtime/workspace/aureon-os-upstream/.env",
            "/srv/aureon/runtime/workspace/aureon_radar/.env",
        ):
            assert "-" + path in inaccessible
    with pytest.raises(release.ReleaseError, match="pinned_cloud_secret"):
        release.render_unit("aureon-cloud-ui.service", PurePosixPath("/srv/aureon/runtime/workspace"), REVISION, "fixture-project", "http-bearer", "latest",
                            "supabase-tenant", "3")
    with pytest.raises(release.ReleaseError, match="tenant_secret"):
        release.render_unit("aureon-cloud-operator.service", PurePosixPath("/srv/aureon/runtime/workspace"), REVISION, "fixture-project", "http-bearer", "7")
    with pytest.raises(release.ReleaseError, match="owner_provider_secret"):
        release.render_unit("aureon-cloud-operator.service", PurePosixPath("/srv/aureon/runtime/workspace"), REVISION,
                            "fixture-project", "http-bearer", "7", "supabase-tenant", "3")


def test_operator_never_references_existing_private_config(monkeypatch):
    monkeypatch.setattr(Path, "is_file", lambda path: path.name == ".env")
    body = release.render_unit("aureon-cloud-operator.service", PurePosixPath("/srv/aureon/runtime/workspace"), REVISION, "fixture-project", "http-bearer", "7",
                               "supabase-tenant", "3", "owner-provider", "9",
                               OWNER_SUBJECT, OWNER_EMAIL_SHA256).decode()
    assert "Environment=AUREON_ENV_FILE=" not in body
    assert "AUREON_ENV_FILE" in next(
        line for line in body.splitlines() if line.startswith("UnsetEnvironment=")
    )
    assert "Environment=AUREON_CLOUD_TRADE_READBACK_PATH=" + release.TRADE_READBACK_PATH in body


@pytest.mark.parametrize(
    ("subject", "email_sha256"),
    [
        ("", ""),
        (OWNER_SUBJECT, ""),
        ("", OWNER_EMAIL_SHA256),
        ("00000000-0000-0000-0000-000000000000", OWNER_EMAIL_SHA256),
        ("aaaaaaaa-aaaa-6aaa-8aaa-aaaaaaaaaaaa", OWNER_EMAIL_SHA256),
        (OWNER_SUBJECT.upper(), OWNER_EMAIL_SHA256),
        (OWNER_SUBJECT, OWNER_EMAIL_SHA256.upper()),
    ],
)
def test_operator_owner_identity_binding_is_atomic_and_canonical(
    subject, email_sha256
):
    with pytest.raises(release.ReleaseError, match="supabase_owner_identity"):
        release.render_unit(
            "aureon-cloud-operator.service",
            PurePosixPath("/srv/aureon/runtime/workspace"),
            REVISION,
            "fixture-project",
            "http-bearer",
            "7",
            "supabase-tenant",
            "3",
            "owner-provider",
            "9",
            subject,
            email_sha256,
        )


@pytest.mark.parametrize("name", sorted(release.PROVIDER_CONFIG_ORGANS))
def test_selected_read_organs_receive_only_pinned_provider_reference(name):
    unit = f"aureon-organ@{name}.service"
    body = release.render_unit(
        unit,
        PurePosixPath("/srv/aureon/runtime/workspace"),
        REVISION,
        "fixture-project",
        "",
        "",
        "",
        "",
        "owner-provider",
        "9",
    ).decode()
    assert "cloud_read_organ.py " + name in body
    assert "--project fixture-project" in body
    assert "--provider-secret owner-provider --provider-secret-version 9" in body
    assert "User=aureon-provider" in body and "Group=aureon-provider" in body
    assert "Environment=AUREON_GOOGLE_TOKEN_FILE=/run/aureon-cloud-identity/provider/token.json" in body
    assert "Requires=aureon-cloud-token-broker.service" in body
    assert "DynamicUser=yes" not in body
    for address in release.METADATA_ADDRESSES:
        assert "IPAddressDeny=" + address in body
    assert "NASA_API_KEY=" not in body and "OLLAMA_API_KEY=" not in body
    for key, value in release.HOLDS.items():
        assert "Environment=" + key + "=" + value in body


def test_provider_reference_is_rejected_when_unpinned_and_omitted_from_other_organs():
    unit = "aureon-organ@hnc_live_daemon.service"
    with pytest.raises(release.ReleaseError, match="owner_provider_secret"):
        release.render_unit(
            unit, PurePosixPath("/srv/aureon/runtime/workspace"), REVISION,
            "fixture-project", "", "", "", "", "owner-provider", "latest"
        )
    body = release.render_unit(
        "aureon-organ@hnc_core.service",
        PurePosixPath("/srv/aureon/runtime/workspace"),
        REVISION,
        "fixture-project",
        "",
        "",
        "",
        "",
        "owner-provider",
        "9",
    ).decode()
    assert "--provider-secret" not in body and "--project fixture-project" not in body
    assert "DynamicUser=yes" in body
    assert "AUREON_GOOGLE_TOKEN_FILE" not in body
    assert "aureon-cloud-token-broker.service" not in body
    assert "ReadOnlyPaths=/srv/aureon/runtime/workspace" in body
    assert "/srv/aureon/runtime/workspace" not in next(
        line for line in body.splitlines() if line.startswith("ReadWritePaths=")
    )


def test_terminal_receipt_collector_is_a_distinct_held_service():
    unit = "aureon-cloud-trade-receipt.service"
    body = release.render_unit(unit, PurePosixPath("/srv/aureon/runtime/workspace"), REVISION, "", "", "").decode()
    assert "cloud_trade_receipt_collector.py" in body
    assert "governed owner intent bridge (local executor held)" in body
    assert "--revision " + REVISION in body
    assert "Environment=AUREON_RELEASE_LEDGER_PATH=" + release.RELEASE_LEDGER_PATH in body
    assert "Environment=AUREON_ORDER_INTENT_STATUS_PATH=" + release.TRADE_BRIDGE_STATUS_PATH in body
    assert "--output " + release.TRADE_READBACK_PATH in body
    assert "User=aureon-trade-bridge" in body and "Group=aureon-trade-bridge" in body
    assert "SupplementaryGroups=aureon-control-readers" in body
    assert "Environment=AUREON_GOOGLE_TOKEN_FILE=/run/aureon-cloud-identity/trade-bridge/token.json" in body
    assert release.TRADE_READBACK_DIR in next(
        line for line in body.splitlines() if line.startswith("ReadWritePaths=")
    )
    assert release.RELEASE_LEDGER_DIR in next(
        line for line in body.splitlines() if line.startswith("ReadOnlyPaths=")
    )
    assert "/srv/aureon/runtime/workspace" not in next(
        line for line in body.splitlines() if line.startswith("ReadWritePaths=")
    )
    assert "ProtectProc=invisible" in body and "ProcSubset=pid" in body
    for address in release.METADATA_ADDRESSES:
        assert "IPAddressDeny=" + address in body
    for key, value in release.HOLDS.items():
        assert "Environment=" + key + "=" + value in body
    release.validate_service_names([unit])


def test_collector_release_manifest_requires_the_intent_bridge_dependency(tmp_path, monkeypatch):
    workspace, units, bundle, releases, _target, _runtime, services = fixture(tmp_path, monkeypatch)
    with pytest.raises(release.ReleaseError, match="trade_receipt_and_intent_bridge_sources_required"):
        release.prepare(
            bundle, workspace, releases, units,
            ["aureon-cloud-trade-receipt.service"], services,
        )


def test_operator_release_requires_the_complete_operator_runtime(
    tmp_path, monkeypatch
):
    workspace, units, bundle, releases, _target, _runtime, services = fixture(
        tmp_path, monkeypatch
    )
    unit = "aureon-cloud-operator.service"
    (units / unit).write_text("original unit\n")
    with pytest.raises(
        release.ReleaseError, match="operator_runtime_manifest_required"
    ):
        release.prepare(
            bundle,
            workspace,
            releases,
            units,
            [unit],
            services,
            project="fixture-project",
            secret="http-secret",
            version="1",
            tenant_secret="tenant-secret",
            tenant_version="1",
            provider_secret="provider-secret",
            provider_version="1",
            owner_subject=OWNER_SUBJECT,
            owner_email_sha256=OWNER_EMAIL_SHA256,
        )


def test_operator_release_dependency_is_exact_and_contains_no_key_material():
    package_tree = [
        "aureon-os-upstream/aureon/__init__.py",
        "aureon-os-upstream/aureon/operator/__init__.py",
        operator_closure.OPERATOR_ENTRYPOINT,
        "aureon-os-upstream/aureon/operator/transitive_dependency.py",
    ]
    required = operator_closure.required_operator_runtime_sources(package_tree)
    assert set(package_tree).issubset(required)
    assert operator_closure.OPERATOR_COMPANION_SOURCES.issubset(required)
    assert operator_closure.OPERATOR_DEPLOYMENT_SOURCES.issubset(required)
    assert set(required).isdisjoint(
        operator_closure.OPERATOR_PACKAGE_RUNTIME_STATE
    )
    assert all(
        release.source_path(path) == path
        for path in required
    )


def test_operator_apply_removes_stale_python_and_cache_transactionally(
    tmp_path, monkeypatch
):
    workspace = tmp_path / "workspace"
    units = tmp_path / "units"
    bundle = tmp_path / "bundle"
    releases = tmp_path / "releases"
    for path in (workspace, units, bundle / "files", releases):
        path.mkdir(parents=True)
    package_tree = [
        "aureon-os-upstream/aureon/__init__.py",
        "aureon-os-upstream/aureon/operator/__init__.py",
        operator_closure.OPERATOR_ENTRYPOINT,
        "aureon-os-upstream/aureon/operator/transitive_dependency.py",
    ]
    required = operator_closure.required_operator_runtime_sources(package_tree)
    rows = []
    for index, relative in enumerate(required):
        old = workspace / relative
        incoming = bundle / "files" / relative
        old.parent.mkdir(parents=True, exist_ok=True)
        incoming.parent.mkdir(parents=True, exist_ok=True)
        old.write_bytes(f"VALUE = 'old-{index}'\n".encode())
        data = f"VALUE = 'new-{index}'\n".encode()
        incoming.write_bytes(data)
        rows.append(
            {"path": relative, "sha256": release.digest(data), "size": len(data)}
        )
    stale_relative = "aureon-os-upstream/aureon/operator/obsolete.py"
    stale = workspace / stale_relative
    stale.write_bytes(b"VALUE = 'obsolete'\n")
    cache = stale.parent / "__pycache__/obsolete.cpython-312.pyc"
    cache.parent.mkdir()
    cache.write_bytes(b"stale bytecode")
    tree = "b" * 40
    unit = "aureon-cloud-operator.service"
    (units / unit).write_text("old unit\n")
    manifest = {
        "schema": release.SCHEMA,
        "revision": REVISION,
        "release_id": "20260913T130000Z-aaaaaaaa",
        "source_git_revision": REVISION,
        "source_git_tree": tree,
        "payload_sha256": release.manifest_payload_sha256(rows),
        "frontend_dist": None,
        "operator_runtime": operator_closure.build_operator_runtime_manifest(
            package_tree, rows, source_git_tree=tree
        ),
        "vm_python_runtime": vm_runtime_manifest(rows, package_tree),
        "token_broker": component_manifest(
            rows,
            release.TOKEN_BROKER_REQUIRED_SOURCES,
            "aureon.vm-token-broker-release.v1",
        ),
        "files": rows,
    }
    (bundle / "manifest.json").write_text(json.dumps(manifest))
    renderer = release.render_unit
    monkeypatch.setattr(
        release,
        "render_unit",
        lambda name, root, *args: renderer(
            name, PurePosixPath("/srv/aureon/runtime/workspace"), *args
        ),
    )
    services = Services(units, active=False)

    staged = release.prepare(
        bundle,
        workspace,
        releases,
        units,
        [unit],
        services,
        project="fixture-project",
        secret="http-secret",
        version="1",
        tenant_secret="tenant-secret",
        tenant_version="1",
        provider_secret="provider-secret",
        provider_version="1",
        owner_subject=OWNER_SUBJECT,
        owner_email_sha256=OWNER_EMAIL_SHA256,
        identity_snapshot=broker_identity,
    )
    journal = json.loads((staged / "journal.json").read_text())
    stale_entries = [
        entry for entry in journal["entries"] if entry["kind"] == "source_delete"
    ]
    assert [entry["path"] for entry in stale_entries] == [stale_relative]
    assert stale.exists() and cache.exists() and not services.events

    bootstrap_and_quiesce(staged, services)
    receipt, receipt_sha = authority_receipt(tmp_path)
    committed = release.apply(
        staged,
        services,
        held_health,
        authority_receipt=receipt,
        authority_receipt_sha256=receipt_sha,
        identity_snapshot=broker_identity,
        broker_health=broker_token_receipts,
        boot_id=lambda: BOOT_HASH,
    )
    assert committed["phase"] == "committed"
    assert not stale.exists() and not cache.exists()
    assert release.check(staged)["phase"] == "committed"

    release.rollback(staged, services, identity_snapshot=broker_identity)
    assert stale.read_bytes() == b"VALUE = 'obsolete'\n"
    assert not cache.exists()  # Derived bytecode is purged, never restored.
    assert release.check(staged)["phase"] == "rolled_back"


def test_collector_and_intent_bridge_can_only_be_prepared_together(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    units = tmp_path / "units"
    bundle = tmp_path / "bundle"
    releases = tmp_path / "releases"
    for path in (workspace, units, bundle / "files", releases):
        path.mkdir(parents=True)
    required_sources = (
        set(release.COLLECTOR_REQUIRED_SOURCES)
        | set(vm_runtime_sources())
        | set(release.TOKEN_BROKER_REQUIRED_SOURCES)
    )
    rows = []
    for relative in sorted(required_sources):
        data = b"VALUE = 'reviewed source fixture'\n"
        target = bundle / "files" / Path(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        rows.append({"path": relative, "sha256": release.digest(data), "size": len(data)})
    (bundle / "manifest.json").write_text(json.dumps({
        "schema": release.SCHEMA,
        "revision": REVISION,
        "release_id": "20260913T120000Z-aaaaaaaa",
        "source_git_revision": REVISION,
        "source_git_tree": "b" * 40,
        "payload_sha256": release.manifest_payload_sha256(rows),
        "frontend_dist": None,
        "vm_python_runtime": vm_runtime_manifest(rows),
        "token_broker": component_manifest(
            rows,
            release.TOKEN_BROKER_REQUIRED_SOURCES,
            "aureon.vm-token-broker-release.v1",
        ),
        "files": rows,
    }))
    unit = "aureon-cloud-trade-receipt.service"
    (units / unit).write_text("original unit\n")
    renderer = release.render_unit
    monkeypatch.setattr(
        release,
        "render_unit",
        lambda name, root, *args: renderer(
            name, PurePosixPath("/srv/aureon/runtime/workspace"), *args,
        ),
    )
    services = Services(units, active=False)
    staged = release.prepare(
        bundle,
        workspace,
        releases,
        units,
        [unit],
        services,
        identity_snapshot=broker_identity,
    )
    journal = json.loads((staged / "journal.json").read_text())
    source_paths = {
        entry["path"] for entry in journal["entries"] if entry["kind"] == "source"
    }
    assert source_paths == required_sources
    assert release.COLLECTOR_REQUIRED_SOURCES.issubset(source_paths)
    generated_unit = next(
        entry for entry in journal["entries"]
        if entry["kind"] == "unit" and entry["path"] == unit
    )
    assert release.digest((staged / "staged" / generated_unit["slot"]).read_bytes()) == generated_unit["after_sha256"]


def cutover_fixture(tmp_path, monkeypatch, *, original_identity=None):
    workspace = tmp_path / "workspace"
    units = tmp_path / "units"
    bundle = tmp_path / "bundle"
    releases = tmp_path / "releases"
    public_root = tmp_path / "public-entry"
    public_config = tmp_path / "etc-aureon-public"
    for path in (
        workspace,
        units,
        bundle / "files",
        releases,
        public_root,
        public_config,
    ):
        path.mkdir(parents=True)
    monkeypatch.setattr(release, "PUBLIC_BRIDGE_INSTALL_ROOT", public_root)
    monkeypatch.setattr(
        release, "PUBLIC_BRIDGE_INSTALL_SOURCE", public_root / "public_entry.py"
    )
    bridge_env = public_config / "bridge.env"
    bridge_env.write_bytes(
        b"AUREON_PUBLIC_ACCESS_MODE=hybrid\n"
        b"AUREON_ALLOWED_USER_EMAILS=legacy-owner@example.invalid\n"
        + f"AUREON_REVISION={OLD_REVISION}\n".encode("ascii")
        + b"AUREON_BRIDGE_URL=https://10.40.0.2:8443\n"
    )
    monkeypatch.setattr(release, "PUBLIC_BRIDGE_ENV", bridge_env)
    package_tree = sorted(MINIMAL_PACKAGE_TREE)
    required = (
        set(operator_closure.required_operator_runtime_sources(package_tree))
        | set(release.UI_GATEWAY_REQUIRED_SOURCES)
        | set(release.TOKEN_BROKER_REQUIRED_SOURCES)
        | set(release.PUBLIC_BRIDGE_REQUIRED_SOURCES)
        | set(vm_runtime_sources(package_tree))
    )
    rows = []
    for relative in sorted(required):
        if relative.endswith(".py"):
            data = b"VALUE = 'reviewed cutover source'\n"
        elif relative.endswith(".service"):
            data = b"[Unit]\nDescription=reviewed fixture\n"
        else:
            data = b"<!doctype html><title>Aureon</title>\n"
        target = bundle / "files" / Path(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        rows.append(
            {"path": relative, "sha256": release.digest(data), "size": len(data)}
        )
    indexed = {row["path"]: row for row in rows}
    certificate_sha = "c" * 64
    certificate_evidence = bridge_certificate_evidence()
    public_manifest = component_manifest(
        rows,
        release.PUBLIC_BRIDGE_REQUIRED_SOURCES,
        "aureon.vm-public-bridge-release.v1",
    )
    public_manifest.update(
        {
            "revision": REVISION,
            "source_sha256": indexed[release.PUBLIC_BRIDGE_SOURCE]["sha256"],
            "unit_sha256": indexed[release.PUBLIC_BRIDGE_UNIT_SOURCE]["sha256"],
            "certificate": {
                "path": str(release.PUBLIC_BRIDGE_CERTIFICATE),
                "algorithm": "x509-der-sha256",
                "sha256": certificate_sha,
                "receipt": {
                    "schema": "aureon.gcp.vm-public-bridge-certificate-receipt.v1",
                    "sha256": "d" * 64,
                    "project": release.GCP_PROJECT,
                    "zone": "europe-west1-b",
                    "instance": "aureon-sero-20260906",
                    "fingerprint_sha256": certificate_sha,
                    "recorded_at": datetime.now(UTC).isoformat(),
                    "required_ip_sans": certificate_evidence[
                        "required_ip_sans"
                    ],
                    "not_before": certificate_evidence["not_before"],
                    "not_after": certificate_evidence["not_after"],
                    "minimum_remaining_validity_seconds": 86_400,
                },
            },
        }
    )
    manifest = {
        "schema": release.SCHEMA,
        "revision": REVISION,
        "release_id": "20260913T150000Z-aaaaaaaa",
        "source_git_revision": REVISION,
        "source_git_tree": TREE,
        "payload_sha256": release.manifest_payload_sha256(rows),
        "operator_runtime": operator_closure.build_operator_runtime_manifest(
            package_tree, rows, source_git_tree=TREE
        ),
        "vm_python_runtime": vm_runtime_manifest(rows, package_tree),
        "frontend_dist": {
            "schema": "aureon.frontend-reproducible-build.v1",
            "entrypoint": "aureon-os-upstream/frontend/dist/index.html",
            "files": 1,
            "sha256": release.manifest_payload_sha256(
                [indexed["aureon-os-upstream/frontend/dist/index.html"]]
            ),
            "source_git_tree": TREE,
            "recipe": [
                "npm ci --ignore-scripts --no-audit --no-fund",
                "npm run build",
            ],
            "environment_keys": [
                "VITE_REQUIRE_AUTH",
                "VITE_SUPABASE_PUBLISHABLE_KEY",
                "VITE_SUPABASE_URL",
            ],
            "environment_sha256": "e" * 64,
            "toolchain": {"node": "v22.0.0", "npm": "10.0.0"},
        },
        "token_broker": component_manifest(
            rows,
            release.TOKEN_BROKER_REQUIRED_SOURCES,
            "aureon.vm-token-broker-release.v1",
        ),
        "public_bridge": public_manifest,
        "files": rows,
    }
    (bundle / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    selected = [
        "aureon-cloud-operator.service",
        "aureon-cloud-ui.service",
        release.PUBLIC_BRIDGE_UNIT,
    ]
    for unit in selected:
        (units / unit).write_text(f"old {unit}\n", encoding="utf-8")
    old_public_source = b"OLD_PUBLIC_ENTRY = True\n"
    (public_root / "public_entry.py").write_bytes(old_public_source)
    services = Services(units, active=False)
    for unit in selected:
        services.active[unit] = True
        services.enablement[unit] = True
    renderer = release.render_unit
    monkeypatch.setattr(
        release,
        "render_unit",
        lambda name, root, *args: renderer(
            name, PurePosixPath("/srv/aureon/runtime/workspace"), *args
        ),
    )
    identity = original_identity or broker_identity()
    def bridge_readback(expected, revision):
        environment = bridge_env.read_bytes()
        environment_revision = release._public_bridge_environment_revision(
            environment
        )
        iap_admin_email_sha256, plaintext_identity_names = (
            release._public_bridge_environment_identity(environment)
        )
        bridge_readback.expected_revisions.append(revision)
        if revision is not None and environment_revision != revision:
            raise release.ReleaseError(
                "public_bridge_environment_revision_mismatch"
            )
        return {
            "certificate_fingerprint_sha256": expected,
            "certificate_required_ip_sans": certificate_evidence[
                "required_ip_sans"
            ],
            "certificate_not_before": certificate_evidence["not_before"],
            "certificate_not_after": certificate_evidence["not_after"],
            "certificate_minimum_remaining_validity_seconds": 86_400,
            "private_key_preserved": True,
            "environment_revision": environment_revision,
            "environment_sha256": release.digest(environment),
            "iap_admin_email_sha256": iap_admin_email_sha256,
            "plaintext_identity_environment_names": plaintext_identity_names,
        }
    bridge_readback.expected_revisions = []
    staged = release.prepare(
        bundle,
        workspace,
        releases,
        units,
        selected,
        services,
        project="fixture-project",
        secret="http-secret",
        version="1",
        tenant_secret="tenant-secret",
        tenant_version="1",
        provider_secret="provider-secret",
        provider_version="1",
        owner_subject=OWNER_SUBJECT,
        owner_email_sha256=OWNER_EMAIL_SHA256,
        iap_admin_email_sha256=IAP_ADMIN_EMAIL_SHA256,
        identity_snapshot=lambda: identity,
        bridge_identity=bridge_readback,
    )
    return staged, services, units, public_root, old_public_source, bridge_readback


def apply_cutover(tmp_path, staged, services, bridge_readback, **kwargs):
    receipt, receipt_sha = authority_receipt(tmp_path)
    return release.apply(
        staged,
        services,
        held_health,
        authority_receipt=receipt,
        authority_receipt_sha256=receipt_sha,
        identity_snapshot=broker_identity,
        broker_health=broker_token_receipts,
        bridge_identity=bridge_readback,
        bridge_health=lambda *_: {
            "tls": True,
            "http_status": 401,
            "certificate_pinned": True,
            "response_sha256": "b" * 64,
        },
        boot_id=lambda: BOOT_HASH,
        **kwargs,
    )


def test_broker_release_requires_explicit_quiescence_before_apply(
    tmp_path, monkeypatch
):
    staged, services, _units, _root, _old, bridge_readback = cutover_fixture(
        tmp_path, monkeypatch
    )
    release.bootstrap_broker(staged, services)
    events_before = list(services.events)

    with pytest.raises(
        release.ReleaseError,
        match="cutover_quiescence_required_before_apply",
    ):
        apply_cutover(tmp_path, staged, services, bridge_readback)

    assert services.events == events_before
    assert json.loads((staged / "journal.json").read_text())["phase"] == (
        "broker_installed"
    )


def test_quiescence_records_exact_off_inventory_without_changing_rollback_state(
    tmp_path, monkeypatch
):
    staged, services, _units, _root, _old, _bridge_readback = cutover_fixture(
        tmp_path, monkeypatch
    )
    installed = release.bootstrap_broker(staged, services)
    original_services = json.loads(json.dumps(installed["original_services"]))
    event_offset = len(services.events)

    quiesced = release.quiesce_for_identity_cutover(staged, services)

    assert quiesced["phase"] == "quiesced"
    assert quiesced["original_services"] == original_services
    record = quiesced["cutover_quiescence"]
    assert record["schema"] == release.CUTOVER_QUIESCENCE_SCHEMA
    assert record["service_order"] == quiesced["services"]
    assert record["provider_readback"] == record["expected_services"]
    assert all(
        state["active"] is False
        and state["enabled"] is False
        and state["main_pid"] == 0
        for state in record["expected_services"].values()
    )
    assert all(not services.active.get(unit, False) for unit in quiesced["services"])
    assert all(
        not services.enablement.get(unit, False) for unit in quiesced["services"]
    )
    transition_events = services.events[event_offset:]
    last_disable = max(
        index for index, event in enumerate(transition_events) if event[0] == "enabled"
    )
    first_stop = min(
        index for index, event in enumerate(transition_events) if event[0] == "stop"
    )
    assert last_disable < first_stop
    assert not any(event[0] in {"start", "restart"} for event in transition_events)
    assert release.check(staged)["phase"] == "quiesced"


def test_interrupted_quiescence_resumes_from_only_recorded_reachable_states(
    tmp_path, monkeypatch
):
    staged, services, _units, _root, _old, _bridge_readback = cutover_fixture(
        tmp_path, monkeypatch
    )
    release.bootstrap_broker(staged, services)
    stop = services.stop
    failed = False

    def interrupt_once(unit):
        nonlocal failed
        if unit == "aureon-cloud-ui.service" and not failed:
            failed = True
            services.events.append(("stop-interrupted", unit))
            raise RuntimeError("simulated interruption")
        stop(unit)

    services.stop = interrupt_once
    with pytest.raises(RuntimeError, match="simulated interruption"):
        release.quiesce_for_identity_cutover(staged, services)
    assert json.loads((staged / "journal.json").read_text())["phase"] == "quiescing"
    with pytest.raises(
        release.ReleaseError, match="interrupted_transaction_requires_rollback"
    ):
        release.check(staged)

    services.stop = stop
    resumed = release.quiesce_for_identity_cutover(staged, services)
    assert resumed["phase"] == "quiesced"
    assert resumed["cutover_quiescence"]["provider_readback"] == resumed[
        "cutover_quiescence"
    ]["expected_services"]
    assert not any(event[0] in {"start", "restart"} for event in services.events)


def test_interrupted_quiescence_rejects_unrecorded_interim_service_state(
    tmp_path, monkeypatch
):
    staged, services, _units, _root, _old, _bridge_readback = cutover_fixture(
        tmp_path, monkeypatch
    )
    release.bootstrap_broker(staged, services)
    stop = services.stop

    def interrupt_on_ui(unit):
        if unit == "aureon-cloud-ui.service":
            raise RuntimeError("simulated interruption")
        stop(unit)

    services.stop = interrupt_on_ui
    with pytest.raises(RuntimeError, match="simulated interruption"):
        release.quiesce_for_identity_cutover(staged, services)
    services.stop = stop
    services.enablement[release.PUBLIC_BRIDGE_UNIT] = True
    events_before = list(services.events)

    with pytest.raises(
        release.ReleaseError,
        match="service_inventory_changed_during_quiescence",
    ):
        release.quiesce_for_identity_cutover(staged, services)

    assert services.events == events_before
    assert json.loads((staged / "journal.json").read_text())["phase"] == "quiescing"


def test_rollback_from_interrupted_quiescence_restores_exact_original_services(
    tmp_path, monkeypatch
):
    staged, services, units, _root, _old, _bridge_readback = cutover_fixture(
        tmp_path, monkeypatch
    )
    release.bootstrap_broker(staged, services)
    original = json.loads((staged / "journal.json").read_text())["original_services"]
    stop = services.stop

    def interrupt_after_one_stop(unit):
        stop(unit)
        services.stop = lambda _unit: (_ for _ in ()).throw(
            RuntimeError("simulated interruption")
        )

    services.stop = interrupt_after_one_stop
    with pytest.raises(RuntimeError, match="simulated interruption"):
        release.quiesce_for_identity_cutover(staged, services)
    services.stop = stop

    rolled = release.rollback(
        staged, services, identity_snapshot=broker_identity
    )

    assert rolled["phase"] == "rolled_back"
    assert rolled["original_services"] == original
    assert not (units / release.TOKEN_BROKER_UNIT).exists()
    for unit, state in original.items():
        assert services.snapshot(unit)["exists"] == state["exists"]
        assert services.snapshot(unit)["active"] == state["active"]
        assert services.snapshot(unit)["enabled"] == state["enabled"]


def test_apply_rejects_service_drift_after_quiescence_without_mutation(
    tmp_path, monkeypatch
):
    staged, services, _units, _root, _old, bridge_readback = cutover_fixture(
        tmp_path, monkeypatch
    )
    bootstrap_and_quiesce(staged, services)
    services.enablement["aureon-cloud-operator.service"] = True
    events_before = list(services.events)

    with pytest.raises(
        release.ReleaseError,
        match="service_inventory_changed_after_quiescence",
    ):
        apply_cutover(tmp_path, staged, services, bridge_readback)

    assert services.events == events_before
    assert json.loads((staged / "journal.json").read_text())["phase"] == "quiesced"


def test_quiesced_command_rejects_tampered_recorded_provider_readback(
    tmp_path, monkeypatch
):
    staged, services, _units, _root, _old, _bridge_readback = cutover_fixture(
        tmp_path, monkeypatch
    )
    bootstrap_and_quiesce(staged, services)
    journal = json.loads((staged / "journal.json").read_text())
    journal["cutover_quiescence"]["provider_readback"] = None
    (staged / "journal.json").write_text(json.dumps(journal), encoding="utf-8")
    events_before = list(services.events)

    with pytest.raises(
        release.ReleaseError,
        match="cutover_quiescence_journal_invalid",
    ):
        release.quiesce_for_identity_cutover(staged, services)

    assert services.events == events_before


def test_apply_accepts_quiesced_inventory_after_only_volatile_snapshot_changes(
    tmp_path, monkeypatch
):
    staged, services, _units, _root, _old, bridge_readback = cutover_fixture(
        tmp_path, monkeypatch
    )
    bootstrap_and_quiesce(staged, services)
    snapshot = services.snapshot
    observation = 0

    def with_reboot_volatile_fields(unit):
        nonlocal observation
        observation += 1
        return {
            **snapshot(unit),
            "result": "success",
            "exec_main_status": 0,
            "started_at": f"post-reboot-observation-{observation}",
        }

    services.snapshot = with_reboot_volatile_fields
    committed = apply_cutover(tmp_path, staged, services, bridge_readback)

    assert committed["phase"] == "committed"


def test_prepare_records_old_bridge_state_and_only_stages_contract_migration(
    tmp_path, monkeypatch
):
    staged, _services, _units, _root, _old, bridge_readback = cutover_fixture(
        tmp_path, monkeypatch
    )
    environment = release.PUBLIC_BRIDGE_ENV.read_bytes()
    journal = json.loads((staged / "journal.json").read_text())
    entry = next(
        row
        for row in journal["entries"]
        if row["kind"] == "public_bridge_environment"
    )
    staged_environment = (staged / "staged" / entry["slot"]).read_bytes()

    assert release._public_bridge_environment_revision(environment) == OLD_REVISION
    assert release._public_bridge_environment_identity(environment) == (
        None,
        ["AUREON_ALLOWED_USER_EMAILS"],
    )
    assert journal["public_bridge_identity"]["environment_revision"] == OLD_REVISION
    assert journal["public_bridge_identity"]["environment_sha256"] == release.digest(
        environment
    )
    assert entry["before_sha256"] == release.digest(environment)
    assert release._public_bridge_environment_revision(staged_environment) == REVISION
    commitment, plaintext_names = release._public_bridge_environment_identity(
        staged_environment
    )
    assert commitment == IAP_ADMIN_EMAIL_SHA256
    assert plaintext_names == []
    assert b"legacy-owner@example.invalid" not in staged_environment
    assert b"AUREON_PUBLIC_ACCESS_MODE=hybrid\n" in staged_environment
    assert b"AUREON_BRIDGE_URL=https://10.40.0.2:8443\n" in staged_environment
    assert bridge_readback.expected_revisions == [None]


def test_apply_refuses_changed_old_bridge_environment_before_service_cutover(
    tmp_path, monkeypatch
):
    staged, services, _units, _root, _old, bridge_readback = cutover_fixture(
        tmp_path, monkeypatch
    )
    bootstrap_and_quiesce(staged, services)
    release.PUBLIC_BRIDGE_ENV.write_bytes(
        release.PUBLIC_BRIDGE_ENV.read_bytes()
        + b"AUREON_OWNER_ORIGIN=https://changed.example\n"
    )
    events_before = list(services.events)

    with pytest.raises(
        release.ReleaseError,
        match="source_changed_after_prepare",
    ):
        apply_cutover(tmp_path, staged, services, bridge_readback)

    assert services.events == events_before
    assert release._public_bridge_environment_revision(
        release.PUBLIC_BRIDGE_ENV.read_bytes()
    ) == OLD_REVISION
    assert release._public_bridge_environment_identity(
        release.PUBLIC_BRIDGE_ENV.read_bytes()
    ) == (None, ["AUREON_ALLOWED_USER_EMAILS"])


def test_broker_start_failure_never_starts_dependents_and_requires_external_identity_rollback(
    tmp_path, monkeypatch
):
    old_identity = {
        **broker_identity(),
        "email": "aureon-cloud-runtime@aureon-trading.iam.gserviceaccount.com",
    }
    staged, services, _units, _public_root, _old, bridge_readback = cutover_fixture(
        tmp_path, monkeypatch, original_identity=old_identity
    )
    bootstrap_and_quiesce(staged, services)
    original_start = services.start

    def fail_broker(unit):
        if unit == release.TOKEN_BROKER_UNIT:
            services.events.append(("start-failed", unit))
            raise RuntimeError("broker failed")
        original_start(unit)

    services.start = fail_broker
    with pytest.raises(release.ReleaseError, match="external_identity_rollback_required"):
        apply_cutover(tmp_path, staged, services, bridge_readback)
    journal = json.loads((staged / "journal.json").read_text())
    assert journal["phase"] == "rollback_external_identity_required"
    assert not any(
        event[0] == "start" and event[1] != release.TOKEN_BROKER_UNIT
        for event in services.events
    )
    assert all(not services.active.get(unit, False) for unit in journal["services"])


def test_public_bridge_mid_replace_failure_restores_source_unit_and_service_state(
    tmp_path, monkeypatch
):
    staged, services, units, public_root, old_source, bridge_readback = cutover_fixture(
        tmp_path, monkeypatch
    )
    old_unit = (units / release.PUBLIC_BRIDGE_UNIT).read_bytes()
    bootstrap_and_quiesce(staged, services)
    installer = release._install_entry

    def fail_after_bridge(release_root, journal, entry):
        installer(release_root, journal, entry)
        if entry["kind"] == "public_bridge_source":
            raise RuntimeError("mid bridge replacement")

    monkeypatch.setattr(release, "_install_entry", fail_after_bridge)
    with pytest.raises(release.ReleaseError, match="source_rolled_back"):
        apply_cutover(tmp_path, staged, services, bridge_readback)
    assert (public_root / "public_entry.py").read_bytes() == old_source
    assert (units / release.PUBLIC_BRIDGE_UNIT).read_bytes() == old_unit
    assert release._public_bridge_environment_revision(
        release.PUBLIC_BRIDGE_ENV.read_bytes()
    ) == OLD_REVISION
    assert services.active[release.PUBLIC_BRIDGE_UNIT]


def test_release_refuses_vm_certificate_different_from_staged_build(
    tmp_path, monkeypatch
):
    staged, services, _units, _root, _old, bridge_readback = cutover_fixture(
        tmp_path, monkeypatch
    )
    bootstrap_and_quiesce(staged, services)

    def wrong_san(expected, revision):
        value = bridge_readback(expected, revision)
        value["certificate_required_ip_sans"] = ["10.40.0.3"]
        return value

    with pytest.raises(
        release.ReleaseError,
        match="public_bridge_certificate_evidence_mismatch",
    ):
        apply_cutover(tmp_path, staged, services, wrong_san)


def test_bridge_health_failure_rolls_back_and_success_starts_bridge_last(
    tmp_path, monkeypatch
):
    staged, services, units, public_root, old_source, bridge_readback = cutover_fixture(
        tmp_path, monkeypatch
    )
    old_unit = (units / release.PUBLIC_BRIDGE_UNIT).read_bytes()
    bootstrap_and_quiesce(staged, services)
    receipt, receipt_sha = authority_receipt(tmp_path)
    with pytest.raises(release.ReleaseError, match="source_rolled_back"):
        release.apply(
            staged,
            services,
            held_health,
            authority_receipt=receipt,
            authority_receipt_sha256=receipt_sha,
            identity_snapshot=broker_identity,
            broker_health=broker_token_receipts,
            bridge_identity=bridge_readback,
            bridge_health=lambda *_: (_ for _ in ()).throw(
                RuntimeError("bridge unavailable")
            ),
            boot_id=lambda: BOOT_HASH,
        )
    assert (public_root / "public_entry.py").read_bytes() == old_source
    assert (units / release.PUBLIC_BRIDGE_UNIT).read_bytes() == old_unit
    assert release._public_bridge_environment_revision(
        release.PUBLIC_BRIDGE_ENV.read_bytes()
    ) == OLD_REVISION
    assert release._public_bridge_environment_identity(
        release.PUBLIC_BRIDGE_ENV.read_bytes()
    ) == (None, ["AUREON_ALLOWED_USER_EMAILS"])
    assert services.active[release.PUBLIC_BRIDGE_UNIT]

    staged, services, _units, _root, _old, bridge_readback = cutover_fixture(
        tmp_path / "success", monkeypatch
    )
    bootstrap_and_quiesce(staged, services)
    committed = apply_cutover(tmp_path / "success", staged, services, bridge_readback)
    starts = [event[1] for event in services.events if event[0] == "start"]
    assert starts[0] == release.TOKEN_BROKER_UNIT
    assert starts[-1] == release.PUBLIC_BRIDGE_UNIT
    assert release._public_bridge_environment_revision(
        release.PUBLIC_BRIDGE_ENV.read_bytes()
    ) == REVISION
    assert committed["public_bridge_identity"]["environment_revision"] == REVISION
    assert committed["public_bridge_identity"]["iap_admin_email_sha256"] == (
        IAP_ADMIN_EMAIL_SHA256
    )
    assert committed["public_bridge_identity"][
        "plaintext_identity_environment_names"
    ] == []
    assert bridge_readback.expected_revisions == [
        None,
        OLD_REVISION,
        REVISION,
        REVISION,
    ]
    receipt_value = release.validate_vm_release_receipt(staged, committed)
    assert receipt_value["public_bridge_source_sha256"]
    assert receipt_value["public_bridge_certificate_sha256"] == "c" * 64
    assert "access_token" not in json.dumps(receipt_value)
    journal_paths = {entry["path"] for entry in committed["entries"]}
    assert str(release.PUBLIC_BRIDGE_PRIVATE_KEY) not in journal_paths
    assert str(release.PUBLIC_BRIDGE_CERTIFICATE) not in journal_paths
    reboot = release.record_vm_reboot_continuity(
        staged,
        services,
        identity_snapshot=broker_identity,
        broker_health=broker_token_receipts,
        health=held_health,
        bridge_identity=bridge_readback,
        bridge_health=lambda *_: {
            "tls": True,
            "http_status": 401,
            "certificate_pinned": True,
            "response_sha256": "b" * 64,
        },
        boot_id=lambda: "1" * 64,
    )
    reboot_value = json.loads((staged / "vm-reboot-continuity.json").read_text())
    assert reboot["sha256"] == release.digest(
        (staged / "vm-reboot-continuity.json").read_bytes()
    )
    assert reboot_value["schema"] == release.VM_REBOOT_CONTINUITY_SCHEMA
    assert reboot_value["boot_id_changed"] is True
    assert reboot_value["vm_release_receipt_sha256"] == committed[
        "vm_release_receipt"
    ]["sha256"]
    assert "access_token" not in json.dumps(reboot_value)
    assert release.check(staged)["phase"] == "committed"


def test_service_names_do_not_allow_foreign_units_or_duplicate_registry_http():
    for names in (["ssh.service"], [UNIT, UNIT], ["aureon-organ@operator_gateway.service"], ["aureon-organ@frontend_vite.service"]):
        with pytest.raises(release.ReleaseError):
            release.validate_service_names(names)


def test_metadata_identity_readback_binds_vm_placement_and_exact_broker_scope():
    root = "http://metadata.google.internal/computeMetadata/v1/"
    responses = {
        root + "project/project-id": b"aureon-trading\n",
        root + "instance/zone": b"projects/4435775023/zones/europe-west1-b\n",
        root + "instance/name": b"aureon-sero-20260906\n",
        root + "instance/service-accounts/default/email": (
            release.BROKER_SERVICE_ACCOUNT + "\n"
        ).encode("ascii"),
        root + "instance/service-accounts/default/scopes": (
            release.BROKER_SCOPE + "\n"
        ).encode("ascii"),
    }
    observed = release.metadata_identity_snapshot(responses.__getitem__)
    assert observed == broker_identity()
    release.require_broker_identity(observed)
    responses[root + "instance/service-accounts/default/scopes"] += (
        b"https://www.googleapis.com/auth/compute\n"
    )
    with pytest.raises(release.ReleaseError, match="attached_identity"):
        release.require_broker_identity(
            release.metadata_identity_snapshot(responses.__getitem__)
        )


def test_service_identity_is_checked_from_systemd_not_just_unit_name():
    systemd = object.__new__(release.Systemd)
    systemd.workspace = PurePosixPath("/srv/aureon/runtime/workspace")
    systemd.unit_root = PurePosixPath("/etc/systemd/system")
    systemd.allowed = {UNIT}
    def row(user=release.service_identity(UNIT), launcher="cloud_organ.py"):
        return ("LoadState=loaded\nActiveState=active\nSubState=running\nMainPID=123\nUnitFileState=enabled\nUser=" + user +
                "\nFragmentPath=/etc/systemd/system/aureon-organ@.service\nExecStart=/srv/aureon/venv/bin/python "
                "/srv/aureon/runtime/workspace/deployment/google-cloud/" + launcher + " hnc_core\n")
    systemd.run = lambda *args: row()
    assert systemd.snapshot(UNIT)["active"]
    systemd.run = lambda *args: row(user="aureon")
    assert systemd.snapshot(UNIT)["active"]  # exact legacy unit may migrate
    systemd.run = lambda *args: row(user="root")
    with pytest.raises(release.ReleaseError, match="ownership_unverified"):
        systemd.snapshot(UNIT)
    systemd.run = lambda *args: row(launcher="unrelated.py")
    with pytest.raises(release.ReleaseError, match="ownership_unverified"):
        systemd.snapshot(UNIT)


def test_managed_units_have_bounded_distinct_identities_and_private_state():
    ordinary = sorted(release.READ_ORGANS - release.PROVIDER_CONFIG_ORGANS)
    identities = {
        name: release.service_identity(f"aureon-organ@{name}.service")
        for name in ordinary
    }
    assert len(set(identities.values())) == len(ordinary)
    assert all(identity.startswith("aureon-organ-") for identity in identities.values())
    assert {
        release.service_identity(unit) for unit in release.HTTP_UNITS | release.COLLECTOR_UNITS
    } == {"aureon-operator", "aureon-ui", "aureon-trade-bridge"}


def test_source_parent_immutability_checks_every_ancestor(tmp_path, monkeypatch):
    workspace = (tmp_path / "workspace").resolve()
    package = (workspace / "aureon-os-upstream/aureon/operator").resolve()
    package.mkdir(parents=True)
    source = package / "operator_server.py"
    metadata = {}
    cursor = package
    while True:
        metadata[cursor] = (0o755, (0, 0))
        if cursor == workspace:
            break
        cursor = cursor.parent
    monkeypatch.setattr(release, "os", SimpleNamespace(name="posix"))
    monkeypatch.setattr(release, "_directory_metadata", lambda path: metadata[path])
    assert release.immutable_source_parent_metadata(source, workspace)
    metadata[workspace / "aureon-os-upstream"] = (0o775, (0, 0))
    assert not release.immutable_source_parent_metadata(source, workspace)
    metadata[workspace / "aureon-os-upstream"] = (0o755, (1000, 1000))
    assert not release.immutable_source_parent_metadata(source, workspace)


def test_posix_source_directory_plan_accepts_only_google_cloud_deployment_ancestor(
    tmp_path, monkeypatch
):
    workspace = (tmp_path / "workspace").resolve()
    workspace.mkdir()
    monkeypatch.setattr(release, "os", SimpleNamespace(name="posix"))

    plan = release.operator_source_directory_plan(
        workspace,
        frozenset({"deployment/google-cloud/cloud_operator.py"}),
    )

    assert [row["path"] for row in plan] == [
        ".",
        "deployment",
        "deployment/google-cloud",
    ]
    with pytest.raises(release.ReleaseError, match="deployment_path_not_allowed"):
        release.operator_source_directory_plan(
            workspace,
            frozenset({"deployment/not-google-cloud/tool.py"}),
        )


@pytest.mark.skipif(os.name != "posix" or os.geteuid() != 0, reason="root POSIX metadata transaction")
def test_source_directory_plan_hardens_and_rolls_back(tmp_path):
    workspace = tmp_path / "workspace"
    parent = workspace / "aureon-os-upstream/aureon/operator"
    parent.mkdir(parents=True)
    os.chmod(workspace, 0o777)
    os.chmod(parent, 0o777)
    sources = frozenset({operator_closure.OPERATOR_ENTRYPOINT})
    plan = release.operator_source_directory_plan(workspace, sources)
    release.apply_operator_source_directory_plan(workspace, plan)
    assert release.immutable_source_parent_metadata(
        parent / "operator_server.py", workspace
    )
    release.rollback_operator_source_directory_plan(workspace, plan)
    assert os.stat(workspace).st_mode & 0o022
