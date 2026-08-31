import hashlib
import io
import json
import tarfile

import pytest

from aureon.harmonic.hnc_quantum_packet_crypto import HNCPacketError, decode_hnc_swarm_packet
from aureon.vault.hnc_repo_singularity_vault import (
    build_repo_singularity_vault,
    decode_repo_singularity_archive,
    write_repo_singularity_vault,
)

AGENTS = {
    "seer": hashlib.sha256(b"seer-singularity-test-key").digest(),
    "lyra": hashlib.sha256(b"lyra-singularity-test-key").digest(),
    "king": hashlib.sha256(b"king-singularity-test-key").digest(),
}


def test_repo_singularity_manifest_is_non_destructive_and_skips_sensitive_profiles(tmp_path):
    (tmp_path / "aureon").mkdir()
    (tmp_path / "scripts").mkdir()
    (tmp_path / "aureon" / "core.py").write_text("print('alive')\n", encoding="utf-8")
    (tmp_path / ".env").write_text("SECRET=value\n", encoding="utf-8")
    (tmp_path / ".env1.txt").write_text("SECRET=value\n", encoding="utf-8")
    (tmp_path / "local.env").write_text("SECRET=value\n", encoding="utf-8")
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "runtime.log").write_text("noise", encoding="utf-8")

    report = build_repo_singularity_vault(tmp_path)

    paths = {record["path"] for record in report["files"]}
    skipped = {record["path"] for record in report["skipped"]}

    assert report["mode"] == "non_destructive_repo_wrapper"
    assert report["profile"]["live_working_tree_mutated"] is False
    assert "aureon/core.py" in paths
    assert ".env" in skipped
    assert ".env1.txt" in skipped
    assert "local.env" in skipped
    assert "logs" in skipped
    assert report["seal"]["sealed"] is False


def test_repo_singularity_seals_and_decodes_small_repo(tmp_path):
    (tmp_path / "aureon").mkdir()
    (tmp_path / "scripts").mkdir()
    (tmp_path / "aureon" / "core.py").write_text("print('alive')\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Test Repo\n", encoding="utf-8")

    report = build_repo_singularity_vault(tmp_path, seal=True, agent_secrets=AGENTS)
    packet = report["seal"]["packet"]
    archive_bytes = decode_repo_singularity_archive(
        packet,
        {"seer": AGENTS["seer"], "lyra": AGENTS["lyra"]},
        expected_root_sha256=report["summary"]["root_sha256"],
        expected_file_count=report["summary"]["file_count"],
    )

    assert report["status"] == "sealed_singularity_ready"
    assert report["seal"]["swarm_breaker"]["passed"] is True
    assert decode_hnc_swarm_packet(packet, {"seer": AGENTS["seer"], "king": AGENTS["king"]}).plaintext == archive_bytes

    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as archive:
        names = set(archive.getnames())
    assert "aureon/core.py" in names
    assert "README.md" in names
    assert "print('alive')" not in json.dumps(report["seal"]["packet"])


def test_repo_singularity_decode_requires_externally_pinned_snapshot_identity(tmp_path):
    (tmp_path / "aureon").mkdir()
    (tmp_path / "aureon" / "core.py").write_text("print('alive')\n", encoding="utf-8")
    report = build_repo_singularity_vault(tmp_path, seal=True, agent_secrets=AGENTS)
    packet = report["seal"]["packet"]
    available_agents = {"seer": AGENTS["seer"], "lyra": AGENTS["lyra"]}

    with pytest.raises(HNCPacketError, match="operator_aad_mismatch"):
        decode_repo_singularity_archive(
            packet,
            available_agents,
            expected_root_sha256="0" * 64,
            expected_file_count=report["summary"]["file_count"],
        )
    with pytest.raises(HNCPacketError, match="operator_aad_mismatch"):
        decode_repo_singularity_archive(
            packet,
            available_agents,
            expected_root_sha256=report["summary"]["root_sha256"],
            expected_file_count=report["summary"]["file_count"] + 1,
        )


def test_repo_singularity_writes_reports_and_obsidian_note(tmp_path):
    (tmp_path / "aureon").mkdir()
    (tmp_path / "scripts").mkdir()
    (tmp_path / "aureon" / "core.py").write_text("print('alive')\n", encoding="utf-8")
    report = build_repo_singularity_vault(tmp_path)

    output_json, output_md, public_json, obsidian = write_repo_singularity_vault(
        report,
        tmp_path / "docs" / "audits" / "aureon_repo_singularity_vault.json",
        tmp_path / "docs" / "audits" / "aureon_repo_singularity_vault.md",
        tmp_path / "frontend" / "public" / "aureon_repo_singularity_vault.json",
        tmp_path / ".obsidian" / "Aureon Self Understanding" / "aureon_hnc_singularity_vault.md",
    )

    assert output_json.exists()
    assert output_md.exists()
    assert public_json.exists()
    assert obsidian.exists()
    assert "must never hold raw agent keys" in obsidian.read_text(encoding="utf-8")
