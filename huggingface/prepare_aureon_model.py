#!/usr/bin/env python3
"""Prepare Aureon 7B metadata without modifying or copying the model export.

Usage:
    python prepare_aureon_model.py SOURCE_EXPORT OUTPUT_OVERLAY

The output is a metadata overlay. In particular, the required
model.safetensors is hashed for the receipt but never copied into the output
directory.
Only Python's standard library is required.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

CANONICAL_SOURCE = Path(
    "/projects/u6vs/hnc-organism/runs/aureon-7b-sft-label-fix/hf"
)
MODEL_NAME = "aureon-7b"
PARAMETER_COUNT = 6_995_383_808
EXPECTED_VOCAB_SIZE = 65_536
EXPECTED_EOS_ID = 1
EOS_TOKEN = "<eos>"
SFT_STEP = 1578
SUPERVISED_TOKENS = 62_658_432
EXPECTED_ARCHITECTURE = "Qwen2ForCausalLM"
EXPECTED_CONFIG_VALUES = {
    "num_hidden_layers": 28,
    "hidden_size": 3584,
    "max_position_embeddings": 32_768,
    "vocab_size": EXPECTED_VOCAB_SIZE,
}
EVALUATION = {
    "file": "eval-sft-label-fix.json",
    "rows": 1125,
    "parse_rate": 0.4624183006535948,
    "parse_scored": 612,
    "symbol_recall": 0.2411196294744682,
    "symbol_scored": 775,
    "line_f1": 0.035554558485818205,
    "implement_rows": 638,
    "implement_symbol_recall": 0.30049261083743845,
    "implement_line_f1": 0.016413346611668555,
    "explain_rows": 66,
    "explain_symbol_recall": 0.061392267344648296,
    "explain_line_f1": 0.19042254384675905,
}
OUTPUT_FILENAMES = (
    "config.json",
    "generation_config.json",
    "tokenizer_config.json",
    "tokenizer.json",
    "aureon_export.json",
)
RECEIPT_FILENAME = "preparation_receipt.json"


class PreparationError(RuntimeError):
    """An export or destination failed a packaging safety check."""


def _reject_duplicate_keys(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PreparationError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle, object_pairs_hook=_reject_duplicate_keys)
    except PreparationError as exc:
        raise PreparationError(f"{path}: {exc}") from exc
    except FileNotFoundError as exc:
        raise PreparationError(f"required export file is missing: {path}") from exc
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PreparationError(f"cannot read JSON object {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PreparationError(f"expected a JSON object in {path}")
    return value


def _validate_config(config: Mapping[str, Any]) -> None:
    architectures = config.get("architectures")
    if architectures != [EXPECTED_ARCHITECTURE]:
        raise PreparationError(
            "invalid export architectures: expected "
            f"[{EXPECTED_ARCHITECTURE!r}], got {architectures!r}"
        )

    if config.get("model_type", "qwen2") != "qwen2":
        raise PreparationError(
            f"invalid export model_type: expected 'qwen2', got {config.get('model_type')!r}"
        )

    for key, expected in EXPECTED_CONFIG_VALUES.items():
        value = config.get(key)
        if type(value) is not int or value != expected:
            raise PreparationError(
                f"invalid export config {key}: expected {expected}, got {value!r}"
            )

    dtype = config.get("torch_dtype")
    if dtype is None:
        dtype = config.get("dtype")
    if dtype not in {"bf16", "bfloat16"}:
        raise PreparationError(
            f"invalid export dtype: expected bf16/bfloat16, got {dtype!r}"
        )


def _validate_export_manifest(export: Mapping[str, Any]) -> None:
    expected = {
        "source_checkpoint": "sft_0001578.pt",
        "step": SFT_STEP,
        "tokens": SUPERVISED_TOKENS,
        "params": PARAMETER_COUNT,
        "vocab_size": EXPECTED_VOCAB_SIZE,
        "eos_token": EOS_TOKEN,
    }
    for key, expected_value in expected.items():
        value = export.get(key)
        if type(value) is not type(expected_value) or value != expected_value:
            raise PreparationError(
                f"invalid aureon_export.json {key}: "
                f"expected {expected_value!r}, got {value!r}"
            )


def _collect_token_ids(tokenizer: Mapping[str, Any]) -> dict[str, int]:
    model = tokenizer.get("model")
    if not isinstance(model, dict) or model.get("type") != "BPE":
        raise PreparationError("tokenizer.json must contain a BPE model")
    vocab = model.get("vocab")
    if not isinstance(vocab, dict):
        raise PreparationError("tokenizer.json model.vocab must be an object")

    token_ids: dict[str, int] = {}
    id_owners: dict[int, str] = {}

    def add_token(token: Any, token_id: Any, origin: str) -> None:
        if not isinstance(token, str) or type(token_id) is not int or token_id < 0:
            raise PreparationError(f"invalid token entry in {origin}: {token!r}")
        previous_id = token_ids.get(token)
        if previous_id is not None and previous_id != token_id:
            if token == EOS_TOKEN:
                raise PreparationError(
                    f"ambiguous EOS IDs in tokenizer.json: {previous_id} and {token_id}"
                )
            raise PreparationError(
                f"ambiguous IDs for token {token!r}: {previous_id} and {token_id}"
            )
        previous_token = id_owners.get(token_id)
        if previous_token is not None and previous_token != token:
            raise PreparationError(
                f"tokenizer vocabulary ID {token_id} is shared by "
                f"{previous_token!r} and {token!r}"
            )
        token_ids[token] = token_id
        id_owners[token_id] = token

    for token, token_id in vocab.items():
        add_token(token, token_id, "model.vocab")

    added_tokens = tokenizer.get("added_tokens", [])
    if not isinstance(added_tokens, list):
        raise PreparationError("tokenizer.json added_tokens must be an array")
    for entry in added_tokens:
        if not isinstance(entry, dict):
            raise PreparationError("tokenizer.json added_tokens entries must be objects")
        add_token(entry.get("content"), entry.get("id"), "added_tokens")

    return token_ids


def _derive_and_verify_eos(token_ids: Mapping[str, int]) -> int:
    eos_id = token_ids.get(EOS_TOKEN)
    if eos_id is None:
        raise PreparationError(f"missing {EOS_TOKEN!r} token in tokenizer.json")
    if eos_id != EXPECTED_EOS_ID:
        raise PreparationError(
            f"derived EOS ID {eos_id} does not match the verified handoff ID "
            f"{EXPECTED_EOS_ID}"
        )
    return eos_id


def _verify_vocabulary(token_ids: Mapping[str, int]) -> None:
    ids = set(token_ids.values())
    expected_ids = set(range(EXPECTED_VOCAB_SIZE))
    if len(ids) != EXPECTED_VOCAB_SIZE or ids != expected_ids:
        minimum = min(ids) if ids else None
        maximum = max(ids) if ids else None
        raise PreparationError(
            "tokenizer vocabulary mismatch: expected exactly "
            f"{EXPECTED_VOCAB_SIZE} contiguous token IDs (0..{EXPECTED_VOCAB_SIZE - 1}), "
            f"got {len(ids)} unique IDs with range {minimum}..{maximum}"
        )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise PreparationError(f"cannot hash {path}: {exc}") from exc
    return digest.hexdigest()


def _json_bytes(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    ).encode("utf-8")


def _write_atomic(path: Path, content: bytes) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    except Exception:
        try:
            temporary_path.unlink()
        except OSError:
            pass
        raise


def _paths_are_same(source: Path, output: Path) -> bool:
    if source == output:
        return True
    try:
        return os.path.samefile(source, output)
    except (FileNotFoundError, OSError):
        return False


def prepare_aureon_model(
    source_directory: os.PathLike[str] | str,
    output_directory: os.PathLike[str] | str,
) -> dict[str, Any]:
    """Validate an export and write its separate metadata overlay.

    Returns the preparation receipt.  No source file is opened for writing.
    """

    source = Path(source_directory).expanduser().resolve()
    output = Path(output_directory).expanduser().resolve()
    if _paths_are_same(source, output):
        raise PreparationError("output directory must be different from the source export")
    if output.is_relative_to(source):
        raise PreparationError("output directory must not be inside the source export")
    if not source.is_dir():
        raise PreparationError(f"source export is not a directory: {source}")

    source_config = _load_json_object(source / "config.json")
    source_tokenizer_config = _load_json_object(source / "tokenizer_config.json")
    source_tokenizer = _load_json_object(source / "tokenizer.json")
    source_export = _load_json_object(source / "aureon_export.json")
    generation_path = source / "generation_config.json"
    source_generation = (
        _load_json_object(generation_path) if generation_path.is_file() else {}
    )
    _validate_config(source_config)
    _validate_export_manifest(source_export)

    token_ids = _collect_token_ids(source_tokenizer)
    eos_id = _derive_and_verify_eos(token_ids)
    _verify_vocabulary(token_ids)

    # Honor the export's tokenizer metadata. The real candidate deliberately
    # uses <eos> for BOS and padding as well as EOS.
    configured_bos = source_tokenizer_config.get("bos_token") or EOS_TOKEN
    if not isinstance(configured_bos, str) or configured_bos not in token_ids:
        raise PreparationError(
            f"configured BOS token is missing from tokenizer.json: {configured_bos!r}"
        )
    bos_token = configured_bos
    bos_id = token_ids[bos_token]

    config = copy.deepcopy(source_config)
    config["bos_token_id"] = bos_id
    config["eos_token_id"] = eos_id

    generation_config = copy.deepcopy(source_generation)
    generation_config["bos_token_id"] = bos_id
    generation_config["eos_token_id"] = eos_id

    tokenizer_config = copy.deepcopy(source_tokenizer_config)
    tokenizer_config["bos_token"] = bos_token
    tokenizer_config["eos_token"] = EOS_TOKEN

    # Preserve the original export receipt and add canonical packaging fields.
    export_manifest = copy.deepcopy(source_export)
    export_manifest.update({
        "schema_version": 1,
        "model_name": MODEL_NAME,
        "parameters": PARAMETER_COUNT,
        "architecture": EXPECTED_ARCHITECTURE,
        "random_initialization": True,
        "training_run": "aureon-7b-sft-label-fix",
        "base_checkpoint": "runs/aureon-7b-v65k/pinned/ckpt_0017000.pt",
        "base_source_step": 17_000,
        "evidence_jobs": {"sft": "8602598", "export": "8602600", "evaluation": "8602611"},
        "sft_step": SFT_STEP,
        "supervised_tokens": SUPERVISED_TOKENS,
        "vocab_size": EXPECTED_VOCAB_SIZE,
        "num_hidden_layers": EXPECTED_CONFIG_VALUES["num_hidden_layers"],
        "hidden_size": EXPECTED_CONFIG_VALUES["hidden_size"],
        "max_position_embeddings": EXPECTED_CONFIG_VALUES[
            "max_position_embeddings"
        ],
        "dtype": "bf16",
        "tokenizer": {
            "type": "byte-level BPE",
            "eos_token": EOS_TOKEN,
            "eos_token_id": eos_id,
            "bos_token": bos_token,
            "bos_token_id": bos_id,
        },
        "source_path": str(source),
        "destination_path": str(output),
        "weights": {"filename": "model.safetensors", "copied": False},
        "evaluation": copy.deepcopy(EVALUATION),
    })

    documents = {
        "config.json": config,
        "generation_config.json": generation_config,
        "tokenizer_config.json": tokenizer_config,
        "tokenizer.json": source_tokenizer,
        "aureon_export.json": export_manifest,
    }
    encoded_documents = {name: _json_bytes(value) for name, value in documents.items()}

    weights_path = source / "model.safetensors"
    if not weights_path.is_file() or weights_path.stat().st_size == 0:
        raise PreparationError("required non-empty model.safetensors is missing")
    source_names = [
        "config.json",
        "tokenizer_config.json",
        "tokenizer.json",
        "aureon_export.json",
        "model.safetensors",
    ]
    if generation_path.is_file():
        source_names.append("generation_config.json")
    # Hash, but do not copy, the canonical single-file weights.
    source_hashes = {name: _sha256_file(source / name) for name in source_names}
    output_hashes = {
        name: hashlib.sha256(content).hexdigest()
        for name, content in encoded_documents.items()
    }

    receipt = {
        "schema_version": 1,
        "hash_algorithm": "sha256",
        "source_path": str(source),
        "destination_path": str(output),
        "derived_eos_token": EOS_TOKEN,
        "derived_eos_token_id": eos_id,
        "weights_copied": False,
        "source_hashes": source_hashes,
        "output_hashes": output_hashes,
    }

    try:
        output.mkdir(parents=True, exist_ok=True)
        for name in OUTPUT_FILENAMES:
            _write_atomic(output / name, encoded_documents[name])
        _write_atomic(output / RECEIPT_FILENAME, _json_bytes(receipt))
    except OSError as exc:
        raise PreparationError(f"cannot write metadata overlay {output}: {exc}") from exc

    return receipt


# Short alias for callers that use the tool as a library.
prepare_model = prepare_aureon_model


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate an Aureon 7B export and write a metadata-only overlay; "
            "the source and its weights are never modified or copied."
        )
    )
    parser.add_argument("source", type=Path, help="existing Hugging Face export")
    parser.add_argument("output", type=Path, help="separate metadata overlay directory")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _argument_parser()
    arguments = parser.parse_args(argv)
    try:
        receipt = prepare_aureon_model(arguments.source, arguments.output)
    except PreparationError as exc:
        parser.exit(1, f"error: {exc}\n")
    print(
        f"Prepared metadata overlay at {receipt['destination_path']} "
        f"(derived {EOS_TOKEN} ID {receipt['derived_eos_token_id']}); "
        "weights were not copied."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
