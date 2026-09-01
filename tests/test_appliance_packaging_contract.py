from __future__ import annotations

import json
import subprocess
import tarfile
from io import BytesIO
from pathlib import Path

import pytest

from aureon.appliance import build_pipeline as pipeline

ROOT = Path(__file__).resolve().parents[1]
APPLIANCE = ROOT / "packaging" / "appliance"
PROFILE_PATH = APPLIANCE / "profile.json"
INPUTS_PATH = APPLIANCE / "inputs.example.json"


def _profile() -> dict:
    return pipeline.load_profile(PROFILE_PATH)


def _inputs() -> dict:
    return pipeline.load_inputs(INPUTS_PATH)


def test_profile_is_fail_closed_and_hnc_is_not_authority() -> None:
    profile = _profile()
    runtime = profile["runtime"]
    safe = runtime["safe_environment"]

    assert runtime["enabled_on_image"] == [
        "aureon-boot-attestation.service",
        "aureon-firstboot-console.service",
    ]
    assert runtime["enabled_after_firstboot"] == []
    assert safe["AUREON_AUDIT_MODE"] == "1"
    assert safe["AUREON_LIVE_TRADING"] == "0"
    assert safe["AUREON_DISABLE_REAL_ORDERS"] == "1"
    assert safe["AUREON_DISABLE_EXCHANGE_MUTATIONS"] == "1"
    assert safe["AUREON_LLM_OFFLINE"] == "1"
    assert safe["AUREON_DISABLE_LLM_HTTP"] == "1"
    assert safe["AUREON_LOCAL_ACTIONS_ARMED"] == "0"
    assert safe["AUREON_SOUL_ACT"] == "0"
    assert safe["AUREON_OPERATOR_HOST"] == "127.0.0.1"
    hnc = profile["hnc_evidence_policy"]
    assert hnc == {
        "model": "film_reel_engineering_translation_v1",
        "immutable_frames": True,
        "receipt_memory": True,
        "gamma_is_authority": False,
        "hard_gates_override": True,
    }
    assert profile["build"]["minimum_repart_version"] == 261


def test_profile_rejects_hnc_policy_drift(tmp_path: Path) -> None:
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    profile["hnc_evidence_policy"]["immutable_frames"] = False
    path = tmp_path / "profile.json"
    path.write_text(json.dumps(profile), encoding="utf-8")
    with pytest.raises(pipeline.ApplianceHold, match="HNC coherence must never replace hard gates"):
        pipeline.load_profile(path)


def test_payload_is_a_small_tracked_allowlist_without_sensitive_paths() -> None:
    paths = _profile()["build"]["payload_paths"]
    assert paths == [
        "LICENSE",
        "README.md",
        "aureon",
        "pyproject.toml",
        "scripts/bootstrap/protected_bootstrap_v05.py",
    ]
    tracked = set(
        subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
    )
    assert "LICENSE" in tracked
    assert "README.md" in tracked
    assert "pyproject.toml" in tracked
    assert any(item.startswith("aureon/") for item in tracked)
    assert (ROOT / "scripts" / "bootstrap" / "protected_bootstrap_v05.py").is_file()
    lowered = "\n".join(paths).lower()
    for denied in (".env", "state", "logs", "imports", "archive", "uploads", "data"):
        assert denied not in lowered


def test_payload_rejects_git_option_injection(tmp_path: Path) -> None:
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    profile["build"]["payload_paths"] = ["--add-file=/etc/shadow"]
    path = tmp_path / "profile.json"
    path.write_text(json.dumps(profile), encoding="utf-8")
    with pytest.raises(pipeline.ApplianceHold, match="option marker"):
        pipeline.load_profile(path)
    source = (ROOT / "aureon" / "appliance" / "build_pipeline.py").read_text(encoding="utf-8")
    assert 'inputs["source"]["commit"],\n                "--",\n                *payload' in source


def test_example_lock_is_structurally_valid_but_cannot_build() -> None:
    inputs = _inputs()
    assert inputs["source"]["commit"] == "f5fb1916c07ac26eb7fc38c34ff2dc9bd029e21d"
    report = pipeline.preflight(ROOT, PROFILE_PATH, INPUTS_PATH)
    assert report["status"] == "hold"
    codes = {item["code"] for item in report["checks"] if item["status"] == "hold"}
    assert codes & {"dirty_source", "missing_input", "linux_builder_required"}
    assert report["hnc_coherence_is_authority"] is False


