#!/usr/bin/env python3
"""Deterministic, state-safe pytest collection and shard execution.

The module has two roles:

* a command-line harness that creates/verifies a canonical collection manifest
  and runs exactly one deterministic file shard; and
* a small pytest plugin (loaded with ``-p`` by the harness) that records exact
  collected node IDs, collection problems, loaded plugins, and test outcomes.

The harness never repairs, deletes, or restores operational state.  A changed
fingerprint is terminal evidence: the current receipt records it and every
later shard for the same manifest is refused.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from collections import Counter, defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

SCHEMA = "aureon.pytest-no-skip-shards.v1"
PLUGIN_MODULE = "scripts.validation.pytest_no_skip_shards"
REPORT_OPTION = "--aureon-shard-report"

# This list is intentionally explicit.  Missing files are fingerprinted as
# missing so creation during collection or a shard is also detected.
OPERATIONAL_PATHS: tuple[str, ...] = (
    "aureon/exchanges/.kraken_nonce",
    "real_portfolio_state.json",
    "thoughts.jsonl",
    "trade_logger.log",
    "state/lambda_history.json",
    "state/lighthouse_event.jsonl",
    "state/capital_cfd_last_exchange_trace.json",
    "state/capital_cfd_pending_execution.json",
    "state/capital_shadow_promotions.jsonl",
    "state/aureon_capital_tradable_asset_registry.json",
    "state/unified_order_lifecycle_latest.json",
    "state/unified_order_lifecycle_events.jsonl",
)

SAFETY_ENVIRONMENT: Mapping[str, str] = {
    "AUREON_AUDIT_MODE": "1",
    "AUREON_LIVE": "0",
    "AUREON_LIVE_TRADING": "0",
    "AUREON_OBSERVER_MODE": "dry_run",
    "AUREON_DRY_RUN": "1",
    "AUREON_LLM_OFFLINE": "1",
    "AUREON_DISABLE_LLM_HTTP": "1",
    "AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS": "1",
    "AUREON_ALLOW_PAID_PROVIDERS": "false",
    "AUREON_PROVIDER_MODE": "offline",
    "LIVE": "0",
    "DRY_RUN": "1",
    "OFFLINE": "1",
    "NO_NETWORK": "1",
    "BINANCE_DRY_RUN": "true",
    "KRAKEN_DRY_RUN": "true",
    "ALPACA_DRY_RUN": "true",
    "CAPITAL_DEMO": "true",
    "OANDA_ENVIRONMENT": "practice",
    "AWS_EC2_METADATA_DISABLED": "true",
    "HF_HUB_OFFLINE": "1",
    "TRANSFORMERS_OFFLINE": "1",
    "PIP_NO_INDEX": "1",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHON_DOTENV_DISABLED": "1",
    "PYTEST_ADDOPTS": "",
    "HTTP_PROXY": "http://127.0.0.1:9",
    "HTTPS_PROXY": "http://127.0.0.1:9",
    "ALL_PROXY": "http://127.0.0.1:9",
    "NO_PROXY": "",
    "http_proxy": "http://127.0.0.1:9",
    "https_proxy": "http://127.0.0.1:9",
    "all_proxy": "http://127.0.0.1:9",
    "no_proxy": "",
}

_PROVIDER_PREFIXES = (
    "ALPACA_",
    "ANTHROPIC_",
    "AWS_",
    "BINANCE_",
    "BYBIT_",
    "CAPITAL_",
    "CLOUDFLARE_",
    "COINBASE_",
    "GEMINI_",
    "KRAKEN_",
    "KUCOIN_",
    "OANDA_",
    "OPENAI_",
    "STRIPE_",
    "SUPABASE_",
)
_CREDENTIAL_NAME = re.compile(
    r"(?:^|_)(?:API_KEY|API_SECRET|ACCESS_KEY|ACCESS_TOKEN|AUTH_TOKEN|BEARER_TOKEN|"
    r"CLIENT_SECRET|CONNECTION_STRING|COOKIE|CREDENTIAL|CREDENTIALS|DATABASE_URL|PASSWORD|"
    r"PASSPHRASE|PRIVATE_KEY|REFRESH_TOKEN|SECRET|SECRET_KEY|SERVICE_ACCOUNT|"
    r"SESSION_TOKEN|TOKEN)(?:$|_)",
)
_EXTERNAL_PYTEST_ENV = {"PYTEST_DISABLE_PLUGIN_AUTOLOAD", "PYTEST_PLUGINS"}
_ACTIVE_PYTEST_CONFIG: Any | None = None


class HarnessError(RuntimeError):
    """Fail-closed harness error with no state recovery side effect."""


@dataclass(frozen=True)
class ProcessCapture:
    argv: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool = False


Runner = Callable[[Sequence[str], Path, Mapping[str, str], float | None], ProcessCapture]


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _normalise_distribution(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _safe_relative_path(root: Path, value: str | Path) -> str:
    candidate = Path(value)
    resolved = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    try:
        relative = resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise HarnessError(f"path escapes repository root: {value}") from exc
    return relative.as_posix()


def _is_sensitive_environment_name(name: str) -> bool:
    upper = name.upper()
    return upper.startswith(_PROVIDER_PREFIXES) or bool(_CREDENTIAL_NAME.search(upper))


def safe_subprocess_environment(
    inherited: Mapping[str, str] | None = None,
) -> tuple[dict[str, str], tuple[str, ...]]:
    """Return a credential-scrubbed, fail-closed subprocess environment."""

    source = os.environ if inherited is None else inherited
    safe: dict[str, str] = {}
    scrubbed: list[str] = []
    for key, value in source.items():
        if key.upper() in _EXTERNAL_PYTEST_ENV or _is_sensitive_environment_name(key):
            scrubbed.append(key)
            continue
        safe[key] = value
    safe.update(SAFETY_ENVIRONMENT)
    return safe, tuple(sorted(scrubbed, key=str.upper))


def isolate_runtime_writers(environment: Mapping[str, str], temporary: Path) -> dict[str, str]:
    """Route supported append-only runtime writers into the shard temp root."""

    isolated = dict(environment)
    isolated.update(
        {
            "AUREON_THOUGHT_BUS_PATH": str(temporary / "thoughts.jsonl"),
            "AUREON_BUS_TRACE_DIR": str(temporary / "bus-traces"),
            "AUREON_HNC_TRACE_PATH": str(temporary / "hnc-live-trace.jsonl"),
        }
    )
    return isolated


def installed_pytest_plugin_inventory() -> list[dict[str, str]]:
    """Return a deterministic inventory of auto-loadable pytest entry points."""

    discovered = importlib.metadata.entry_points()
    selected = (
        discovered.select(group="pytest11")
        if hasattr(discovered, "select")
        else discovered.get("pytest11", [])
    )
    inventory: list[dict[str, str]] = []
    for entry_point in selected:
        distribution = getattr(entry_point, "dist", None)
        distribution_name = ""
        version = ""
        if distribution is not None:
            distribution_name = str(distribution.metadata.get("Name") or "")
            version = str(distribution.version or "")
        inventory.append(
            {
                "distribution": distribution_name,
                "entry_point": str(entry_point.name),
                "module": str(entry_point.value),
                "version": version,
            }
        )
    return sorted(
        inventory,
        key=lambda row: (
            _normalise_distribution(row["distribution"]),
            row["entry_point"],
            row["module"],
            row["version"],
        ),
    )


def require_pytest_socket(plugin_inventory: Sequence[Mapping[str, str]]) -> None:
    installed = {_normalise_distribution(str(entry.get("distribution") or "")) for entry in plugin_inventory}
    if "pytest-socket" not in installed:
        raise HarnessError(
            "pytest-socket is required for a no-network collection/shard; install it before running the harness"
        )


def fingerprint_operational_paths(
    root: Path,
    paths: Sequence[str] = OPERATIONAL_PATHS,
) -> dict[str, dict[str, Any]]:
    """Fingerprint exact protected paths without following symlinks."""

    root = root.resolve()
    fingerprints: dict[str, dict[str, Any]] = {}
    for raw_path in paths:
        relative = _safe_relative_path(root, raw_path)
        path = root / Path(relative)
        if not path.exists() and not path.is_symlink():
            fingerprints[relative] = {"exists": False}
            continue
        stat = path.lstat()
        common = {
            "exists": True,
            "mtime_ns": stat.st_mtime_ns,
            "size": stat.st_size,
        }
        if path.is_symlink():
            target = os.readlink(path)
            fingerprints[relative] = {
                **common,
                "kind": "symlink",
                "target": target,
                "sha256": _sha256_bytes(os.fsencode(target)),
            }
        elif path.is_file():
            fingerprints[relative] = {**common, "kind": "file", "sha256": _sha256_file(path)}
        elif path.is_dir():
            fingerprints[relative] = {**common, "kind": "directory"}
        else:
            fingerprints[relative] = {**common, "kind": "other"}
    return fingerprints


def operational_changes(
    before: Mapping[str, Mapping[str, Any]],
    after: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    for path in sorted(set(before) | set(after)):
        old = before.get(path)
        new = after.get(path)
        if old != new:
            changes.append({"path": path, "before": old, "after": new})
    return changes


def default_runner(
    argv: Sequence[str],
    cwd: Path,
    env: Mapping[str, str],
    timeout_seconds: float | None,
) -> ProcessCapture:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            list(argv),
            cwd=cwd,
            env=dict(env),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        return ProcessCapture(
            argv=tuple(str(part) for part in argv),
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            duration_seconds=time.monotonic() - started,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return ProcessCapture(
            argv=tuple(str(part) for part in argv),
            returncode=124,
            stdout=stdout,
            stderr=stderr,
            duration_seconds=time.monotonic() - started,
            timed_out=True,
        )
    except OSError as exc:
        return ProcessCapture(
            argv=tuple(str(part) for part in argv),
            returncode=127,
            stdout="",
            stderr=f"pytest process could not start: {exc}",
            duration_seconds=time.monotonic() - started,
        )


def _pytest_command(
    *,
    root: Path,
    config_path: Path,
    report_path: Path,
    cache_path: Path,
    targets: Sequence[str],
    collect_only: bool,
) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "pytest",
        "--rootdir",
        str(root),
        "-c",
        str(config_path),
        "-p",
        PLUGIN_MODULE,
        "--disable-socket",
        "--strict-config",
        "-o",
        f"cache_dir={cache_path}",
        f"{REPORT_OPTION}={report_path}",
    ]
    if collect_only:
        command.append("--collect-only")
    command.extend(targets)
    return command


def _load_json(path: Path, description: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HarnessError(f"unable to read {description} at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise HarnessError(f"{description} must be a JSON object: {path}")
    return value


def _write_new_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
    except FileExistsError as exc:
        raise HarnessError(f"refusing to overwrite existing evidence: {path}") from exc


def _validate_plugin_report(report: Mapping[str, Any]) -> None:
    if report.get("schema") != SCHEMA:
        raise HarnessError("pytest plugin report schema mismatch")
    if not report.get("socket_blocker_loaded"):
        raise HarnessError("pytest-socket was not loaded by pytest")
    if not report.get("socket_blocking_requested"):
        raise HarnessError("pytest did not honor --disable-socket")
    if not isinstance(report.get("items"), list):
        raise HarnessError("pytest plugin report has no item list")
    if not isinstance(report.get("collection_errors"), list):
        raise HarnessError("pytest plugin report has no collection error list")
    if not isinstance(report.get("collection_skips"), list):
        raise HarnessError("pytest plugin report has no collection skip list")


def _normalise_items(root: Path, raw_items: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for raw_item in raw_items:
        node_id = str(raw_item.get("node_id") or "")
        source_file = str(raw_item.get("source_file") or "")
        if not node_id or not source_file:
            raise HarnessError("every collected item must retain a node ID and source file")
        items.append({"node_id": node_id, "source_file": _safe_relative_path(root, source_file)})
    items.sort(key=lambda item: item["node_id"])
    duplicates = sorted(
        node_id for node_id, count in Counter(item["node_id"] for item in items).items() if count > 1
    )
    if duplicates:
        raise HarnessError(f"duplicate collected node IDs: {duplicates[:5]}")
    return items


def _canonical_skip(skip: Mapping[str, Any]) -> dict[str, str]:
    return {
        "node_id": str(skip.get("node_id") or ""),
        "reason": str(skip.get("reason") or ""),
    }


def assign_lpt_shards(items: Sequence[Mapping[str, str]], shard_count: int) -> list[dict[str, Any]]:
    """Assign whole files by deterministic longest-processing-time approximation."""

    if shard_count < 1:
        raise HarnessError("shard count must be positive")
    by_file: dict[str, list[str]] = defaultdict(list)
    for item in items:
        by_file[str(item["source_file"])].append(str(item["node_id"]))
    if not by_file:
        raise HarnessError("collection contained no test items")
    if shard_count > len(by_file):
        raise HarnessError(f"shard count {shard_count} exceeds collected source-file count {len(by_file)}")

    assignments: list[list[str]] = [[] for _ in range(shard_count)]
    loads = [0] * shard_count
    ordered_files = sorted(by_file, key=lambda path: (-len(by_file[path]), path))
    for source_file in ordered_files:
        shard_index = min(range(shard_count), key=lambda index: (loads[index], index))
        assignments[shard_index].append(source_file)
        loads[shard_index] += len(by_file[source_file])

    shards: list[dict[str, Any]] = []
    for index, files in enumerate(assignments, start=1):
        ordered = sorted(files)
        node_ids = sorted(node_id for source in ordered for node_id in by_file[source])
        shards.append(
            {
                "files": ordered,
                "item_count": len(node_ids),
                "node_ids": node_ids,
                "shard": index,
            }
        )
    return shards


def _assignment_proofs(
    items: Sequence[Mapping[str, str]], shards: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    collected_node_ids = sorted(str(item["node_id"]) for item in items)
    assigned_node_ids = [str(node_id) for shard in shards for node_id in shard["node_ids"]]
    counts = Counter(assigned_node_ids)
    duplicate_assignments = sorted(node_id for node_id, count in counts.items() if count != 1)
    missing = sorted(set(collected_node_ids) - set(assigned_node_ids))
    unexpected = sorted(set(assigned_node_ids) - set(collected_node_ids))
    if duplicate_assignments or missing or unexpected or len(assigned_node_ids) != len(collected_node_ids):
        raise HarnessError("shard assignment is not disjoint and exhaustive")
    collected_files = sorted({str(item["source_file"]) for item in items})
    assigned_files = [str(path) for shard in shards for path in shard["files"]]
    if len(assigned_files) != len(set(assigned_files)) or sorted(assigned_files) != collected_files:
        raise HarnessError("source-file shard assignment is not disjoint and exhaustive")
    return {
        "assigned_item_count": len(assigned_node_ids),
        "assigned_node_ids_sha256": _sha256_bytes(_canonical_bytes(sorted(assigned_node_ids))),
        "collected_item_count": len(collected_node_ids),
        "collected_node_ids_sha256": _sha256_bytes(_canonical_bytes(collected_node_ids)),
        "disjoint": True,
        "exhaustive": True,
        "source_file_count": len(collected_files),
        "source_files_sha256": _sha256_bytes(_canonical_bytes(collected_files)),
    }


def build_manifest(
    *,
    root: Path,
    config_path: Path,
    collection_targets: Sequence[str],
    shard_count: int,
    plugin_inventory: Sequence[Mapping[str, str]],
    plugin_report: Mapping[str, Any],
    baseline: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    _validate_plugin_report(plugin_report)
    collection_errors = plugin_report["collection_errors"]
    if collection_errors:
        raise HarnessError(f"pytest collection reported {len(collection_errors)} error(s)")
    items = _normalise_items(root, plugin_report["items"])
    shards = assign_lpt_shards(items, shard_count)
    proofs = _assignment_proofs(items, shards)
    root = root.resolve()
    payload: dict[str, Any] = {
        "collection": {
            "collection_skip_count": len(plugin_report["collection_skips"]),
            "collection_skips": sorted(
                (_canonical_skip(skip) for skip in plugin_report["collection_skips"]),
                key=lambda skip: (skip["node_id"], skip["reason"]),
            ),
            "items": items,
            "loaded_plugins": plugin_report.get("loaded_plugins", []),
            "targets": [_safe_relative_path(root, target) for target in collection_targets],
        },
        "operational_paths": list(OPERATIONAL_PATHS),
        "operational_state_baseline": dict(baseline),
        "proofs": proofs,
        "pytest_config": _safe_relative_path(root, config_path),
        "pytest_plugin_inventory": list(plugin_inventory),
        "safety": {
            "credential_environment_scrubbed": True,
            "external_pytest_option_injection_removed": sorted(_EXTERNAL_PYTEST_ENV),
            "network_blocker": "pytest-socket --disable-socket",
            "provider_environment": dict(SAFETY_ENVIRONMENT),
        },
        "schema": SCHEMA,
        "shard_count": shard_count,
        "shards": shards,
    }
    payload["manifest_sha256"] = _sha256_bytes(_canonical_bytes(payload))
    return payload


def verify_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    if manifest.get("schema") != SCHEMA:
        raise HarnessError("manifest schema mismatch")
    claimed_digest = str(manifest.get("manifest_sha256") or "")
    payload = dict(manifest)
    payload.pop("manifest_sha256", None)
    actual_digest = _sha256_bytes(_canonical_bytes(payload))
    if not claimed_digest or claimed_digest != actual_digest:
        raise HarnessError("manifest digest mismatch")
    items = manifest.get("collection", {}).get("items")
    shards = manifest.get("shards")
    if not isinstance(items, list) or not isinstance(shards, list):
        raise HarnessError("manifest collection/shards are malformed")
    expected_shards = assign_lpt_shards(items, int(manifest.get("shard_count") or 0))
    if shards != expected_shards:
        raise HarnessError("manifest shard assignment is not canonical LPT output")
    proofs = _assignment_proofs(items, shards)
    if manifest.get("proofs") != proofs:
        raise HarnessError("manifest assignment proofs do not verify")
    if manifest.get("operational_paths") != list(OPERATIONAL_PATHS):
        raise HarnessError("manifest operational path contract differs from this harness")
    return {"manifest_sha256": claimed_digest, "proofs": proofs}


def _process_payload(capture: ProcessCapture) -> dict[str, Any]:
    payload = asdict(capture)
    payload["argv"] = list(capture.argv)
    payload["stdout_sha256"] = _sha256_bytes(capture.stdout.encode("utf-8"))
    payload["stderr_sha256"] = _sha256_bytes(capture.stderr.encode("utf-8"))
    return payload


def _collection_receipt_path(manifest_path: Path) -> Path:
    return manifest_path.with_name(f"{manifest_path.name}.collection-receipt.json")


def _receipt_directory(manifest_path: Path) -> Path:
    return manifest_path.with_name(f"{manifest_path.name}.receipts")


def _shard_receipt_path(manifest_path: Path, shard_index: int) -> Path:
    return _receipt_directory(manifest_path) / f"shard-{shard_index:04d}.json"


def _prior_mutation_receipts(manifest_path: Path, manifest_sha256: str) -> list[Path]:
    receipt_dir = _receipt_directory(manifest_path)
    if not receipt_dir.exists():
        return []
    blocked: list[Path] = []
    for path in sorted(receipt_dir.glob("shard-*.json")):
        receipt = _load_json(path, "shard receipt")
        if receipt.get("manifest_sha256") != manifest_sha256:
            raise HarnessError(f"receipt belongs to another manifest: {path}")
        if receipt.get("state_mutation_detected"):
            blocked.append(path)
    return blocked


def collect_and_write_manifest(
    *,
    root: Path,
    config_path: Path,
    manifest_path: Path,
    shard_count: int,
    collection_targets: Sequence[str] = ("tests",),
    timeout_seconds: float | None = 900.0,
    runner: Runner = default_runner,
    plugin_inventory: Sequence[Mapping[str, str]] | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    config_path = config_path.resolve()
    manifest_path = manifest_path.resolve()
    if manifest_path.exists():
        raise HarnessError(f"refusing to overwrite existing manifest: {manifest_path}")
    receipt_path = _collection_receipt_path(manifest_path)
    if receipt_path.exists():
        raise HarnessError(f"refusing to overwrite existing collection receipt: {receipt_path}")
    if not config_path.is_file():
        raise HarnessError(f"pytest config does not exist: {config_path}")
    config_path = root / Path(_safe_relative_path(root, config_path))
    manifest_path = root / Path(_safe_relative_path(root, manifest_path))
    inventory = list(installed_pytest_plugin_inventory() if plugin_inventory is None else plugin_inventory)
    require_pytest_socket(inventory)
    environment, scrubbed = safe_subprocess_environment()
    before = fingerprint_operational_paths(root)

    with tempfile.TemporaryDirectory(prefix="aureon-pytest-collect-") as temp_dir:
        temporary = Path(temp_dir)
        environment = isolate_runtime_writers(environment, temporary)
        report_path = temporary / "pytest-report.json"
        command = _pytest_command(
            root=root,
            config_path=config_path,
            report_path=report_path,
            cache_path=temporary / "pytest-cache",
            targets=collection_targets,
            collect_only=True,
        )
        capture = runner(command, root, environment, timeout_seconds)
        plugin_report_error = ""
        try:
            plugin_report = (
                _load_json(report_path, "pytest collection report") if report_path.exists() else None
            )
        except HarnessError as exc:
            plugin_report = None
            plugin_report_error = str(exc)

    after = fingerprint_operational_paths(root)
    changes = operational_changes(before, after)
    receipt: dict[str, Any] = {
        "collection_errors": plugin_report.get("collection_errors", []) if plugin_report else [],
        "collection_skip_count": len(plugin_report.get("collection_skips", [])) if plugin_report else 0,
        "credential_keys_scrubbed": list(scrubbed),
        "operational_state_after": after,
        "operational_state_before": before,
        "operational_state_changes": changes,
        "process": _process_payload(capture),
        "pytest_report_error": plugin_report_error,
        "schema": SCHEMA,
        "state_mutation_detected": bool(changes),
    }
    _write_new_json(receipt_path, receipt)
    if changes:
        raise HarnessError("operational state changed during pytest collection; manifest creation aborted")
    if capture.timed_out:
        raise HarnessError("pytest collection timed out")
    if plugin_report is None:
        raise HarnessError("pytest did not produce its structured collection report")
    _validate_plugin_report(plugin_report)
    if capture.returncode != 0:
        error_count = len(plugin_report.get("collection_errors", []))
        raise HarnessError(
            f"pytest collection exited {capture.returncode} with {error_count} collection error(s)"
        )
    if plugin_report["collection_skips"]:
        raise HarnessError(
            f"pytest collection reported {len(plugin_report['collection_skips'])} skip(s)"
        )
    manifest = build_manifest(
        root=root,
        config_path=config_path,
        collection_targets=collection_targets,
        shard_count=shard_count,
        plugin_inventory=inventory,
        plugin_report=plugin_report,
        baseline=before,
    )
    _write_new_json(manifest_path, manifest)
    return manifest


def _acquire_lock(lock_path: Path, manifest_sha256: str, shard_index: int) -> None:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with lock_path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(
                {
                    "manifest_sha256": manifest_sha256,
                    "pid": os.getpid(),
                    "shard": shard_index,
                },
                handle,
                sort_keys=True,
            )
            handle.write("\n")
    except FileExistsError as exc:
        raise HarnessError(f"another shard run or an unreviewed interrupted run owns {lock_path}") from exc


def execute_one_shard(
    *,
    root: Path,
    manifest_path: Path,
    shard_index: int,
    timeout_seconds: float | None = 1800.0,
    runner: Runner = default_runner,
    plugin_inventory: Sequence[Mapping[str, str]] | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    manifest_path = manifest_path.resolve()
    manifest_path = root / Path(_safe_relative_path(root, manifest_path))
    manifest = _load_json(manifest_path, "pytest shard manifest")
    verification = verify_manifest(manifest)
    manifest_sha256 = verification["manifest_sha256"]
    if shard_index < 1 or shard_index > len(manifest["shards"]):
        raise HarnessError(f"shard index must be between 1 and {len(manifest['shards'])}")
    inventory = list(installed_pytest_plugin_inventory() if plugin_inventory is None else plugin_inventory)
    require_pytest_socket(inventory)
    if inventory != manifest["pytest_plugin_inventory"]:
        raise HarnessError("installed pytest plugin inventory differs from the collection manifest")
    prior_mutations = _prior_mutation_receipts(manifest_path, manifest_sha256)
    if prior_mutations:
        raise HarnessError(
            f"prior shard mutated operational state; further shards are blocked: {prior_mutations[0]}"
        )
    receipt_path = _shard_receipt_path(manifest_path, shard_index)
    if receipt_path.exists():
        raise HarnessError(f"refusing to overwrite existing shard receipt: {receipt_path}")

    baseline = manifest["operational_state_baseline"]
    before = fingerprint_operational_paths(root)
    baseline_changes = operational_changes(baseline, before)
    if baseline_changes:
        receipt = {
            "manifest_sha256": manifest_sha256,
            "operational_state_before": before,
            "operational_state_changes": baseline_changes,
            "schema": SCHEMA,
            "shard": shard_index,
            "state_mutation_detected": True,
            "status": "baseline_mismatch_before_run",
        }
        _write_new_json(receipt_path, receipt)
        raise HarnessError("operational state no longer matches the collection baseline; shard not started")

    config_path = root / Path(str(manifest["pytest_config"]))
    shard = manifest["shards"][shard_index - 1]
    environment, scrubbed = safe_subprocess_environment()
    receipt_dir = _receipt_directory(manifest_path)
    lock_path = receipt_dir / ".active-shard.lock"
    _acquire_lock(lock_path, manifest_sha256, shard_index)
    capture: ProcessCapture | None = None
    plugin_report: dict[str, Any] | None = None
    plugin_report_error = ""
    after = before
    try:
        with tempfile.TemporaryDirectory(prefix=f"aureon-pytest-shard-{shard_index:04d}-") as temp_dir:
            temporary = Path(temp_dir)
            environment = isolate_runtime_writers(environment, temporary)
            report_path = temporary / "pytest-report.json"
            command = _pytest_command(
                root=root,
                config_path=config_path,
                report_path=report_path,
                cache_path=temporary / "pytest-cache",
                targets=shard["files"],
                collect_only=False,
            )
            capture = runner(command, root, environment, timeout_seconds)
            try:
                plugin_report = (
                    _load_json(report_path, "pytest shard report") if report_path.exists() else None
                )
            except HarnessError as exc:
                plugin_report = None
                plugin_report_error = str(exc)
        after = fingerprint_operational_paths(root)
    finally:
        # This is a harness coordination lock, never an operational state file.
        # Failure to remove it is fail-closed: later shards refuse to start.
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass

    if capture is None:
        raise HarnessError("pytest shard runner returned no process capture")
    changes = operational_changes(before, after)
    status = "passed"
    selection_changes: dict[str, list[str]] = {"missing": [], "unexpected": []}
    if changes:
        status = "state_mutation_detected"
    elif capture.timed_out:
        status = "timed_out"
    elif plugin_report is None:
        status = "missing_pytest_report"
    else:
        try:
            _validate_plugin_report(plugin_report)
        except HarnessError as exc:
            plugin_report_error = str(exc)
            status = "invalid_pytest_report"
        else:
            actual_node_ids = sorted(str(item["node_id"]) for item in plugin_report["items"])
            expected_node_ids = sorted(str(node_id) for node_id in shard["node_ids"])
            selection_changes = {
                "missing": sorted(set(expected_node_ids) - set(actual_node_ids)),
                "unexpected": sorted(set(actual_node_ids) - set(expected_node_ids)),
            }
            if selection_changes["missing"] or selection_changes["unexpected"]:
                status = "selection_mismatch"
            elif plugin_report["collection_errors"]:
                status = "collection_error"
            elif capture.returncode != 0:
                status = "tests_failed"
            elif plugin_report.get("runtime_skip_count", 0) or plugin_report["collection_skips"]:
                status = "runtime_skips_detected"

    receipt = {
        "collection_errors": plugin_report.get("collection_errors", []) if plugin_report else [],
        "collection_skip_count": len(plugin_report.get("collection_skips", [])) if plugin_report else 0,
        "credential_keys_scrubbed": list(scrubbed),
        "expected_item_count": int(shard["item_count"]),
        "manifest_sha256": manifest_sha256,
        "operational_state_after": after,
        "operational_state_before": before,
        "operational_state_changes": changes,
        "process": _process_payload(capture),
        "pytest_report_error": plugin_report_error,
        "pytest_results": plugin_report,
        "runtime_skip_count": int(plugin_report.get("runtime_skip_count", 0)) if plugin_report else 0,
        "schema": SCHEMA,
        "selection_changes": selection_changes,
        "shard": shard_index,
        "state_mutation_detected": bool(changes),
        "status": status,
    }
    _write_new_json(receipt_path, receipt)
    return receipt


def verify_existing_manifest(
    *,
    root: Path,
    manifest_path: Path,
    plugin_inventory: Sequence[Mapping[str, str]] | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    manifest_path = root / Path(_safe_relative_path(root, manifest_path.resolve()))
    manifest = _load_json(manifest_path, "pytest shard manifest")
    verification = verify_manifest(manifest)
    inventory = list(installed_pytest_plugin_inventory() if plugin_inventory is None else plugin_inventory)
    require_pytest_socket(inventory)
    if inventory != manifest["pytest_plugin_inventory"]:
        raise HarnessError("installed pytest plugin inventory differs from the collection manifest")
    current = fingerprint_operational_paths(root)
    changes = operational_changes(manifest["operational_state_baseline"], current)
    if changes:
        raise HarnessError("operational state differs from the collection baseline")
    blocked = _prior_mutation_receipts(manifest_path, verification["manifest_sha256"])
    if blocked:
        raise HarnessError(f"manifest is blocked by a state-mutation receipt: {blocked[0]}")
    return {
        **verification,
        "collection_skip_count": int(manifest["collection"]["collection_skip_count"]),
        "operational_state_matches": True,
        "shard_count": int(manifest["shard_count"]),
    }


def _plugin_state(config: Any) -> dict[str, Any]:
    state = getattr(config, "_aureon_shard_report_state", None)
    if state is None:
        state = {
            "collection_errors": [],
            "collection_skips": [],
            "items": [],
            "runtime_phases": [],
        }
        config._aureon_shard_report_state = state
    return state


def pytest_addoption(parser: Any) -> None:
    group = parser.getgroup("aureon-state-safe-shards")
    group.addoption(
        REPORT_OPTION,
        action="store",
        default=None,
        dest="aureon_shard_report",
        help="write Aureon pytest JSON report",
    )


def pytest_configure(config: Any) -> None:
    global _ACTIVE_PYTEST_CONFIG
    _ACTIVE_PYTEST_CONFIG = config
    _plugin_state(config)


def pytest_collectreport(report: Any) -> None:
    config = _ACTIVE_PYTEST_CONFIG
    if config is None:
        return
    state = _plugin_state(config)
    if report.failed:
        state["collection_errors"].append({"node_id": str(report.nodeid), "reason": str(report.longrepr)})
    elif report.skipped:
        state["collection_skips"].append({"node_id": str(report.nodeid), "reason": str(report.longrepr)})


def pytest_collection_finish(session: Any) -> None:
    root = Path(str(session.config.rootpath)).resolve()
    state = _plugin_state(session.config)
    items: list[dict[str, str]] = []
    for item in session.items:
        item_path = Path(str(item.path)).resolve()
        try:
            source_file = item_path.relative_to(root).as_posix()
        except ValueError:
            source_file = str(item_path)
        items.append({"node_id": str(item.nodeid), "source_file": source_file})
    state["items"] = items


def pytest_runtest_logreport(report: Any) -> None:
    config = _ACTIVE_PYTEST_CONFIG
    if config is None:
        return
    state = _plugin_state(config)
    state["runtime_phases"].append(
        {
            "duration_seconds": float(report.duration),
            "node_id": str(report.nodeid),
            "outcome": str(report.outcome),
            "was_xfail": str(getattr(report, "wasxfail", "")),
            "when": str(report.when),
        }
    )


def _normalise_loaded_plugin_path(root: Path, raw_path: str) -> str:
    path = Path(raw_path)
    if not path.is_absolute():
        return raw_path.replace("\\", "/")
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return path.name


def _loaded_plugin_inventory(config: Any) -> list[dict[str, Any]]:
    root = Path(str(config.rootpath)).resolve()
    plugin_manager = config.pluginmanager
    distribution_by_plugin = {
        id(plugin): {
            "distribution": str(distribution.project_name or ""),
            "version": str(distribution.version or ""),
        }
        for plugin, distribution in plugin_manager.list_plugin_distinfo()
    }
    loaded: list[dict[str, Any]] = []
    for name, plugin in plugin_manager.list_name_plugin():
        if plugin is None:
            continue
        plugin_file = str(getattr(plugin, "__file__", "") or "")
        row: dict[str, Any] = {
            "module": str(getattr(plugin, "__name__", plugin.__class__.__module__)),
            "registered_as": _normalise_loaded_plugin_path(root, str(name)),
        }
        if plugin_file:
            row["source"] = _normalise_loaded_plugin_path(root, plugin_file)
        row.update(distribution_by_plugin.get(id(plugin), {}))
        loaded.append(row)
    return sorted(
        loaded,
        key=lambda row: (
            str(row.get("registered_as", "")),
            str(row.get("module", "")),
            str(row.get("distribution", "")),
        ),
    )


def pytest_sessionfinish(session: Any, exitstatus: int) -> None:
    config = session.config
    report_path_raw = config.getoption("aureon_shard_report")
    if not report_path_raw:
        return
    state = _plugin_state(config)
    loaded_plugins = _loaded_plugin_inventory(config)
    socket_loaded = any(
        _normalise_distribution(str(plugin.get("distribution") or "")) == "pytest-socket"
        for plugin in loaded_plugins
    )
    try:
        socket_requested = bool(config.getoption("disable_socket"))
    except (AttributeError, ValueError):
        socket_requested = False
    runtime_phases = state["runtime_phases"]
    runtime_skip_count = len({phase["node_id"] for phase in runtime_phases if phase["outcome"] == "skipped"})
    payload = {
        "collection_errors": state["collection_errors"],
        "collection_skips": state["collection_skips"],
        "items": state["items"],
        "loaded_plugins": loaded_plugins,
        "pytest_exitstatus": int(exitstatus),
        "runtime_phases": runtime_phases,
        "runtime_skip_count": runtime_skip_count,
        "schema": SCHEMA,
        "socket_blocker_loaded": socket_loaded,
        "socket_blocking_requested": socket_requested,
    }
    path = Path(str(report_path_raw))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def pytest_unconfigure(config: Any) -> None:
    global _ACTIVE_PYTEST_CONFIG
    if _ACTIVE_PYTEST_CONFIG is config:
        _ACTIVE_PYTEST_CONFIG = None


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="repository root (default: inferred from this script)",
    )
    parser.add_argument("--manifest", type=Path, required=True, help="canonical manifest JSON path")
    parser.add_argument("--pytest-config", type=Path, default=Path("pyproject.toml"))
    parser.add_argument("--shard-count", type=int, default=8)
    parser.add_argument("--timeout-seconds", type=float, default=None)
    parser.add_argument("--collection-target", action="append", default=[])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--manifest-only", action="store_true")
    mode.add_argument("--one-shard", type=int, metavar="INDEX", help="run one 1-based shard")
    mode.add_argument("--verify-existing-manifest", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = args.repo_root.resolve()
    manifest_path = args.manifest if args.manifest.is_absolute() else root / args.manifest
    config_path = args.pytest_config if args.pytest_config.is_absolute() else root / args.pytest_config
    collection_targets = tuple(args.collection_target or ["tests"])
    try:
        if args.manifest_only:
            timeout = 900.0 if args.timeout_seconds is None else args.timeout_seconds
            manifest = collect_and_write_manifest(
                root=root,
                config_path=config_path,
                manifest_path=manifest_path,
                shard_count=args.shard_count,
                collection_targets=collection_targets,
                timeout_seconds=timeout,
            )
            result = {
                "collection_skip_count": manifest["collection"]["collection_skip_count"],
                "item_count": manifest["proofs"]["collected_item_count"],
                "manifest": str(manifest_path),
                "manifest_sha256": manifest["manifest_sha256"],
                "shard_count": manifest["shard_count"],
                "status": "manifest_created",
            }
            exit_code = 0
        elif args.one_shard is not None:
            timeout = 1800.0 if args.timeout_seconds is None else args.timeout_seconds
            receipt = execute_one_shard(
                root=root,
                manifest_path=manifest_path,
                shard_index=args.one_shard,
                timeout_seconds=timeout,
            )
            result = {
                "receipt": str(_shard_receipt_path(manifest_path, args.one_shard)),
                "runtime_skip_count": receipt["runtime_skip_count"],
                "shard": args.one_shard,
                "status": receipt["status"],
            }
            exit_code = 0 if receipt["status"] == "passed" else 1
            if receipt["state_mutation_detected"]:
                exit_code = 4
        else:
            verification = verify_existing_manifest(root=root, manifest_path=manifest_path)
            result = {**verification, "manifest": str(manifest_path), "status": "verified"}
            exit_code = 0
    except HarnessError as exc:
        print(json.dumps({"error": str(exc), "status": "blocked"}, sort_keys=True), file=sys.stderr)
        return 4 if "state" in str(exc).lower() or "mutation" in str(exc).lower() else 2
    print(json.dumps(result, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
