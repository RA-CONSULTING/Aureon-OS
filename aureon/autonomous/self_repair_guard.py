"""Denylist and fail-safe switch for Aureon self-repair and self-coding writes.

Live trading is never armed by the system. Evidence gates are never loosened.
Credential files are never created or modified. Position sizing is never changed
to satisfy a test. Those checks run before a patch is applied.

Self-repair stays off unless both of these are true:

- ``AUREON_SELF_REPAIR_ENABLE=1``
- ``state/self_repair_config.json`` exists and contains ``{"enabled": true}``

``AUREON_SELF_REPAIR_KILL=1`` stops it even when both are set. A missing or
unreadable config stops it too.
"""

from __future__ import annotations

import ast
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

ENABLE_ENV = "AUREON_SELF_REPAIR_ENABLE"
KILL_ENV = "AUREON_SELF_REPAIR_KILL"
CONFIG_RELATIVE = Path("state/self_repair_config.json")
LOG_RELATIVE = Path("state/self_repair_review_log.jsonl")

_LIVE_ARM = re.compile(
    r"AUREON_LIVE_TRADING"
    r"|AUREON_FUSION_ARM_LIVE"
    r"|CONFIRM_LIVE_TRADING"
    r"|LIVE_TRADING"
    r"|REAL_MONEY"
    r"|real_money"
    r"|BINANCE_TESTNET\s*[:=]\s*['\"]?false\b"
    r"|PAPER_MODE\s*[:=]\s*['\"]?false\b"
    r"|AUREON_DISABLE_REAL_ORDERS\s*[:=]\s*['\"]?0\b"
    r"|testnet\s*[:=]\s*['\"]?false\b"
    r"|live_trading\s*[:=]\s*['\"]?(?:1|true|yes)\b",
    re.IGNORECASE,
)
_GATE = re.compile(
    r"\b(?:HOLD|RELEASE)\b"
    r"|\b(?:may_act|action_eligible|economic_mutation|evidence_gate)\b"
    r"|\bgate\s*[:=]\s*['\"](?:HOLD|RELEASE)['\"]"
)
_POSITION_NAME = re.compile(
    r"^(?:position_qty|position_size|position_sizing|order_size|stake_size|qty_for_price)$",
    re.IGNORECASE,
)
_POSITION_TEXT = re.compile(
    r"\b(?:position_qty|position_size|position_sizing|order_size|stake_size|qty_for_price)\b",
    re.IGNORECASE,
)
_EXAMPLE_ENV = ("example", "template", "sample")


class SelfRepairBlocked(RuntimeError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def kill_switch_engaged() -> bool:
    return os.environ.get(KILL_ENV, "").strip().lower() in {"1", "true", "yes", "on"}


def explicitly_enabled() -> bool:
    return os.environ.get(ENABLE_ENV, "").strip().lower() in {"1", "true", "yes", "on"}


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def review_log_path(repo_root: Path) -> Path:
    return repo_root / LOG_RELATIVE


def config_path(repo_root: Path) -> Path:
    return repo_root / CONFIG_RELATIVE


def append_review(repo_root: Path, event: str, **fields: object) -> None:
    path = review_log_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    record: dict[str, object] = {"ts": _utc(), "event": event}
    for key, value in fields.items():
        if str(key).lower() in {"secret", "token", "authorization", "api_key", "api_secret", "content", "patch", "patch_text"}:
            continue
        record[key] = value
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True, default=str) + "\n")


def contained(repo_root: Path, file_path: str) -> Path:
    root = repo_root.resolve()
    candidate = Path(file_path)
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()
    if resolved != root and root not in resolved.parents:
        raise SelfRepairBlocked("path_outside_repository")
    return resolved


def is_protected_path(file_path: str) -> bool:
    """True for .env files and credential material. Examples and templates are not included."""

    raw = str(file_path or "").replace("\\", "/").strip()
    if not raw:
        return False
    path = Path(raw)
    name = path.name.lower()
    if name == ".env" or (name.startswith(".env.") and not any(token in name for token in _EXAMPLE_ENV)):
        return True
    if name in {
        "credentials",
        "credentials.json",
        "secrets.json",
        "id_rsa",
        "id_rsa.pub",
        "service-account.json",
        "serviceaccount.json",
    }:
        return True
    if path.suffix.lower() in {".pem", ".key", ".p12", ".pfx", ".keystore"}:
        return True
    if any(token in name for token in ("credential", "private_key", "id_rsa", "keystore", "api_secret")):
        return True
    if "secret" in name and "self_repair" not in name:
        return True
    parts = [part.lower() for part in path.parts]
    return any(part in {"secrets", "credentials", "private_keys"} for part in parts)


def _position_sources(text: str) -> dict[str, str]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return {}
    lines = text.splitlines()
    found: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and _POSITION_NAME.match(node.name):
            end = getattr(node, "end_lineno", None) or node.lineno
            found[node.name] = "\n".join(lines[node.lineno - 1 : end])
    return found


def _has_gate(text: str) -> bool:
    return _GATE.search(text) is not None