def test_json_loader_rejects_duplicates_and_nonfinite_values() -> None:
    with pytest.raises(pipeline.ApplianceHold, match="duplicate JSON key"):
        pipeline._strict_json_bytes(b'{"schema":"x","schema":"y"}', label="test")
    with pytest.raises(pipeline.ApplianceHold, match="non-finite"):
        pipeline._strict_json_bytes(b'{"value":NaN}', label="test")


def test_mkosi_config_is_offline_bootable_and_deterministic() -> None:
    config = pipeline.render_mkosi_config(
        profile=_profile(),
        inputs=_inputs(),
        work_dir=Path("/unused"),
    )
    assert "Format=disk" in config
    assert "OutputExtension=iso" in config
    assert "Bootable=yes" in config
    assert "Bootloader=systemd-boot" in config
    assert "ElTorito=yes" in config
    assert "CacheOnly=always" in config
    assert "WithNetwork=no" in config
    assert "Ssh=never" in config
    assert "SourceDateEpoch=1786688033" in config
    assert "History=no" in config
    assert "KernelCommandLine=console=tty0 console=ttyS0,115200n8" in config
    assert "http://" not in config
    assert "https://" not in config
    content_section = config.split("[Content]\n", 1)[1].split("[Build]\n", 1)[0]
    build_section = config.split("[Build]\n", 1)[1]
    assert "SourceDateEpoch=1786688033" in content_section
    assert "SourceDateEpoch=" not in build_section

    percent_inputs = _inputs()
    percent_inputs["base_tree"]["path"] = "/locked/%D/base.raw"
    percent_config = pipeline.render_mkosi_config(
        profile=_profile(), inputs=percent_inputs, work_dir=Path("/unused")
    )
    assert 'BaseTrees="/locked/%%D/base.raw"' in percent_config


def test_mkosi_capability_probe_parses_the_exact_rendered_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    verbs: list[str] = []
    profile = _profile()

    def fake_run(argv: tuple[str, ...], **_: object) -> subprocess.CompletedProcess[str]:
        verbs.append(argv[-1])
        if argv[-1] == "cat-config":
            config = (Path(argv[2]) / "mkosi.conf").read_text(encoding="utf-8")
            return subprocess.CompletedProcess(argv, 0, config, "")
        output = f"{profile['image']['id']}-{profile['image']['version']}.iso"
        output_directory = Path(argv[2]) / "artifacts"
        summary = (
            "Output Format: disk\n"
            f"Output: {output}\n"
            f"Output Directory: {output_directory}\n"
            "El Torito: enabled\n"
            "Source Date Epoch: 1786688033\n"
            "Bootable: enabled\n"
            "Bootloader: systemd-boot\n"
        )
        return subprocess.CompletedProcess(argv, 0, summary, "")

    monkeypatch.setattr(pipeline, "_run_checked", fake_run)
    monkeypatch.setattr(pipeline, "_minimal_env", lambda *_: {"PATH": "/usr/bin:/bin"})
    digest = pipeline._verify_mkosi_config(
        mkosi=tmp_path / "mkosi",
        profile=profile,
        inputs=_inputs(),
        repo=ROOT,
        epoch=1786688033,
    )
    assert verbs == ["summary", "cat-config"]
    assert len(digest) == 64


def test_mkosi_capability_probe_rejects_ignored_unknown_settings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_old_mkosi(argv: tuple[str, ...], **_: object) -> subprocess.CompletedProcess[str]:
        if argv[-1] == "cat-config":
            config = (Path(argv[2]) / "mkosi.conf").read_text(encoding="utf-8")
            return subprocess.CompletedProcess(argv, 0, config, "")
        return subprocess.CompletedProcess(
            argv,
            0,
            "Output Format: disk\nOutput: aureon.raw\nSource Date Epoch: none\n",
            "Unknown setting ElTorito\n",
        )

    monkeypatch.setattr(pipeline, "_run_checked", fake_old_mkosi)
    monkeypatch.setattr(pipeline, "_minimal_env", lambda *_: {"PATH": "/usr/bin:/bin"})
    with pytest.raises(pipeline.ApplianceHold, match="compatibility warning"):
        pipeline._verify_mkosi_config(
            mkosi=tmp_path / "old-mkosi",
            profile=_profile(),
            inputs=_inputs(),
            repo=ROOT,
            epoch=1786688033,
        )


