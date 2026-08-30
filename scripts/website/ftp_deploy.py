#!/usr/bin/env python3
"""Upload the built static site to the home.pl server over FTP(S).

**Credentials come only from environment variables — never from the command line, never from a
committed file, and they are never printed.** The script refuses to run if any required variable
is unset. The exact FTPS mode and port are mandatory; neither is guessed.

Required env:
    HOMEPL_FTPS_HOST          hostname of the FTP server
    HOMEPL_FTPS_USER          username
    HOMEPL_FTPS_PASSWORD      password
    HOMEPL_FTPS_REMOTE_ROOT   exact authenticated document root (never assume "/" or "/public_html")
    HOMEPL_FTPS_PORT          exact authenticated port (commonly 21 explicit or 990 implicit)
    HOMEPL_FTPS_MODE          "explicit" or "implicit"; no default

Usage:
    # 1) build first
    python -m scripts.website.build_package --out dist --source-commit <full-HEAD>
    # 2) preview (no network) — always safe
    python -m scripts.website.ftp_deploy --package dist/website_package --dry-run
    # 3) upload (needs the env vars set in your shell)
    python -m scripts.website.ftp_deploy --package dist/website_package

The uploader only creates/overwrites remote files and never prunes. A live run requires a fresh,
validated backup receipt and an internally consistent commit-bound package. Upload completion is
not publication proof: exact read-back remains mandatory.
Pure standard library (`ftplib`).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import socket
import ssl
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from ftplib import FTP, FTP_TLS
from pathlib import Path, PurePosixPath
from typing import Any

from scripts.website.readback import ReadbackInputError, compare_readback_directory

_REQUIRED_ENV = (
    "HOMEPL_FTPS_HOST",
    "HOMEPL_FTPS_USER",
    "HOMEPL_FTPS_PASSWORD",
    "HOMEPL_FTPS_REMOTE_ROOT",
    "HOMEPL_FTPS_PORT",
    "HOMEPL_FTPS_MODE",
)
_BACKUP_SCHEMA = "aureon.homepl-backup-transfer.v1"
_CONNECT_TIMEOUT_SECONDS = 30.0


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class FtpConfig:
    host: str
    user: str
    password: str
    remote_dir: str
    port: int
    mode: str

    @property
    def safe_summary(self) -> str:
        """A credential-free one-liner safe to print/log."""
        return (
            f"FTPS-{self.mode} {self.host}:{self.port} -> {self.remote_dir} "
            f"(user set: {'yes' if self.user else 'no'})"
        )


@dataclass(frozen=True)
class BackupReceipt:
    """Validated, credential-free proof that a fresh served-root backup exists."""

    path: Path
    completed_at: datetime
    remote_root: str
    file_count: int
    total_bytes: int
    manifest_sha256: str


def _normalise_remote_root(value: str) -> str:
    raw = value.strip().replace("\\", "/")
    if not raw.startswith("/") or ".." in raw.split("/") or "\n" in raw or "\r" in raw:
        raise ValueError("HOMEPL_FTPS_REMOTE_ROOT must be one exact absolute remote path")
    return raw.rstrip("/") or "/"


def _normalise_host(value: str) -> str:
    if (
        not value
        or value != value.strip()
        or any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in value)
    ):
        raise ValueError("HOMEPL_FTPS_HOST must be one hostname without whitespace or control characters")
    return value


def load_config(env: Mapping[str, str] | None = None) -> FtpConfig:
    """Build an :class:`FtpConfig` from the environment. Raises ``KeyError`` listing what's missing."""
    source_env: Mapping[str, str] = os.environ if env is None else env
    missing = [k for k in _REQUIRED_ENV if not source_env.get(k)]
    if missing:
        raise KeyError("missing required env var(s): " + ", ".join(missing))
    mode = source_env["HOMEPL_FTPS_MODE"].strip().casefold()
    if mode not in {"explicit", "implicit"}:
        raise ValueError("HOMEPL_FTPS_MODE must be exactly 'explicit' or 'implicit'")
    port = int(source_env["HOMEPL_FTPS_PORT"])
    if not 1 <= port <= 65535:
        raise ValueError("HOMEPL_FTPS_PORT must be between 1 and 65535")
    return FtpConfig(
        host=_normalise_host(source_env["HOMEPL_FTPS_HOST"]),
        user=source_env["HOMEPL_FTPS_USER"],
        password=source_env["HOMEPL_FTPS_PASSWORD"],
        remote_dir=_normalise_remote_root(source_env["HOMEPL_FTPS_REMOTE_ROOT"]),
        port=port,
        mode=mode,
    )


