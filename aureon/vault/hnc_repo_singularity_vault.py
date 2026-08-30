"""Repo singularity vault.

The singularity vault wraps the repository as evidence without mutating the live
working tree. It produces a Merkle-like file manifest, optional HNC swarm-sealed
archive packet, and an Obsidian key-holder note that stores no raw keys.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import io
import json
import os
import tarfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from aureon.obsidian_paths import resolve_obsidian_note_path
from aureon.harmonic.hnc_quantum_packet_crypto import (
    HNCPacketError,
    build_hnc_swarm_packet,
    decode_hnc_swarm_packet,
    packet_public_summary,
    run_hnc_swarm_breaker_checks,
    stream_hnc_probability_fragments,
)


SCHEMA_VERSION = "aureon-repo-singularity-vault-v1"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_JSON = REPO_ROOT / "docs/audits/aureon_repo_singularity_vault.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs/audits/aureon_repo_singularity_vault.md"
DEFAULT_PUBLIC_JSON = REPO_ROOT / "frontend/public/aureon_repo_singularity_vault.json"
DEFAULT_OBSIDIAN_NOTE = Path(".obsidian/Aureon Self Understanding/aureon_hnc_singularity_vault.md")
DEFAULT_SEALED_PACKET_BLOB = REPO_ROOT / "state/aureon_repo_singularity_vault_packet.json"

DEFAULT_EXCLUDES = (
    ".git/**",
    ".venv/**",
    ".pytest_cache/**",
    ".env",
    ".env*",
    ".env.*",
    "*.env",
    "*.env.*",
    "**/__pycache__/**",
    "frontend/node_modules/**",
    "frontend/dist/**",
    "node_modules/**",
    "logs/**",
    "state/**",
    "bussiness accounts/**",
    "*.bak-*",
    "*.tmp-*",
    "thoughts.jsonl",
    "*.log",
    "*.zip",
    "*.png",
    "*.pdf",
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    "id_rsa",
    "id_rsa.pub",
)

DEFAULT_EXCLUDE_DIRS = {
    ".git",
    ".venv",
    ".pytest_cache",
    "__pycache__",
    "node_modules",
    "dist",
    "logs",
    "state",
    "bussiness accounts",
    "queen_backups",
    "harmonic_cache",
    "ws_cache",
}


@dataclass(frozen=True)
class RepoFileRecord:
    path: str
    size_bytes: int
    sha256: str
    modified_at: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _matches_any(path: str, patterns: Iterable[str]) -> bool:
    normal = path.replace("\\", "/")
    return any(fnmatch.fnmatch(normal, pattern) for pattern in patterns)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _display_path(path: Path) -> str:
    if not path.is_absolute():
        return path.as_posix()
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except Exception:
        return str(path)


def sanitize_report_for_repository(report: Mapping[str, Any]) -> dict[str, Any]:
    public_report = json.loads(json.dumps(report, default=str))
    public_report["repo_root"] = "."
    public_report.pop("key_store", None)
    summary = public_report.get("summary")
    if isinstance(summary, dict):
        summary["obsidian_key_holder"] = _display_path(DEFAULT_OBSIDIAN_NOTE)
    seal = public_report.get("seal")
    if isinstance(seal, dict):
        blob = str(seal.get("sealed_packet_blob") or "")
        if blob:
            seal["sealed_packet_blob"] = _display_path(Path(blob))
        seal.pop("packet", None)
        seal.pop("fragments", None)
    return public_report


def discover_repo_files(
    repo_root: Path = REPO_ROOT,
    *,
    excludes: Iterable[str] = DEFAULT_EXCLUDES,
    max_file_size_mb: float = 25.0,
    include_large: bool = False,
) -> tuple[list[RepoFileRecord], list[dict[str, Any]]]:
    root = repo_root.resolve()
    max_bytes = int(max_file_size_mb * 1024 * 1024)
    records: list[RepoFileRecord] = []
    skipped: list[dict[str, Any]] = []
    for current, dirnames, filenames in os.walk(root):
        current_path = Path(current)
        rel_dir = current_path.relative_to(root).as_posix() if current_path != root else ""
        kept_dirs: list[str] = []
        for dirname in sorted(dirnames):
            rel_child = f"{rel_dir}/{dirname}".strip("/")
            if dirname in DEFAULT_EXCLUDE_DIRS or _matches_any(f"{rel_child}/**", excludes):
                skipped.append({"path": rel_child, "reason": "excluded_directory_by_profile"})
                continue
            kept_dirs.append(dirname)
        dirnames[:] = kept_dirs
        for filename in sorted(filenames):
            path = current_path / filename
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            if _matches_any(rel, excludes):
                skipped.append({"path": rel, "reason": "excluded_by_profile"})
                continue
            try:
                stat = path.stat()
            except OSError as exc:
                skipped.append({"path": rel, "reason": f"stat_failed:{type(exc).__name__}"})
                continue
            if not include_large and stat.st_size > max_bytes:
                skipped.append({"path": rel, "reason": "too_large_for_default_singularity_profile", "size_bytes": stat.st_size})
                continue
            try:
                records.append(
                    RepoFileRecord(
                        path=rel,
                        size_bytes=stat.st_size,
                        sha256=_sha256_file(path),
                        modified_at=datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                    )
                )
            except OSError as exc:
                skipped.append({"path": rel, "reason": f"read_failed:{type(exc).__name__}"})
    records.sort(key=lambda record: record.path)
    skipped.sort(key=lambda item: str(item.get("path")))
    return records, skipped


def _root_hash(records: list[RepoFileRecord]) -> str:
    digest = hashlib.sha256()
    for record in records:
        digest.update(json.dumps(record.__dict__, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    return digest.hexdigest()


def build_repo_singularity_manifest(
    repo_root: Path = REPO_ROOT,
    *,
    max_file_size_mb: float = 25.0,
    include_large: bool = False,
) -> dict[str, Any]:
    records, skipped = discover_repo_files(
        repo_root,
        max_file_size_mb=max_file_size_mb,
        include_large=include_large,
    )
    total_bytes = sum(record.size_bytes for record in records)
    root_hash = _root_hash(records)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "status": "manifest_ready",
        "mode": "non_destructive_repo_wrapper",
        "repo_root": str(repo_root.resolve()),
        "profile": {
            "name": "safe_source_manifest",
            "include_large": include_large,
            "max_file_size_mb": max_file_size_mb,
            "excludes": list(DEFAULT_EXCLUDES),
            "live_working_tree_mutated": False,
            "secret_policy": "hashes_and_encrypted_locknotes_only_no_raw_keys",
        },
        "summary": {
            "file_count": len(records),
            "skipped_count": len(skipped),
            "total_bytes": total_bytes,
            "root_sha256": root_hash,
            "obsidian_key_holder": str(
                resolve_obsidian_note_path(DEFAULT_OBSIDIAN_NOTE, repo_root=repo_root)
            ),
            "can_rebuild_active_repo_from_manifest_only": False,
        },
        "files": [record.__dict__ for record in records],
        "skipped": skipped,
    }


def _build_tar_gz_bytes(repo_root: Path, records: list[RepoFileRecord]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for record in records:
            path = repo_root / record.path
            info = archive.gettarinfo(str(path), arcname=record.path)
            info.mtime = 0
            with path.open("rb") as handle:
                archive.addfile(info, handle)
    return buffer.getvalue()


def seal_repo_singularity_packet(
    manifest: Mapping[str, Any],
    agent_secrets: Mapping[str, str],
    *,
    max_archive_mb: float = 100.0,
) -> dict[str, Any]:
    repo_root = Path(str(manifest["repo_root"]))
    records = [RepoFileRecord(**record) for record in manifest.get("files", [])]
    archive = _build_tar_gz_bytes(repo_root, records)
    if len(archive) > int(max_archive_mb * 1024 * 1024):
        raise HNCPacketError("singularity_archive_too_large_for_memory_packet_profile")
    packet = build_hnc_swarm_packet(
        archive,
        agent_secrets,
        purpose="repo:singularity_vault",
        operator_aad={"root_sha256": manifest["summary"]["root_sha256"], "file_count": manifest["summary"]["file_count"]},
        hnc_context={"domain": "repo_singularity_vault", "root_sha256": manifest["summary"]["root_sha256"]},
    )
    fragments = stream_hnc_probability_fragments(packet, fragment_size=4096)
    breaker = run_hnc_swarm_breaker_checks(packet, agent_secrets)
    return {
        "sealed": True,
        "archive_size_bytes": len(archive),
        "packet_summary": packet_public_summary(packet),
        "fragment_count": len(fragments),
        "fragments": fragments,
        "swarm_breaker": breaker,
        "packet": packet,
        "secret_policy": "packet_contains_encrypted_archive_no_plaintext_files",
    }


def externalize_sealed_packet_blob(report: dict[str, Any], blob_path: Path = DEFAULT_SEALED_PACKET_BLOB) -> dict[str, Any]:
    seal = report.get("seal")
    if not isinstance(seal, dict) or not seal.get("sealed"):
        return report
    packet = seal.get("packet")
    fragments = seal.get("fragments")
    if not packet and not fragments:
        return report
    blob_path.parent.mkdir(parents=True, exist_ok=True)
    blob = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "repo_root_sha256": report.get("summary", {}).get("root_sha256"),
        "packet": packet,
        "fragments": fragments,
        "secret_policy": "encrypted_packet_blob_only_no_raw_keys_no_plaintext_repo",
    }
    blob_path.write_text(json.dumps(blob, indent=2, sort_keys=True, default=str), encoding="utf-8")
    seal["sealed_packet_blob"] = _display_path(blob_path)
    seal["sealed_packet_blob_sha256"] = _sha256_file(blob_path)
    seal.pop("packet", None)
    seal.pop("fragments", None)
    return report


def decode_repo_singularity_archive(packet: Mapping[str, Any], agent_secrets: Mapping[str, str]) -> bytes:
    decoded = decode_hnc_swarm_packet(packet, agent_secrets, expected_purpose="repo:singularity_vault")
    return decoded.plaintext


def build_obsidian_key_holder_note(report: Mapping[str, Any]) -> str:
    summary = report.get("summary", {})
    seal = report.get("seal", {}) if isinstance(report.get("seal"), dict) else {}
    packet_summary = seal.get("packet_summary", {}) if isinstance(seal.get("packet_summary"), dict) else {}
    lines = [
        "# Aureon HNC Singularity Vault",
        "",
        f"Generated: `{report.get('generated_at')}`",
        "",
        "This note is the Obsidian key-holder map. It stores public hashes, packet summaries, and locknote instructions only. It must never hold raw agent keys.",
        "",
        "## Repo Root",
        "",
        f"- `{report.get('repo_root')}`",
        "",
        "## Singularity Root",
        "",
        f"- Files wrapped: `{summary.get('file_count')}`",
        f"- Skipped by safety profile: `{summary.get('skipped_count')}`",
        f"- Root SHA-256: `{summary.get('root_sha256')}`",
        "",
        "## Swarm Locknote Policy",
        "",
        "- One agent key alone cannot decode the sealed packet.",
        "- Any valid two-agent pair can unite their locknotes and decode.",
        "- Agent keys belong in Windows Credential Manager or another OS secret store, not in this vault note.",
        "- The live repo is not encrypted in place; this is a sealed snapshot/wrapper so Aureon keeps running.",
        "",
    ]
    if seal.get("sealed"):
        lines.extend(
            [
                "## Sealed Packet",
                "",
                f"- Packet SHA-256: `{packet_summary.get('packet_sha256')}`",
                f"- HNC alignment SHA-256: `{packet_summary.get('hnc_alignment_sha256')}`",
                f"- Fragment count: `{seal.get('fragment_count')}`",
                f"- Swarm breaker passed: `{(seal.get('swarm_breaker') or {}).get('passed')}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Reassembly Flow",
            "",
            "1. Load the public singularity report JSON.",
            "2. Gather the required two agent keys from OS secret storage.",
            "3. Reassemble all temporal fragments.",
            "4. Verify packet hash, HNC geometry, locknotes, and AAD.",
            "5. Decode the archive into a quarantine/recovery directory.",
            "",
        ]
    )
    return "\n".join(lines)


def render_markdown(report: Mapping[str, Any]) -> str:
    summary = report.get("summary", {})
    seal = report.get("seal", {}) if isinstance(report.get("seal"), dict) else {}
    lines = [
        "# Aureon Repo Singularity Vault",
        "",
        f"Generated: `{report.get('generated_at')}`",
        "",
        "## Summary",
        "",
        f"- Mode: `{report.get('mode')}`",
        f"- Files wrapped: `{summary.get('file_count')}`",
        f"- Skipped: `{summary.get('skipped_count')}`",
        f"- Root SHA-256: `{summary.get('root_sha256')}`",
        f"- Sealed archive present: `{bool(seal.get('sealed'))}`",
        f"- Live working tree mutated: `{report.get('profile', {}).get('live_working_tree_mutated')}`",
        "",
        "## Safety",
        "",
        "- The active repo is not encrypted in place.",
        "- Raw keys are not written to the Obsidian note or public JSON.",
        "- Large logs, runtime state, private business folders, and generated binaries are excluded by the default profile.",
        "",
    ]
    if seal.get("sealed"):
        lines.extend(
            [
                "## Sealed Packet",
                "",
                f"- Archive size bytes: `{seal.get('archive_size_bytes')}`",
                f"- Fragment count: `{seal.get('fragment_count')}`",
                f"- Sealed packet blob: `{seal.get('sealed_packet_blob')}`",
                f"- Sealed packet blob SHA-256: `{seal.get('sealed_packet_blob_sha256')}`",
                f"- Breaker passed: `{(seal.get('swarm_breaker') or {}).get('passed')}`",
                "",
            ]
        )
    return "\n".join(lines)


def write_repo_singularity_vault(
    report: dict[str, Any],
    output_json: Path = DEFAULT_OUTPUT_JSON,
    output_md: Path = DEFAULT_OUTPUT_MD,
    public_json: Path = DEFAULT_PUBLIC_JSON,
    obsidian_note: Path = DEFAULT_OBSIDIAN_NOTE,
) -> tuple[Path, Path, Path, Path]:
    report = externalize_sealed_packet_blob(report)
    public_report = sanitize_report_for_repository(report)
    resolved_obsidian_note = resolve_obsidian_note_path(
        obsidian_note,
        repo_root=REPO_ROOT,
    )
    for path in (output_json, output_md, public_json, resolved_obsidian_note):
        path.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(public_report, indent=2, sort_keys=True, default=str), encoding="utf-8")
    output_md.write_text(render_markdown(public_report), encoding="utf-8")
    public_json.write_text(json.dumps(public_report, indent=2, sort_keys=True, default=str), encoding="utf-8")
    resolved_obsidian_note.write_text(build_obsidian_key_holder_note(public_report), encoding="utf-8")
    return output_json, output_md, public_json, resolved_obsidian_note


def build_repo_singularity_vault(
    repo_root: Path = REPO_ROOT,
    *,
    seal: bool = False,
    agent_secrets: Mapping[str, str] | None = None,
    max_file_size_mb: float = 25.0,
    max_archive_mb: float = 100.0,
    include_large: bool = False,
) -> dict[str, Any]:
    report = build_repo_singularity_manifest(repo_root, max_file_size_mb=max_file_size_mb, include_large=include_large)
    report["generated_at"] = utc_now()
    if seal:
        if not agent_secrets:
            raise HNCPacketError("seal_requires_agent_secrets")
        report["seal"] = seal_repo_singularity_packet(report, agent_secrets, max_archive_mb=max_archive_mb)
        report["status"] = "sealed_singularity_ready"
    else:
        report["seal"] = {
            "sealed": False,
            "reason": "manifest_only_default_use_--seal_to_create_encrypted_swarm_archive",
        }
    return report


def _agent_secrets_from_env() -> dict[str, str]:
    pairs = {
        "seer": os.environ.get("AUREON_SWARM_SEER_KEY", ""),
        "lyra": os.environ.get("AUREON_SWARM_LYRA_KEY", ""),
        "king": os.environ.get("AUREON_SWARM_KING_KEY", ""),
    }
    return {name: value for name, value in pairs.items() if value}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build Aureon repo singularity vault manifest or sealed snapshot.")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--seal", action="store_true", help="Create an encrypted HNC swarm archive packet.")
    parser.add_argument("--generate-dpapi-keys", action="store_true", help="Generate missing Windows DPAPI-protected swarm keys under state/.")
    parser.add_argument("--use-dpapi-keys", action="store_true", help="Load swarm keys from Windows DPAPI-protected state blobs.")
    parser.add_argument("--rotate-dpapi-keys", action="store_true", help="Rotate DPAPI-protected swarm keys before sealing.")
    parser.add_argument("--include-large", action="store_true", help="Include files larger than --max-file-size-mb.")
    parser.add_argument("--max-file-size-mb", type=float, default=25.0)
    parser.add_argument("--max-archive-mb", type=float, default=100.0)
    parser.add_argument("--json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--md", type=Path, default=DEFAULT_OUTPUT_MD)
    parser.add_argument("--public-json", type=Path, default=DEFAULT_PUBLIC_JSON)
    parser.add_argument("--obsidian-note", type=Path, default=DEFAULT_OBSIDIAN_NOTE)
    args = parser.parse_args(argv)
    secrets = None
    key_store_report = None
    if args.seal and (args.generate_dpapi_keys or args.use_dpapi_keys or args.rotate_dpapi_keys):
        from aureon.vault.hnc_swarm_key_store import ensure_dpapi_swarm_keys, load_dpapi_swarm_agent_keys

        if args.generate_dpapi_keys or args.rotate_dpapi_keys:
            key_store_report = ensure_dpapi_swarm_keys(rotate=args.rotate_dpapi_keys)
        secrets = load_dpapi_swarm_agent_keys()
    elif args.seal:
        secrets = _agent_secrets_from_env()
    report = build_repo_singularity_vault(
        args.repo_root,
        seal=args.seal,
        agent_secrets=secrets,
        max_file_size_mb=args.max_file_size_mb,
        max_archive_mb=args.max_archive_mb,
        include_large=args.include_large,
    )
    if key_store_report:
        report["key_store"] = key_store_report
    outputs = write_repo_singularity_vault(report, args.json, args.md, args.public_json, args.obsidian_note)
    print(json.dumps({"ok": True, "status": report["status"], "outputs": [str(path) for path in outputs]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