def test_mkosi_capability_probe_does_not_scan_rendered_paths_as_warnings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    profile = _profile()
    inputs = _inputs()
    inputs["base_tree"]["path"] = "/locked/unknown setting/base.raw"

    def fake_run(argv: tuple[str, ...], **_: object) -> subprocess.CompletedProcess[str]:
        if argv[-1] == "cat-config":
            config = (Path(argv[2]) / "mkosi.conf").read_text(encoding="utf-8")
            assert "unknown setting" in config
            return subprocess.CompletedProcess(argv, 0, config, "")
        output_directory = Path(argv[2]) / "artifacts"
        summary = (
            "Output Format: disk\n"
            f"Output: {profile['image']['id']}-{profile['image']['version']}.iso\n"
            f"Output Directory: {output_directory}\n"
            "El Torito: enabled\n"
            "Source Date Epoch: 1786688033\n"
            "Bootable: enabled\n"
            "Bootloader: systemd-boot\n"
        )
        return subprocess.CompletedProcess(argv, 0, summary, "")

    monkeypatch.setattr(pipeline, "_run_checked", fake_run)
    monkeypatch.setattr(pipeline, "_minimal_env", lambda *_: {"PATH": "/usr/bin:/bin"})
    digest = pipeline._verify_mkosi_config(
        mkosi=tmp_path / "mkosi",
        profile=profile,
        inputs=inputs,
        repo=ROOT,
        epoch=1786688033,
    )
    assert len(digest) == 64


def test_mkosi_capability_probe_does_not_confuse_output_directory_with_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_run(argv: tuple[str, ...], **_: object) -> subprocess.CompletedProcess[str]:
        if argv[-1] == "cat-config":
            config = (Path(argv[2]) / "mkosi.conf").read_text(encoding="utf-8")
            return subprocess.CompletedProcess(argv, 0, config, "")
        summary = (
            "Output Format: disk\n"
            f"Output Directory: {Path(argv[2]) / 'artifacts'}\n"
            "El Torito: enabled\n"
            "Source Date Epoch: 1786688033\n"
            "Bootable: enabled\n"
            "Bootloader: systemd-boot\n"
        )
        return subprocess.CompletedProcess(argv, 0, summary, "")

    monkeypatch.setattr(pipeline, "_run_checked", fake_run)
    monkeypatch.setattr(pipeline, "_minimal_env", lambda *_: {"PATH": "/usr/bin:/bin"})
    with pytest.raises(pipeline.ApplianceHold, match="omitted resolved field: Output"):
        pipeline._verify_mkosi_config(
            mkosi=tmp_path / "mkosi",
            profile=_profile(),
            inputs=_inputs(),
            repo=ROOT,
            epoch=1786688033,
        )


def test_command_plan_has_exact_argv_and_never_uses_shell_text(tmp_path: Path) -> None:
    plan = pipeline.build_command_plan(profile=_profile(), inputs=_inputs(), work_dir=tmp_path)
    assert plan["image"][-1] == "build"
    assert plan["image"][1:3] == ["--directory", str(tmp_path)]
    assert plan["vhdx"][1:8] == [
        "convert",
        "-f",
        "raw",
        "-O",
        "vhdx",
        "-o",
        "subformat=fixed,block_size=2097152",
    ]
    assert plan["vhdx_check"][1:4] == ["check", "-f", "vhdx"]
    assert all(isinstance(argv, list) for argv in plan.values())
    assert not any("curl" in item or "wget" in item for argv in plan.values() for item in argv)


def test_receipt_ledger_is_hash_chained_and_detects_tampering(tmp_path: Path) -> None:
    ledger = pipeline.ReceiptLedger(tmp_path / "receipts.jsonl")
    first = ledger.append(stage="preflight", status="hold", evidence={"reason": "base_missing"})
    second = ledger.append(stage="stage", status="pass", evidence={"source": "locked"})
    assert first["previous_sha256"] == "0" * 64
    assert second["previous_sha256"] == first["entry_sha256"]
    assert len(ledger._validated_entries()) == 2

    lines = ledger.path.read_text(encoding="utf-8").splitlines()
    tampered = json.loads(lines[0])
    tampered["status"] = "pass"
    lines[0] = json.dumps(tampered, sort_keys=True, separators=(",", ":"))
    ledger.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(pipeline.ApplianceHold, match="hash mismatch"):
        ledger._validated_entries()