def _receipt_object(value: object) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError("backup receipt must be a JSON object")
    return value


def _safe_backup_path(value: object) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\n" in value or "\r" in value:
        raise ValueError("backup manifest path is unsafe")
    path = PurePosixPath(value)
    if path.is_absolute() or path.as_posix() == "." or ".." in path.parts or "." in path.parts:
        raise ValueError("backup manifest path is unsafe")
    return path.as_posix()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(131_072), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_bound_file(data: Mapping[str, Any], path_field: str, hash_field: str) -> Path:
    raw_path = data.get(path_field)
    raw_hash = data.get(hash_field)
    if not isinstance(raw_path, str) or not isinstance(raw_hash, str):
        raise ValueError(f"backup receipt must bind {path_field}")
    unresolved = Path(raw_path)
    if unresolved.is_symlink():
        raise ValueError(f"backup receipt {path_field} is not an ordinary file")
    path = unresolved.resolve(strict=True)
    if not path.is_file():
        raise ValueError(f"backup receipt {path_field} is not an ordinary file")
    actual = _sha256_file(path)
    if len(raw_hash) != 64 or actual.casefold() != raw_hash.casefold():
        raise ValueError(f"backup receipt {path_field} hash does not match")
    return path


def _validate_backup_manifest(
    manifest: Path,
    backup_directory: Path,
    expected_count: int,
    expected_bytes: int,
) -> None:
    try:
        reader = csv.DictReader(io.StringIO(manifest.read_text(encoding="utf-8-sig")))
    except UnicodeDecodeError as exc:
        raise ValueError("backup manifest must be UTF-8 CSV") from exc
    if reader.fieldnames != ["Path", "Bytes", "Sha256"]:
        raise ValueError("backup manifest must use the Path,Bytes,Sha256 schema")
    rows = list(reader)
    paths: list[str] = []
    total_bytes = 0
    for index, row in enumerate(rows):
        relative = _safe_backup_path(row.get("Path"))
        try:
            size = int(str(row.get("Bytes", "")))
        except ValueError as exc:
            raise ValueError(f"backup manifest row {index} has an invalid byte count") from exc
        digest = str(row.get("Sha256", ""))
        if size < 0 or len(digest) != 64 or any(char not in "0123456789abcdefABCDEF" for char in digest):
            raise ValueError(f"backup manifest row {index} is malformed")
        unresolved = backup_directory / Path(*PurePosixPath(relative).parts)
        if unresolved.is_symlink():
            raise ValueError(f"backup manifest row {index} is not an ordinary backed-up file")
        local = unresolved.resolve(strict=True)
        try:
            local.relative_to(backup_directory)
        except ValueError as exc:
            raise ValueError(f"backup manifest row {index} escapes the backup directory") from exc
        if not local.is_file():
            raise ValueError(f"backup manifest row {index} is not an ordinary backed-up file")
        if local.stat().st_size != size or _sha256_file(local).casefold() != digest.casefold():
            raise ValueError(f"backup manifest row {index} does not match the backed-up file")
        paths.append(relative)
        total_bytes += size
    if paths != sorted(paths, key=lambda item: (item.casefold(), item)) or len(paths) != len(set(paths)):
        raise ValueError("backup manifest paths must be unique and sorted")
    entries = list(backup_directory.rglob("*"))
    if any(path.is_symlink() for path in entries):
        raise ValueError("backup directory contains a link or reparse entry")
    actual_paths = {path.relative_to(backup_directory).as_posix() for path in entries if path.is_file()}
    if actual_paths != set(paths):
        raise ValueError("backup directory and manifest file sets differ")
    if len(rows) != expected_count or total_bytes != expected_bytes:
        raise ValueError("backup receipt counters do not match its deterministic manifest")


