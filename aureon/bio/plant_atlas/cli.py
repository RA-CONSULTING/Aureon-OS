"""Command-line interface for AGPHA staging, validation, and shard execution."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

from .harmonics import protein_sequence_signature
from .models import inventory_summary, load_species_shard
from .sharding import (
    build_run_manifest,
    load_run_manifest,
    taxon_input_relpath,
    write_run_manifest,
)
from .source_registry import source_registry_payload
from .source_snapshot import load_source_snapshot, sha256_file, verify_source_snapshot
from .worker import run_manifest_shard


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _read_fasta(path: Path) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    sequence = "".join(line.strip() for line in lines if line.strip() and not line.startswith(">"))
    if not sequence:
        raise ValueError(f"FASTA contains no sequence: {path}")
    return sequence


def _read_taxon_keys(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    stripped = text.lstrip()
    if stripped.startswith("["):
        payload = json.loads(text)
        if not isinstance(payload, list):
            raise ValueError("taxa JSON must contain a list")
        return [str(item).strip() for item in payload if str(item).strip()]
    return [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]


def _iter_json_files(paths: Iterable[str]) -> Iterable[Path]:
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            yield from sorted(path.rglob("*.json"))
        else:
            yield path


def _cmd_validate(args: argparse.Namespace) -> int:
    failed = 0
    for path in _iter_json_files(args.paths):
        try:
            shard = load_species_shard(path)
            print(f"PASS {path} {shard.content_sha256()}")
        except Exception as exc:
            failed += 1
            print(f"FAIL {path}: {exc}", file=sys.stderr)
    return 1 if failed else 0


def _cmd_inventory(args: argparse.Namespace) -> int:
    shards = [load_species_shard(path) for path in _iter_json_files(args.paths)]
    print(json.dumps(inventory_summary(shards), indent=2, ensure_ascii=False))
    return 0


def _cmd_sequence(args: argparse.Namespace) -> int:
    sequence = _read_fasta(Path(args.fasta))
    mapping = protein_sequence_signature(
        args.subject_id,
        sequence,
        top_modes_per_channel=args.top_modes,
        max_dft_modes=args.max_modes,
    )
    payload = _jsonable(asdict(mapping))
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


def _cmd_manifest(args: argparse.Namespace) -> int:
    keys = _read_taxon_keys(Path(args.taxa))
    input_checksums: dict[str, str] | None = None
    if not args.allow_unverified_inputs:
        source_root = Path(args.source_root)
        input_checksums = {}
        missing: list[str] = []
        for key in keys:
            path = source_root / taxon_input_relpath(key)
            if not path.is_file():
                missing.append(str(path))
            else:
                input_checksums[key] = sha256_file(path)
        if missing:
            raise ValueError(
                "input bundle(s) missing; stage them before creating a strict manifest: "
                + ", ".join(missing[:10])
            )
    manifest = build_run_manifest(
        keys,
        run_id=args.run_id,
        snapshot_id=args.snapshot_id,
        created_at=args.created_at,
        source_snapshot_root=args.source_root,
        output_root=args.output_root,
        shard_count=args.shards,
        input_checksums=input_checksums,
        require_source_checksums=not args.allow_unverified_inputs,
    )
    write_run_manifest(manifest, args.output)
    print(json.dumps({
        "manifest": str(args.output),
        "sha256": manifest.content_sha256(),
        "taxa": sum(len(shard.items) for shard in manifest.shards),
        "shards": manifest.shard_count,
    }, indent=2))
    return 0


def _cmd_run_shard(args: argparse.Namespace) -> int:
    manifest = load_run_manifest(args.manifest)
    receipt = run_manifest_shard(
        manifest,
        args.shard_index,
        source_snapshot_root=args.source_root,
        output_root=args.output_root,
    )
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return 1 if receipt["failed"] else 0


def _cmd_sources(_args: argparse.Namespace) -> int:
    print(json.dumps(source_registry_payload(), indent=2, ensure_ascii=False))
    return 0


def _cmd_verify_snapshot(args: argparse.Namespace) -> int:
    snapshot = load_source_snapshot(args.manifest)
    report = verify_source_snapshot(snapshot, args.root)
    print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    return 0 if report.passed else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m aureon.bio.plant_atlas",
        description="Aureon Global Plant Harmonic Atlas — evidence-first species shards",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate-shard", help="validate one or more species-shard JSON files")
    validate.add_argument("paths", nargs="+")
    validate.set_defaults(func=_cmd_validate)

    inventory = subparsers.add_parser("inventory", help="summarise a directory of species shards")
    inventory.add_argument("paths", nargs="+")
    inventory.set_defaults(func=_cmd_inventory)

    sequence = subparsers.add_parser("sequence-signature", help="derive a non-physical protein sequence signature")
    sequence.add_argument("--subject-id", required=True)
    sequence.add_argument("--fasta", required=True)
    sequence.add_argument("--output")
    sequence.add_argument("--top-modes", type=int, default=4)
    sequence.add_argument("--max-modes", type=int, default=64)
    sequence.set_defaults(func=_cmd_sequence)

    manifest = subparsers.add_parser("make-manifest", help="create a deterministic Eigenbot/Isambard run manifest")
    manifest.add_argument("--taxa", required=True, help="newline-delimited keys or JSON list")
    manifest.add_argument("--run-id", required=True)
    manifest.add_argument("--snapshot-id", required=True)
    manifest.add_argument("--created-at", required=True, help="UTC ISO-8601 timestamp")
    manifest.add_argument("--source-root", required=True)
    manifest.add_argument("--output-root", required=True)
    manifest.add_argument("--shards", required=True, type=int)
    manifest.add_argument("--output", required=True)
    manifest.add_argument(
        "--allow-unverified-inputs",
        action="store_true",
        help="development-only: omit input bundle checksums from the manifest",
    )
    manifest.set_defaults(func=_cmd_manifest)

    run_shard = subparsers.add_parser("run-shard", help="execute one offline manifest shard")
    run_shard.add_argument("--manifest", required=True)
    run_shard.add_argument("--shard-index", required=True, type=int)
    run_shard.add_argument("--source-root")
    run_shard.add_argument("--output-root")
    run_shard.set_defaults(func=_cmd_run_shard)

    sources = subparsers.add_parser("sources", help="print the acquisition source registry")
    sources.set_defaults(func=_cmd_sources)

    verify_snapshot = subparsers.add_parser(
        "verify-snapshot",
        help="verify every byte declared by an immutable source snapshot manifest",
    )
    verify_snapshot.add_argument("--manifest", required=True)
    verify_snapshot.add_argument("--root", required=True)
    verify_snapshot.set_defaults(func=_cmd_verify_snapshot)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