def test_receipt_ledger_refuses_a_concurrent_writer_lock(tmp_path: Path) -> None:
    ledger = pipeline.ReceiptLedger(tmp_path / "receipts.jsonl")
    (tmp_path / "receipts.jsonl.lock").write_text("occupied", encoding="ascii")
    with pytest.raises(pipeline.ApplianceHold, match="exclusive receipt writer lock"):
        ledger.append(stage="stage", status="pass", evidence={})


def test_operation_lease_serializes_the_entire_work_directory(tmp_path: Path) -> None:
    work_dir = tmp_path / "image-work"
    lock_path = tmp_path / ".image-work.operation.lock"
    with pipeline._operation_lease(work_dir):
        assert lock_path.is_file()
        with (
            pytest.raises(pipeline.ApplianceHold, match="exclusive appliance operation lock"),
            pipeline._operation_lease(work_dir),
        ):
            pass
    assert not lock_path.exists()


@pytest.mark.skipif(pipeline.os.name != "nt", reason="Windows path grammar")
def test_windows_input_paths_reject_network_and_named_streams(tmp_path: Path) -> None:
    with pytest.raises(pipeline.ApplianceHold, match="UNC or device"):
        pipeline._assert_safe_existing_file(Path(r"\\server\share\input.json"), label="input")
    with pytest.raises(pipeline.ApplianceHold, match="alternate data stream"):
        pipeline._assert_safe_existing_file(Path(str(tmp_path / "input.json") + ":payload"), label="input")


def test_source_tar_extractor_rejects_links_and_secret_names(tmp_path: Path) -> None:
    link_tar = tmp_path / "link.tar"
    with tarfile.open(link_tar, "w") as archive:
        member = tarfile.TarInfo("aureon/link")
        member.type = tarfile.SYMTYPE
        member.linkname = "/etc/passwd"
        archive.addfile(member)
    with pytest.raises(pipeline.ApplianceHold, match="special/link"):
        pipeline._safe_extract_tar(link_tar, tmp_path / "out-link")

    secret_tar = tmp_path / "secret.tar"
    with tarfile.open(secret_tar, "w") as archive:
        raw = b"secret"
        member = tarfile.TarInfo("aureon/.env")
        member.size = len(raw)
        archive.addfile(member, BytesIO(raw))
    with pytest.raises(pipeline.ApplianceHold, match="payload member"):
        pipeline._safe_extract_tar(secret_tar, tmp_path / "out-secret")


def test_requirements_lock_forbids_network_and_requires_hashes(tmp_path: Path) -> None:
    good = tmp_path / "good.lock"
    good.write_text(
        "flask==3.1.2 \\\n" + "    --hash=sha256:" + "a" * 64 + "\n",
        encoding="utf-8",
    )
    pipeline._validate_requirements_lock(good)

    network = tmp_path / "network.lock"
    network.write_text("thing @ https://example.test/thing.whl\n", encoding="utf-8")
    with pytest.raises(pipeline.ApplianceHold, match="network"):
        pipeline._validate_requirements_lock(network)

    unhashed = tmp_path / "unhashed.lock"
    unhashed.write_text("flask==3.1.2\n", encoding="utf-8")
    with pytest.raises(pipeline.ApplianceHold, match="hash"):
        pipeline._validate_requirements_lock(unhashed)

    borrowed_hash = tmp_path / "borrowed-hash.lock"
    borrowed_hash.write_text(
        "one==1 \\\n"
        + "    --hash=sha256:"
        + "a" * 64
        + " \\\n"
        + "    --hash=sha256:"
        + "b" * 64
        + "\ntwo==2\n",
        encoding="utf-8",
    )
    with pytest.raises(pipeline.ApplianceHold, match="logical entry"):
        pipeline._validate_requirements_lock(borrowed_hash)

    include = tmp_path / "include.lock"
    include.write_text("-r nested.lock==1 --hash=sha256:" + "c" * 64 + "\n", encoding="utf-8")
    with pytest.raises(pipeline.ApplianceHold, match="logical entry"):
        pipeline._validate_requirements_lock(include)


