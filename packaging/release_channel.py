#!/usr/bin/env python3
"""Public source-archive channel for a tip prerelease.

The command reads the committed go-live records and the published pin. It
builds a git archive, a zip, checksums, and a manifest. It does not create a
tag, does not call GitHub, does not move PINNED_COMMIT, does not place an
order, and does not report the system alive.

`publish` always exits non-zero. Go-live stays HOLD. Charlie, Buzz, and Spike
PASS do not publish. The command waits for Gary's own yes and still does not
create a release or a tag.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

PUBLISHED_PIN = "bb04503119681adcf832f3c3e9b0cbf09fc7a938"
LINEAGE_TIP = "08f04936088689e29b7995d89530b21b425c35f9"
SCHEMA = "aureon.public-release-channel.v1"
NOTES = Path("docs/releases/RELEASE_NOTES_tip.md")
ORANGE_BADGE = "release%20boundary-HOLD-orange"
TAG_RE = re.compile(r"^tip-([0-9a-f]{7,40})$")
PIN_RE = re.compile(r'^PINNED_COMMIT = "([0-9a-f]{40})"$', re.MULTILINE)

# Substrings the tip notes must contain while production publish is refused.
# The pin and the lineage tip are added from the constants above.
STATIC_REQUIRED_PHRASES = (
    "./install.sh --smoke",
    "AUREON_AUTONOMY_MODE=guarded",
    "live trading stays off",
    "release boundary stays HOLD",
    "orange release-boundary badge stays HOLD",
    "This pull request does not move the pin.",
    "The system is not claimed alive.",
    "No order is placed.",
    "production go-live is not cleared",
    "Receipts 1-5 are not verified on this commit",
    "Go-live stays HOLD",
)

FORBIDDEN_PHRASES = (
    "The system is alive.",
    "go_live_clear: true",
    "release boundary-CLEAR",
    "badge stays green",
    "production go-live is cleared on this commit",
    "production-ready",
    "production ready",
    "production_ready",
    "validated",
)

RECEIPT_SPECS = (
    {
        "id": 1,
        "name": "native process containment with a zero-network default",
        "path": "reports/measured/native_process_containment.json",
        "commit_keys": ("git_head_at_measurement",),
    },
    {
        "id": 2,
        "name": "exact target-source measurement and immutable release provenance",
        "path": "measured/go_live_stage6_provenance.json",
        "commit_keys": ("tip",),
    },
    {
        "id": 3,
        "name": "durable HNC evidence with an external monotonic head anchor",
        "path": "evidence/output/hnc_head_anchor.json",
        "commit_keys": ("tip", "git_head_at_measurement"),
    },
    {
        "id": 4,
        "name": "complete source-boundary census closure",
        "path": "measured/go_live_stage6_source_census.json",
        "commit_keys": ("tip",),
    },
    {
        "id": 5,
        "name": "authenticated deployment receipt and provider-side read-back",
        "path": None,
        "candidates": (
            "measured/authenticated_deployment_receipt.json",
            "reports/measured/authenticated_deployment.json",
        ),
        "commit_keys": ("tip", "git_head", "git_head_at_measurement"),
    },
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=check,
        capture_output=True,
        text=True,
    )


def git_head(root: Path) -> str:
    return _git(root, "rev-parse", "HEAD").stdout.strip()


def read_pinned_commit(root: Path) -> str:
    text = (root / "mcp" / "aureon_public" / "guard_loader.py").read_text(encoding="utf-8")
    match = PIN_RE.search(text)
    if match is None:
        raise ValueError("PINNED_COMMIT is missing from mcp/aureon_public/guard_loader.py")
    return match.group(1)


def _load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} is not a JSON object")
    return value


def _hold_flag(record: dict) -> bool:
    if record.get("go_live_clear") is True:
        return False
    decision = str(record.get("decision", "")).upper()
    go_live = str(record.get("go_live", "")).upper()
    boundary = str(record.get("release_boundary", "")).upper()
    if decision == "HOLD" or go_live == "HOLD" or boundary == "HOLD":
        return True
    if record.get("go_live_clear") is False:
        return True
    return True


def _verified_on_head(record: dict | None, head: str, commit_keys: tuple[str, ...]) -> bool:
    if record is None:
        return False
    if record.get("go_live_clear") is not True:
        return False
    if str(record.get("decision", "")).upper() == "HOLD":
        return False
    if str(record.get("go_live", "")).upper() == "HOLD":
        return False
    if str(record.get("release_boundary", "")).upper() == "HOLD":
        return False
    if record.get("system_alive") is True:
        return False
    named = [record.get(key) for key in commit_keys]
    return head in named


def _receipt_row(root: Path, head: str, spec: dict) -> dict:
    path_text = spec.get("path")
    candidates = list(spec.get("candidates") or ())
    if path_text:
        candidates = [path_text, *candidates]
    found = next((item for item in candidates if (root / item).is_file()), None)
    record = _load_json(root / found) if found else None
    named = None
    if record is not None:
        for key in spec["commit_keys"]:
            if record.get(key):
                named = record.get(key)
                break
    verified = _verified_on_head(record, head, spec["commit_keys"])
    return {
        "id": spec["id"],
        "name": spec["name"],
        "path": found,
        "present": record is not None,
        "bound_commit": named,
        "bound_to_head": named == head,
        "decision": None if record is None else record.get("decision", record.get("go_live")),
        "go_live_clear": False if record is None else record.get("go_live_clear") is True,
        "release_boundary": None if record is None else record.get("release_boundary"),
        "system_alive": False if record is None else record.get("system_alive") is True,
        "orders_placed": False if record is None else record.get("orders_placed") is True,
        "live_trading": False if record is None else record.get("live_trading") is True,
        "hold": True if record is None else _hold_flag(record),
        "verified_on_head": verified,
    }


def _notes_text(root: Path) -> str:
    path = root / NOTES
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    result = _git(root, "merge-base", "--is-ancestor", ancestor, descendant, check=False)
    return result.returncode == 0


def evaluate(root: Path | None = None) -> dict:
    root = (root or repo_root()).resolve()
    head = git_head(root)
    pin = read_pinned_commit(root)
    notes = _notes_text(root)
    readme = (root / "README.md").read_text(encoding="utf-8")
    receipts = [_receipt_row(root, head, spec) for spec in RECEIPT_SPECS]
    receipts_verified_on_head = all(row["verified_on_head"] for row in receipts)
    problems: list[str] = []
    if pin != PUBLISHED_PIN:
        problems.append(
            "PINNED_COMMIT does not match packaging/release_channel.py PUBLISHED_PIN. "
            "This tool does not move the pin."
        )
    if ORANGE_BADGE not in readme:
        problems.append("README.md is missing the orange release-boundary HOLD badge.")
    if not notes:
        problems.append(f"{NOTES.as_posix()} is missing.")
    if "Go-live stays HOLD" not in readme:
        problems.append("README.md does not show go-live as HOLD.")
    required = (*STATIC_REQUIRED_PHRASES, pin, LINEAGE_TIP)
    for phrase in required:
        if phrase not in notes:
            problems.append(f"release notes are missing {phrase!r}")
    for label, text in (("release notes", notes), ("README.md", readme)):
        lowered = text.lower()
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lowered:
                problems.append(f"{label} contain forbidden phrase {phrase!r}")
    if not _ancestor(root, LINEAGE_TIP, head):
        problems.append(f"{LINEAGE_TIP} is not an ancestor of HEAD {head}")
    for row in receipts:
        if row["system_alive"]:
            problems.append(f"receipt {row['id']} sets system_alive true")
        if row["orders_placed"]:
            problems.append(f"receipt {row['id']} sets orders_placed true")
        if row["live_trading"]:
            problems.append(f"receipt {row['id']} sets live_trading true")
    return {
        "schema": SCHEMA,
        "head": head,
        "lineage_tip": LINEAGE_TIP,
        "lineage_tip_is_ancestor": _ancestor(root, LINEAGE_TIP, head),
        "pin": pin,
        "pin_short": pin[:8],
        "pin_moved": False,
        "orange_badge": "HOLD" if ORANGE_BADGE in readme else "missing",
        "release_boundary": "HOLD",
        "go_live": "HOLD",
        "go_live_clear": False,
        "receipts_verified_on_head": receipts_verified_on_head,
        "production_publish_allowed": False,
        "gary_yes_required": True,
        "triple_pass_publishes": False,
        "system_alive": False,
        "live_trading": False,
        "orders_placed": False,
        "published": False,
        "draft": True,
        "prerelease": True,
        "stranger_commands": ["./install.sh", "./install.sh --smoke"],
        "receipts": receipts,
        "problems": problems,
    }


def accept_tag(tag: str, head: str) -> str:
    match = TAG_RE.fullmatch(tag)
    if match is None:
        raise ValueError(
            f"refusing tag {tag!r}. The channel accepts tip- plus 7 to 40 "
            "lowercase hex digits of the archived commit."
        )
    short = match.group(1)
    if not head.startswith(short):
        raise ValueError(f"tag {tag} is not a prefix of HEAD {head}")
    return tag


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_tree_archives(root: Path, dest: Path, basename: str) -> list[dict]:
    """Write a tar.gz and a zip of `root`'s git HEAD. Checksums are of those bytes."""
    dest.mkdir(parents=True, exist_ok=True)
    prefix = f"{basename}/"
    written: list[dict] = []
    for suffix, fmt in (("tar.gz", "tar.gz"), ("zip", "zip")):
        target = dest / f"{basename}.{suffix}"
        _git(
            root,
            "archive",
            f"--format={fmt}",
            f"--prefix={prefix}",
            f"--output={target}",
            "HEAD",
        )
        written.append(
            {
                "name": target.name,
                "sha256": _sha256(target),
                "bytes": target.stat().st_size,
            }
        )
    return written


