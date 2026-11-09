"""Denylist and fail-safe switch for Aureon self-repair and self-coding writes.

The public default is full mode. Live flags, HOLD/RELEASE, ``may_act``, and
position sizing are editable. ``AUREON_AUTONOMY_MODE=guarded`` puts that
denylist back. Credential files are refused in both modes. See AUTONOMY.md.

Self-repair stays off unless both of these are true:

- ``AUREON_SELF_REPAIR_ENABLE=1``
- ``state/self_repair_config.json`` exists and contains ``{"enabled": true}``

``AUREON_SELF_REPAIR_KILL`` and ``state/SELF_REPAIR_KILL`` do not stop it.
A missing or unreadable config still does.
"""

from __future__ import annotations

import ast
import difflib
import json
import os
import re
import subprocess
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
_CREDENTIAL_MATERIAL = re.compile(
    r"(?i)\b(?:api[_-]?secret|api[_-]?key|aws_secret_access_key|private_key|access_token|refresh_token)\b"
    r"\s*[:=]\s*['\"]?[A-Za-z0-9_\-+/=]{6,}"
)
_HARDCODED_HOST = re.compile(
    r"(?i)(?:\b(?:\d{1,3}\.){3}\d{1,3}\b|\blocalhost\b|https?://\S+)"
)


