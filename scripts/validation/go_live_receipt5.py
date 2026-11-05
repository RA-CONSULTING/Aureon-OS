#!/usr/bin/env python3
"""Stage 10 go-live receipt 5: authenticated deployment and provider read-back.

The runner writes reports/measured/go_live_receipt5_deployment.json and the
matching markdown. A receipt is measured only after this process deploys a
resource and reads that resource back from the provider API. A machine with
no Hugging Face token and no usable Google Cloud credential gets a HOLD skip.
The skip names the missing auth. It does not invent a provider payload.

A Hugging Face token does not upload by itself. The upload runs only when
AUREON_RECEIPT5_ALLOW_HF_UPLOAD=1 as well. It uploads huggingface/hnc-field
and reads the Space runtime from huggingface.co. Hardware stays cpu-basic.
A new Space stays private unless AUREON_RECEIPT5_HF_PUBLIC=1. An existing
Space is read before upload. create_repo(exist_ok=True) does not change
privacy, hardware, or SDK, so those options are not the check. The upload
is refused when that Space is not private, the hardware is not cpu-basic,
or the SDK or other settings do not match. Cloud Run is not created unless
AUREON_RECEIPT5_ALLOW_CLOUD_RUN_DEPLOY=1 and a service, project, region, and
image are set. That flag is a spend guard. This script does not place an
order, open a tunnel, or move the public pin.

go_live_clear stays false. The orange badge is not this stage.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.parse
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "aureon.go-live.deployment-receipt.v1"
SCHEMA_PATH = Path("scripts/validation/go_live_receipt5.schema.json")
JSON_PATH = Path("reports/measured/go_live_receipt5_deployment.json")
MARKDOWN_PATH = Path("reports/measured/go_live_receipt5_deployment.md")
PIN = "bb04503119681adcf832f3c3e9b0cbf09fc7a938"
STARTED_FROM = "29fab7f21fc93da40224566dd8f34faacb3d74d4"
RECEIPT3_PIN = "34864ff0547d2cff03e707414743a3b0cc8770b5"
PIN_SOURCE = (
    "mcp/aureon_public/guard_loader.py PINNED_COMMIT at started_from; "
    "published require-pin. evidence/output/hnc_head_anchor.json public_require_pin "
    "stays the receipt 3 value and is not rewritten. This receipt does not move the pin"
)
SCAFFOLD = Path("huggingface/hnc-field")
HF_API = "https://huggingface.co/api"
GCP_API = "https://run.googleapis.com"
RUNNER = "scripts/validation/go_live_receipt5.py"
SPEND_GUARD = (
    "A Hugging Face token does not upload. Upload also requires "
    "AUREON_RECEIPT5_ALLOW_HF_UPLOAD=1. Hardware must stay cpu-basic. "
    "A new Space stays private unless AUREON_RECEIPT5_HF_PUBLIC=1. "
    "An existing Space is refused unless it is already private, cpu-basic, and gradio. "
    "create_repo exist_ok does not change those settings and is not the check. "
    "Cloud Run is not created unless AUREON_RECEIPT5_ALLOW_CLOUD_RUN_DEPLOY=1 "
    "and AUREON_RECEIPT5_CLOUD_RUN_SERVICE, AUREON_RECEIPT5_GCP_PROJECT, "
    "AUREON_RECEIPT5_CLOUD_RUN_REGION, and AUREON_RECEIPT5_CLOUD_RUN_IMAGE are set."
)
MEASUREMENT_NOTE = (
    "git_head_at_measurement is HEAD when this command ran. "
    "The commit that adds this file is not a second measurement. "
    "provider_readback_digest is sha256 of the redacted provider payload. "
    "A null digest means this run has no provider payload. "
    "The UTC stamps are this machine's clock, not receipt 3. "
    "The pin value was read at started_from. This command does not move it. "
    "Receipts 1-4 were not re-run."
)
TITLE = "authenticated deployment receipt and provider-side read-back"
BADGE_FLIP = "stage 11 / separate PR"

HF_TOKEN_ENV = ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN")
HF_UPLOAD_FLAG = "AUREON_RECEIPT5_ALLOW_HF_UPLOAD"
HF_TOKEN_FILES = (
    ".cache/huggingface/token",
    ".huggingface/token",
    ".config/huggingface/token",
)
GCP_ADC_REL = ".config/gcloud/application_default_credentials.json"
GCP_DB_REL = ".config/gcloud/credentials.db"

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}
SECRET_KEY = re.compile(
    r"(token|secret|password|authorization|credential|private[-_]?key|access[-_]?token|api[-_]?key)",
    re.IGNORECASE,
)
SECRET_TEXT = ("BEGIN PRIVATE", "BEGIN OPENSSH", "-----BEGIN", "Bearer ", "ya29.", "AKIA")
SAFE_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9-]{0,62}$")
SAFE_REGION = re.compile(r"^[a-z]+-[a-z0-9]+[0-9]$")
SAFE_PROJECT = re.compile(r"^[a-z][a-z0-9-]{4,28}[a-z0-9]$")
SAFE_IMAGE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$")
SECRET_FILENAMES = {
    ".env",
    ".env.local",
    "token",
    "credentials.json",
    "service-account.json",
    "id_rsa",
    "id_ed25519",
}
RUNTIME_KEYS = (
    "stage",
    "hardware",
    "requested_hardware",
    "requestedHardware",
    "gcTimeout",
    "errorMessage",
    "replicas",
)
REPO_KEYS = ("id", "sha", "lastModified", "private", "createdAt", "gated", "disabled")

Which = Callable[[str], str | None]
GcloudLister = Callable[[], bool | None]
Runner = Callable[..., subprocess.CompletedProcess[str]]


class DeployError(Exception):
    """A deploy stopped before a complete provider read-back. The message is safe to store."""

    def __init__(
        self,
        blocker: str,
        *,
        attempted: bool = False,
        api_called: bool = False,
        performed: bool = False,
    ) -> None:
        super().__init__(blocker)
        self.blocker = blocker
        self.attempted = attempted
        self.api_called = api_called
        self.performed = performed

    def with_progress(self, *, attempted: bool, api_called: bool, performed: bool) -> DeployError:
        """Keep a later failure from clearing a side effect that already happened."""

        self.performed = self.performed or performed
        self.attempted = self.attempted or attempted or self.performed
        self.api_called = self.api_called or api_called or self.attempted or self.performed
        return self


def canonical(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode(
            "utf-8"
        )
        + b"\n"
    )


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest(value: object) -> str:
    return sha256(canonical(value))


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def file_state(path: Path, *, read_text: bool = True) -> str:
    """Return absent, empty, present, or unreadable. Never return file bytes."""

    try:
        if not path.exists():
            return "absent"
        if not path.is_file() or path.is_symlink():
            return "unreadable"
        if not read_text:
            return "present" if path.stat().st_size > 0 else "empty"
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "unreadable"
    return "present" if text.strip() else "empty"


def _label(kind: str, name: str) -> str:
    return f"{kind}:{name}"


def default_gcloud_lister(which: Which) -> bool | None:
    binary = which("gcloud")
    if not binary:
        return None
    try:
        proc = subprocess.run(
            [binary, "auth", "list", "--format=json"],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    if proc.returncode != 0:
        return False
    try:
        rows = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError:
        return False
    if not isinstance(rows, list):
        return False
    return any(isinstance(row, dict) and row.get("status") == "ACTIVE" for row in rows)


def probe_auth(
    *,
    environ: Mapping[str, str] | None = None,
    home: Path | None = None,
    which: Which | None = None,
    gcloud_lister: GcloudLister | None = None,
) -> dict[str, Any]:
    """Name which auth sources exist. Do not return secret values."""

    env = os.environ if environ is None else environ
    root = Path.home() if home is None else home
    find = shutil.which if which is None else which
    active = default_gcloud_lister(find) if gcloud_lister is None else gcloud_lister()

    missing: list[str] = []
    unused: list[str] = []
    unreadable: list[str] = []
    hf_method: str | None = None

    for name in HF_TOKEN_ENV:
        label = _label("env", name)
        if env.get(name, "").strip():
            if hf_method is None:
                hf_method = label
            else:
                unused.append(label)
        else:
            missing.append(label)

    for rel in HF_TOKEN_FILES:
        label = _label("file", f"~/{rel}")
        state = file_state(root / rel)
        if state == "present":
            if hf_method is None:
                hf_method = label
            else:
                unused.append(label)
        elif state == "unreadable":
            unreadable.append(label)
        else:
            missing.append(label)

    gcloud_bin = find("gcloud")
    gcloud_label = "command:gcloud"
    if gcloud_bin:
        if active is True:
            unused.append("gcloud:active-account")
        else:
            unused.append(gcloud_label)
    else:
        missing.append(gcloud_label)

    adc_env = env.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    adc_label = "env:GOOGLE_APPLICATION_CREDENTIALS"
    if adc_env:
        state = file_state(Path(adc_env), read_text=False)
        if state == "present":
            unused.append(adc_label)
        elif state == "unreadable":
            unreadable.append(adc_label)
        else:
            missing.append(adc_label)
    else:
        missing.append(adc_label)

    for rel, label in (
        (GCP_ADC_REL, _label("file", f"~/{GCP_ADC_REL}")),
        (GCP_DB_REL, _label("file", f"~/{GCP_DB_REL}")),
    ):
        state = file_state(root / rel, read_text=False)
        if state == "present":
            unused.append(label)
        elif state == "unreadable":
            unreadable.append(label)
        else:
            missing.append(label)

    flag = env.get("AUREON_RECEIPT5_ALLOW_CLOUD_RUN_DEPLOY", "") == "1"
    opt_in = False
    if flag:
        try:
            opt_in = cloud_run_spec(env) is not None
        except DeployError:
            opt_in = False
    hf_upload_flag = env.get(HF_UPLOAD_FLAG, "") == "1"
    if hf_method is not None and not hf_upload_flag:
        unused.insert(0, hf_method)
    return {
        "hf_auth_method": hf_method,
        "hf_token_present": hf_method is not None,
        "hf_upload_flag": hf_upload_flag,
        "hf_upload_opt_in": bool(hf_upload_flag and hf_method),
        "gcloud_on_path": bool(gcloud_bin),
        "gcloud_active_account": active is True,
        "gcp_credential_present": any(
            item.startswith("env:GOOGLE_") or item.startswith("file:~/.config/gcloud/") or item == "gcloud:active-account"
            for item in unused
        ),
        "missing_provider_auth": missing,
        "unused_provider_auth": unused,
        "unreadable_provider_auth": unreadable,
        "cloud_run_opt_in": opt_in,
        "cloud_run_flag": flag,
    }


def cloud_run_spec(env: Mapping[str, str]) -> dict[str, str] | None:
    if env.get("AUREON_RECEIPT5_ALLOW_CLOUD_RUN_DEPLOY", "") != "1":
        return None
    service = env.get("AUREON_RECEIPT5_CLOUD_RUN_SERVICE", "").strip()
    project = env.get("AUREON_RECEIPT5_GCP_PROJECT", "").strip()
    region = env.get("AUREON_RECEIPT5_CLOUD_RUN_REGION", "").strip()
    image = env.get("AUREON_RECEIPT5_CLOUD_RUN_IMAGE", "").strip()
    if not (SAFE_NAME.fullmatch(service) and SAFE_PROJECT.fullmatch(project) and SAFE_REGION.fullmatch(region)):
        raise DeployError(
            "AUREON_RECEIPT5_ALLOW_CLOUD_RUN_DEPLOY=1 but the Cloud Run service, project, or region "
            "is missing or refused by the name check. No provider API was called."
        )
    if not SAFE_IMAGE.fullmatch(image) or ":" not in image or image.startswith(":"):
        raise DeployError(
            "AUREON_RECEIPT5_CLOUD_RUN_IMAGE must be an explicit image:tag with no shell characters. "
            "No provider API was called."
        )
    return {"service": service, "project": project, "region": region, "image": image}


def _host(url: str) -> str:
    return (urllib.parse.urlparse(url).hostname or "").lower()


def provider_host_ok(url: str) -> bool:
    host = _host(url)
    local = not host or host in LOCAL_HOSTS or host.endswith(".local") or host.endswith(".localhost")
    return not local


def redact(value: Any, secrets: tuple[str, ...]) -> Any:
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            name = str(key)
            if SECRET_KEY.search(name):
                cleaned[name] = "[redacted]"
            else:
                cleaned[name] = redact(item, secrets)
        return cleaned
    if isinstance(value, list):
        return [redact(item, secrets) for item in value]
    if isinstance(value, str):
        text = value
        for secret in secrets:
            if secret and secret in text:
                text = text.replace(secret, "[redacted]")
        return text
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return redact(str(value), secrets)


def assert_no_secrets(value: object, secrets: tuple[str, ...]) -> None:
    text = json.dumps(value, ensure_ascii=True, default=str)
    for marker in SECRET_TEXT:
        if marker in text:
            raise DeployError("refusing to record a provider payload that still contains secret material")
    for secret in secrets:
        if secret and secret in text:
            raise DeployError("refusing to record a secret value in the receipt")


def scaffold_tree(root: Path) -> dict[str, Any]:
    folder = root / SCAFFOLD
    if not folder.is_dir():
        raise DeployError(f"scaffold {SCAFFOLD.as_posix()} is not a directory")
    files: list[dict[str, Any]] = []
    for path in sorted(folder.rglob("*")):
        rel = path.relative_to(folder).as_posix()
        if path.is_symlink():
            raise DeployError(f"scaffold contains a symlink: {rel}")
        if not path.is_file():
            continue
        if path.name in SECRET_FILENAMES or path.suffix in {".pem", ".key", ".p12"}:
            raise DeployError(f"scaffold contains a secret-shaped filename: {rel}")
        data = path.read_bytes()
        files.append({"path": rel, "sha256": sha256(data), "size": len(data)})
    return {
        "path": SCAFFOLD.as_posix(),
        "file_count": len(files),
        "files": files,
        "sha256": digest(files),
        "source": "local-worktree",
    }


def _base(
    *,
    meta: dict[str, Any],
    probe: dict[str, Any],
    scaffold: dict[str, Any],
    outcome: str,
    blocker: str | None,
    auth_method: str | None,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "stage": 10,
        "receipt": 5,
        "title": TITLE,
        "decision": "HOLD",
        "outcome": outcome,
        "receipt_5_complete": False,
        "go_live_clear": False,
        "system_alive_claimed": False,
        "release_boundary": "HOLD",
        "orange_badge": "unchanged",
        "badge_flip": BADGE_FLIP,
        "pin": PIN,
        "pin_changed": False,
        "pin_measured_at": STARTED_FROM,
        "pin_source": PIN_SOURCE,
        "started_from": STARTED_FROM,
        "git_head_at_measurement": meta["git_head"],
        "worktree_dirty_at_measurement": meta["dirty"],
        "provider": None,
        "auth_method": auth_method,
        "missing_provider_auth": list(probe["missing_provider_auth"]),
        "unused_provider_auth": list(probe["unused_provider_auth"]),
        "blocker": blocker,
        "deploy_attempted": False,
        "deploy_performed": False,
        "deploy_timestamp": None,
        "deploy_timestamp_source": None,
        "resource_id": None,
        "provider_api": None,
        "provider_api_called": False,
        "provider_status": None,
        "provider_readback_digest": None,
        "provider_readback": None,
        "healthy": False,
        "localhost_substituted_for_provider": False,
        "live_trading": False,
        "orders_placed": False,
        "market_data_fetched": False,
        "tunnels_opened": False,
        "secrets_recorded": False,
        "mcp_stages_3_and_4_opened": False,
        "installers_switched_on": False,
        "receipts_1_to_4_reverified": False,
        "scaffold": scaffold,
        "spend_guard": SPEND_GUARD,
        "auth_probe": {
            "hf_token_present": probe["hf_token_present"],
            "hf_auth_method": probe["hf_auth_method"],
            "hf_upload_opt_in": probe["hf_upload_opt_in"],
            "gcloud_on_path": probe["gcloud_on_path"],
            "gcloud_active_account": probe["gcloud_active_account"],
            "gcp_credential_present": probe["gcp_credential_present"],
            "cloud_run_deploy_opt_in": probe["cloud_run_opt_in"],
            "unreadable_provider_auth": list(probe["unreadable_provider_auth"]),
        },
        "runner": RUNNER,
        "measured_at": meta["measured_at"],
        "measurement_note": MEASUREMENT_NOTE,
    }


def skip_blocker(probe: dict[str, Any]) -> str:
    missing = ", ".join(probe["missing_provider_auth"]) or "none"
    unused = ", ".join(probe["unused_provider_auth"]) or "none"
    parts = [
        "Authenticated deploy was not attempted.",
        f"Missing provider auth: {missing}.",
        f"Present and unused: {unused}.",
        "No provider API was called. No provider read-back was fabricated.",
    ]
    if probe["hf_token_present"] and not probe["hf_upload_flag"]:
        parts.insert(
            3,
            "A Hugging Face token is present. Upload stays off without "
            f"{HF_UPLOAD_FLAG}=1. Token presence is not an upload.",
        )
    elif probe["cloud_run_flag"] is False and probe["gcp_credential_present"]:
        parts.insert(
            3,
            "Google credential material is present. Cloud Run stays off without "
            "AUREON_RECEIPT5_ALLOW_CLOUD_RUN_DEPLOY=1 and a service, project, region, and image.",
        )
    elif probe["hf_token_present"] is False and probe["gcloud_on_path"] and not probe["gcloud_active_account"]:
        parts.insert(3, "gcloud is on PATH and listed no ACTIVE account.")
    return " ".join(parts)


def measurement_meta(root: Path, now: Callable[[], str] | None = None) -> dict[str, Any]:
    clock = utc_now if now is None else now
    return {
        "git_head": _git(root, "rev-parse", "HEAD"),
        "dirty": bool(_git(root, "status", "--porcelain")),
        "measured_at": clock(),
    }


def _read_token(env: Mapping[str, str], home: Path, method: str) -> str:
    if method.startswith("env:"):
        return env[method.removeprefix("env:")].strip()
    rel = method.removeprefix("file:~/")
    return (home / rel).read_text(encoding="utf-8").strip()


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if hasattr(value, "__dict__"):
        return {key: item for key, item in vars(value).items() if not key.startswith("_")}
    return {}


def _pick(payload: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    return {key: payload[key] for key in keys if key in payload}


def _hf_hardware(env: Mapping[str, str]) -> str:
    hardware = env.get("AUREON_RECEIPT5_HF_HARDWARE", "cpu-basic").strip() or "cpu-basic"
    if hardware != "cpu-basic":
        raise DeployError(
            f"refusing Hugging Face hardware {hardware!r}. Receipt 5 allows cpu-basic only (spend guard). "
            "No provider API was called."
        )
    return hardware


def _hf_repo(env: Mapping[str, str], username: str) -> str:
    org = env.get("HF_ORG", "").strip() or env.get("AUREON_RECEIPT5_HF_ORG", "").strip() or username
    name = env.get("AUREON_RECEIPT5_HF_REPO", "aureon-os-receipt5-hnc-field").strip()
    if not org or not SAFE_NAME.fullmatch(name) or "/" in org or " " in org:
        raise DeployError("Hugging Face repo id is missing or refused by the name check. No upload was started.")
    return f"{org}/{name}"


def _sdk_name(info: Mapping[str, Any]) -> str | None:
    for key in ("sdk", "space_sdk"):
        value = info.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().lower()
    card = info.get("card_data")
    if card is None:
        card = info.get("cardData")
    if card is None:
        return None
    card_dict = card if isinstance(card, dict) else _as_dict(card)
    for key in ("sdk", "space_sdk"):
        value = card_dict.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().lower()
    return None


def _hardware_fields(runtime: Mapping[str, Any]) -> tuple[str | None, str | None]:
    current: str | None = None
    requested: str | None = None
    raw = runtime.get("hardware")
    if isinstance(raw, str) and raw.strip():
        current = raw.strip()
    elif isinstance(raw, dict):
        seen = raw.get("current") or raw.get("hardware")
        asked = raw.get("requested") or raw.get("requestedHardware") or raw.get("requested_hardware")
        if isinstance(seen, str) and seen.strip():
            current = seen.strip()
        if isinstance(asked, str) and asked.strip():
            requested = asked.strip()
    for key in ("requested_hardware", "requestedHardware"):
        value = runtime.get(key)
        if isinstance(value, str) and value.strip():
            requested = value.strip()
    return current, requested


def _settings_mismatch(
    *,
    info: Mapping[str, Any],
    runtime: Mapping[str, Any],
    private: bool,
    hardware: str,
    repo_id: str,
    existed: bool,
) -> str | None:
    """Return a safe reason to refuse, or None when the Space matches the receipt."""

    problems: list[str] = []
    seen_private = info.get("private")
    if existed:
        if seen_private is not True:
            problems.append(f"private={seen_private!r}; existing Space must be private")
        elif private is not True:
            problems.append("AUREON_RECEIPT5_HF_PUBLIC=1 does not apply to an existing Space")
    elif seen_private is not private:
        problems.append(f"private={seen_private!r} expected {private!r}")
    current, requested = _hardware_fields(runtime)
    if current != hardware or (requested is not None and requested != hardware):
        problems.append(
            f"hardware={current!r} requested_hardware={requested!r} expected {hardware!r}"
        )
    sdk = _sdk_name(info)
    if sdk != "gradio":
        problems.append(f"sdk={sdk!r} expected 'gradio'")
    seen_id = info.get("id")
    if isinstance(seen_id, str) and seen_id and seen_id != repo_id:
        problems.append("repo id did not match the requested Space")
    if not problems:
        return None
    return "; ".join(problems)


def _space_exists(client: Any, repo_id: str) -> bool:
    exists = client.repo_exists(repo_id, repo_type="space")
    if isinstance(exists, bool):
        return exists
    raise DeployError(
        "Hugging Face repo_exists did not return a boolean. No upload was started.",
        api_called=True,
    )


def _confirm_space(client: Any, repo_id: str, *, private: bool, hardware: str, existed: bool) -> str | None:
    info = _as_dict(client.repo_info(repo_id, repo_type="space"))
    runtime = _as_dict(client.get_space_runtime(repo_id))
    return _settings_mismatch(
        info=info,
        runtime=runtime,
        private=private,
        hardware=hardware,
        repo_id=repo_id,
        existed=existed,
    )


def deploy_huggingface(
    *,
    token: str,
    auth_method: str,
    root: Path,
    env: Mapping[str, str],
    client: Any = None,
    now: Callable[[], str] | None = None,
) -> dict[str, Any]:
    """Upload the in-repo Space scaffold and read the runtime from the Hub API."""

    if not provider_host_ok(HF_API):
        raise DeployError("Hugging Face API host failed the provider-host check")
    hardware = _hf_hardware(env)
    private = env.get("AUREON_RECEIPT5_HF_PUBLIC", "") != "1"
    folder = root / SCAFFOLD
    if client is None:
        try:
            from huggingface_hub import HfApi
        except ImportError as exc:
            raise DeployError(
                "Hugging Face token is present but huggingface_hub is not installed. "
                "Install huggingface_hub>=1.33 and rerun. No provider read-back was fabricated."
            ) from exc
        client = HfApi(token=token)
    progress = {"attempted": False, "api_called": False, "performed": False}

    def fail(message: str) -> None:
        raise DeployError(
            message,
            attempted=progress["attempted"],
            api_called=progress["api_called"],
            performed=progress["performed"],
        )

    try:
        progress["api_called"] = True
        who = _as_dict(client.whoami())
        username = who.get("name")
        if not isinstance(username, str) or not username.strip():
            fail("Hugging Face whoami returned no username. No upload was started.")
        repo_id = _hf_repo(env, username.strip())
        existed = _space_exists(client, repo_id)
        if existed:
            mismatch = _confirm_space(client, repo_id, private=private, hardware=hardware, existed=True)
            if mismatch:
                fail(
                    "refusing upload: existing Space settings are not acceptable "
                    f"({mismatch}). create_repo exist_ok does not update privacy, hardware, or SDK. "
                    "No upload was started."
                )
        else:
            progress["attempted"] = True
            client.create_repo(
                repo_id,
                repo_type="space",
                space_sdk="gradio",
                exist_ok=False,
                private=private,
                space_hardware=hardware,
            )
            mismatch = _confirm_space(client, repo_id, private=private, hardware=hardware, existed=False)
            if mismatch:
                fail(
                    "refusing upload: Space settings after create_repo do not match the request "
                    f"({mismatch}). No upload was started."
                )
        progress["attempted"] = True
        uploaded = _as_dict(
            client.upload_folder(
                repo_id=repo_id,
                folder_path=str(folder),
                repo_type="space",
                commit_message="Receipt 5: upload in-repo hnc-field scaffold",
            )
        )
        progress["performed"] = True
        runtime = _pick(_as_dict(client.get_space_runtime(repo_id)), RUNTIME_KEYS)
        info = _pick(_as_dict(client.repo_info(repo_id, repo_type="space")), REPO_KEYS)
    except DeployError as exc:
        exc.with_progress(
            attempted=progress["attempted"],
            api_called=progress["api_called"],
            performed=progress["performed"],
        )
        raise
    except Exception as exc:
        message = redact(str(exc), (token,))
        phase = "after the upload" if progress["performed"] else "before the upload finished"
        raise DeployError(
            f"Hugging Face deploy or runtime read failed {phase}. No fabricated read-back was kept. "
            f"error_type={type(exc).__name__} error={message}",
            attempted=progress["attempted"] or progress["performed"],
            api_called=True,
            performed=progress["performed"],
        ) from exc
    stage = runtime.get("stage")
    if not isinstance(stage, str) or not stage:
        raise DeployError(
            "Hugging Face runtime read-back had no stage. The upload already finished. "
            "Receipt 5 is not complete.",
            attempted=True,
            api_called=True,
            performed=True,
        )
    clock = utc_now if now is None else now
    provider_stamp = info.get("lastModified") if isinstance(info.get("lastModified"), str) else None
    readback = redact(
        {
            "api": HF_API,
            "repo_id": repo_id,
            "repo_type": "space",
            "space_sdk": "gradio",
            "private": private,
            "hardware": hardware,
            "scaffold": SCAFFOLD.as_posix(),
            "auth_type": (who.get("auth") or {}).get("type") if isinstance(who.get("auth"), dict) else None,
            "upload_oid": uploaded.get("oid") or uploaded.get("commit_hash"),
            "runtime": runtime,
            "repo": info,
        },
        (token,),
    )
    try:
        assert_no_secrets(readback, (token,))
    except DeployError as exc:
        raise DeployError(
            exc.blocker + " The upload already finished. No read-back was kept.",
            attempted=True,
            api_called=True,
            performed=True,
        ) from exc
    return {
        "provider": "huggingface",
        "auth_method": auth_method,
        "resource_id": repo_id,
        "provider_api": HF_API,
        "deploy_timestamp": provider_stamp or clock(),
        "deploy_timestamp_source": "provider" if provider_stamp else "local-clock",
        "provider_status": {"stage": stage, "hardware": runtime.get("hardware"), "healthy": stage == "RUNNING"},
        "provider_readback": readback,
        "healthy": stage == "RUNNING",
    }


def _gcloud_argv(binary: str, action: str, spec: dict[str, str]) -> list[str]:
    if action == "deploy":
        argv = [binary, "run", "deploy", spec["service"], f"--image={spec['image']}", "--no-allow-unauthenticated"]
    elif action == "describe":
        argv = [binary, "run", "services", "describe", spec["service"]]
    else:
        raise DeployError(f"unknown gcloud action {action}")
    argv.extend(
        [
            f"--project={spec['project']}",
            f"--region={spec['region']}",
            "--platform=managed",
            "--format=json",
            "--quiet",
        ]
    )
    return argv


def _run_gcloud(runner: Runner, argv: list[str]) -> dict[str, Any]:
    try:
        proc = runner(argv, capture_output=True, text=True, timeout=180, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise DeployError(
            f"gcloud {argv[2]} did not finish ({type(exc).__name__}). No read-back was fabricated.",
            attempted=True,
            api_called=True,
        ) from exc
    if proc.returncode != 0:
        raise DeployError(
            f"gcloud {argv[2]} exited {proc.returncode}. No provider read-back was fabricated.",
            attempted=True,
            api_called=True,
        )
    try:
        payload = json.loads(proc.stdout or "null")
    except json.JSONDecodeError as exc:
        raise DeployError(
            "gcloud returned non-JSON. No provider read-back was fabricated.",
            attempted=True,
            api_called=True,
        ) from exc
    if not isinstance(payload, dict):
        raise DeployError(
            "gcloud JSON was not an object. No provider read-back was fabricated.",
            attempted=True,
            api_called=True,
        )
    return payload


def deploy_cloud_run(
    *,
    spec: dict[str, str],
    which: Which,
    runner: Runner | None = None,
    now: Callable[[], str] | None = None,
) -> dict[str, Any]:
    if not provider_host_ok(GCP_API):
        raise DeployError("Cloud Run API host failed the provider-host check")
    binary = which("gcloud")
    if not binary:
        raise DeployError("Cloud Run opt-in is set and gcloud is not on PATH. No provider API was called.")
    execute = runner or subprocess.run
    _run_gcloud(execute, _gcloud_argv(binary, "deploy", spec))
    try:
        described = _run_gcloud(execute, _gcloud_argv(binary, "describe", spec))
    except DeployError as exc:
        raise DeployError(
            "Cloud Run deploy command finished and the describe read-back failed. "
            "No describe payload was recorded. " + exc.blocker,
            attempted=True,
            api_called=True,
            performed=True,
        ) from exc
    meta = described.get("metadata") if isinstance(described.get("metadata"), dict) else {}
    status = described.get("status") if isinstance(described.get("status"), dict) else {}
    conditions = []
    for item in status.get("conditions") or []:
        if isinstance(item, dict):
            conditions.append(
                {"type": item.get("type"), "status": item.get("status"), "reason": item.get("reason")}
            )
    ready = next((item for item in conditions if item.get("type") == "Ready"), None)
    healthy = bool(ready and ready.get("status") == "True")
    clock = utc_now if now is None else now
    readback = redact(
        {
            "api": GCP_API,
            "kind": described.get("kind"),
            "name": meta.get("name"),
            "region": spec["region"],
            "project_sha256": sha256(spec["project"].encode("utf-8")),
            "image_sha256": sha256(spec["image"].encode("utf-8")),
            "generation": meta.get("generation"),
            "observed_generation": status.get("observedGeneration"),
            "latest_ready_revision": status.get("latestReadyRevisionName"),
            "url_present": bool(status.get("url")),
            "conditions": conditions,
        },
        (spec["project"], spec["image"]),
    )
    try:
        assert_no_secrets(readback, (spec["project"], spec["image"]))
    except DeployError as exc:
        raise DeployError(
            exc.blocker + " The Cloud Run deploy command already finished. No read-back was kept.",
            attempted=True,
            api_called=True,
            performed=True,
        ) from exc
    if readback.get("name") != spec["service"]:
        raise DeployError(
            "Cloud Run describe name did not match the requested service. Receipt 5 is not complete.",
            attempted=True,
            api_called=True,
            performed=True,
        )
    return {
        "provider": "google-cloud-run",
        "auth_method": "gcloud:active-account",
        "resource_id": spec["service"],
        "provider_api": GCP_API,
        "deploy_timestamp": clock(),
        "deploy_timestamp_source": "local-clock",
        "provider_status": {
            "ready": None if ready is None else ready.get("status"),
            "reason": None if ready is None else ready.get("reason"),
            "healthy": healthy,
        },
        "provider_readback": readback,
        "healthy": healthy,
    }


def _apply_failure(receipt: dict[str, Any], exc: DeployError, provider: str) -> dict[str, Any]:
    receipt["blocker"] = exc.blocker
    receipt["provider"] = provider
    receipt["deploy_performed"] = bool(exc.performed)
    receipt["deploy_attempted"] = bool(exc.attempted or exc.performed)
    receipt["provider_api_called"] = bool(exc.api_called or exc.attempted or exc.performed)
    return receipt


def _finish_measured(receipt: dict[str, Any], deployed: dict[str, Any], secrets: tuple[str, ...]) -> dict[str, Any]:
    if not provider_host_ok(str(deployed["provider_api"])):
        raise DeployError("provider read-back host is local. Receipt 5 is not complete.")
    payload = deployed["provider_readback"]
    assert_no_secrets(payload, secrets)
    used = deployed["auth_method"]
    receipt.update(
        {
            "outcome": "measured",
            "receipt_5_complete": True,
            "provider": deployed["provider"],
            "auth_method": used,
            "unused_provider_auth": [item for item in receipt["unused_provider_auth"] if item != used],
            "blocker": None,
            "deploy_attempted": True,
            "deploy_performed": True,
            "deploy_timestamp": deployed["deploy_timestamp"],
            "deploy_timestamp_source": deployed["deploy_timestamp_source"],
            "resource_id": deployed["resource_id"],
            "provider_api": deployed["provider_api"],
            "provider_api_called": True,
            "provider_status": deployed["provider_status"],
            "provider_readback": payload,
            "provider_readback_digest": digest(payload),
            "healthy": deployed["healthy"],
            "missing_provider_auth": [],
        }
    )
    return receipt


def produce(
    root: Path,
    *,
    environ: Mapping[str, str] | None = None,
    home: Path | None = None,
    which: Which | None = None,
    gcloud_lister: GcloudLister | None = None,
    hf_client: Any = None,
    gcloud_runner: Runner | None = None,
    now: Callable[[], str] | None = None,
) -> dict[str, Any]:
    env = os.environ if environ is None else environ
    root_home = Path.home() if home is None else home
    find = shutil.which if which is None else which
    try:
        probe = probe_auth(environ=env, home=root_home, which=find, gcloud_lister=gcloud_lister)
        scaffold = scaffold_tree(root)
        meta = measurement_meta(root, now)
    except DeployError as exc:
        # Spec errors happen before a receipt can name a scaffold. Still emit a fail
        # only when the opt-in itself is invalid; a missing scaffold is the same.
        probe = probe_auth(environ=env, home=root_home, which=find, gcloud_lister=gcloud_lister)
        meta = measurement_meta(root, now)
        receipt = _base(meta=meta, probe=probe, scaffold={"path": SCAFFOLD.as_posix(), "source": "unavailable"}, outcome="fail", blocker=exc.blocker, auth_method=None)
        receipt["deploy_attempted"] = False
        return receipt

    if probe["unreadable_provider_auth"]:
        labels = ", ".join(probe["unreadable_provider_auth"])
        receipt = _base(
            meta=meta,
            probe=probe,
            scaffold=scaffold,
            outcome="fail",
            blocker=(
                f"Provider auth path unreadable: {labels}. "
                "Deploy was not attempted. No provider read-back was fabricated."
            ),
            auth_method=None,
        )
        return receipt

    if probe["hf_upload_flag"]:
        method = probe["hf_auth_method"] if probe["hf_token_present"] else None
        receipt = _base(
            meta=meta,
            probe=probe,
            scaffold=scaffold,
            outcome="fail",
            blocker=None,
            auth_method=str(method) if method else None,
        )
        if not probe["hf_token_present"]:
            receipt["blocker"] = (
                f"{HF_UPLOAD_FLAG}=1 and no Hugging Face token is present. "
                "No provider API was called. No provider read-back was fabricated."
            )
            return receipt
        token = _read_token(env, root_home, str(method))
        try:
            deployed = deploy_huggingface(
                token=token,
                auth_method=str(method),
                root=root,
                env=env,
                client=hf_client,
                now=now,
            )
            return _finish_measured(receipt, deployed, (token,))
        except DeployError as exc:
            return _apply_failure(receipt, exc, "huggingface")

    if probe["cloud_run_flag"]:
        receipt = _base(
            meta=meta,
            probe=probe,
            scaffold=scaffold,
            outcome="fail",
            blocker=None,
            auth_method="gcloud:active-account" if probe["gcloud_active_account"] else None,
        )
        try:
            spec = cloud_run_spec(env)
            if spec is None or not (probe["gcloud_active_account"] or probe["gcp_credential_present"]):
                raise DeployError(
                    "Cloud Run deploy was requested and no ACTIVE gcloud account or credential file "
                    "was available. No provider API was called."
                )
            deployed = deploy_cloud_run(spec=spec, which=find, runner=gcloud_runner, now=now)
            return _finish_measured(receipt, deployed, (spec["project"], spec["image"]))
        except DeployError as exc:
            return _apply_failure(receipt, exc, "google-cloud-run")

    return _base(
        meta=meta,
        probe=probe,
        scaffold=scaffold,
        outcome="skip",
        blocker=skip_blocker(probe),
        auth_method=None,
    )


def validate_receipt(receipt: dict[str, Any]) -> list[str]:
    """Structural gate shared by the writer and --check. Independent of a local test pass."""

    errors: list[str] = []

    def need(key: str, expected: object) -> None:
        if receipt.get(key) != expected:
            errors.append(f"{key}={receipt.get(key)!r} expected {expected!r}")

    need("schema", SCHEMA)
    need("stage", 10)
    need("receipt", 5)
    need("decision", "HOLD")
    need("go_live_clear", False)
    need("system_alive_claimed", False)
    need("release_boundary", "HOLD")
    need("orange_badge", "unchanged")
    need("badge_flip", BADGE_FLIP)
    need("pin", PIN)
    need("pin_changed", False)
    need("started_from", STARTED_FROM)
    need("live_trading", False)
    need("orders_placed", False)
    need("tunnels_opened", False)
    need("secrets_recorded", False)
    need("mcp_stages_3_and_4_opened", False)
    need("installers_switched_on", False)
    need("receipts_1_to_4_reverified", False)
    need("localhost_substituted_for_provider", False)
    need("runner", RUNNER)
    if receipt.get("outcome") not in {"skip", "measured", "fail"}:
        errors.append("outcome is not skip, measured, or fail")
    outcome = receipt.get("outcome")
    if outcome == "skip":
        for key, expected in (
            ("receipt_5_complete", False),
            ("provider", None),
            ("deploy_attempted", False),
            ("deploy_performed", False),
            ("deploy_timestamp", None),
            ("provider_api_called", False),
            ("provider_readback", None),
            ("provider_readback_digest", None),
            ("provider_status", None),
            ("healthy", False),
        ):
            if receipt.get(key) != expected:
                errors.append(f"skip receipt {key}={receipt.get(key)!r}")
        if not receipt.get("blocker"):
            errors.append("skip receipt has no blocker")
        if not receipt.get("missing_provider_auth") and not receipt.get("unused_provider_auth"):
            errors.append("skip receipt names neither missing nor unused auth")
    elif outcome == "measured":
        if receipt.get("receipt_5_complete") is not True:
            errors.append("measured receipt is not complete")
        if not receipt.get("deploy_performed") or not receipt.get("provider_api_called"):
            errors.append("measured receipt did not record a deploy and a provider call")
        payload = receipt.get("provider_readback")
        if not isinstance(payload, dict):
            errors.append("measured receipt has no provider payload")
        elif receipt.get("provider_readback_digest") != digest(payload):
            errors.append("provider_readback_digest does not match the payload")
        api = receipt.get("provider_api")
        if not isinstance(api, str) or not provider_host_ok(api):
            errors.append("provider_api is missing or local")
        if not receipt.get("auth_method") or not receipt.get("deploy_timestamp") or not receipt.get("resource_id"):
            errors.append("measured receipt is missing auth, timestamp, or resource id")
        status = receipt.get("provider_status")
        if not isinstance(status, dict) or "healthy" not in status:
            errors.append("provider_status has no healthy field")
    elif outcome == "fail":
        if receipt.get("receipt_5_complete") is not False or receipt.get("provider_readback") is not None:
            errors.append("fail receipt must not carry a provider payload or a complete flag")
        if receipt.get("provider_readback_digest") is not None or receipt.get("healthy") is not False:
            errors.append("fail receipt must keep a null digest and healthy false")
        if receipt.get("deploy_performed"):
            if receipt.get("deploy_attempted") is not True or receipt.get("provider_api_called") is not True:
                errors.append("fail receipt recorded a finished deploy without the provider-call flags")
        elif receipt.get("deploy_attempted") and receipt.get("provider_api_called") is not True:
            errors.append("fail receipt recorded a deploy attempt without a provider call")
        if not receipt.get("blocker"):
            errors.append("fail receipt has no blocker")
    try:
        assert_no_secrets(receipt, ())
    except DeployError as exc:
        errors.append(exc.blocker)
    return errors


def render_markdown(receipt: dict[str, Any]) -> str:
    probe = receipt.get("auth_probe") or {}
    missing = ", ".join(receipt.get("missing_provider_auth") or []) or "none"
    unused = ", ".join(receipt.get("unused_provider_auth") or []) or "none"
    status = receipt.get("provider_status")
    status_text = "none" if not isinstance(status, dict) else json.dumps(status, sort_keys=True)
    scaffold = receipt.get("scaffold") or {}
    lines = [
        "# Authenticated deployment — receipt 5",
        "",
        "Stage 10 only. This file is a deployment receipt. It is not a claim that a live Aureon instance exists, and it is not a claim that the system is alive.",
        "",
        f"Outcome: **{receipt.get('outcome')}**. Receipt 5 complete: **{receipt.get('receipt_5_complete')}**.",
        f"Decision: **{receipt.get('decision')}**. `go_live_clear`: **{receipt.get('go_live_clear')}**.",
        f"Release boundary: **{receipt.get('release_boundary')}**. Orange badge: {receipt.get('orange_badge')}.",
        f"Badge flip: {receipt.get('badge_flip')}.",
        f"Public pin: `{receipt.get('pin')}` (changed: {receipt.get('pin_changed')}).",
        f"Pin measured at tip `{receipt.get('pin_measured_at')}`. {receipt.get('pin_source')}",
        "Live trading: false. Orders placed: false. Tunnels opened: false. Market data fetched: false.",
        "MCP plan stages 3 and 4 opened: false. Installers switched on: false. Receipts 1-4 re-verified: false.",
        "",
        "## Provider",
        "",
        f"Provider: `{receipt.get('provider')}`. Auth method: `{receipt.get('auth_method')}`.",
        f"Provider API: `{receipt.get('provider_api')}`. Provider API called: **{receipt.get('provider_api_called')}**.",
        f"Resource id: `{receipt.get('resource_id')}`.",
        f"Deploy attempted: **{receipt.get('deploy_attempted')}**. Deploy performed: **{receipt.get('deploy_performed')}**.",
        f"Deploy timestamp: `{receipt.get('deploy_timestamp')}` ({receipt.get('deploy_timestamp_source')}).",
        f"Healthy: **{receipt.get('healthy')}**. Provider status: `{status_text}`.",
        f"Read-back digest: `{receipt.get('provider_readback_digest')}`.",
        f"Localhost substituted for the provider: **{receipt.get('localhost_substituted_for_provider')}**.",
        "",
        "## Auth probe",
        "",
        f"Missing provider auth: {missing}.",
        f"Present and unused: {unused}.",
        (
            "Probe flags: "
            f"hf_token_present={probe.get('hf_token_present')} "
            f"hf_upload_opt_in={probe.get('hf_upload_opt_in')} "
            f"gcloud_on_path={probe.get('gcloud_on_path')} "
            f"gcloud_active_account={probe.get('gcloud_active_account')} "
            f"gcp_credential_present={probe.get('gcp_credential_present')} "
            f"cloud_run_deploy_opt_in={probe.get('cloud_run_deploy_opt_in')}."
        ),
        "",
        f"Blocker: {receipt.get('blocker')}",
        "",
        "## Scaffold",
        "",
        (
            f"Eligible upload: `{scaffold.get('path')}` "
            f"files={scaffold.get('file_count')} sha256=`{scaffold.get('sha256')}` "
            f"source={scaffold.get('source')}. This hash is a local worktree hash, not a provider read-back."
        ),
        "",
        "Spend guard: " + str(receipt.get("spend_guard")),
        "",
        "Runner: `" + str(receipt.get("runner")) + "`.",
        "",
        str(receipt.get("measurement_note")),
        "",
    ]
    return "\n".join(lines)


def write_receipt(root: Path, receipt: dict[str, Any]) -> None:
    errors = validate_receipt(receipt)
    if errors:
        raise DeployError("receipt failed validation: " + "; ".join(errors))
    json_path = root / JSON_PATH
    md_path = root / MARKDOWN_PATH
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(receipt), encoding="utf-8")


def load_receipt(root: Path) -> dict[str, Any]:
    return json.loads((root / JSON_PATH).read_text(encoding="utf-8"))


def check(root: Path, *, environ: Mapping[str, str] | None = None, home: Path | None = None, which: Which | None = None) -> list[str]:
    """Re-probe auth and require the committed file to agree. Do not deploy."""

    errors = validate_receipt(load_receipt(root))
    markdown = (root / MARKDOWN_PATH).read_text(encoding="utf-8")
    receipt = load_receipt(root)
    if markdown != render_markdown(receipt):
        errors.append("markdown does not match the json")
    if f"`{receipt.get('provider_readback_digest')}`" not in markdown:
        errors.append("markdown omits the digest")
    probe = probe_auth(environ=environ, home=home, which=which)
    deploy_requested = bool(probe["hf_upload_flag"] or probe["cloud_run_flag"])
    if deploy_requested:
        if receipt.get("outcome") == "skip":
            errors.append("committed receipt is a skip and a deploy opt-in is now set")
    else:
        if receipt.get("outcome") != "skip":
            errors.append("live probe has no deploy auth but the committed receipt is not a skip")
        if receipt.get("missing_provider_auth") != probe["missing_provider_auth"]:
            errors.append("missing_provider_auth does not match a fresh probe")
        if receipt.get("unused_provider_auth") != probe["unused_provider_auth"]:
            errors.append("unused_provider_auth does not match a fresh probe")
    if receipt.get("pin") != PIN or receipt.get("pin_changed") is not False:
        errors.append("pin field moved")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write or check go-live receipt 5.")
    parser.add_argument("--check", action="store_true", help="re-probe auth and verify the committed receipt; do not deploy")
    args = parser.parse_args(argv)
    if args.check:
        errors = check(ROOT)
        if errors:
            print("\n".join(errors), file=sys.stderr)
            return 1
        print(f"ok {JSON_PATH.as_posix()}")
        return 0
    receipt = produce(ROOT)
    write_receipt(ROOT, receipt)
    print(f"wrote {JSON_PATH.as_posix()} outcome={receipt['outcome']} complete={receipt['receipt_5_complete']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