def _write_sums(dest: Path, rows: list[dict]) -> None:
    lines = [f"{row['sha256']}  {row['name']}" for row in rows]
    (dest / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def archive(root: Path | None = None, dest: Path | None = None, tag: str | None = None) -> dict:
    root = (root or repo_root()).resolve()
    if dest is None:
        raise ValueError("dest is required")
    report = evaluate(root)
    if report["problems"]:
        raise ValueError("refusing to archive: " + "; ".join(report["problems"]))
    head = report["head"]
    if tag:
        accept_tag(tag, head)
        basename = f"Aureon-OS-{tag}"
    else:
        basename = f"Aureon-OS-{head}"
    archives = build_tree_archives(root, dest, basename)
    manifest = {
        "schema": SCHEMA,
        "kind": "source-archive-prerelease",
        "head": head,
        "lineage_tip": report["lineage_tip"],
        "tag": tag,
        "pin": report["pin"],
        "pin_moved": False,
        "release_boundary": "HOLD",
        "go_live": "HOLD",
        "orange_badge": report["orange_badge"],
        "go_live_clear": False,
        "production_publish_allowed": False,
        "gary_yes_required": True,
        "triple_pass_publishes": False,
        "system_alive": False,
        "live_trading": False,
        "orders_placed": False,
        "published": False,
        "draft": True,
        "prerelease": True,
        "stranger_commands": report["stranger_commands"],
        "receipts": report["receipts"],
        "archives": archives,
    }
    if manifest["system_alive"] is not False or manifest["orders_placed"] is not False:
        raise ValueError("refusing a manifest that claims alive or an order")
    if manifest["go_live"] != "HOLD" or manifest["go_live_clear"] is not False:
        raise ValueError("refusing a manifest that clears go-live")
    manifest_path = dest / "release-channel.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    rows = list(archives)
    rows.append(
        {
            "name": manifest_path.name,
            "sha256": _sha256(manifest_path),
            "bytes": manifest_path.stat().st_size,
        }
    )
    _write_sums(dest, rows)
    manifest["checksum_file"] = "SHA256SUMS"
    return manifest


def _print(report: dict) -> None:
    json.dump(report, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Aureon public source-archive channel")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check", help="Read receipts. Exit 0 when the notes match a refused production publish.")
    archive_parser = sub.add_parser("archive", help="Write source archives, checksums, and the channel manifest.")
    archive_parser.add_argument("--dest", type=Path, required=True)
    archive_parser.add_argument("--tag", default=None)
    tag_parser = sub.add_parser("accept-tag", help="Exit 0 when the tag is tip- plus a prefix of HEAD.")
    tag_parser.add_argument("tag")
    sub.add_parser(
        "publish",
        help="Always refuse. Go-live stays HOLD until Gary's own yes. Never calls GitHub.",
    )
    args = parser.parse_args(argv)
    root = repo_root()
    if args.command == "check":
        report = evaluate(root)
        _print(report)
        return 1 if report["problems"] else 0
    if args.command == "archive":
        try:
            manifest = archive(root, args.dest, args.tag)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        _print(
            {
                "wrote": str(args.dest),
                "go_live_clear": manifest["go_live_clear"],
                "system_alive": manifest["system_alive"],
                "published": manifest["published"],
                "archives": [item["name"] for item in manifest["archives"]],
            }
        )
        return 0
    if args.command == "accept-tag":
        try:
            accept_tag(args.tag, git_head(root))
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(args.tag)
        return 0
    report = evaluate(root)
    if report["problems"]:
        _print({"problems": report["problems"], "published": False, "go_live": "HOLD"})
        return 1
    _print(
        {
            "published": False,
            "go_live": "HOLD",
            "go_live_clear": False,
            "production_publish_allowed": False,
            "gary_yes_required": True,
            "triple_pass_publishes": False,
            "receipts_verified_on_head": report["receipts_verified_on_head"],
            "reason": (
                "Go-live stays HOLD. Publish waits for Gary's own yes. "
                "Charlie, Buzz, and Spike PASS do not publish. "
                "This command does not create a release or a tag."
            ),
        }
    )
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