class SelfRepairBlocked(RuntimeError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


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
    line = json.dumps(record, sort_keys=True, default=str)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    from aureon.autonomous.autonomy_mode import audit_event

    omitted = {"secret", "token", "authorization", "api_key", "api_secret", "content", "patch", "patch_text"}
    audit_event(
        event,
        repo_root,
        **{key: value for key, value in fields.items() if str(key).lower() not in omitted},
    )


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


def _guardrails_open(repo_root: Path | None) -> bool:
    from aureon.autonomous.autonomy_mode import guardrails_open

    return guardrails_open(repo_root)


def block_reason_for_write(
    file_path: str,
    new_content: str,
    previous: str | None,
    repo_root: Path | None = None,
) -> str | None:
    """Return a refusal reason, or None when the write is outside the denylist.

    Credential paths and credential assignments are refused in both modes.
    Live flags, evidence gates, and position sizing are refused in guarded
    mode and allowed when the owner has opened full autonomy.
    """

    if is_protected_path(file_path):
        return "credential_path"
    if _CREDENTIAL_MATERIAL.search(new_content or ""):
        return "credential_material"
    if _guardrails_open(repo_root):
        return None
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
    paths = list(dict.fromkeys([*target_paths, *paths_from_patch(patch_text)]))
    repo_root = Path(root).resolve()
    if _CREDENTIAL_MATERIAL.search(added_text):
        return "credential_material"
    if not _guardrails_open(repo_root):
        if _LIVE_ARM.search(added_text):
            return "live_trading_flag"
        if _has_gate(added_text) or _has_gate(removed_text):
            return "evidence_gate"
        if _POSITION_TEXT.search(added_text) or _POSITION_TEXT.search(removed_text):
            return "position_sizing"
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
        if _guardrails_open(repo_root):
            continue
        if _LIVE_ARM.search(previous):
            return "live_trading_flag"
        if _has_gate(previous):
            return "evidence_gate"
        if _position_sources(previous) or _POSITION_TEXT.search(previous):
            return "position_sizing"
    return None


def block_reason_for_proposal(*parts: object, repo_root: Path | None = None) -> str | None:
    """Auto-approve must not cover a credential, and in guarded mode not a protected pattern.

    Full mode lets auto-approve cover live flags, evidence gates, and position
    sizing. Credential paths and credential assignments stay on human review.
    """

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
    if _CREDENTIAL_MATERIAL.search(blob):
        return "credential_material"
    if _guardrails_open(repo_root):
        return None
    if _LIVE_ARM.search(blob):
        return "live_trading_flag"
    if _has_gate(blob):
        return "evidence_gate"
    if _POSITION_TEXT.search(blob):
        return "position_sizing"
    return None


def require_self_repair_enabled(repo_root: Path) -> None:
    """Raise unless the operator explicitly enabled repair."""

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

    resolved = contained(repo_root, file_path)
    relative = resolved.name if resolved == repo_root.resolve() else resolved.relative_to(repo_root.resolve()).as_posix()
    reason = block_reason_for_write(relative, new_content, previous, repo_root)
    if reason:
        raise SelfRepairBlocked(reason)
    return resolved


def inspect_delete(repo_root: Path, file_path: str, previous: str | None) -> Path:
    resolved = contained(repo_root, file_path)
    relative = resolved.relative_to(repo_root.resolve()).as_posix()
    if is_protected_path(relative):
        raise SelfRepairBlocked("credential_path")
    text = previous or ""
    if not _guardrails_open(repo_root):
        if _has_gate(text):
            raise SelfRepairBlocked("evidence_gate")
        if _position_sources(text) or _POSITION_TEXT.search(text):
            raise SelfRepairBlocked("position_sizing")
        if _LIVE_ARM.search(text):
            raise SelfRepairBlocked("live_trading_flag")
    return resolved


def inspect_execution(code: str, repo_root: Path | None = None) -> None:
    reason = block_reason_for_write("snippet.py", code, "", repo_root)
    if reason:
        raise SelfRepairBlocked(reason)


def _git_text(root: Path, args: list[str]) -> str | None:
    try:
        done = subprocess.run(args, cwd=root, capture_output=True, text=True, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    if done.returncode != 0:
        return None
    return done.stdout


def added_diff_lines(before: str, after: str) -> list[str]:
    """Lines a repair diff would add. The file itself is not changed."""

    diff = difflib.unified_diff(
        before.splitlines(),
        after.splitlines(),
        lineterm="",
    )
    return [line[1:] for line in diff if line.startswith("+") and not line.startswith("+++")]


def repair_diff_text(path: str, before: str, after: str) -> str:
    diff = difflib.unified_diff(
        before.splitlines(),
        after.splitlines(),
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
        lineterm="",
    )
    lines = list(diff)
    if not lines:
        return ""
    return "\n".join(lines) + "\n"


def lines_removed_by_later_commit(root: Path, relative: str) -> set[str]:
    """Lines present in an older blob of ``relative`` and absent from HEAD.

    A later commit removed them. Blank lines are ignored.
    """

    head = _git_text(root, ["git", "show", f"HEAD:{relative}"])
    head_lines = set(head.splitlines()) if head is not None else set()
    log = _git_text(root, ["git", "log", "--format=%H", "--", relative])
    if not log:
        return set()
    historical: set[str] = set()
    for sha in log.splitlines():
        sha = sha.strip()
        if not sha:
            continue
        blob = _git_text(root, ["git", "show", f"{sha}:{relative}"])
        if blob is None:
            continue
        historical.update(blob.splitlines())
    return {line for line in historical - head_lines if line.strip()}


def block_reason_for_repair_diff(root: Path, relative: str, before: str, after: str) -> str | None:
    """Refuse a repair diff that puts history or a hard-coded address back.

    ``reintroduced_removed_line`` means an added line was deleted by a later
    commit and is not on HEAD. ``hardcoded_host`` means an added line carries
    a literal host or IP. Neither check writes the tree.
    """

    added = added_diff_lines(before, after)
    if not added:
        return None
    removed = lines_removed_by_later_commit(root, relative)
    if any(line in removed for line in added):
        return "reintroduced_removed_line"
    if any(_HARDCODED_HOST.search(line) for line in added):
        return "hardcoded_host"
    return None


def propose_repair_diff(root: Path, relative: str, after: str) -> dict[str, object]:
    """Propose a unified diff. Never writes ``relative`` or any other source file.

    A refused diff is logged as a failed repair. The working tree is left as it was.
    """

    repo = Path(root)
    rel = str(relative or "").replace("\\", "/").lstrip("/")
    proposal: dict[str, object] = {
        "path": rel,
        "applied": False,
        "wrote_tree": False,
        "diff": "",
        "status": "repair_failed",
        "reason": "",
    }
    try:
        contained(repo, rel)
    except SelfRepairBlocked as exc:
        proposal["reason"] = exc.reason
        append_review(repo, "repair_failed", reason=exc.reason, path=rel, applied=False)
        return proposal
    target = repo / rel
    try:
        before = target.read_text(encoding="utf-8") if target.is_file() else ""
    except OSError:
        proposal["reason"] = "credential_path"
        append_review(repo, "repair_failed", reason="credential_path", path=rel, applied=False)
        return proposal
    reason = block_reason_for_repair_diff(repo, rel, before, after)
    proposal["diff"] = repair_diff_text(rel, before, after)
    if reason:
        proposal["reason"] = reason
        proposal["status"] = "repair_failed"
        append_review(repo, "repair_failed", reason=reason, path=rel, applied=False)
        return proposal
    proposal["status"] = "repair_proposed"
    proposal["reason"] = "proposed_only"
    return proposal
