"""Fail-closed ISO/VHDX appliance pipeline.

The pipeline intentionally separates four evidence-bearing transitions:

``preflight -> stage -> image -> verify``

That ordering borrows the useful engineering interpretation of the HNC
film-reel model: inputs are immutable frames, transitions are explicit, and
the prior receipt is carried forward as memory.  HNC coherence values are
informational only; they never authorize a build, a boot, or a privileged
host mutation.

No command in this module downloads an operating system or dependencies.
Every external byte must be supplied in a content-addressed input lock.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence

INPUT_SCHEMA = "aureon.appliance.inputs.v1"
PROFILE_SCHEMA = "aureon.appliance.profile.v1"
WHEELHOUSE_SCHEMA = "aureon.appliance.wheelhouse.v1"
RECEIPT_SCHEMA = "aureon.appliance.receipt.v1"
ARTIFACT_SCHEMA = "aureon.appliance.artifacts.v1"

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
SAFE_TOOL_ENV_KEYS = ("PATH", "SYSTEMROOT", "WINDIR")
PAYLOAD_DENY_PARTS = frozenset(
    {
        ".env",
        ".git",
        ".aureon",
        "archive",
        "data",
        "imports",
        "logs",
        "state",
        "uploads",
        "provider_keys.json.enc",
        "provider_keys.key",
    }
)
SECRET_SUFFIXES = (".key", ".pem", ".p12", ".pfx", ".kdbx")
CORE_UNITS = (
    "aureon-operator.service",
    "aureon-organism.service",
    "aureon-hnc.service",
)
BOOT_MARKER = "AUREON_APPLIANCE_BOOTABLE_FIRSTBOOT_REQUIRED"
BOOT_ATTESTATION = {
    "schema": "aureon.appliance.boot.v1",
    "status": "hold",
    "reason": "local_console_firstboot_required",
    "core_started": False,
}


class ApplianceHold(RuntimeError):
    """A safe, expected refusal caused by an unmet build contract."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number is forbidden: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _strict_json_bytes(raw: bytes, *, label: str) -> Any:
    if raw.startswith((b"\xef\xbb\xbf", b"\xff\xfe", b"\xfe\xff")):
        raise ApplianceHold("invalid_json", f"{label} must be UTF-8 without a BOM")
    try:
        text = raw.decode("utf-8")
        value = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ApplianceHold("invalid_json", f"{label}: {exc}") from exc
    return value


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("utf-8")


def _read_json(path: Path, *, label: str) -> Any:
    try:
        _assert_safe_existing_file(path, label=label)
        return _strict_json_bytes(path.read_bytes(), label=label)
    except OSError as exc:
        raise ApplianceHold("read_failed", f"{label}: {exc}") from exc


def _exact_keys(value: Mapping[str, Any], expected: Iterable[str], *, label: str) -> None:
    expected_set = set(expected)
    actual = set(value)
    if actual != expected_set:
        missing = sorted(expected_set - actual)
        unknown = sorted(actual - expected_set)
        raise ApplianceHold(
            "schema_mismatch",
            f"{label} missing={missing or 'none'} unknown={unknown or 'none'}",
        )


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _write_all(descriptor: int, payload: bytes, *, label: str) -> None:
    remaining = memoryview(payload)
    while remaining:
        written = os.write(descriptor, remaining)
        if written <= 0:
            raise ApplianceHold("write_failed", f"short write while recording {label}")
        remaining = remaining[written:]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_relpath(value: str, *, label: str) -> PurePosixPath:
    if (
        not isinstance(value, str)
        or not value
        or "\\" in value
        or any(ord(character) < 32 for character in value)
    ):
        raise ApplianceHold("unsafe_path", f"{label} is not canonical POSIX text")
    if value.startswith("-"):
        raise ApplianceHold("unsafe_path", f"{label} may not begin with an option marker")
    path = PurePosixPath(value)
    if path.is_absolute() or str(path) != value or any(part in {"", ".", ".."} for part in path.parts):
        raise ApplianceHold("unsafe_path", f"{label} is not canonical repo-relative POSIX: {value!r}")
    if ":" in path.parts[0]:
        raise ApplianceHold("unsafe_path", f"{label} contains a drive or ADS marker")
    return path


def _payload_path_is_denied(path: PurePosixPath) -> bool:
    for part in path.parts:
        folded = part.casefold()
        if folded in PAYLOAD_DENY_PARTS or folded.startswith(".env."):
            return True
    return str(path).casefold().endswith(SECRET_SUFFIXES)


def _is_reparse_or_link(path: Path) -> bool:
    try:
        info = path.lstat()
    except OSError:
        return False
    attrs = getattr(info, "st_file_attributes", 0)
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return stat.S_ISLNK(info.st_mode) or bool(attrs & reparse)


def _assert_local_host_path(path: Path, *, label: str) -> None:
    """Reject Windows path forms that can trigger remote I/O or named streams."""

    raw = os.fspath(path)
    if "\x00" in raw:
        raise ApplianceHold("unsafe_path", f"{label} contains a NUL byte")
    if os.name != "nt":
        if raw.startswith("//"):
            raise ApplianceHold("unsafe_path", f"{label} may not use a network-style path")
        return
    normalized = raw.replace("/", "\\")
    if normalized.startswith("\\\\"):
        raise ApplianceHold("unsafe_path", f"{label} may not use UNC or device paths")
    drive, tail = os.path.splitdrive(normalized)
    if re.fullmatch(r"[A-Za-z]:", drive) is None:
        raise ApplianceHold("unsafe_path", f"{label} must use one local drive letter")
    if ":" in tail:
        raise ApplianceHold("unsafe_path", f"{label} may not use an NTFS alternate data stream")
    import ctypes

    if ctypes.windll.kernel32.GetDriveTypeW(drive + "\\") == 4:
        raise ApplianceHold("unsafe_path", f"{label} may not use a mapped network drive")


def _assert_safe_existing_file(path: Path, *, label: str) -> None:
    if not path.is_absolute():
        raise ApplianceHold("unsafe_path", f"{label} must be absolute: {path}")
    _assert_local_host_path(path, label=label)
    current = path
    while True:
        if _is_reparse_or_link(current):
            raise ApplianceHold("unsafe_path", f"{label} traverses a link/reparse point: {current}")
        if current.parent == current:
            break
        current = current.parent
    if not path.is_file():
        raise ApplianceHold("missing_input", f"{label} does not exist: {path}")


def _assert_safe_existing_dir(path: Path, *, label: str) -> None:
    if not path.is_absolute():
        raise ApplianceHold("unsafe_path", f"{label} must be absolute: {path}")
    _assert_local_host_path(path, label=label)
    current = path
    while True:
        if _is_reparse_or_link(current):
            raise ApplianceHold("unsafe_path", f"{label} traverses a link/reparse point: {current}")
        if current.parent == current:
            break
        current = current.parent
    if not path.is_dir():
        raise ApplianceHold("missing_input", f"{label} does not exist: {path}")


def _assert_safe_fresh_output(path: Path, *, repo: Path | None = None) -> None:
    if not path.is_absolute() or path.parent == path:
        raise ApplianceHold("unsafe_output", f"output must be a non-root absolute path: {path}")
    _assert_local_host_path(path, label="output")
    if path.exists() or _is_reparse_or_link(path):
        raise ApplianceHold("unsafe_output", f"output must not already exist: {path}")
    if repo is not None and (path == repo or repo in path.parents):
        raise ApplianceHold("unsafe_output", "output must be outside the source checkout")
    current = path.parent
    while not current.exists() and current.parent != current:
        current = current.parent
    _assert_safe_existing_dir(current, label="output ancestor")


