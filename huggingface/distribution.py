"""Measure Hugging Face distribution. Default path does not sign in and does not deploy.

A public Space, a public dataset, and a public listener need Gary's own yes.
This file records HOLD when that yes, a token, or a PRO plan is missing.
It never writes a token value into the receipt.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

PIN = "34864ff0547d2cff03e707414743a3b0cc8770b5"
SOURCE_TIP_FALLBACK = "bb04503119681adcf832f3c3e9b0cbf09fc7a938"
TOKEN_NAMES = ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN")
SPACES = ("hnc-field", "auris-coherence", "qgita-snr", "organism-replay")
DATASET = "fixed-seed-reproducible-runs"
FREE_FLAVOR = "cpu-basic"
IGNORE = (
    ".env",
    ".env.*",
    "**/.env",
    "**/.env.*",
    "**/*.pem",
    "**/*.key",
    "**/.git/**",
    "**/secrets/**",
)


def repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in (here.parent, *here.parents):
        if (parent / "aureon" / "core" / "hnc_field.py").is_file():
            return parent
    raise FileNotFoundError("repo root was not found above huggingface/distribution.py")


def _present(env: dict[str, str], name: str) -> bool:
    return bool(str(env.get(name, "")).strip())


def _token_present(env: dict[str, str]) -> bool:
    return any(_present(env, name) for name in TOKEN_NAMES)


def _redact(text: str, env: dict[str, str]) -> str:
    redacted = text
    for name in TOKEN_NAMES:
        value = str(env.get(name, "")).strip()
        if value:
            redacted = redacted.replace(value, "[redacted]")
    return redacted


def _source_tip(root: Path) -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return SOURCE_TIP_FALLBACK
    sha = completed.stdout.strip()
    if completed.returncode == 0 and len(sha) == 40:
        return sha
    return SOURCE_TIP_FALLBACK


def _flavor(env: dict[str, str]) -> str:
    return env.get("AUREON_HF_FLAVOR", FREE_FLAVOR).strip() or FREE_FLAVOR


def _pro_required(flavor: str) -> bool:
    return flavor != FREE_FLAVOR


def measure(env: dict[str, str] | None = None, *, root: Path | None = None, now: str | None = None) -> dict:
    """HOLD-skip facts. This function does not call Hugging Face."""

    source = os.environ if env is None else env
    checkout = repo_root() if root is None else root
    flavor = _flavor(source)
    missing: list[str] = []
    if not _token_present(source):
        missing.append("HF_TOKEN")
    if source.get("AUREON_HF_GARY_YES") != "1":
        missing.append("GARY_YES")
    if _pro_required(flavor):
        missing.append("PRO")
    stamp = now or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    reason = (
        "HOLD-skip. "
        + (
            "Missing token: HF_TOKEN (also checked HUGGING_FACE_HUB_TOKEN). "
            if "HF_TOKEN" in missing
            else "A token name is set. The value was not read into this receipt and was not sent. "
        )
        + (
            "PRO is required for flavor "
            f"{flavor}. ZeroGPU and paid hardware were not requested. "
            if "PRO" in missing
            else (
                "PRO was not queried. No sign-in was performed. "
                "This scaffold selects cpu-basic and does not select ZeroGPU, "
                "so a PRO plan is not required for these files. "
                "A Hub response that requires PRO stays HOLD. "
            )
        )
        + (
            "Gary's own yes was not set (AUREON_HF_GARY_YES). "
            if "GARY_YES" in missing
            else "Gary's own yes is set. "
        )
        + "Charlie gate: a public Space and a public listener need that yes. "
        "Deploy was not attempted. The Space is not live. Go-live: HOLD."
    )
    return {
        "bind_default": "127.0.0.1",
        "charlie_gate": "public Space and public listener need Gary's own yes; sign-in was not performed",
        "dataset": DATASET,
        "decision": "HOLD",
        "deploy_attempted": False,
        "flavor": flavor,
        "gary_yes": source.get("AUREON_HF_GARY_YES") == "1",
        "git_head_at_measurement": _source_tip(checkout),
        "go_live": "HOLD",
        "go_live_clear": False,
        "gradio_share": False,
        "hf_cli": "present" if shutil.which("hf") else "absent",
        "hf_org_present": _present(source, "HF_ORG"),
        "is_pro": "not_queried",
        "can_pay": "not_queried",
        "live_trading": False,
        "measured_at": stamp,
        "missing": missing,
        "orange_badge": "unchanged",
        "orders_placed": False,
        "pin_moved": False,
        "pro_required": _pro_required(flavor),
        "pro_status": "not_queried",
        "public_listener_opened": False,
        "public_require_pin": PIN,
        "reason": reason,
        "schema": "aureon.hf_space.distribution.v1",
        "sign_in_attempted": False,
        "space_live": False,
        "spaces": list(SPACES),
        "tag": "hold-skip",
        "token_names_checked": list(TOKEN_NAMES),
        "token_present": _token_present(source),
        "token_value_recorded": False,
        "visibility_selected": "private",
    }


def render_markdown(receipt: dict) -> str:
    missing = ", ".join(f"`{name}`" for name in receipt["missing"]) or "none"
    lines = [
        "# Hugging Face distribution receipt",
        "",
        (
            f"Decision: **HOLD**. Tag: `{receipt['tag']}`. "
            + (
                "Runtime stage RUNNING was read back. Go-live stays HOLD."
                if receipt["space_live"]
                else "The Space is not live."
            )
        ),
        "",
        (
            f"Measured at `{receipt['git_head_at_measurement']}` on {receipt['measured_at']}. "
            "Go-live: **HOLD**. This receipt does not clear go-live. "
            "The orange release-boundary badge is unchanged. "
            f"Public pin `{receipt['public_require_pin']}` is unchanged. "
            "No order was placed. Live trading is off."
        ),
        "",
        f"Missing: {missing}.",
        "",
        receipt["reason"],
        "",
        (
            f"Default bind: `{receipt['bind_default']}`. Gradio share: off. "
            f"Visibility selected for a later upload: `{receipt['visibility_selected']}`. "
            f"Hardware flavor on this scaffold: `{receipt['flavor']}`. "
            f"`hf` CLI: {receipt['hf_cli']}. "
            f"`isPro`: {receipt['is_pro']}. `canPay`: {receipt['can_pay']}."
        ),
        "",
        "Spaces in the scaffold: " + ", ".join(f"`{name}`" for name in receipt["spaces"]) + ".",
        f"Dataset in the scaffold: `{receipt['dataset']}`.",
        "",
        (
            "This file is a measurement of the local scaffold. "
            "It is not a claim that a Hugging Face Space is running."
        ),
        "",
    ]
    return "\n".join(lines)


def _hub_client(token: str):
    from huggingface_hub import HfApi

    return HfApi(token=token)


def _info_field(info: object, name: str):
    if isinstance(info, dict):
        return info.get(name)
    return getattr(info, name, None)


def _runtime_stage(info: object) -> str:
    runtime = _info_field(info, "runtime")
    stage = runtime.get("stage") if isinstance(runtime, dict) else getattr(runtime, "stage", None)
    if isinstance(stage, str) and stage.strip():
        return stage.strip()
    return "not_read"


def _pro_error(message: str) -> bool:
    text = message.lower()
    markers = (
        "pro subscription",
        "pro plan",
        "requires pro",
        "hugging face pro",
        "billing",
        "payment required",
        "402",
    )
    return any(marker in text for marker in markers)


def _refuse(receipt: dict, reason: str) -> dict:
    refused = dict(receipt)
    refused["decision"] = "HOLD"
    refused["tag"] = "hold-skip"
    refused["deploy_attempted"] = False
    refused["sign_in_attempted"] = False
    refused["space_live"] = False
    refused["public_listener_opened"] = False
    refused["go_live"] = "HOLD"
    refused["go_live_clear"] = False
    refused["reason"] = reason
    return refused


def deploy(
    env: dict[str, str] | None = None,
    *,
    client_factory=None,
    root: Path | None = None,
) -> dict:
    """Upload only a private cpu-basic scaffold when the gates pass.

    The default command does not call this. A public visibility value is
    refused unless AUREON_HF_PUBLIC=1 is also set. space_live stays false
    unless every read-back stage is RUNNING. Go-live stays HOLD either way.
    """

    source = dict(os.environ if env is None else env)
    receipt = measure(source, root=root)
    flavor = receipt["flavor"]
    if receipt["pro_required"]:
        return _refuse(
            receipt,
            f"HOLD-skip. PRO is required for flavor {flavor}. "
            "cpu-basic is the scaffold flavor. Sign-in was not performed. The Space is not live.",
        )
    if not receipt["token_present"]:
        return _refuse(
            receipt,
            "HOLD-skip. Missing token: HF_TOKEN (also checked HUGGING_FACE_HUB_TOKEN). "
            "PRO was not queried. Sign-in was not performed. The Space is not live.",
        )
    if not receipt["gary_yes"]:
        return _refuse(
            receipt,
            "HOLD-skip. A token name is set. The value was not sent. "
            "Gary's own yes was not set (AUREON_HF_GARY_YES). "
            "Charlie gate: sign-in and a public listener need that yes. "
            "PRO was not queried. The Space is not live.",
        )
    visibility = source.get("AUREON_HF_VISIBILITY", "private").strip() or "private"
    if visibility != "private" and source.get("AUREON_HF_PUBLIC") != "1":
        return _refuse(
            receipt,
            "HOLD-skip. Public visibility was requested without AUREON_HF_PUBLIC=1. "
            "A public Space needs Gary's own yes. Deploy was not attempted. The Space is not live.",
        )
    if not receipt["hf_org_present"]:
        return _refuse(
            receipt,
            "HOLD-skip. HF_ORG is absent, so there is no destination repo. "
            "Sign-in was not performed. The Space is not live.",
        )
    if client_factory is None:
        client_factory = _hub_client

    token = ""
    for name in TOKEN_NAMES:
        if _present(source, name):
            token = str(source[name]).strip()
            break
    try:
        client = client_factory(token)
    except Exception as exc:
        message = _redact(str(exc), source)
        return _refuse(
            receipt,
            "HOLD-skip. The Hugging Face client did not start. "
            f"{type(exc).__name__}: {message}. The Space is not live. PRO status: not_queried.",
        )
    receipt["sign_in_attempted"] = True
    receipt["deploy_attempted"] = True
    org = str(source["HF_ORG"]).strip()
    private = visibility != "public"
    created: list[dict] = []
    checkout = repo_root() if root is None else root
    targets = [(DATASET, "dataset", None)] + [(name, "space", "gradio") for name in SPACES]
    try:
        for name, repo_type, sdk in targets:
            repo_id = f"{org}/{name}"
            kwargs = {"repo_id": repo_id, "repo_type": repo_type, "private": private, "exist_ok": True}
            if sdk is not None:
                kwargs["space_sdk"] = sdk
            client.create_repo(**kwargs)
            folder = checkout / "huggingface" / name
            client.upload_folder(
                repo_id=repo_id,
                folder_path=str(folder),
                repo_type=repo_type,
                commit_message="Guarded Aureon scaffold. Live trading off.",
                ignore_patterns=list(IGNORE),
            )
            info = client.repo_info(repo_id, repo_type=repo_type)
            created.append(
                {
                    "private": bool(_info_field(info, "private")),
                    "repo_id": repo_id,
                    "repo_type": repo_type,
                    "runtime_stage": _runtime_stage(info),
                }
            )
    except Exception as exc:
        message = _redact(str(exc), source)
        if _pro_error(message):
            if "PRO" not in receipt["missing"]:
                receipt["missing"] = [*receipt["missing"], "PRO"]
            receipt["pro_status"] = "hub_required"
        receipt["read_back"] = created
        receipt["decision"] = "HOLD"
        receipt["tag"] = "hold-skip"
        receipt["space_live"] = False
        receipt["go_live"] = "HOLD"
        receipt["go_live_clear"] = False
        receipt["reason"] = (
            "HOLD-skip. Deploy was attempted and did not finish. "
            f"{type(exc).__name__}: {message}. The Space is not live. Go-live: HOLD."
        )
        return receipt
    receipt["read_back"] = created
    receipt["visibility_selected"] = "private" if private else "public"
    stages = [str(row.get("runtime_stage")) for row in created]
    receipt["space_live"] = bool(created) and all(stage == "RUNNING" for stage in stages)
    receipt["decision"] = "HOLD"
    receipt["go_live"] = "HOLD"
    receipt["go_live_clear"] = False
    receipt["public_listener_opened"] = bool(receipt["space_live"] and not private)
    if receipt["space_live"]:
        receipt["tag"] = "runtime-running"
        receipt["reason"] = (
            "Runtime stage RUNNING was read back for every repo. "
            "Go-live stays HOLD. This is not an authenticated deployment receipt. "
            "The orange release-boundary badge is unchanged."
        )
    else:
        receipt["tag"] = "uploaded-not-live"
        shown = ", ".join(stages) if stages else "not_read"
        receipt["reason"] = (
            f"Upload returned. Runtime stage: {shown}. The Space is not live. "
            "Go-live stays HOLD. This is not an authenticated deployment receipt."
        )
    return receipt


def write_receipt(receipt: dict, root: Path | None = None) -> tuple[Path, Path]:
    checkout = repo_root() if root is None else root
    directory = checkout / "measured"
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / "hf_space_distribution.json"
    md_path = directory / "hf_space_distribution.md"
    json_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(receipt), encoding="utf-8")
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--deploy" in args:
        receipt = deploy()
    else:
        receipt = measure()
    write_receipt(receipt)
    summary = {
        "decision": receipt["decision"],
        "space_live": receipt["space_live"],
        "tag": receipt["tag"],
    }
    sys.stdout.write(json.dumps(summary) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