def test_staged_digest_rejects_any_extra_mkosi_discovery_input(tmp_path: Path) -> None:
    for name in ("mkosi.conf", "mkosi.seed", "mkosi.postinst.chroot", "mkosi.finalize.chroot"):
        (tmp_path / name).write_text(name, encoding="utf-8")
    (tmp_path / "mkosi.extra").mkdir()
    (tmp_path / "mkosi.repart").mkdir()
    baseline = pipeline._staged_input_digest(tmp_path)
    assert len(baseline) == 64

    (tmp_path / "mkosi.conf.d").mkdir()
    (tmp_path / "mkosi.conf.d" / "override.conf").write_text(
        "[Build]\nWithNetwork=yes\n", encoding="utf-8"
    )
    with pytest.raises(pipeline.ApplianceHold, match="auto-discovered by mkosi"):
        pipeline._staged_input_digest(tmp_path)


def test_stage_exports_the_appliance_template_from_the_locked_git_object() -> None:
    source = (ROOT / "aureon" / "appliance" / "build_pipeline.py").read_text(encoding="utf-8")
    assert '"packaging/appliance/rootfs"' in source
    assert '"packaging/appliance/mkosi.repart"' in source
    assert '"packaging/appliance/mkosi.postinst.chroot"' in source
    assert '"packaging/appliance/mkosi.finalize.chroot"' in source
    assert 'template_dir = template_snapshot / "packaging" / "appliance"' in source
    assert "shutil.rmtree(template_snapshot)" in source


def test_appliance_units_are_firstboot_gated_and_do_not_start_trading() -> None:
    unit_root = APPLIANCE / "rootfs" / "usr" / "lib" / "systemd" / "system"
    target = (unit_root / "aureon-appliance.target").read_text(encoding="utf-8")
    assert "ConditionPathExists=/etc/aureon/firstboot.complete" in target
    assert "Requires=aureon-operator.service aureon-organism.service aureon-hnc.service" in target
    assert "trading" not in target.lower()

    operator = (unit_root / "aureon-operator.service").read_text(encoding="utf-8")
    assert "EnvironmentFile=" not in operator
    assert "protected_bootstrap_v05.py --target-id operator" in operator
    assert "Restart=no" in operator
    assert "IPAddressAllow=" not in operator
    assert "IPAddressDeny=any" in operator
    assert "0.0.0.0" not in operator

    for name in ("aureon-organism.service", "aureon-hnc.service"):
        source = (unit_root / name).read_text(encoding="utf-8")
        assert "RestrictAddressFamilies=AF_UNIX" in source
        assert "ConditionPathExists=/etc/aureon/firstboot.complete" in source

    console = (unit_root / "aureon-firstboot-console.service").read_text(encoding="utf-8")
    assert "ExecStart=/usr/sbin/aureon-firstboot --console-gate" in console
    assert "TTYPath=/dev/tty1" in console
    assert "ConditionPathExists=!/etc/aureon/firstboot.complete" in console

    firstboot = (APPLIANCE / "rootfs" / "usr" / "sbin" / "aureon-firstboot").read_text(
        encoding="utf-8"
    )
    assert '"decision":"HOLD"' in firstboot
    assert '"process_start_authorized":false' in firstboot
    assert '"target_enabled":false' in firstboot
    assert '"file_written":false' in firstboot
    assert '"network_accessed":false' in firstboot
    assert "systemctl" not in firstboot
    assert "install " not in firstboot
    assert "ENABLE AUREON" not in firstboot