def block_reason_for_write(file_path: str, new_content: str, previous: str | None) -> str | None:
    """Return a refusal reason, or None when the write is outside the denylist."""

    if is_protected_path(file_path):
        return "credential_path"
    if _LIVE_ARM.search(new_content):
        return "live_trading_flag"
    previous_text = previous or ""
    if (_has_gate(previous_text) or _has_gate(new_content)) and previous_text != new_content:
        return "evidence_gate"
    if _position_sources(previous_text) != _position_sources(new_content):
        return "position_sizing"
    if previous_text != new_content and not _position_sources(previous_text) and not _position_sources(new_content):
        if _POSITION_TEXT.search(previous_text) or _POSITION_TEXT.search(new_content):
            return "position_sizing"
    return None


def paths_from_patch(patch_text: str) -> list[str]:
    found: list[str] = []
    for line in str(patch_text or "").splitlines():
        if line.startswith("diff --git "):
            parts = line.split()
            if len(parts) >= 4:
                raw = parts[3]
                found.append(raw[2:] if raw.startswith("b/") else raw)
        elif line.startswith("+++ "):
            raw = line[4:].split("\t", 1)[0].strip()
            if raw and raw != "/dev/null":
                found.append(raw[2:] if raw.startswith("b/") else raw)
    return list(dict.fromkeys(found))


def block_reason_for_patch(root: Path, patch_text: str, target_paths: list[str] | tuple[str, ...] = ()) -> str | None:
    """Refuse a diff before git apply. Protected paths are never covered by auto-approve."""

    added = [
        line[1:]
        for line in str(patch_text or "").splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]
    removed = [
        line[1:]
        for line in str(patch_text or "").splitlines()
        if line.startswith("-") and not line.startswith("---")
    ]
    added_text = "\n".join(added)
    removed_text = "\n".join(removed)
    if _LIVE_ARM.search(added_text):
        return "live_trading_flag"
    if _has_gate(added_text) or _has_gate(removed_text):
        return "evidence_gate"
    if _POSITION_TEXT.search(added_text) or _POSITION_TEXT.search(removed_text):
        return "position_sizing"
    paths = list(dict.fromkeys([*target_paths, *paths_from_patch(patch_text)]))
    repo_root = Path(root).resolve()
    for raw in paths:
        if is_protected_path(raw):
            return "credential_path"
        candidate = Path(raw)
        if candidate.is_absolute():
            return "credential_path" if is_protected_path(candidate.name) else "path_outside_repository"
        full = repo_root / candidate
        if not full.is_file():
            continue
        try:
            previous = full.read_text(encoding="utf-8")
        except OSError:
            return "credential_path"
        if _LIVE_ARM.search(previous):
            return "live_trading_flag"
        if _has_gate(previous):
            return "evidence_gate"
        if _position_sources(previous) or _POSITION_TEXT.search(previous):
            return "position_sizing"
    return None


def block_reason_for_proposal(*parts: object) -> str | None:
    """Auto-approve must not cover a proposal that names a protected path or pattern."""

    texts: list[str] = []
    paths: list[str] = []
    for part in parts:
        if isinstance(part, (list, tuple)):
            for item in part:
                raw = str(item or "")
                paths.append(raw)
                texts.append(raw)
        else:
            texts.append(str(part or ""))
    blob = "\n".join(texts)
    for path in paths:
        if is_protected_path(path):
            return "credential_path"
    if _LIVE_ARM.search(blob):
        return "live_trading_flag"
    if _has_gate(blob):
        return "evidence_gate"
    if _POSITION_TEXT.search(blob):
        return "position_sizing"
    return None


def require_self_repair_enabled(repo_root: Path) -> None:
    """Raise unless the operator explicitly enabled repair and the kill switch is off."""

    if kill_switch_engaged():
        raise SelfRepairBlocked("kill_switch")
    path = config_path(repo_root)
    if not path.is_file():
        raise SelfRepairBlocked("missing_config")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SelfRepairBlocked("missing_config") from exc
    if not isinstance(payload, dict) or payload.get("enabled") is not True or not explicitly_enabled():
        raise SelfRepairBlocked("self_repair_disabled")


def inspect_write(repo_root: Path, file_path: str, new_content: str, previous: str | None) -> Path:
    """Raise SelfRepairBlocked before a protected write. Return the resolved path otherwise."""

    if kill_switch_engaged():
        raise SelfRepairBlocked("kill_switch")
    resolved = contained(repo_root, file_path)
    relative = resolved.name if resolved == repo_root.resolve() else resolved.relative_to(repo_root.resolve()).as_posix()
    reason = block_reason_for_write(relative, new_content, previous)
    if reason:
        raise SelfRepairBlocked(reason)
    return resolved


def inspect_delete(repo_root: Path, file_path: str, previous: str | None) -> Path:
    if kill_switch_engaged():
        raise SelfRepairBlocked("kill_switch")
    resolved = contained(repo_root, file_path)
    relative = resolved.relative_to(repo_root.resolve()).as_posix()
    if is_protected_path(relative):
        raise SelfRepairBlocked("credential_path")
    text = previous or ""
    if _has_gate(text):
        raise SelfRepairBlocked("evidence_gate")
    if _position_sources(text) or _POSITION_TEXT.search(text):
        raise SelfRepairBlocked("position_sizing")
    if _LIVE_ARM.search(text):
        raise SelfRepairBlocked("live_trading_flag")
    return resolved


def inspect_execution(code: str) -> None:
    if kill_switch_engaged():
        raise SelfRepairBlocked("kill_switch")
    reason = block_reason_for_write("snippet.py", code, "")
    if reason:
        raise SelfRepairBlocked(reason)