def load_backup_receipt(
    path: Path,
    expected_remote_root: str,
    *,
    now: datetime | None = None,
    maximum_age: timedelta = timedelta(hours=24),
) -> BackupReceipt:
    """Validate the audited backup tool's non-secret transfer receipt."""

    resolved = path.resolve(strict=True)
    if not resolved.is_file() or resolved.stat().st_size > 1_000_000:
        raise ValueError("backup receipt must be a bounded regular file")
    try:
        data = _receipt_object(json.loads(resolved.read_text(encoding="utf-8")))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("backup receipt must be valid UTF-8 JSON") from exc
    remote_root = _normalise_remote_root(str(data.get("remote_root", "")))
    expected_root = _normalise_remote_root(expected_remote_root)
    if (
        data.get("schema") != _BACKUP_SCHEMA
        or data.get("state") != "backup-complete"
        or data.get("method") != "homepl-ftps"
        or data.get("source_tool") != "repo-read-only-ftps-script"
        or data.get("source_assertion") != "Authenticated Home.pl document-root download"
        or remote_root != expected_root
        or data.get("remote_write_methods_used") is not False
        or data.get("credentials_recorded") is not False
    ):
        raise ValueError("backup receipt does not bind a completed read-only backup of this remote root")

    file_count = data.get("file_count")
    total_bytes = data.get("total_bytes")
    if (
        not isinstance(file_count, int)
        or isinstance(file_count, bool)
        or file_count < 1
        or not isinstance(total_bytes, int)
        or isinstance(total_bytes, bool)
        or total_bytes < 1
    ):
        raise ValueError("backup receipt must record a non-empty transfer")
    completed_raw = data.get("completed_at")
    if not isinstance(completed_raw, str):
        raise ValueError("backup receipt has no completion timestamp")
    try:
        completed_at = datetime.fromisoformat(completed_raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("backup receipt completion timestamp is invalid") from exc
    if completed_at.tzinfo is None:
        raise ValueError("backup receipt completion timestamp must include a timezone")
    check_now = (now or datetime.now(UTC)).astimezone(UTC)
    completed_utc = completed_at.astimezone(UTC)
    if completed_utc > check_now + timedelta(minutes=5) or completed_utc < check_now - maximum_age:
        raise ValueError("backup receipt is future-dated or stale")

    manifest = _verify_bound_file(data, "manifest", "manifest_sha256")
    backup_value = data.get("backup_directory")
    if not isinstance(backup_value, str):
        raise ValueError("backup receipt must bind its downloaded directory")
    unresolved_backup = Path(backup_value)
    if unresolved_backup.is_symlink():
        raise ValueError("backup directory is not an ordinary directory")
    backup_directory = unresolved_backup.resolve(strict=True)
    if not backup_directory.is_dir():
        raise ValueError("backup directory is not an ordinary directory")
    backup_script = _verify_bound_file(data, "backup_script", "backup_script_sha256")
    if backup_script.name != "backup-homepl-ftps.ps1":
        raise ValueError("backup receipt names an unsupported producer")
    _validate_backup_manifest(manifest, backup_directory, file_count, total_bytes)
    actual_digest = _sha256_file(manifest)
    return BackupReceipt(
        path=resolved,
        completed_at=completed_utc,
        remote_root=remote_root,
        file_count=file_count,
        total_bytes=total_bytes,
        manifest_sha256=actual_digest,
    )


def plan_uploads(package_dir: Path, remote_dir: str) -> list[tuple[Path, str]]:
    """Enumerate (local_file, remote_path) pairs, deterministically sorted."""
    package_dir = package_dir.resolve()
    base = remote_dir.rstrip("/")
    plan: list[tuple[Path, str]] = []
    for local in sorted(p for p in package_dir.rglob("*") if p.is_file()):
        rel = local.relative_to(package_dir).as_posix()
        plan.append((local, f"{base}/{rel}"))
    return plan


def _remote_dirs(plan: list[tuple[Path, str]], remote_root: str) -> list[str]:
    """Ordered unique remote directories needed for the plan (parents before children)."""
    base = remote_root.rstrip("/")
    dirs: set[str] = set()
    for _local, remote in plan:
        parent = remote.rsplit("/", 1)[0]
        while parent and parent != base and parent not in dirs:
            dirs.add(parent)
            parent = parent.rsplit("/", 1)[0]
    return sorted(dirs, key=lambda d: d.count("/"))


def _new_tls_context() -> ssl.SSLContext:
    """Return the certificate- and hostname-validating context used by both FTPS modes."""

    context = ssl.create_default_context()
    if context.verify_mode != ssl.CERT_REQUIRED or not context.check_hostname:
        raise RuntimeError("FTPS requires certificate and hostname validation")
    return context


def _network_options(
    timeout: float,
    source_address: tuple[str, int] | None,
) -> tuple[float, tuple[str, int] | None]:
    """Validate bounded socket options before any connection can be attempted."""

    if isinstance(timeout, bool) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("FTPS connect timeout must be a positive finite number")
    if source_address is None:
        return float(timeout), None
    if not isinstance(source_address, tuple) or len(source_address) != 2:
        raise ValueError("FTPS source address must be a (host, port) tuple")
    host, port = source_address
    if not isinstance(host, str) or any(
        char.isspace() or ord(char) < 32 or ord(char) == 127 for char in host
    ):
        raise ValueError("FTPS source address host is invalid")
    if isinstance(port, bool) or not isinstance(port, int) or not 0 <= port <= 65535:
        raise ValueError("FTPS source address port must be between 0 and 65535")
    return float(timeout), (host, port)


class ImplicitFTP_TLS(FTP_TLS):
    """``FTP_TLS`` transport whose control socket is TLS-wrapped before the welcome reply."""

    def connect_implicit(
        self,
        host: str,
        port: int,
        *,
        timeout: float,
        source_address: tuple[str, int] | None,
    ) -> str:
        if self.sock is not None:
            raise RuntimeError("FTPS control socket is already connected")
        self.host = host
        self.port = port
        self.timeout = timeout
        self.source_address = source_address
        raw_socket = socket.create_connection(
            (host, port),
            timeout=timeout,
            source_address=source_address,
        )
        try:
            self.af = raw_socket.family
            wrapped_socket = self.context.wrap_socket(raw_socket, server_hostname=host)
        except Exception:
            raw_socket.close()
            raise
        self.sock = wrapped_socket
        try:
            self.file = wrapped_socket.makefile("r", encoding=self.encoding)
            self.welcome = self.getresp()
            return self.welcome
        except Exception:
            self.close()
            raise

    def auth(self) -> str:
        """Fail closed if code tries to negotiate explicit TLS on an implicit control socket."""

        raise RuntimeError("AUTH TLS is invalid on an already TLS-wrapped implicit connection")

    def login(
        self,
        user: str = "",
        passwd: str = "",
        acct: str = "",
        secure: bool = True,
    ) -> str:
        """Authenticate inside the existing TLS tunnel without ``FTP_TLS.login`` calling AUTH."""

        if not secure:
            raise RuntimeError("implicit FTPS login cannot disable its existing TLS tunnel")
        return FTP.login(self, user, passwd, acct)


def _connect(
    cfg: FtpConfig,
    *,
    timeout: float = _CONNECT_TIMEOUT_SECONDS,
    source_address: tuple[str, int] | None = None,
) -> FTP:  # pragma: no cover - real sockets are replaced by fakes in unit tests
    if cfg.mode not in {"explicit", "implicit"}:
        raise ValueError("FTPS mode must be exactly 'explicit' or 'implicit'")
    if isinstance(cfg.port, bool) or not isinstance(cfg.port, int) or not 1 <= cfg.port <= 65535:
        raise ValueError("FTPS port must be between 1 and 65535")
    try:
        _normalise_host(cfg.host)
    except ValueError as exc:
        raise ValueError("FTPS host is invalid") from exc
    if not cfg.user or not cfg.password:
        raise ValueError("FTPS credentials are missing")
    checked_timeout, checked_source = _network_options(timeout, source_address)
    context = _new_tls_context()

    if cfg.mode == "explicit":
        explicit = FTP_TLS(context=context)
        try:
            explicit.connect(
                cfg.host,
                cfg.port,
                timeout=checked_timeout,
                source_address=checked_source,
            )
            explicit.login(cfg.user, cfg.password)
            explicit.prot_p()
        except Exception:
            explicit.close()
            raise
        return explicit

    implicit = ImplicitFTP_TLS(context=context)
    try:
        implicit.connect_implicit(
            cfg.host,
            cfg.port,
            timeout=checked_timeout,
            source_address=checked_source,
        )
        implicit.login(cfg.user, cfg.password)
        implicit.prot_p()
    except Exception:
        implicit.close()
        raise
    return implicit


def _upload(cfg: FtpConfig, package_dir: Path) -> int:  # pragma: no cover - network
    plan = plan_uploads(package_dir, cfg.remote_dir)
    ftp = _connect(cfg)
    try:
        for d in _remote_dirs(plan, cfg.remote_dir):
            try:
                ftp.mkd(d)
            except Exception:  # noqa: BLE001 - already exists is fine
                pass
        for local, remote in plan:
            with local.open("rb") as fh:
                ftp.storbinary(f"STOR {remote}", fh)
            print(f"  UPLOAD {remote}  ({local.stat().st_size} B)")
    finally:
        ftp.quit()
    return len(plan)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Upload the built static site to the server over FTP(S). Credentials come only from env vars."
    )
    parser.add_argument(
        "--package", default=None, help="built package dir (default: <repo>/dist/website_package)"
    )
    parser.add_argument("--dry-run", action="store_true", help="print the upload plan and touch no network")
    parser.add_argument(
        "--backup-receipt",
        default=None,
        help="fresh aureon.homepl-backup-transfer.v1 receipt (required for a live upload)",
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help="unsupported safety flag; any use is refused because this deployer never deletes",
    )
    args = parser.parse_args(argv)

    package_dir = Path(args.package) if args.package else _repo_root() / "dist" / "website_package"
    if not package_dir.is_dir():
        print(
            f"package dir not found: {package_dir}\n"
            f"run: python -m scripts.website.build_package --out {package_dir.parent}",
            file=sys.stderr,
        )
        return 2

    try:
        cfg = load_config()
    except (KeyError, ValueError) as exc:
        print(f"FTP deploy refused - {exc}", file=sys.stderr)
        print(
            "Set the credentials in your shell environment (never commit them). See "
            "scripts/website/README.md.",
            file=sys.stderr,
        )
        return 1

    plan = plan_uploads(package_dir, cfg.remote_dir)
    print(f"Target: {cfg.safe_summary}")
    print(f"Package: {package_dir}  ({len(plan)} files)")

    if args.prune:
        print(
            "FTP deploy refused - pruning is disabled; this tool never deletes remote files", file=sys.stderr
        )
        return 1
    if args.dry_run:
        print("DRY RUN - no network. Planned uploads:")
        for _local, remote in plan:
            print(f"  UPLOAD {remote}")
        print(f"  {len(plan)} file(s) would be uploaded.")
        return 0

    if not args.backup_receipt:
        print("FTP deploy refused - a fresh --backup-receipt is required", file=sys.stderr)
        return 1
    try:
        package_check = compare_readback_directory(package_dir, package_dir)
        if not package_check.passed:
            raise ValueError("local package does not match its per-file SHA-256 manifest")
        backup = load_backup_receipt(Path(args.backup_receipt), cfg.remote_dir)
    except (OSError, ReadbackInputError, ValueError) as exc:
        print(f"FTP deploy refused - {exc}", file=sys.stderr)
        return 1

    print(f"Uploading after validated backup ({backup.file_count} files, {backup.total_bytes} bytes) ...")
    n = _upload(cfg, package_dir)
    print(f"Upload completed - {n} file(s) sent to {cfg.host}:{cfg.remote_dir}")
    print("Publication is not proven until exact public/remote read-back passes.")
    return 0


if __name__ == "__main__":  # pragma: no cover - manual entry point
    raise SystemExit(main())