def _validate_hash(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        raise ApplianceHold("schema_mismatch", f"{label} must be lowercase SHA-256")
    return value


def _validate_file_lock(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ApplianceHold("schema_mismatch", f"{label} must be an object")
    _exact_keys(value, ("path", "sha256", "size"), label=label)
    if not isinstance(value["path"], str) or not value["path"]:
        raise ApplianceHold("input_unconfigured", f"{label}.path is required")
    _validate_hash(value["sha256"], label=f"{label}.sha256")
    if not isinstance(value["size"], int) or isinstance(value["size"], bool) or value["size"] <= 0:
        raise ApplianceHold("schema_mismatch", f"{label}.size must be a positive integer")
    return dict(value)


def _verify_locked_file(value: Mapping[str, Any], *, label: str) -> Path:
    path = Path(value["path"])
    _assert_safe_existing_file(path, label=label)
    size = path.stat().st_size
    if size != value["size"]:
        raise ApplianceHold("size_mismatch", f"{label}: expected {value['size']}, got {size}")
    digest = sha256_file(path)
    if digest != value["sha256"]:
        raise ApplianceHold("hash_mismatch", f"{label}: expected {value['sha256']}, got {digest}")
    return path


def _validate_requirements_lock(path: Path) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ApplianceHold("invalid_requirements_lock", str(exc)) from exc
    forbidden = (
        "http://",
        "https://",
        "git+",
        "--index-url",
        "--extra-index-url",
        "--find-links",
        "--trusted-host",
        "--editable",
        "${",
    )
    lowered = text.casefold()
    if any(token in lowered for token in forbidden):
        raise ApplianceHold("invalid_requirements_lock", "network, VCS, variable, and editable inputs are forbidden")
    blocks: list[str] = []
    pending = ""
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            if pending and stripped.startswith("#"):
                raise ApplianceHold("invalid_requirements_lock", "comments may not interrupt a requirement")
            continue
        continued = stripped.endswith("\\")
        fragment = stripped[:-1].rstrip() if continued else stripped
        pending = f"{pending} {fragment}".strip()
        if not continued:
            blocks.append(pending)
            pending = ""
    if pending:
        raise ApplianceHold("invalid_requirements_lock", "unterminated line continuation")
    exact_requirement = re.compile(
        r"^[A-Za-z0-9][A-Za-z0-9_.-]*"
        r"(?:\[[A-Za-z0-9_,.-]+\])?"
        r"==[^\s;@/\\]+"
        r"(?:\s+--hash=sha256:[0-9a-f]{64})+$"
    )
    if not blocks or any(exact_requirement.fullmatch(block) is None for block in blocks):
        raise ApplianceHold(
            "invalid_requirements_lock",
            "each logical entry must be one exact package==version with its own lowercase SHA-256 hash(es)",
        )


def load_profile(path: Path) -> dict[str, Any]:
    value = _read_json(path, label="profile")
    if not isinstance(value, dict):
        raise ApplianceHold("schema_mismatch", "profile must be an object")
    _exact_keys(
        value,
        (
            "schema",
            "image",
            "build",
            "runtime",
            "hnc_evidence_policy",
        ),
        label="profile",
    )
    if value["schema"] != PROFILE_SCHEMA:
        raise ApplianceHold("schema_mismatch", f"unsupported profile schema: {value['schema']!r}")
    image = value["image"]
    build = value["build"]
    runtime = value["runtime"]
    hnc = value["hnc_evidence_policy"]
    if not all(isinstance(item, dict) for item in (image, build, runtime, hnc)):
        raise ApplianceHold("schema_mismatch", "profile sections must be objects")
    _exact_keys(
        image,
        ("id", "version", "distribution", "release", "architecture", "disk_size", "seed"),
        label="profile.image",
    )
    _exact_keys(
        build,
        (
            "minimum_free_bytes",
            "minimum_repart_version",
            "payload_paths",
            "el_torito",
        ),
        label="profile.build",
    )
    _exact_keys(
        runtime,
        ("enabled_on_image", "enabled_after_firstboot", "safe_environment"),
        label="profile.runtime",
    )
    _exact_keys(
        hnc,
        ("model", "immutable_frames", "receipt_memory", "gamma_is_authority", "hard_gates_override"),
        label="profile.hnc_evidence_policy",
    )
    if image["architecture"] != "x86-64" or image["distribution"] != "debian":
        raise ApplianceHold("unsupported_profile", "only Debian x86-64 is currently accepted")
    safe_field = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
    for key in ("id", "version", "release"):
        if not isinstance(image[key], str) or safe_field.fullmatch(image[key]) is None:
            raise ApplianceHold("schema_mismatch", f"profile.image.{key} is not a safe identifier")
    if not isinstance(image["disk_size"], str) or re.fullmatch(r"[1-9][0-9]{0,3}G", image["disk_size"]) is None:
        raise ApplianceHold("schema_mismatch", "profile.image.disk_size must be 1..9999G syntax")
    if not isinstance(image["seed"], str) or UUID_RE.fullmatch(image["seed"]) is None:
        raise ApplianceHold("schema_mismatch", "profile.image.seed must be a fixed UUID")
    if not isinstance(build["minimum_free_bytes"], int) or build["minimum_free_bytes"] <= 0:
        raise ApplianceHold("schema_mismatch", "minimum_free_bytes must be positive")
    if not isinstance(build["minimum_repart_version"], int) or build["minimum_repart_version"] < 261:
        raise ApplianceHold("schema_mismatch", "El Torito requires systemd-repart 261 or newer")
    if build["el_torito"] is not True:
        raise ApplianceHold("schema_mismatch", "the ISO profile requires el_torito=true")
    paths = build["payload_paths"]
    if not isinstance(paths, list) or not paths:
        raise ApplianceHold("schema_mismatch", "payload_paths must be a non-empty list")
    canonical = [_canonical_relpath(item, label="payload path") for item in paths]
    lowered = [str(item).casefold() for item in canonical]
    if len(lowered) != len(set(lowered)):
        raise ApplianceHold("unsafe_path", "payload paths contain duplicate/case-colliding entries")
    for item in canonical:
        if _payload_path_is_denied(item):
            raise ApplianceHold("unsafe_payload", f"secret-like payload path is denied: {item}")
    safe_env = runtime["safe_environment"]
    if not isinstance(safe_env, dict) or not all(
        isinstance(key, str) and isinstance(item, str) for key, item in safe_env.items()
    ):
        raise ApplianceHold("schema_mismatch", "safe_environment must map strings to strings")
    if any(
        re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", key) is None
        or any(character in item for character in "\r\n\x00")
        for key, item in safe_env.items()
    ):
        raise ApplianceHold("schema_mismatch", "safe_environment contains an unsafe key or value")
    required_safe = {
        "AUREON_AUDIT_MODE": "1",
        "AUREON_LIVE_TRADING": "0",
        "AUREON_DISABLE_REAL_ORDERS": "1",
        "AUREON_DISABLE_EXCHANGE_MUTATIONS": "1",
        "AUREON_DRY_RUN": "1",
        "DRY_RUN": "1",
        "LIVE": "0",
        "AUREON_LLM_OFFLINE": "1",
        "AUREON_DISABLE_LLM_HTTP": "1",
        "AUREON_LOCAL_ACTIONS_ARMED": "0",
        "AUREON_SOUL_ACT": "0",
        "AUREON_AUTONOMY": "0",
        "AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS": "1",
        "AUREON_OPERATOR_HOST": "127.0.0.1",
        "AUREON_OPERATOR_PORT": "8790",
        "AUREON_OPERATOR_HTTP_PROCESSES": "1",
        "AUREON_OPERATOR_REPLICAS": "1",
    }
    if safe_env != required_safe:
        raise ApplianceHold("unsafe_runtime", "safe environment does not preserve every hard gate")
    if runtime["enabled_on_image"] != [
        "aureon-boot-attestation.service",
        "aureon-firstboot-console.service",
    ]:
        raise ApplianceHold(
            "unsafe_runtime",
            "only boot attestation and the owner console gate may be enabled in the image",
        )
    if runtime["enabled_after_firstboot"] != ["aureon-appliance.target"]:
        raise ApplianceHold("unsafe_runtime", "first boot may enable only aureon-appliance.target")
    if (
        hnc.get("model") != "film_reel_engineering_translation_v1"
        or hnc.get("immutable_frames") is not True
        or hnc.get("receipt_memory") is not True
        or hnc.get("gamma_is_authority") is not False
        or hnc.get("hard_gates_override") is not True
    ):
        raise ApplianceHold("unsafe_hnc_policy", "HNC coherence must never replace hard gates")
    return value


def load_inputs(path: Path) -> dict[str, Any]:
    value = _read_json(path, label="input lock")
    if not isinstance(value, dict):
        raise ApplianceHold("schema_mismatch", "input lock must be an object")
    _exact_keys(
        value,
        (
            "schema",
            "source",
            "base_tree",
            "tools_tree",
            "requirements_lock",
            "wheelhouse",
            "tools",
            "boot_test",
        ),
        label="input lock",
    )
    if value["schema"] != INPUT_SCHEMA:
        raise ApplianceHold("schema_mismatch", f"unsupported input schema: {value['schema']!r}")
    source = value["source"]
    if not isinstance(source, dict):
        raise ApplianceHold("schema_mismatch", "source must be an object")
    _exact_keys(source, ("commit", "tree", "source_date_epoch"), label="input lock.source")
    for key in ("commit", "tree"):
        if not isinstance(source[key], str) or re.fullmatch(r"[0-9a-f]{40}", source[key]) is None:
            raise ApplianceHold("schema_mismatch", f"source.{key} must be a lowercase Git object id")
    if not isinstance(source["source_date_epoch"], int) or source["source_date_epoch"] <= 0:
        raise ApplianceHold("schema_mismatch", "source.source_date_epoch must be positive")
    for name in ("base_tree", "tools_tree", "requirements_lock"):
        _validate_file_lock(value[name], label=name)
    wheelhouse = value["wheelhouse"]
    if not isinstance(wheelhouse, dict):
        raise ApplianceHold("schema_mismatch", "wheelhouse must be an object")
    _exact_keys(wheelhouse, ("path", "manifest"), label="wheelhouse")
    if not isinstance(wheelhouse["path"], str) or not wheelhouse["path"]:
        raise ApplianceHold("input_unconfigured", "wheelhouse.path is required")
    _validate_file_lock(wheelhouse["manifest"], label="wheelhouse.manifest")
    tools = value["tools"]
    if not isinstance(tools, dict):
        raise ApplianceHold("schema_mismatch", "tools must be an object")
    _exact_keys(tools, ("git", "mkosi", "qemu_img"), label="tools")
    for name, tool in tools.items():
        if not isinstance(tool, dict):
            raise ApplianceHold("schema_mismatch", f"tools.{name} must be an object")
        _exact_keys(tool, ("path", "sha256", "size", "version_output_sha256"), label=f"tools.{name}")
        _validate_file_lock(
            {key: tool[key] for key in ("path", "sha256", "size")},
            label=f"tools.{name}",
        )
        _validate_hash(tool["version_output_sha256"], label=f"tools.{name}.version_output_sha256")
    boot = value["boot_test"]
    if not isinstance(boot, dict):
        raise ApplianceHold("schema_mismatch", "boot_test must be an object")
    _exact_keys(boot, ("qemu_system", "ovmf_code", "ovmf_vars", "timeout_seconds"), label="boot_test")
    for name in ("qemu_system", "ovmf_code", "ovmf_vars"):
        _validate_file_lock(boot[name], label=f"boot_test.{name}")
    if not isinstance(boot["timeout_seconds"], int) or not 30 <= boot["timeout_seconds"] <= 600:
        raise ApplianceHold("schema_mismatch", "boot timeout must be 30..600 seconds")
    return value


def _run_checked(
    argv: Sequence[str], *, cwd: Path, env: Mapping[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    if not argv or any(not isinstance(item, str) or "\x00" in item for item in argv):
        raise ApplianceHold("invalid_command", "command argv must contain non-empty safe strings")
    with tempfile.TemporaryDirectory(prefix="aureon-tool-env-") as temporary_home:
        if env is None:
            executable_parent = str(Path(argv[0]).resolve().parent)
            if os.name == "nt":
                system_root = os.environ.get("SYSTEMROOT", os.environ.get("WINDIR", r"C:\Windows"))
                safe_path = os.pathsep.join((executable_parent, str(Path(system_root) / "System32")))
            else:
                safe_path = os.pathsep.join(dict.fromkeys((executable_parent, "/usr/bin", "/bin")))
            actual_env = {
                key: os.environ[key] for key in ("SYSTEMROOT", "WINDIR") if key in os.environ
            }
            actual_env.update(
                {
                    "PATH": safe_path,
                    "HOME": temporary_home,
                    "XDG_CONFIG_HOME": temporary_home,
                    "XDG_CACHE_HOME": temporary_home,
                    "LANG": "C.UTF-8",
                    "LC_ALL": "C.UTF-8",
                    "TZ": "UTC",
                    "PYTHONNOUSERSITE": "1",
                    "GIT_CONFIG_NOSYSTEM": "1",
                    "GIT_CONFIG_GLOBAL": os.devnull,
                    "GIT_TERMINAL_PROMPT": "0",
                    "GIT_OPTIONAL_LOCKS": "0",
                    "http_proxy": "",
                    "https_proxy": "",
                    "HTTP_PROXY": "",
                    "HTTPS_PROXY": "",
                    "ALL_PROXY": "",
                    "NO_PROXY": "*",
                }
            )
        else:
            actual_env = dict(env)
        try:
            completed = subprocess.run(
                list(argv),
                cwd=cwd,
                env=actual_env,
                shell=False,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except OSError as exc:
            raise ApplianceHold("command_start_failed", f"argv={list(argv)!r}: {exc}") from exc
    if completed.returncode != 0:
        stdout_raw = completed.stdout.encode("utf-8")
        stderr_raw = completed.stderr.encode("utf-8")
        raise ApplianceHold(
            "command_failed",
            " ".join(
                (
                    f"argv={list(argv)!r}",
                    f"rc={completed.returncode}",
                    f"stdout_size={len(stdout_raw)}",
                    f"stdout_sha256={_sha256_bytes(stdout_raw)}",
                    f"stderr_size={len(stderr_raw)}",
                    f"stderr_sha256={_sha256_bytes(stderr_raw)}",
                )
            ),
        )
    return completed


def _git(repo: Path, *args: str, executable: str = "git") -> str:
    return _run_checked(
        (
            executable,
            "-c",
            "core.quotepath=false",
            "-c",
            f"core.hooksPath={os.devnull}",
            "-c",
            "core.fsmonitor=false",
            "-c",
            "credential.helper=",
            *args,
        ),
        cwd=repo,
    ).stdout.strip()


def _repo_identity(repo: Path, *, git_executable: str = "git") -> dict[str, Any]:
    _assert_safe_existing_dir(repo, label="source checkout")
    git_directory = repo / ".git"
    if _is_reparse_or_link(git_directory) or not git_directory.is_dir():
        raise ApplianceHold("unsafe_repo", f"not a safe absolute Git checkout: {repo}")
    status = _git(repo, "status", "--porcelain=v1", "--untracked-files=all", executable=git_executable)
    if status:
        raise ApplianceHold("dirty_source", "source checkout must be completely clean")
    return {
        "commit": _git(repo, "rev-parse", "HEAD", executable=git_executable),
        "tree": _git(repo, "rev-parse", "HEAD^{tree}", executable=git_executable),
        "source_date_epoch": int(
            _git(repo, "show", "-s", "--format=%ct", "HEAD", executable=git_executable)
        ),
    }


def _verify_tool(tool: Mapping[str, Any], *, name: str, repo: Path) -> Path:
    path = _verify_locked_file(tool, label=f"tool {name}")
    completed = _run_checked((str(path), "--version"), cwd=repo)
    raw = (completed.stdout + completed.stderr).encode("utf-8")
    digest = _sha256_bytes(raw)
    if digest != tool["version_output_sha256"]:
        raise ApplianceHold(
            "tool_version_mismatch",
            f"{name}: expected version output hash {tool['version_output_sha256']}, got {digest}",
        )
    return path


def _verify_repart_capability(
    *, mkosi: Path, tools_tree: Path, minimum_version: int, repo: Path, epoch: int
) -> None:
    with tempfile.TemporaryDirectory(prefix="aureon-repart-probe-") as temporary:
        probe = Path(temporary)
        (probe / "mkosi.conf").write_text(
            "[Build]\n"
            f"ToolsTree={_mkosi_value(str(tools_tree))}\n"
            "WithNetwork=no\n"
            "CacheOnly=always\n"
            "History=no\n",
            encoding="utf-8",
            newline="\n",
        )
        completed = _run_checked(
            (str(mkosi), "--directory", str(probe), "box", "--", "systemd-repart", "--version"),
            cwd=repo,
            env=_minimal_env(probe, epoch),
        )
    match = re.search(r"(?m)^systemd\s+([0-9]+)(?:\s|$)", completed.stdout + completed.stderr)
    if match is None or int(match.group(1)) < minimum_version:
        actual = match.group(1) if match else "unparseable"
        raise ApplianceHold(
            "repart_too_old",
            f"systemd-repart {minimum_version}+ is required for El Torito; got {actual}",
        )


def _verify_mkosi_config(
    *,
    mkosi: Path,
    profile: Mapping[str, Any],
    inputs: Mapping[str, Any],
    repo: Path,
    epoch: int,
) -> str:
    with tempfile.TemporaryDirectory(prefix="aureon-mkosi-config-probe-") as temporary:
        probe = Path(temporary)
        (probe / "mkosi.repart").mkdir()
        config = render_mkosi_config(profile=profile, inputs=inputs, work_dir=probe)
        (probe / "mkosi.conf").write_text(config, encoding="utf-8", newline="\n")
        summary = _run_checked(
            (str(mkosi), "--directory", str(probe), "summary"),
            cwd=repo,
            env=_minimal_env(probe, epoch),
        )
        loaded = _run_checked(
            (str(mkosi), "--directory", str(probe), "cat-config"),
            cwd=repo,
            env=_minimal_env(probe, epoch),
        )
        expected_output = f"{profile['image']['id']}-{profile['image']['version']}.iso"
        expected_output_directory = probe / "artifacts"
    evidence = summary.stdout + summary.stderr + loaded.stdout + loaded.stderr
    diagnostic_lines = re.sub(
        r"\x1b\[[0-?]*[ -/]*[@-~]", "", summary.stderr + "\n" + loaded.stderr
    ).splitlines()
    compatibility_warning = re.compile(
        r"^(?:warning(?:\[[^]]+\])?\s*:?\s*)?"
        r"(?:unknown setting\b|setting\b.*\bshould be configured in\b|"
        r"setting\b.*\bis deprecated\b)",
        re.IGNORECASE,
    )
    if any(
        compatibility_warning.search(re.sub(r"^[^A-Za-z0-9]+", "", line.strip()))
        for line in diagnostic_lines
    ):
        raise ApplianceHold(
            "mkosi_config_mismatch",
            "mkosi emitted a configuration compatibility warning",
        )
    resolved = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", summary.stdout)

    def summary_value(label: str) -> str:
        match = re.search(rf"(?m)^\s*{re.escape(label)}:\s*(.*?)\s*$", resolved)
        if match is None:
            raise ApplianceHold(
                "mkosi_config_mismatch", f"mkosi summary omitted resolved field: {label}"
            )
        return match.group(1)

    actual = {
        "Output Format": summary_value("Output Format"),
        "Output": summary_value("Output"),
        "Output Directory": summary_value("Output Directory"),
        "El Torito": summary_value("El Torito"),
        "Source Date Epoch": summary_value("Source Date Epoch"),
        "Bootable": summary_value("Bootable"),
        "Bootloader": summary_value("Bootloader"),
    }
    if (
        actual["Output Format"] != "disk"
        or actual["Output"] != expected_output
        or Path(actual["Output Directory"]) != expected_output_directory
        or actual["El Torito"] not in {"enabled", "yes", "true"}
        or actual["Source Date Epoch"] != str(epoch)
        or actual["Bootable"] not in {"enabled", "yes", "true"}
        or actual["Bootloader"] != "systemd-boot"
    ):
        raise ApplianceHold(
            "mkosi_config_mismatch",
            "mkosi summary did not resolve the required disk/ISO/boot/reproducibility settings",
        )
    if "ElTorito=yes" not in loaded.stdout or f"SourceDateEpoch={epoch}" not in loaded.stdout:
        raise ApplianceHold(
            "mkosi_config_mismatch",
            "mkosi did not load the exact rendered ISO/reproducibility settings",
        )
    return _sha256_bytes(evidence.encode("utf-8"))


def _verify_wheelhouse(inputs: Mapping[str, Any]) -> list[dict[str, Any]]:
    wheelhouse = inputs["wheelhouse"]
    root = Path(wheelhouse["path"])
    _assert_safe_existing_dir(root, label="wheelhouse")
    manifest_path = _verify_locked_file(wheelhouse["manifest"], label="wheelhouse manifest")
    manifest = _read_json(manifest_path, label="wheelhouse manifest")
    if not isinstance(manifest, dict):
        raise ApplianceHold("schema_mismatch", "wheelhouse manifest must be an object")
    _exact_keys(manifest, ("schema", "files"), label="wheelhouse manifest")
    if manifest["schema"] != WHEELHOUSE_SCHEMA or not isinstance(manifest["files"], list):
        raise ApplianceHold("schema_mismatch", "unsupported wheelhouse manifest")
    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, entry in enumerate(manifest["files"]):
        label = f"wheelhouse.files[{index}]"
        if not isinstance(entry, dict):
            raise ApplianceHold("schema_mismatch", f"{label} must be an object")
        _exact_keys(entry, ("path", "sha256", "size"), label=label)
        relative = _canonical_relpath(entry["path"], label=f"{label}.path")
        folded = str(relative).casefold()
        if folded in seen:
            raise ApplianceHold("unsafe_path", "wheelhouse contains duplicate/case-colliding paths")
        seen.add(folded)
        _validate_hash(entry["sha256"], label=f"{label}.sha256")
        if not isinstance(entry["size"], int) or entry["size"] <= 0:
            raise ApplianceHold("schema_mismatch", f"{label}.size must be positive")
        candidate = root.joinpath(*relative.parts)
        _assert_safe_existing_file(candidate, label=label)
        if candidate.stat().st_size != entry["size"] or sha256_file(candidate) != entry["sha256"]:
            raise ApplianceHold("hash_mismatch", f"wheelhouse entry does not match: {relative}")
        results.append({"path": str(relative), "sha256": entry["sha256"], "size": entry["size"]})
    if not results or results != sorted(results, key=lambda item: item["path"]):
        raise ApplianceHold("schema_mismatch", "wheelhouse files must be non-empty and sorted")
    return results


def _verified_material_digest(inputs: Mapping[str, Any]) -> str:
    locked: list[tuple[str, Mapping[str, Any]]] = [
        ("base_tree", inputs["base_tree"]),
        ("tools_tree", inputs["tools_tree"]),
        ("requirements_lock", inputs["requirements_lock"]),
        ("wheelhouse_manifest", inputs["wheelhouse"]["manifest"]),
    ]
    locked.extend((f"tool_{name}", value) for name, value in sorted(inputs["tools"].items()))
    locked.extend(
        (f"boot_{name}", inputs["boot_test"][name])
        for name in ("qemu_system", "ovmf_code", "ovmf_vars")
    )
    entries: list[dict[str, Any]] = []
    for label, value in locked:
        path = _verify_locked_file(value, label=label)
        entries.append(
            {
                "label": label,
                "path": str(path),
                "size": value["size"],
                "sha256": value["sha256"],
            }
        )
    for entry in _verify_wheelhouse(inputs):
        entries.append({"label": "wheel", **entry})
    return _sha256_bytes(_canonical_bytes(entries))


def preflight(repo: Path, profile_path: Path, inputs_path: Path) -> dict[str, Any]:
    """Validate all immutable inputs without mutating the checkout or host."""
    checks: list[dict[str, str]] = []

    def check(name: str, operation: Any) -> Any:
        try:
            result = operation()
        except ApplianceHold as exc:
            checks.append({"check": name, "status": "hold", "code": exc.code, "detail": exc.detail})
            return None
        checks.append({"check": name, "status": "pass", "code": "ok", "detail": "verified"})
        return result

    profile = check("profile", lambda: load_profile(profile_path))
    inputs = check("input_lock", lambda: load_inputs(inputs_path))
    git_path = None
    if inputs is not None:
        git_path = check("git", lambda: _verify_tool(inputs["tools"]["git"], name="git", repo=repo))
    identity = None
    if git_path is not None:
        identity = check("source", lambda: _repo_identity(repo, git_executable=str(git_path)))
    if profile is not None and inputs is not None:
        check("base_tree", lambda: _verify_locked_file(inputs["base_tree"], label="base_tree"))
        tools_tree_path = check(
            "tools_tree", lambda: _verify_locked_file(inputs["tools_tree"], label="tools_tree")
        )

        def requirements_check() -> None:
            locked = _verify_locked_file(inputs["requirements_lock"], label="requirements_lock")
            _validate_requirements_lock(locked)

        check("requirements_lock", requirements_check)
        check("wheelhouse", lambda: _verify_wheelhouse(inputs))
        mkosi_path = check(
            "mkosi", lambda: _verify_tool(inputs["tools"]["mkosi"], name="mkosi", repo=repo)
        )
        check("qemu_img", lambda: _verify_tool(inputs["tools"]["qemu_img"], name="qemu-img", repo=repo))
        if mkosi_path is not None and tools_tree_path is not None:
            check(
                "mkosi_config",
                lambda: _verify_mkosi_config(
                    mkosi=mkosi_path,
                    profile=profile,
                    inputs=inputs,
                    repo=repo,
                    epoch=inputs["source"]["source_date_epoch"],
                ),
            )
            check(
                "tools_tree_systemd_repart",
                lambda: _verify_repart_capability(
                    mkosi=mkosi_path,
                    tools_tree=tools_tree_path,
                    minimum_version=profile["build"]["minimum_repart_version"],
                    repo=repo,
                    epoch=inputs["source"]["source_date_epoch"],
                ),
            )
        check("qemu_system", lambda: _verify_locked_file(inputs["boot_test"]["qemu_system"], label="qemu_system"))
        check("ovmf_code", lambda: _verify_locked_file(inputs["boot_test"]["ovmf_code"], label="ovmf_code"))
        check("ovmf_vars", lambda: _verify_locked_file(inputs["boot_test"]["ovmf_vars"], label="ovmf_vars"))

    if profile is not None and inputs is not None and identity is not None:
        def source_binding() -> None:
            expected = inputs["source"]
            if expected != identity:
                raise ApplianceHold("source_mismatch", f"expected {expected}, got {identity}")

        check("source_binding", source_binding)

    def host_check() -> None:
        if platform.system() != "Linux":
            raise ApplianceHold("linux_builder_required", f"mkosi image build requires Linux, got {platform.system()}")
        if platform.machine().lower() not in {"x86_64", "amd64"}:
            raise ApplianceHold("unsupported_host", f"x86-64 builder required, got {platform.machine()}")
        if profile is not None:
            free = shutil.disk_usage(repo).free
            if free < profile["build"]["minimum_free_bytes"]:
                raise ApplianceHold("insufficient_space", f"need {profile['build']['minimum_free_bytes']}, got {free}")

    check("builder_host", host_check)
    status = "pass" if checks and all(item["status"] == "pass" for item in checks) else "hold"
    return {
        "schema": "aureon.appliance.preflight.v1",
        "status": status,
        "checks": checks,
        "source": identity,
        "profile_sha256": sha256_file(profile_path) if profile_path.is_file() else None,
        "inputs_sha256": sha256_file(inputs_path) if inputs_path.is_file() else None,
        "hnc_coherence_is_authority": False,
    }


@dataclass(frozen=True)
class ReceiptLedger:
    path: Path

    def _validated_entries(self) -> list[dict[str, Any]]:
        if self.path.parent.exists():
            _assert_safe_existing_dir(self.path.parent, label="receipt directory")
        if not self.path.exists():
            return []
        if self.path.is_symlink() or not self.path.is_file():
            raise ApplianceHold("unsafe_receipt", f"receipt ledger is not a regular file: {self.path}")
        entries: list[dict[str, Any]] = []
        previous = "0" * 64
        for line_number, raw in enumerate(self.path.read_bytes().splitlines(), 1):
            entry = _strict_json_bytes(raw, label=f"receipt line {line_number}")
            if not isinstance(entry, dict) or entry.get("schema") != RECEIPT_SCHEMA:
                raise ApplianceHold("invalid_receipt", f"line {line_number} has wrong schema")
            claimed = entry.get("entry_sha256")
            if not isinstance(claimed, str) or entry.get("previous_sha256") != previous:
                raise ApplianceHold("invalid_receipt", f"line {line_number} breaks the chain")
            body = dict(entry)
            body.pop("entry_sha256", None)
            actual = _sha256_bytes(_canonical_bytes(body))
            if claimed != actual:
                raise ApplianceHold("invalid_receipt", f"line {line_number} hash mismatch")
            previous = claimed
            entries.append(entry)
        return entries

    def append(self, *, stage: str, status: str, evidence: Mapping[str, Any]) -> dict[str, Any]:
        if status not in {"pass", "hold", "failed"}:
            raise ApplianceHold("invalid_receipt", f"unsupported receipt status: {status}")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        _assert_safe_existing_dir(self.path.parent, label="receipt directory")
        lock_path = self.path.with_name(self.path.name + ".lock")
        lock_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        try:
            lock_descriptor = os.open(lock_path, lock_flags, 0o600)
        except FileExistsError as exc:
            raise ApplianceHold("receipt_locked", f"exclusive receipt writer lock exists: {lock_path}") from exc
        nonce = os.urandom(16).hex().encode("ascii")
        try:
            _write_all(lock_descriptor, nonce, label="receipt lock")
            os.fsync(lock_descriptor)
            entries = self._validated_entries()
            body: dict[str, Any] = {
                "schema": RECEIPT_SCHEMA,
                "sequence": len(entries) + 1,
                "stage": stage,
                "status": status,
                "previous_sha256": entries[-1]["entry_sha256"] if entries else "0" * 64,
                "observed_unix_ns": time.time_ns(),
                "evidence": dict(evidence),
            }
            entry = {**body, "entry_sha256": _sha256_bytes(_canonical_bytes(body))}
            flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0)
            descriptor = os.open(self.path, flags, 0o600)
            try:
                _write_all(descriptor, _canonical_bytes(entry), label="receipt entry")
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            return entry
        finally:
            os.close(lock_descriptor)
            try:
                if lock_path.read_bytes() == nonce:
                    lock_path.unlink()
            except OSError:
                pass


@contextmanager
def _operation_lease(work_dir: Path) -> Iterable[None]:
    """Serialize every mutating stage for one exact work directory."""

    _assert_local_host_path(work_dir, label="work directory")
    parent = work_dir.parent
    parent.mkdir(parents=True, exist_ok=True)
    _assert_safe_existing_dir(parent, label="operation lock directory")
    lock_path = parent / f".{work_dir.name}.operation.lock"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(lock_path, flags, 0o600)
    except FileExistsError as exc:
        raise ApplianceHold(
            "operation_locked", f"exclusive appliance operation lock exists: {lock_path}"
        ) from exc
    except OSError as exc:
        raise ApplianceHold("operation_lock_failed", f"cannot create operation lock: {exc}") from exc
    nonce = os.urandom(16).hex().encode("ascii")
    try:
        _write_all(descriptor, nonce, label="operation lock")
        os.fsync(descriptor)
        yield
    finally:
        os.close(descriptor)
        try:
            if lock_path.read_bytes() == nonce:
                lock_path.unlink()
        except OSError:
            # A stale or changed lock intentionally blocks all later writers.
            pass


def _mkosi_value(value: str) -> str:
    if "\n" in value or "\r" in value or "\x00" in value:
        raise ApplianceHold("unsafe_path", "mkosi value contains control characters")
    escaped = value.replace("%", "%%").replace("\\", "\\\\").replace('"', '\\"')
    return '"' + escaped + '"'


def render_mkosi_config(
    *,
    profile: Mapping[str, Any],
    inputs: Mapping[str, Any],
    work_dir: Path,
) -> str:
    image = profile["image"]
    base = inputs["base_tree"]["path"]
    tools_tree = inputs["tools_tree"]["path"]
    return f"""# Generated from hash-locked Aureon appliance inputs. Do not edit.
[Distribution]
Distribution={image['distribution']}
Release={image['release']}
Architecture={image['architecture']}

[Output]
Format=disk
Output={image['id']}-{image['version']}
OutputExtension=iso
OutputDirectory=%D/artifacts
OutputSize={image['disk_size']}
CompressOutput=no
ManifestFormat=json
Seed={image['seed']}
ElTorito=yes
ElToritoVolume=AUREON_OS
ElToritoPublisher=Aureon
RepartDirectories=%D/mkosi.repart
SplitArtifacts=os-release,repart-definitions

[Content]
BaseTrees={_mkosi_value(base)}
Bootable=yes
Bootloader=systemd-boot
UnifiedKernelImages=auto
KernelCommandLine=console=tty0 console=ttyS0,115200n8 systemd.show_status=yes
Ssh=never
WithDocs=no
SourceDateEpoch={inputs['source']['source_date_epoch']}

[Build]
ToolsTree={_mkosi_value(tools_tree)}
CacheOnly=always
WithNetwork=no
Incremental=no
History=no
RepartOffline=yes
WorkspaceDirectory=%D/workspace
"""


def build_command_plan(
    *, profile: Mapping[str, Any], inputs: Mapping[str, Any], work_dir: Path
) -> dict[str, list[str]]:
    image_name = f"{profile['image']['id']}-{profile['image']['version']}"
    iso = work_dir / "artifacts" / f"{image_name}.iso"
    vhdx = work_dir / "artifacts" / f"{image_name}.vhdx"
    mkosi = str(Path(inputs["tools"]["mkosi"]["path"]))
    qemu_img = str(Path(inputs["tools"]["qemu_img"]["path"]))
    return {
        "image": [mkosi, "--directory", str(work_dir), "--force", "build"],
        "vhdx": [
            qemu_img,
            "convert",
            "-f",
            "raw",
            "-O",
            "vhdx",
            "-o",
            "subformat=fixed,block_size=2097152",
            str(iso),
            str(vhdx),
        ],
        "vhdx_check": [qemu_img, "check", "-f", "vhdx", str(vhdx)],
        "vhdx_info": [qemu_img, "info", "--output=json", str(vhdx)],
    }


def _safe_extract_tar(archive: Path, destination: Path) -> None:
    with tarfile.open(archive, "r:") as bundle:
        members = bundle.getmembers()
        for member in members:
            relative = _canonical_relpath(member.name.rstrip("/"), label="source archive member")
            if _payload_path_is_denied(relative):
                raise ApplianceHold("unsafe_archive", f"secret-like payload member: {relative}")
            if member.issym() or member.islnk() or member.isdev() or member.isfifo():
                raise ApplianceHold("unsafe_archive", f"special/link member is forbidden: {relative}")
            target = destination.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            if member.isdir():
                target.mkdir(exist_ok=True)
            elif member.isfile():
                stream = bundle.extractfile(member)
                if stream is None:
                    raise ApplianceHold("unsafe_archive", f"cannot read member: {relative}")
                with target.open("xb") as output:
                    shutil.copyfileobj(stream, output)
                os.chmod(target, member.mode & 0o777)
            else:
                raise ApplianceHold("unsafe_archive", f"unsupported member: {relative}")


def _copy_tree_no_links(source: Path, destination: Path) -> None:
    for base, directories, files in os.walk(source, followlinks=False):
        base_path = Path(base)
        for name in list(directories):
            candidate = base_path / name
            if _is_reparse_or_link(candidate):
                raise ApplianceHold("unsafe_path", f"static tree contains a link/reparse point: {candidate}")
        relative = base_path.relative_to(source)
        target_base = destination / relative
        target_base.mkdir(parents=True, exist_ok=True)
        for name in files:
            candidate = base_path / name
            if _is_reparse_or_link(candidate) or not candidate.is_file():
                raise ApplianceHold("unsafe_path", f"static tree contains a non-regular file: {candidate}")
            shutil.copyfile(candidate, target_base / name)
            shutil.copymode(candidate, target_base / name)


def _normalize_tree_times(root: Path, epoch: int) -> None:
    paths = sorted(root.rglob("*"), key=lambda item: len(item.parts), reverse=True)
    for path in paths:
        if not path.is_symlink():
            os.utime(path, (epoch, epoch), follow_symlinks=False)
    os.utime(root, (epoch, epoch), follow_symlinks=False)


def _staged_input_digest(root: Path) -> str:
    allowed_top_level = {
        "mkosi.conf",
        "mkosi.seed",
        "mkosi.postinst.chroot",
        "mkosi.finalize.chroot",
        "mkosi.extra",
        "mkosi.repart",
        "receipts.jsonl",
    }
    actual_top_level = {path.name for path in root.iterdir()}
    unexpected = sorted(actual_top_level - allowed_top_level)
    if unexpected:
        raise ApplianceHold(
            "staged_input_drift",
            f"unexpected top-level build input(s) could be auto-discovered by mkosi: {unexpected}",
        )
    candidates = [
        root / "mkosi.conf",
        root / "mkosi.seed",
        root / "mkosi.postinst.chroot",
        root / "mkosi.finalize.chroot",
    ]
    for directory_name in ("mkosi.extra", "mkosi.repart"):
        directory = root / directory_name
        if not directory.is_dir() or _is_reparse_or_link(directory):
            raise ApplianceHold("staged_input_drift", f"missing or unsafe staged directory: {directory_name}")
        candidates.extend(path for path in directory.rglob("*") if path.is_file() or path.is_symlink())
    entries: list[dict[str, Any]] = []
    for path in sorted(candidates, key=lambda item: item.relative_to(root).as_posix()):
        if _is_reparse_or_link(path) or not path.is_file():
            raise ApplianceHold("staged_input_drift", f"staged input is not a regular file: {path}")
        relative = path.relative_to(root).as_posix()
        entries.append(
            {
                "path": relative,
                "size": path.stat().st_size,
                "mode": stat.S_IMODE(path.stat().st_mode),
                "sha256": sha256_file(path),
            }
        )
    return _sha256_bytes(_canonical_bytes(entries))


def _stage_build_unlocked(
    repo: Path, profile_path: Path, inputs_path: Path, work_dir: Path
) -> dict[str, Any]:
    report = preflight(repo, profile_path, inputs_path)
    if report["status"] != "pass":
        raise ApplianceHold("preflight_hold", json.dumps(report["checks"], sort_keys=True))
    if work_dir.exists():
        raise ApplianceHold("workdir_exists", f"refusing pre-existing work directory: {work_dir}")
    _assert_safe_fresh_output(work_dir, repo=repo)
    profile = load_profile(profile_path)
    inputs = load_inputs(inputs_path)
    profile_digest = sha256_file(profile_path)
    inputs_digest = sha256_file(inputs_path)
    if (
        report.get("profile_sha256") != profile_digest
        or report.get("inputs_sha256") != inputs_digest
    ):
        raise ApplianceHold("configuration_drift", "profile or input lock changed after preflight")
    material_digest = _verified_material_digest(inputs)
    parent = work_dir.parent
    parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{work_dir.name}.", dir=parent))
    try:
        source_root = staging / "mkosi.extra" / "opt" / "aureon" / "source"
        source_root.mkdir(parents=True)
        archive = staging / "source.tar"
        payload = list(profile["build"]["payload_paths"])
        _run_checked(
            (
                str(Path(inputs["tools"]["git"]["path"])),
                "-c",
                f"core.hooksPath={os.devnull}",
                "-c",
                "core.fsmonitor=false",
                "-c",
                "credential.helper=",
                "archive",
                "--format=tar",
                f"--output={archive}",
                inputs["source"]["commit"],
                "--",
                *payload,
            ),
            cwd=repo,
        )
        _safe_extract_tar(archive, source_root)
        archive.unlink()

        template_snapshot = staging / ".template"
        template_snapshot.mkdir()
        template_archive = staging / "template.tar"
        _run_checked(
            (
                str(Path(inputs["tools"]["git"]["path"])),
                "-c",
                f"core.hooksPath={os.devnull}",
                "-c",
                "core.fsmonitor=false",
                "-c",
                "credential.helper=",
                "archive",
                "--format=tar",
                f"--output={template_archive}",
                inputs["source"]["commit"],
                "--",
                "packaging/appliance/rootfs",
                "packaging/appliance/mkosi.repart",
                "packaging/appliance/mkosi.postinst.chroot",
                "packaging/appliance/mkosi.finalize.chroot",
            ),
            cwd=repo,
        )
        _safe_extract_tar(template_archive, template_snapshot)
        template_archive.unlink()
        template_dir = template_snapshot / "packaging" / "appliance"
        rootfs = template_dir / "rootfs"
        _copy_tree_no_links(rootfs, staging / "mkosi.extra")
        shutil.copyfile(template_dir / "mkosi.postinst.chroot", staging / "mkosi.postinst.chroot")
        os.chmod(staging / "mkosi.postinst.chroot", 0o755)
        shutil.copyfile(template_dir / "mkosi.finalize.chroot", staging / "mkosi.finalize.chroot")
        os.chmod(staging / "mkosi.finalize.chroot", 0o755)
        _copy_tree_no_links(template_dir / "mkosi.repart", staging / "mkosi.repart")
        shutil.rmtree(template_snapshot)

        input_root = staging / "mkosi.extra" / "opt" / "aureon" / "build-inputs"
        wheel_target = input_root / "wheelhouse"
        wheel_target.mkdir(parents=True)
        wheel_entries = _verify_wheelhouse(inputs)
        wheel_source = Path(inputs["wheelhouse"]["path"])
        for entry in wheel_entries:
            relative = PurePosixPath(entry["path"])
            target = wheel_target.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(wheel_source.joinpath(*relative.parts), target)
            if target.stat().st_size != entry["size"] or sha256_file(target) != entry["sha256"]:
                raise ApplianceHold("staged_input_drift", f"wheel changed while copying: {relative}")
        requirements = _verify_locked_file(inputs["requirements_lock"], label="requirements_lock")
        _validate_requirements_lock(requirements)
        shutil.copyfile(requirements, input_root / "requirements.lock")
        if sha256_file(input_root / "requirements.lock") != inputs["requirements_lock"]["sha256"]:
            raise ApplianceHold("staged_input_drift", "requirements lock changed while copying")
        (staging / "mkosi.conf").write_text(
            render_mkosi_config(profile=profile, inputs=inputs, work_dir=staging),
            encoding="utf-8",
            newline="\n",
        )
        (staging / "mkosi.seed").write_text(profile["image"]["seed"] + "\n", encoding="ascii", newline="\n")
        _normalize_tree_times(staging, inputs["source"]["source_date_epoch"])
        if sha256_file(profile_path) != profile_digest or sha256_file(inputs_path) != inputs_digest:
            raise ApplianceHold("configuration_drift", "profile or input lock changed during staging")
        if _verified_material_digest(inputs) != material_digest:
            raise ApplianceHold("locked_material_drift", "external input material changed during staging")
        staging.replace(work_dir)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    evidence = {
        "status": "pass",
        "source": inputs["source"],
        "profile_sha256": profile_digest,
        "inputs_sha256": inputs_digest,
        "mkosi_config_sha256": sha256_file(work_dir / "mkosi.conf"),
        "staged_input_sha256": _staged_input_digest(work_dir),
        "locked_material_sha256": material_digest,
        "payload_paths": list(profile["build"]["payload_paths"]),
        "wheelhouse_files": wheel_entries,
    }
    ReceiptLedger(work_dir / "receipts.jsonl").append(stage="stage", status="pass", evidence=evidence)
    return evidence


def stage_build(repo: Path, profile_path: Path, inputs_path: Path, work_dir: Path) -> dict[str, Any]:
    with _operation_lease(work_dir):
        return _stage_build_unlocked(repo, profile_path, inputs_path, work_dir)


def _minimal_env(work_dir: Path, epoch: int) -> dict[str, str]:
    env = {key: os.environ[key] for key in SAFE_TOOL_ENV_KEYS if key in os.environ and key != "PATH"}
    env.update(
        {
            "PATH": "/usr/bin:/bin",
            "HOME": str(work_dir / "home"),
            "XDG_CACHE_HOME": str(work_dir / "cache"),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "TZ": "UTC",
            "SOURCE_DATE_EPOCH": str(epoch),
            "http_proxy": "",
            "https_proxy": "",
            "HTTP_PROXY": "",
            "HTTPS_PROXY": "",
            "ALL_PROXY": "",
            "NO_PROXY": "*",
        }
    )
    Path(env["HOME"]).mkdir(exist_ok=True)
    Path(env["XDG_CACHE_HOME"]).mkdir(exist_ok=True)
    return env


def _build_images_unlocked(
    repo: Path, profile_path: Path, inputs_path: Path, work_dir: Path
) -> dict[str, Any]:
    if not work_dir.exists():
        _stage_build_unlocked(repo, profile_path, inputs_path, work_dir)
    _assert_safe_existing_dir(work_dir, label="work directory")
    profile = load_profile(profile_path)
    inputs = load_inputs(inputs_path)
    report = preflight(repo, profile_path, inputs_path)
    if report["status"] != "pass":
        raise ApplianceHold("preflight_hold", "inputs changed after staging")
    entries = ReceiptLedger(work_dir / "receipts.jsonl")._validated_entries()
    if not entries or entries[-1].get("stage") != "stage" or entries[-1].get("status") != "pass":
        raise ApplianceHold("stage_receipt_missing", "a valid immediately-prior stage receipt is required")
    stage_evidence = entries[-1]["evidence"]
    if stage_evidence.get("profile_sha256") != sha256_file(profile_path):
        raise ApplianceHold("staged_input_drift", "profile changed after the stage receipt")
    if stage_evidence.get("inputs_sha256") != sha256_file(inputs_path):
        raise ApplianceHold("staged_input_drift", "input lock changed after the stage receipt")
    material_digest = _verified_material_digest(inputs)
    if stage_evidence.get("locked_material_sha256") != material_digest:
        raise ApplianceHold("staged_input_drift", "locked external material changed after staging")
    expected_config_hash = stage_evidence.get("mkosi_config_sha256")
    if expected_config_hash != sha256_file(work_dir / "mkosi.conf"):
        raise ApplianceHold("staged_input_drift", "mkosi.conf changed after the stage receipt")
    expected_staged_hash = stage_evidence.get("staged_input_sha256")
    if expected_staged_hash != _staged_input_digest(work_dir):
        raise ApplianceHold("staged_input_drift", "staged inputs changed after the stage receipt")
    plan = build_command_plan(profile=profile, inputs=inputs, work_dir=work_dir)
    env = _minimal_env(work_dir, inputs["source"]["source_date_epoch"])
    logs = work_dir / "logs"
    if logs.exists() or _is_reparse_or_link(logs):
        raise ApplianceHold("unsafe_output", "logs directory must not pre-exist image creation")
    try:
        logs.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise ApplianceHold("unsafe_output", "logs directory was created concurrently") from exc
    completed = _run_checked(plan["image"], cwd=work_dir, env=env)
    (logs / "mkosi.stdout").write_text(completed.stdout, encoding="utf-8", newline="\n")
    (logs / "mkosi.stderr").write_text(completed.stderr, encoding="utf-8", newline="\n")
    image_name = f"{profile['image']['id']}-{profile['image']['version']}"
    artifact_directory = work_dir / "artifacts"
    _assert_safe_existing_dir(artifact_directory, label="mkosi artifact directory")
    iso = artifact_directory / f"{image_name}.iso"
    _assert_safe_existing_file(iso, label="mkosi ISO candidate")
    if iso.stat().st_size == 0:
        raise ApplianceHold("missing_artifact", f"mkosi did not produce {iso}")
    vhdx = artifact_directory / f"{image_name}.vhdx"
    if vhdx.exists() or _is_reparse_or_link(vhdx):
        raise ApplianceHold("unsafe_output", "VHDX destination must not pre-exist conversion")
    converted = _run_checked(plan["vhdx"], cwd=work_dir, env=env)
    (logs / "qemu-img-convert.stdout").write_text(converted.stdout, encoding="utf-8", newline="\n")
    (logs / "qemu-img-convert.stderr").write_text(converted.stderr, encoding="utf-8", newline="\n")
    _assert_safe_existing_file(vhdx, label="converted VHDX")
    checked = _run_checked(plan["vhdx_check"], cwd=work_dir, env=env)
    info = _run_checked(plan["vhdx_info"], cwd=work_dir, env=env)
    info_value = _strict_json_bytes(info.stdout.encode("utf-8"), label="qemu-img info")
    if not isinstance(info_value, dict) or info_value.get("format") != "vhdx":
        raise ApplianceHold("vhdx_format_mismatch", "qemu-img did not identify the output as VHDX")
    (logs / "qemu-img-check.stdout").write_text(checked.stdout, encoding="utf-8", newline="\n")
    (logs / "qemu-img-info.json").write_text(info.stdout, encoding="utf-8", newline="\n")
    if _verified_material_digest(inputs) != material_digest:
        raise ApplianceHold("locked_material_drift", "external input material changed during image creation")
    if (
        sha256_file(profile_path) != stage_evidence["profile_sha256"]
        or sha256_file(inputs_path) != stage_evidence["inputs_sha256"]
    ):
        raise ApplianceHold("configuration_drift", "profile or input lock changed during image creation")
    artifacts = {
        "schema": ARTIFACT_SCHEMA,
        "status": "built_unbooted",
        "source": inputs["source"],
        "profile_sha256": sha256_file(profile_path),
        "inputs_sha256": sha256_file(inputs_path),
        "artifacts": [
            {"format": "gpt_el_torito_candidate", "path": iso.name, "size": iso.stat().st_size, "sha256": sha256_file(iso)},
            {"format": "vhdx", "path": vhdx.name, "size": vhdx.stat().st_size, "sha256": sha256_file(vhdx)},
        ],
        "network_policy": "mkosi_cache_only_and_build_scripts_network_disabled",
        "boot_verification": "pending",
        "vhdx_byte_reproducibility": "not_claimed",
        "secrets_embedded_status": "not_asserted_until_post_build_image_scan",
        "trading_enabled": False,
        "hnc_coherence_is_authority": False,
    }
    manifest_path = work_dir / "artifacts" / "aureon-artifacts.json"
    _write_report(manifest_path, artifacts)
    ReceiptLedger(work_dir / "receipts.jsonl").append(
        stage="image", status="pass", evidence={"artifact_manifest_sha256": sha256_file(manifest_path)}
    )
    return artifacts


def build_images(repo: Path, profile_path: Path, inputs_path: Path, work_dir: Path) -> dict[str, Any]:
    with _operation_lease(work_dir):
        return _build_images_unlocked(repo, profile_path, inputs_path, work_dir)


def _verify_artifacts_unlocked(
    inputs_path: Path, work_dir: Path, *, boot: bool = False
) -> dict[str, Any]:
    _assert_safe_existing_dir(work_dir, label="work directory")
    inputs = load_inputs(inputs_path)
    inputs_digest = sha256_file(inputs_path)
    material_digest = _verified_material_digest(inputs)
    manifest_path = work_dir / "artifacts" / "aureon-artifacts.json"
    manifest = _read_json(manifest_path, label="artifact manifest")
    if not isinstance(manifest, dict) or manifest.get("schema") != ARTIFACT_SCHEMA:
        raise ApplianceHold("schema_mismatch", "unsupported artifact manifest")
    _exact_keys(
        manifest,
        (
            "schema",
            "status",
            "source",
            "profile_sha256",
            "inputs_sha256",
            "artifacts",
            "network_policy",
            "boot_verification",
            "vhdx_byte_reproducibility",
            "secrets_embedded_status",
            "trading_enabled",
            "hnc_coherence_is_authority",
        ),
        label="artifact manifest",
    )
    if manifest["status"] != "built_unbooted" or manifest["inputs_sha256"] != inputs_digest:
        raise ApplianceHold("artifact_mismatch", "artifact manifest status or input binding changed")
    receipts = ReceiptLedger(work_dir / "receipts.jsonl")._validated_entries()
    image_receipts = [entry for entry in receipts if entry.get("stage") == "image" and entry.get("status") == "pass"]
    if (
        len(image_receipts) != 1
        or image_receipts[0]["evidence"].get("artifact_manifest_sha256") != sha256_file(manifest_path)
    ):
        raise ApplianceHold("artifact_mismatch", "artifact manifest is not bound to one passing image receipt")
    verified: list[dict[str, Any]] = []
    for entry in manifest.get("artifacts", []):
        if not isinstance(entry, dict):
            raise ApplianceHold("schema_mismatch", "artifact entry must be an object")
        _exact_keys(entry, ("format", "path", "size", "sha256"), label="artifact")
        relative = _canonical_relpath(entry["path"], label="artifact.path")
        artifact = (work_dir / "artifacts").joinpath(*relative.parts)
        _assert_safe_existing_file(artifact, label="artifact")
        if artifact.stat().st_size != entry["size"] or sha256_file(artifact) != entry["sha256"]:
            raise ApplianceHold("artifact_mismatch", f"artifact changed: {relative}")
        verified.append(dict(entry))
    formats = [item["format"] for item in verified]
    if sorted(formats) != ["gpt_el_torito_candidate", "vhdx"]:
        raise ApplianceHold("artifact_mismatch", "exactly one candidate ISO and one VHDX are required")
    qemu_img = _verify_tool(inputs["tools"]["qemu_img"], name="qemu-img", repo=work_dir)
    vhdx_entry = next(item for item in verified if item["format"] == "vhdx")
    vhdx = work_dir / "artifacts" / vhdx_entry["path"]
    _run_checked((str(qemu_img), "check", "-f", "vhdx", str(vhdx)), cwd=work_dir)
    iso_entry = next(item for item in verified if item["format"] == "gpt_el_torito_candidate")
    iso = work_dir / "artifacts" / iso_entry["path"]
    boot_evidence: dict[str, Any] = {"status": "not_requested"}
    if boot:
        boot_evidence = _boot_verify(inputs, work_dir, vhdx, iso)
    if sha256_file(inputs_path) != inputs_digest:
        raise ApplianceHold("configuration_drift", "input lock changed during verification")
    if _verified_material_digest(inputs) != material_digest:
        raise ApplianceHold("locked_material_drift", "external input material changed during verification")
    result = {
        "schema": "aureon.appliance.verification.v1",
        "status": "pass" if not boot or boot_evidence["status"] == "pass" else "hold",
        "artifact_manifest_sha256": sha256_file(manifest_path),
        "inputs_sha256": inputs_digest,
        "artifacts": verified,
        "boot": boot_evidence,
        "hnc_coherence_is_authority": False,
    }
    report_name = "aureon-boot-verification.json" if boot else "aureon-verification.json"
    report_path = work_dir / "artifacts" / report_name
    _write_report(report_path, result)
    ReceiptLedger(work_dir / "receipts.jsonl").append(
        stage="verify",
        status=result["status"],
        evidence={"verification_report_sha256": sha256_file(report_path)},
    )
    return result


def verify_artifacts(inputs_path: Path, work_dir: Path, *, boot: bool = False) -> dict[str, Any]:
    with _operation_lease(work_dir):
        return _verify_artifacts_unlocked(inputs_path, work_dir, boot=boot)


def _qemu_keyval_path(path: Path, *, label: str) -> str:
    value = str(path)
    if not path.is_absolute() or any(character in value for character in ",\r\n\x00"):
        raise ApplianceHold(
            "unsafe_qemu_path",
            f"{label} cannot be represented safely in QEMU key/value syntax",
        )
    return value


def _validate_boot_attestation(serial: str, *, media_kind: str) -> None:
    normalized = serial.replace("\r\n", "\n").replace("\r", "\n")
    if "AUREON_APPLIANCE_POLICY_HOLD" in normalized:
        raise ApplianceHold("boot_policy_hold", f"{media_kind} reported an Aureon policy HOLD")
    lines = [line.strip() for line in normalized.splitlines()]
    marker_positions = [index for index, line in enumerate(lines) if line == BOOT_MARKER]
    if len(marker_positions) != 1:
        raise ApplianceHold(
            "boot_marker_invalid",
            f"{media_kind} must emit exactly one unprefixed boot marker",
        )
    index = marker_positions[0]
    if index + 1 >= len(lines):
        raise ApplianceHold("boot_attestation_missing", f"{media_kind} omitted boot attestation JSON")
    attestation = _strict_json_bytes(
        lines[index + 1].encode("utf-8"), label=f"{media_kind} boot attestation"
    )
    if not isinstance(attestation, dict):
        raise ApplianceHold("boot_attestation_invalid", f"{media_kind} attestation is not an object")
    _exact_keys(attestation, BOOT_ATTESTATION, label=f"{media_kind} boot attestation")
    if attestation != BOOT_ATTESTATION:
        raise ApplianceHold(
            "boot_attestation_invalid", f"{media_kind} attestation values do not match first boot"
        )


def _boot_one(
    *,
    qemu: Path,
    code: Path,
    vars_template: Path,
    media: Path,
    media_kind: str,
    work_dir: Path,
    timeout_seconds: int,
    epoch: int,
) -> dict[str, Any]:
    boot_root = work_dir / "boot-tests"
    if boot_root.exists():
        _assert_safe_existing_dir(boot_root, label="boot-test directory")
    else:
        boot_root.mkdir(mode=0o700)
    attempt = Path(tempfile.mkdtemp(prefix=f"{media_kind}-", dir=boot_root))
    vars_copy = attempt / "OVMF_VARS.fd"
    shutil.copyfile(vars_template, vars_copy)
    serial_log = attempt / "serial.log"
    media_value = _qemu_keyval_path(media, label=media_kind)
    argv = [
        str(qemu),
        "-machine",
        "q35,accel=tcg",
        "-cpu",
        "max",
        "-m",
        "2048",
        "-smp",
        "2",
        "-drive",
        f"if=pflash,format=raw,readonly=on,file={_qemu_keyval_path(code, label='OVMF CODE')}",
        "-drive",
        f"if=pflash,format=raw,file={_qemu_keyval_path(vars_copy, label='OVMF VARS')}",
    ]
    if media_kind == "vhdx":
        argv.extend(("-drive", f"file={media_value},if=virtio,format=vhdx"))
    elif media_kind == "iso":
        argv.extend(
            ("-boot", "order=d", "-drive", f"file={media_value},media=cdrom,readonly=on,format=raw")
        )
    else:
        raise ApplianceHold("invalid_boot_media", f"unsupported boot medium: {media_kind}")
    argv.extend(
        (
            "-snapshot",
            "-nic",
            "none",
            "-display",
            "none",
            "-serial",
            f"file:{serial_log}",
            "-no-reboot",
        )
    )
    timed_out = False
    returncode: int | None
    try:
        completed = subprocess.run(
            argv,
            cwd=attempt,
            env=_minimal_env(attempt, epoch),
            shell=False,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
        )
        stdout = completed.stdout
        stderr = completed.stderr
        returncode = completed.returncode
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        returncode = None
    (attempt / "qemu.stdout").write_text(stdout, encoding="utf-8", newline="\n")
    (attempt / "qemu.stderr").write_text(stderr, encoding="utf-8", newline="\n")
    serial = serial_log.read_text(encoding="utf-8", errors="replace") if serial_log.is_file() else ""
    if returncode not in {None, 0}:
        raise ApplianceHold("boot_failed", f"{media_kind} QEMU exited with rc={returncode}")
    try:
        _validate_boot_attestation(serial, media_kind=media_kind)
    except ApplianceHold as exc:
        rc = "timeout" if timed_out else str(returncode)
        raise ApplianceHold(
            exc.code, f"{media_kind} QEMU rc={rc}; {exc.detail}"
        ) from exc
    vars_copy.unlink(missing_ok=True)
    return {
        "status": "pass",
        "marker": BOOT_MARKER,
        "serial_sha256": _sha256_bytes(serial.encode("utf-8")),
        "timed_out_after_marker": timed_out,
        "media_sha256": sha256_file(media),
        "network": "qemu_nic_none",
        "input": "snapshot" if media_kind == "vhdx" else "read_only_cdrom",
    }


def _boot_verify(inputs: Mapping[str, Any], work_dir: Path, vhdx: Path, iso: Path) -> dict[str, Any]:
    qemu = _verify_locked_file(inputs["boot_test"]["qemu_system"], label="qemu_system")
    code = _verify_locked_file(inputs["boot_test"]["ovmf_code"], label="ovmf_code")
    vars_template = _verify_locked_file(inputs["boot_test"]["ovmf_vars"], label="ovmf_vars")
    timeout_seconds = inputs["boot_test"]["timeout_seconds"]
    epoch = inputs["source"]["source_date_epoch"]
    targets = {
        "vhdx": _boot_one(
            qemu=qemu,
            code=code,
            vars_template=vars_template,
            media=vhdx,
            media_kind="vhdx",
            work_dir=work_dir,
            timeout_seconds=timeout_seconds,
            epoch=epoch,
        ),
        "iso": _boot_one(
            qemu=qemu,
            code=code,
            vars_template=vars_template,
            media=iso,
            media_kind="iso",
            work_dir=work_dir,
            timeout_seconds=timeout_seconds,
            epoch=epoch,
        ),
    }
    return {
        "status": "pass",
        "marker": "AUREON_APPLIANCE_BOOTABLE_FIRSTBOOT_REQUIRED",
        "targets": targets,
        "network": "qemu_nic_none",
        "input": "snapshot_vhdx_and_read_only_el_torito_candidate",
    }


def _write_report(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise ApplianceHold("report_exists", f"refusing to overwrite report: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    _assert_safe_existing_dir(path.parent, label="report directory")
    temporary = path.with_name(path.name + f".{os.getpid()}.tmp")
    try:
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
    except OSError as exc:
        raise ApplianceHold("report_write_failed", f"cannot create report temporary: {exc}") from exc
    try:
        try:
            _write_all(descriptor, _canonical_bytes(value), label="report")
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.link(temporary, path)
        temporary.unlink()
        if os.name != "nt":
            directory_descriptor = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
    except ApplianceHold:
        temporary.unlink(missing_ok=True)
        raise
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise ApplianceHold("report_write_failed", f"cannot publish report atomically: {exc}") from exc


def _default_paths(repo: Path) -> tuple[Path, Path]:
    root = repo / "packaging" / "appliance"
    return root / "profile.json", root / "inputs.example.json"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--inputs", type=Path)
    parser.add_argument("--work-dir", type=Path, required=True)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("preflight")
    subparsers.add_parser("stage")
    subparsers.add_parser("build")
    verify = subparsers.add_parser("verify")
    verify.add_argument("--boot", action="store_true")
    args = parser.parse_args(argv)
    repo = args.repo.absolute()
    default_profile, default_inputs = _default_paths(repo)
    profile_path = (args.profile or default_profile).absolute()
    inputs_path = (args.inputs or default_inputs).absolute()
    work_dir = args.work_dir.absolute()
    try:
        if args.command == "preflight":
            result = preflight(repo, profile_path, inputs_path)
            _assert_safe_fresh_output(work_dir, repo=repo)
            work_dir.mkdir(parents=True, exist_ok=True)
            _write_report(work_dir / "preflight.json", result)
            ReceiptLedger(work_dir / "receipts.jsonl").append(
                stage="preflight", status=result["status"], evidence=result
            )
            print(json.dumps({"status": result["status"], "report": str(work_dir / "preflight.json")}))
            return 0 if result["status"] == "pass" else 2
        with _operation_lease(work_dir):
            try:
                if args.command == "stage":
                    result = _stage_build_unlocked(repo, profile_path, inputs_path, work_dir)
                elif args.command == "build":
                    result = _build_images_unlocked(repo, profile_path, inputs_path, work_dir)
                else:
                    result = _verify_artifacts_unlocked(inputs_path, work_dir, boot=args.boot)
            except ApplianceHold as exc:
                ledger_path = work_dir / "receipts.jsonl"
                if ledger_path.is_file() and not ledger_path.is_symlink():
                    try:
                        ReceiptLedger(ledger_path).append(
                            stage=args.command,
                            status="hold",
                            evidence={
                                "code": exc.code,
                                "detail_sha256": _sha256_bytes(exc.detail.encode("utf-8")),
                            },
                        )
                    except ApplianceHold:
                        pass
                raise
        print(json.dumps({"status": result.get("status", "pass"), "work_dir": str(work_dir)}))
        return 0
    except ApplianceHold as exc:
        print(json.dumps({"status": "hold", "code": exc.code, "detail": exc.detail}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