def test_postinstall_is_offline_and_omits_identity_material() -> None:
    source = (APPLIANCE / "mkosi.postinst.chroot").read_text(encoding="utf-8")
    assert 'WITH_NETWORK:-1}' in source
    assert "PIP_NO_INDEX=1" in source
    assert "--no-index" in source
    assert "--require-hashes" in source
    assert "rm -f /etc/ssh/ssh_host_* /var/lib/systemd/random-seed" in source
    assert "install -m 0444 /dev/null /etc/machine-id" in source
    assert "find /etc/systemd/system -depth -name 'aureon-*'" in source
    assert "rm -f -- /etc/aureon/firstboot.complete" in source
    assert "systemctl mask getty@tty1.service" in source
    assert "systemctl enable aureon-boot-attestation.service aureon-firstboot-console.service" in source
    for forbidden in ("curl ", "wget ", "apt-get ", "npm ", "git clone", "cp .env"):
        assert forbidden not in source

    finalize = (APPLIANCE / "mkosi.finalize.chroot").read_text(encoding="utf-8")
    assert 'WITH_NETWORK:-1}' in finalize
    assert "systemctl disable aureon-appliance.target" in finalize
    assert "systemctl enable aureon-boot-attestation.service aureon-firstboot-console.service" in finalize
    assert "/etc/systemd/system.control" in finalize
    assert "/run/systemd/transient" in finalize
    assert "/run/systemd/generator.early" in finalize
    assert "/usr/local/lib/systemd/system" in finalize
    assert "service.d target.d" in finalize
    assert "aureon-*.service.d" in finalize
    assert 'test ! -L "$override_root/$unit.d"' in finalize
    assert 'test ! -L "/usr/lib/systemd/system/$unit.d"' in finalize
    assert "test ! -e /etc/aureon/firstboot.complete" in finalize

    attest = (APPLIANCE / "rootfs" / "usr" / "lib" / "aureon" / "aureon-boot-attest").read_text(
        encoding="utf-8"
    )
    assert "FragmentPath" in attest
    assert "DropInPaths" in attest
    assert "AUREON_APPLIANCE_POLICY_HOLD" in attest
    assert "require_enablement" in attest
    assert "aureon-boot-attestation.service enabled" in attest
    assert "aureon-firstboot-console.service enabled" in attest
    assert "getty@tty1.service masked" in attest
    assert 'require_enablement "$unit" disabled' in attest
    assert "unexpected_firstboot_marker" in attest
    assert '"status":"pass"' not in attest
    assert "AUREON_APPLIANCE_BOOTABLE_PROVISIONED" not in attest


def test_boot_verifier_is_networkless_snapshot_only() -> None:
    source = (ROOT / "aureon" / "appliance" / "build_pipeline.py").read_text(encoding="utf-8")
    assert '"-nic",' in source and '"none",' in source
    assert '"-snapshot"' in source
    assert '"order=d"' in source
    assert "media=cdrom,readonly=on,format=raw" in source
    assert "AUREON_APPLIANCE_BOOTABLE_PROTECTION_HOLD" in source
    assert "shell=False" in source


def test_boot_attestation_requires_structured_adjacent_evidence_and_no_policy_hold() -> None:
    attestation = json.dumps(pipeline.BOOT_ATTESTATION, sort_keys=True, separators=(",", ":"))
    serial = f"kernel booted\n{pipeline.BOOT_MARKER}\n{attestation}\n"
    pipeline._validate_boot_attestation(serial, media_kind="vhdx")

    with pytest.raises(pipeline.ApplianceHold, match="attestation JSON"):
        pipeline._validate_boot_attestation(pipeline.BOOT_MARKER + "\n", media_kind="iso")
    with pytest.raises(pipeline.ApplianceHold, match="policy HOLD"):
        pipeline._validate_boot_attestation(
            "AUREON_APPLIANCE_POLICY_HOLD\n" + serial, media_kind="iso"
        )


def test_qemu_keyval_paths_reject_comma_option_injection(tmp_path: Path) -> None:
    unsafe = tmp_path / "disk,file=outside.vhdx"
    with pytest.raises(pipeline.ApplianceHold, match="QEMU key/value"):
        pipeline._qemu_keyval_path(unsafe, label="test disk")


def test_hyperv_handoff_is_a_terminal_no_mutation_hold() -> None:
    source = (APPLIANCE / "hyperv" / "Register-AureonAppliance.ps1").read_text(encoding="utf-8")
    assert "#Requires -RunAsAdministrator" not in source
    assert "'HOLD'" in source
    assert "vm_created = $false" in source
    assert "vhdx_copied = $false" in source
    assert "vm_started = $false" in source
    assert "receipt_written = $false" in source
    assert "native_appliance_release_boundary_required" in source
    for forbidden in (
        "Import-Module Hyper-V",
        "New-VM",
        "Start-VM",
        "CopyTo(",
        "Move-Item",
        "Remove-Item",
        "Set-VMFirmware",
        "Test-VHD",
    ):
        assert forbidden not in source


def test_appliance_services_do_not_collide_with_deploy_inventory() -> None:
    appliance_services = list(APPLIANCE.rglob("*.service"))
    assert appliance_services
    assert all("deploy" not in path.parts for path in appliance_services)


def test_appliance_ci_parses_each_shell_script_individually() -> None:
    workflow = (ROOT / ".github" / "workflows" / "appliance-ci.yml").read_text(encoding="utf-8")
    assert "for script in \\" in workflow
    assert 'bash -n "$script"' in workflow
    assert "done" in workflow
