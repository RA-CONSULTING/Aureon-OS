#!/usr/bin/env python3
"""Restore the Space Docker card and the approved L40S request by direct commit.

Why this exists: the ``GaryLeckey/aureon-os`` card was replaced with a
Gradio-only app while the runtime kept requesting ``l4x1``. A Gradio card makes
the Hub substitute a notebook server, so the published Docker image never runs
and the GPU request fails on capacity for hardware nobody uses. The maintained
publisher cannot stage from NTFS (case-distinct tracked paths), so this makes a
narrow, reviewable commit of the card files only.

Default is a dry run that prints the exact plan. ``--apply`` performs one Hub
commit and, only with ``--request-hardware``, one paid-hardware request.
Nothing here spends money unless ``--request-hardware`` is passed explicitly.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SPACE_REPOSITORY = "GaryLeckey/aureon-os"
MODEL_REPOSITORY = "GaryLeckey/aureon-7b"
MODEL_VARIABLE = "AUREON_MODEL_REVISION"
APPROVED_HARDWARE = "l40sx1"
EXPECTED_SDK = "docker"
# Card files this restore owns. app.py is deliberately absent: a Docker Space
# does not need it, and leaving it invites the same misreading of the live tree.
RESTORED_PATHS = ("README.md", "Dockerfile", ".dockerignore")


def local_card(root: Path) -> dict[str, bytes]:
    """Return the maintained card files from the repository checkout."""
    deploy = root / "deploy" / "huggingface"
    return {
        "README.md": (deploy / "README.md").read_bytes(),
        "Dockerfile": (deploy / "Dockerfile").read_bytes(),
        ".dockerignore": (deploy / "Dockerfile.dockerignore").read_bytes(),
    }


def validate_card(card: bytes) -> dict[str, Any]:
    """Fail closed unless the card declares the Docker SDK and approved hardware."""
    import yaml

    text = card.decode("utf-8")
    if not text.startswith("---\n"):
        raise SystemExit("card must start with YAML front matter")
    metadata = yaml.safe_load(text.split("---\n", 2)[1]) or {}
    if metadata.get("sdk") != EXPECTED_SDK:
        raise SystemExit(f"card sdk must be {EXPECTED_SDK}, got {metadata.get('sdk')!r}")
    if metadata.get("suggested_hardware") != APPROVED_HARDWARE:
        raise SystemExit(
            "card suggested_hardware must be "
            f"{APPROVED_HARDWARE}, got {metadata.get('suggested_hardware')!r}"
        )
    if metadata.get("app_port") != 7860:
        raise SystemExit(f"card app_port must be 7860, got {metadata.get('app_port')!r}")
    if MODEL_REPOSITORY not in text:
        raise SystemExit(f"card must name the served model {MODEL_REPOSITORY}")
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--space", default=SPACE_REPOSITORY)
    parser.add_argument("--apply", action="store_true", help="perform the Hub commit")
    parser.add_argument(
        "--request-hardware",
        action="store_true",
        help=f"also request paid {APPROVED_HARDWARE} with sleep disabled (spends money)",
    )
    parser.add_argument("--receipt", type=Path, default=None)
    arguments = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")

    files = local_card(arguments.repo)
    validate_card(files["README.md"])

    from huggingface_hub import CommitOperationAdd, HfApi

    api = HfApi()
    space = api.repo_info(arguments.space, repo_type="space", files_metadata=True)
    remote_sizes = {sibling.rfilename: sibling.size for sibling in space.siblings}
    # runtime.hardware is only populated when explicitly expanded.
    runtime = api.get_space_runtime(arguments.space)
    raw_hardware = (runtime.raw or {}).get("hardware") or {}

    plan: dict[str, Any] = {
        "space": arguments.space,
        "space_revision_before": space.sha,
        "card_before": {
            "sdk": getattr(space.cardData, "sdk", None),
            "suggested_hardware": getattr(space.cardData, "suggested_hardware", None),
            "app_file": getattr(space.cardData, "app_file", None),
        },
        "hardware_before": {
            "stage": str(runtime.stage),
            "requested": raw_hardware.get("requested"),
            "current": raw_hardware.get("current"),
        },
        "files": {
            name: {"local_bytes": len(files[name]), "remote_bytes": remote_sizes.get(name)}
            for name in RESTORED_PATHS
        },
        "applied": False,
        "space_revision_after": None,
        "hardware_request_sent": False,
    }
    print(json.dumps(plan, indent=2, sort_keys=True), flush=True)

    if arguments.apply:
        commit = api.create_commit(
            repo_id=arguments.space,
            repo_type="space",
            operations=[
                CommitOperationAdd(path_in_repo=name, path_or_fileobj=files[name])
                for name in RESTORED_PATHS
            ],
            commit_message=(
                "Restore Docker Space card and the approved L40S request\n\n"
                "The card had been replaced with a Gradio app while the runtime kept "
                "requesting l4x1, so the published Docker image never ran and the GPU "
                "request failed on capacity. Restore sdk: docker with app_port 7860 and "
                f"suggested_hardware {APPROVED_HARDWARE}."
            ),
        )
        plan["applied"] = True
        plan["space_revision_after"] = getattr(commit, "oid", None) or getattr(commit, "sha", None)
        model_revision = str(api.model_info(MODEL_REPOSITORY).sha)
        plan["model_variable"] = model_revision
        api.add_space_variable(
            repo_id=arguments.space,
            key=MODEL_VARIABLE,
            value=model_revision,
        )

    if arguments.request_hardware:
        if not arguments.apply:
            raise SystemExit("--request-hardware requires --apply")
        # The card must be Docker at the moment of the request; otherwise the
        # paid GPU would be attached to a process that never loads the model.
        after = api.repo_info(arguments.space, repo_type="space")
        if getattr(after.cardData, "sdk", None) != EXPECTED_SDK:
            raise SystemExit("refusing paid hardware: live card is not sdk: docker")
        api.request_space_hardware(
            repo_id=arguments.space,
            hardware=APPROVED_HARDWARE,
            sleep_time=-1,
        )
        plan["hardware_request_sent"] = True
        plan["hardware_requested"] = APPROVED_HARDWARE
        # An accepted request is not a running GPU; readiness is proven only by a
        # later runtime probe and the container smoke receipt.
        plan["running_verified"] = False

    if arguments.receipt:
        arguments.receipt.parent.mkdir(parents=True, exist_ok=True)
        arguments.receipt.write_text(
            json.dumps(plan, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
