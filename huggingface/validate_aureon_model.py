#!/usr/bin/env python3
"""Validate the real Aureon checkpoint directly and through its chat server.

This is an acceptance validator, not a training entry point.  It requires one
CUDA GPU, local Hugging Face files, deterministic direct generation, and two
real loopback HTTP completions from training/aureon_chat_server.py.  A single
structured JSON receipt is written for both successful and failed runs.
"""

from __future__ import annotations

import argparse
import copy
import gc
import hashlib
import json
import multiprocessing
import os
import platform
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Mapping, Sequence

SOURCE_EXPORT = Path("/projects/u6vs/hnc-organism/runs/aureon-7b-sft-label-fix/hf")
OVERLAY = Path("/projects/u6vs/aureon-hf-release/model-overlay")
RELEASE_ROOT = Path("/projects/u6vs/aureon-hf-release")
CONSOLIDATED_SOURCE = RELEASE_ROOT / "source"
COMBINED_MODEL = RELEASE_ROOT / "combined-model"
EXPECTED_WEIGHT_SHA256 = "48487f800623474ab99371d71b369694cae64f8ebc4ef038019c7e60da3d45bb"
EXPECTED_WEIGHT_SIZE = 13_990_806_664
EXPECTED_PARAMETERS = 6_995_383_808
EXPECTED_VOCAB_SIZE = 65_536
EXPECTED_EOS_ID = 1
EXPECTED_BOS_ID = 1
MODEL_NAME = "aureon-7b-v65k"
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 11435
REQUIRED_HNC_GEARS = ("parse", "field", "auris", "qgita")
FIXED_PROMPT = (
    "Write a small Python function normalize_path(path) that returns a POSIX "
    "path without '.' segments. Return only executable code."
)
ROUND_TRIP_SAMPLES = (
    "def greet(name: str) -> str:\n    return f\"Hello, {name}!\"\n",
    "Unicode: Λ(t) = λ₀ + sin(φ²); 谐波; déjà vu; 🚀\n",
    "mixed code: if α >= 0.5:\n    print('ζ', '🌀')\n",
)
LINEAGE = {
    "base_checkpoint": "runs/aureon-7b-v65k/pinned/ckpt_0017000.pt",
    "base_source_step": 17000,
    "sft_job_id": "8602598",
    "export_job_id": "8602600",
    "evaluation_job_id": "8602611",
    "previous_chat_job_id": "8602613",
    "previous_chat_binding_failure": "login43",
    "validated_loopback_address": SERVER_HOST,
}


class ValidationError(RuntimeError):
    """A required production validation check failed."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot read JSON receipt {path}: {exc}") from exc
    require(isinstance(value, dict), f"expected a JSON object in {path}")
    return value


def sha256_file(path: Path) -> tuple[str, int]:
    """Independently stream a file digest and size without loading it in memory."""

    digest = hashlib.sha256()
    size = 0
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
                digest.update(chunk)
                size += len(chunk)
    except OSError as exc:
        raise ValidationError(f"cannot hash {path}: {exc}") from exc
    return digest.hexdigest(), size


def _expected_receipt_hash(receipt: Mapping[str, Any]) -> str:
    try:
        value = receipt["source_hashes"]["model.safetensors"]
    except (KeyError, TypeError) as exc:
        raise ValidationError(
            "preparation_receipt.json lacks source_hashes.model.safetensors"
        ) from exc
    if isinstance(value, dict):
        value = value.get("sha256")
    require(isinstance(value, str) and len(value) == 64, "invalid preparation weight hash")
    return value.lower()


def verify_weights(
    model_directory: Path,
    source_directory: Path,
    overlay_directory: Path,
    *,
    expected_sha256: str = EXPECTED_WEIGHT_SHA256,
    expected_size: int = EXPECTED_WEIGHT_SIZE,
) -> dict[str, Any]:
    """Compare an independent weight hash with both preparation and handoff."""

    model_directory = Path(model_directory)
    source_directory = Path(source_directory)
    overlay_directory = Path(overlay_directory)
    weight_path = model_directory / "model.safetensors"
    source_weight = source_directory / "model.safetensors"
    receipt_path = model_directory / "preparation_receipt.json"
    overlay_receipt_path = overlay_directory / "preparation_receipt.json"

    require(weight_path.is_file(), f"missing combined weight: {weight_path}")
    require(source_weight.is_file(), f"missing source weight: {source_weight}")
    try:
        same_file = os.path.samefile(weight_path, source_weight)
    except OSError as exc:
        raise ValidationError(f"cannot compare combined/source weights: {exc}") from exc
    require(same_file, "combined model.safetensors is not the real source weight")

    receipt_bytes = receipt_path.read_bytes()
    overlay_receipt_bytes = overlay_receipt_path.read_bytes()
    require(
        receipt_bytes == overlay_receipt_bytes,
        "combined preparation receipt differs from the metadata overlay receipt",
    )
    preparation_receipt = _load_json(receipt_path)
    receipt_hash = _expected_receipt_hash(preparation_receipt)
    require(
        receipt_hash == expected_sha256.lower(),
        f"preparation weight hash {receipt_hash} differs from the known real hash",
    )

    actual_hash, actual_size = sha256_file(weight_path)
    require(actual_size == expected_size, f"weight size {actual_size} != {expected_size}")
    require(
        actual_hash == receipt_hash,
        f"independent weight hash {actual_hash} != preparation hash {receipt_hash}",
    )
    return {
        "algorithm": "sha256",
        "weight_path": str(weight_path),
        "source_weight_path": str(source_weight),
        "preparation_receipt_path": str(receipt_path),
        "preparation_receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest(),
        "expected_preparation_hash": receipt_hash,
        "expected_handoff_hash": expected_sha256.lower(),
        "actual_hash": actual_hash,
        "expected_size": expected_size,
        "actual_size": actual_size,
        "hash_matches": True,
        "size_matches": True,
        "same_file_as_source": True,
    }


def _memory_stats(torch: Any) -> dict[str, int]:
    return {
        "allocated_bytes": int(torch.cuda.memory_allocated()),
        "reserved_bytes": int(torch.cuda.memory_reserved()),
        "peak_allocated_bytes": int(torch.cuda.max_memory_allocated()),
        "peak_reserved_bytes": int(torch.cuda.max_memory_reserved()),
    }


def run_direct_validation(
    model_directory: Path,
    *,
    max_new_tokens: int = 64,
    torch_module: Any = None,
    transformers_module: Any = None,
    direct_record: dict[str, Any] | None = None,
    require_zero_allocation: bool = True,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load the local model on CUDA and run all direct acceptance checks.

    ``require_zero_allocation=False`` is reserved for the spawned worker below.
    Its parent still requires worker termination and zero parent-side CUDA
    allocation before the HTTP server starts.
    """

    if torch_module is None or transformers_module is None:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        torch_module = torch
        transformers_module = type(
            "TransformersLoader", (), {
                "AutoModelForCausalLM": AutoModelForCausalLM,
                "AutoTokenizer": AutoTokenizer,
                "__version__": __import__("transformers").__version__,
            }
        )
    torch = torch_module
    loaders = transformers_module
    require(torch.cuda.is_available(), "CUDA is required; CPU fallback is not accepted")
    require(max_new_tokens > 0, "max_new_tokens must be positive")

    record = direct_record if direct_record is not None else {}
    record.update(
        {
            "model_path": str(Path(model_directory)),
            "local_files_only": True,
            "prompt": FIXED_PROMPT,
            "max_new_tokens": max_new_tokens,
            "round_trips": [],
            "generations": [],
            "deterministic": False,
            "model_released_before_server": False,
        }
    )
    versions = {
        "python": platform.python_version(),
        "torch": str(getattr(torch, "__version__", "unknown")),
        "transformers": str(getattr(loaders, "__version__", "unknown")),
        "cuda": str(getattr(getattr(torch, "version", None), "cuda", None)),
        "gpu": str(torch.cuda.get_device_name(0)),
    }
    cleanup: dict[str, Any] = {
        "generation_scope_exited": False,
        "gc_collected": None,
        "cuda_cache_emptied": False,
        "cuda_synchronized": False,
        "errors": [],
    }
    record["cleanup"] = cleanup
    started = time.perf_counter()

    def load_and_generate() -> None:
        # Keep every CUDA-owning temporary in this scope. In particular, model
        # parameters, encoded inputs, generate outputs, and generator frames
        # must all be unreachable before the outer cleanup checks the allocator.
        torch.cuda.reset_peak_memory_stats()
        record["memory_before_load"] = _memory_stats(torch)
        load_started = time.perf_counter()
        tokenizer = loaders.AutoTokenizer.from_pretrained(
            str(model_directory), local_files_only=True
        )
        model = loaders.AutoModelForCausalLM.from_pretrained(
            str(model_directory),
            dtype=torch.bfloat16,
            attn_implementation="sdpa",
            local_files_only=True,
        ).to("cuda").eval()
        torch.cuda.synchronize()
        record["load_seconds"] = time.perf_counter() - load_started
        record["memory_after_load"] = _memory_stats(torch)

        parameters = sum(int(parameter.numel()) for parameter in model.parameters())
        require(parameters == EXPECTED_PARAMETERS, f"parameter count {parameters} != {EXPECTED_PARAMETERS}")
        require(int(model.config.vocab_size) == EXPECTED_VOCAB_SIZE, "model vocabulary mismatch")
        require(len(tokenizer) == EXPECTED_VOCAB_SIZE, "tokenizer vocabulary mismatch")
        require(tokenizer.eos_token == "<eos>", "tokenizer EOS token is not <eos>")
        require(tokenizer.bos_token == "<eos>", "tokenizer BOS token is not <eos>")
        eos_id = tokenizer.convert_tokens_to_ids(tokenizer.eos_token)
        bos_id = tokenizer.convert_tokens_to_ids(tokenizer.bos_token)
        require(eos_id == EXPECTED_EOS_ID, f"tokenizer EOS ID {eos_id} != 1")
        require(bos_id == EXPECTED_BOS_ID, f"tokenizer BOS ID {bos_id} != 1")
        require(model.config.eos_token_id == EXPECTED_EOS_ID, "model config EOS ID mismatch")
        require(model.config.bos_token_id == EXPECTED_BOS_ID, "model config BOS ID mismatch")
        require(model.generation_config.eos_token_id == EXPECTED_EOS_ID, "generation EOS ID mismatch")
        require(model.generation_config.bos_token_id == EXPECTED_BOS_ID, "generation BOS ID mismatch")

        parameter_list = list(model.parameters())
        require(parameter_list, "model exposes no parameters")
        require(
            all(parameter.dtype == torch.bfloat16 for parameter in parameter_list),
            "not every model parameter is bf16",
        )
        require(
            all(getattr(parameter.device, "type", None) == "cuda" for parameter in parameter_list),
            "not every model parameter is on CUDA",
        )
        record.update(
            parameter_count=parameters,
            vocab_size=int(model.config.vocab_size),
            eos_token_id=eos_id,
            bos_token_id=bos_id,
            dtype="bf16",
            device="cuda",
        )

        for sample in ROUND_TRIP_SAMPLES:
            token_ids = list(tokenizer.encode(sample, add_special_tokens=False))
            decoded = tokenizer.decode(token_ids, skip_special_tokens=False)
            require(decoded == sample, f"tokenizer round trip changed text: {sample!r}")
            record["round_trips"].append(
                {"input": sample, "token_ids": token_ids, "decoded": decoded, "exact": True}
            )

        encoded = tokenizer(FIXED_PROMPT, return_tensors="pt")
        input_ids = encoded["input_ids"].to("cuda")
        attention_mask = encoded["attention_mask"].to("cuda")
        for run_index in range(2):
            torch.cuda.synchronize()
            torch.cuda.reset_peak_memory_stats()
            generation_started = time.perf_counter()
            with torch.inference_mode():
                output = model.generate(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    max_new_tokens=max_new_tokens,
                    do_sample=False,
                    eos_token_id=EXPECTED_EOS_ID,
                    pad_token_id=EXPECTED_EOS_ID,
                )
            torch.cuda.synchronize()
            elapsed = time.perf_counter() - generation_started
            generated_ids = output[0, input_ids.shape[1]:].detach().cpu().tolist()
            require(generated_ids, "greedy generation returned no tokens")
            text = tokenizer.decode(generated_ids, skip_special_tokens=False)
            record["generations"].append(
                {
                    "run": run_index + 1,
                    "token_ids": generated_ids,
                    "text": text,
                    "seconds": elapsed,
                    "memory": _memory_stats(torch),
                }
            )

        first, second = record["generations"]
        require(first["token_ids"] == second["token_ids"], "direct greedy token IDs differ")
        require(first["text"] == second["text"], "direct greedy text differs")
        record["deterministic"] = True
        record["total_seconds_before_release"] = time.perf_counter() - started

    try:
        load_and_generate()
        cleanup["generation_scope_exited"] = True
    finally:
        # Cleanup is diagnostic and best-effort so it cannot replace an
        # exception from loading, generation, or deterministic comparison.
        cleanup_started = time.perf_counter()
        try:
            cleanup["gc_collected"] = gc.collect()
        except Exception as exc:  # noqa: BLE001 - preserve the validation error
            cleanup["errors"].append(
                {"step": "gc.collect", "type": type(exc).__name__, "message": str(exc)}
            )
        try:
            torch.cuda.empty_cache()
            cleanup["cuda_cache_emptied"] = True
        except Exception as exc:  # noqa: BLE001 - preserve the validation error
            cleanup["errors"].append(
                {"step": "cuda.empty_cache", "type": type(exc).__name__, "message": str(exc)}
            )
        try:
            torch.cuda.synchronize()
            cleanup["cuda_synchronized"] = True
        except Exception as exc:  # noqa: BLE001 - preserve the validation error
            cleanup["errors"].append(
                {"step": "cuda.synchronize", "type": type(exc).__name__, "message": str(exc)}
            )
        try:
            record["memory_after_release"] = _memory_stats(torch)
        except Exception as exc:  # noqa: BLE001 - preserve the validation error
            cleanup["errors"].append(
                {"step": "memory_stats", "type": type(exc).__name__, "message": str(exc)}
            )
        cleanup["seconds"] = time.perf_counter() - cleanup_started
        record["total_seconds_after_release"] = time.perf_counter() - started

    require(
        not cleanup["errors"],
        "CUDA cleanup failed: " + "; ".join(
            f"{error['step']}: {error['message']}" for error in cleanup["errors"]
        ),
    )
    memory_after_release = record["memory_after_release"]
    if require_zero_allocation:
        require(
            memory_after_release["allocated_bytes"] == 0,
            "CUDA allocations remain after releasing the direct-validation model: "
            f"allocated_bytes={memory_after_release['allocated_bytes']}, "
            f"reserved_bytes={memory_after_release['reserved_bytes']}, "
            f"gc_collected={cleanup['gc_collected']}",
        )
        record["model_released_before_server"] = True
    else:
        record["zero_allocation_deferred_to_process_exit"] = True
    return record, versions


def _direct_validation_worker(
    model_directory: Path,
    *,
    max_new_tokens: int,
    result_path: Path,
) -> None:
    """Run direct checks in a disposable process and preserve partial results."""

    direct: dict[str, Any] = {}
    payload: dict[str, Any] = {"direct": direct, "versions": {}, "error": None}
    try:
        direct_result, versions = run_direct_validation(
            model_directory,
            max_new_tokens=max_new_tokens,
            direct_record=direct,
            require_zero_allocation=False,
        )
        payload["versions"] = versions
        require(direct_result["deterministic"], "direct worker was not deterministic")
    except Exception as exc:  # noqa: BLE001 - the parent turns this into a failed receipt
        payload["error"] = {"type": type(exc).__name__, "message": str(exc)}
    write_receipt(result_path, payload)


def _read_worker_result(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot read direct-worker result: {exc}") from exc
    require(isinstance(value, dict), "direct-worker result is not an object")
    require(isinstance(value.get("direct"), dict), "direct-worker result lacks direct evidence")
    require(isinstance(value.get("versions"), dict), "direct-worker result lacks versions")
    return value


def run_direct_validation_isolated(
    model_directory: Path,
    *,
    max_new_tokens: int = 64,
    timeout: float = 900.0,
    direct_record: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Release all direct CUDA state through a joined subprocess before HTTP."""

    require(timeout > 0, "direct-worker timeout must be positive")
    record = direct_record if direct_record is not None else {}
    with tempfile.TemporaryDirectory(prefix="aureon-direct-validation-") as temporary:
        result_path = Path(temporary) / "result.json"
        process = multiprocessing.get_context("spawn").Process(
            target=_direct_validation_worker,
            args=(Path(model_directory),),
            kwargs={"max_new_tokens": max_new_tokens, "result_path": result_path},
            name="aureon-direct-validation",
        )
        process.start()
        try:
            process.join(timeout)
            if process.exitcode is None:
                process.terminate()
                process.join(30)
                if process.exitcode is None:
                    process.kill()
                    process.join(30)
                raise ValidationError(f"direct CUDA worker exceeded {timeout}s and was terminated")
        finally:
            if process.exitcode is None:
                process.kill()
                process.join(30)
            exit_code = process.exitcode
            process.close()
        result = _read_worker_result(result_path)
        record.update(result["direct"])
        require(exit_code == 0, f"direct CUDA worker exited with {exit_code}")
        if result.get("error"):
            error = result["error"]
            raise ValidationError(
                f"direct CUDA worker failed: {error.get('type')}: {error.get('message')}"
            )

    record["worker_process"] = {"started": True, "joined": True, "exit_code": 0}
    record["worker_memory_before_exit"] = copy.deepcopy(record.get("memory_after_release"))
    # Importing Torch here does not load a model or initialize a CUDA context.
    # The direct worker has exited, so the parent must own no CUDA allocation.
    import torch

    parent_memory = _memory_stats(torch)
    record["parent_memory_before_server"] = parent_memory
    require(
        parent_memory["allocated_bytes"] == 0,
        "validator parent owns CUDA memory after the direct worker exited: "
        f"allocated_bytes={parent_memory['allocated_bytes']}",
    )
    record["memory_after_release"] = parent_memory
    record["release_mechanism"] = "spawned_worker_exit"
    record["model_released_before_server"] = True
    return record, result["versions"]


def http_json(
    method: str,
    url: str,
    *,
    payload: Mapping[str, Any] | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            status = response.status
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise ValidationError(f"HTTP {exc.code} from {url}: {body[:1000]}") from exc
    except (urllib.error.URLError, TimeoutError, OSError):
        raise
    require(status == 200, f"HTTP {status} from {url}")
    try:
        value = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"non-JSON response from {url}: {body[:1000]}") from exc
    require(isinstance(value, dict), f"non-object JSON response from {url}")
    return value


def _server_log_tail(log_path: Path) -> str:
    try:
        return log_path.read_text(encoding="utf-8", errors="replace")[-4000:]
    except OSError:
        return ""


def wait_for_models(
    process: Any,
    base_url: str,
    *,
    timeout: float,
    log_path: Path,
    poll_interval: float = 2.0,
) -> dict[str, Any]:
    """Poll /v1/models while detecting an exited server immediately."""

    deadline = time.monotonic() + timeout
    last_error = "not attempted"
    while time.monotonic() < deadline:
        return_code = process.poll()
        if return_code is not None:
            tail = _server_log_tail(log_path)
            raise ValidationError(
                f"chat server exited with {return_code} before readiness; log tail: {tail}"
            )
        try:
            models = http_json("GET", base_url + "/v1/models", timeout=2.0)
            identifiers = [
                item.get("id") for item in models.get("data", []) if isinstance(item, dict)
            ]
            require(MODEL_NAME in identifiers, f"/v1/models omitted {MODEL_NAME}: {identifiers}")
            require(process.poll() is None, "chat server exited immediately after readiness")
            return models
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            time.sleep(poll_interval)
    raise ValidationError(
        f"chat server did not become ready within {timeout}s; last error: {last_error}; "
        f"log tail: {_server_log_tail(log_path)}"
    )


def verify_snapshot_reuse(response: Mapping[str, Any]) -> dict[str, Any]:
    """Verify exposed pre-inference state identities against the HNC receipt.

    Current servers need not expose the snapshot.  When they do, stable field
    and gear receipt identities must match; post-inference Auris vote fields are
    deliberately excluded from this comparison.
    """

    hnc = response.get("hnc_gears")
    require(isinstance(hnc, dict), "missing HNC receipt")
    snapshot = None
    for container in (hnc, response):
        for key in (
            "pre_inference_organism_snapshot",
            "pre_inference_organism",
            "organism_snapshot",
        ):
            if key in container:
                snapshot = container[key]
                break
        if snapshot is not None:
            break
    if snapshot is None:
        return {"exposed": False, "verified": None, "compared_fields": []}
    require(isinstance(snapshot, dict), "exposed organism snapshot is not an object")

    actual_gears = {
        gear.get("name"): gear for gear in hnc.get("gears", []) if isinstance(gear, dict)
    }
    expected_gears = {
        gear.get("name"): gear
        for gear in snapshot.get("gears", [])
        if isinstance(gear, dict)
    }
    stable_keys = (
        "receipt_id",
        "memory_receipt_id",
        "canonical_hash",
        "field_receipt_id",
        "freshness_status",
        "source_timestamp",
        "step",
        "coherence",
        "coherence_gamma",
        "lambda_t",
        "available",
        "grounded_inputs",
    )
    compared: list[str] = []
    for name, expected in expected_gears.items():
        if name == "parse":
            continue
        require(name in actual_gears, f"snapshot gear {name} missing from HNC receipt")
        actual = actual_gears[name]
        for key in stable_keys:
            if key in expected:
                require(
                    actual.get(key) == expected[key],
                    f"post-inference {name}.{key} does not reuse the pre-inference snapshot",
                )
                compared.append(f"{name}.{key}")
    require(compared, "exposed organism snapshot contains no verifiable stable identity")
    return {"exposed": True, "verified": True, "compared_fields": compared}


def hnc_status(response: Mapping[str, Any]) -> dict[str, Any]:
    hnc = response.get("hnc_gears")
    require(isinstance(hnc, dict), "chat response lacks hnc_gears")
    gears = hnc.get("gears")
    require(isinstance(gears, list), "hnc_gears.gears is not an array")
    names = [gear.get("name") for gear in gears if isinstance(gear, dict)]
    for required_name in REQUIRED_HNC_GEARS:
        require(names.count(required_name) == 1, f"HNC receipt requires one {required_name} gear")

    blockers = []
    engagement = {}
    for gear in gears:
        if not isinstance(gear, dict):
            continue
        name = str(gear.get("name"))
        engagement[name] = {
            "turned": bool(gear.get("turned", False)),
            "engaged": bool(gear.get("engaged", False)),
        }
        for key in ("blocker", "error"):
            if gear.get(key):
                blockers.append({"gear": name, "kind": key, "detail": str(gear[key])})
    return {
        "all_turned": bool(hnc.get("all_turned", False)),
        "parsed": bool(hnc.get("parsed", False)),
        "required_gears_present": True,
        "engagement": engagement,
        "blockers": blockers,
        "snapshot_reuse": verify_snapshot_reuse(response),
    }


def terminate_server(process: Any) -> dict[str, Any]:
    """Terminate, then kill if necessary, and always wait for the child."""

    if process is None:
        return {"started": False}
    result: dict[str, Any] = {"started": True}
    if process.poll() is not None:
        result.update(action="already_exited", return_code=process.poll())
        return result
    process.terminate()
    try:
        return_code = process.wait(timeout=10)
        result.update(action="terminated", return_code=return_code)
    except subprocess.TimeoutExpired:
        process.kill()
        return_code = process.wait(timeout=10)
        result.update(action="killed", return_code=return_code)
    return result


def run_http_validation(
    model_directory: Path,
    source_tree: Path,
    receipt_path: Path,
    *,
    startup_timeout: float = 900.0,
    request_timeout: float = 600.0,
    max_new_tokens: int = 64,
    port: int = SERVER_PORT,
    http_record: dict[str, Any] | None = None,
    hnc_record: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Start the real chat server, exercise it twice, and always terminate it."""

    model_directory = Path(model_directory)
    source_tree = Path(source_tree)
    receipt_path = Path(receipt_path)
    server_script = source_tree / "training" / "aureon_chat_server.py"
    require(server_script.is_file(), f"missing consolidated chat server: {server_script}")
    base_url = f"http://{SERVER_HOST}:{port}"
    log_path = receipt_path.parent / f"aureon-chat-server-{os.environ.get('SLURM_JOB_ID', 'local')}.log"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-u",
        str(server_script),
        "--model",
        str(model_directory),
        "--model-name",
        MODEL_NAME,
        "--host",
        SERVER_HOST,
        "--port",
        str(port),
    ]
    environment = os.environ.copy()
    environment.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", PYTHONNOUSERSITE="1")
    python_paths = [str(source_tree), str(source_tree / "training")]
    if environment.get("PYTHONPATH"):
        python_paths.append(environment["PYTHONPATH"])
    environment["PYTHONPATH"] = os.pathsep.join(python_paths)

    http = http_record if http_record is not None else {}
    hnc = hnc_record if hnc_record is not None else {}
    http.update(base_url=base_url, command=command, server_log=str(log_path), responses=[])
    hnc.update(required_gears=list(REQUIRED_HNC_GEARS), responses=[])
    process = None
    started = time.perf_counter()
    try:
        with log_path.open("w", encoding="utf-8") as log_handle:
            process = subprocess.Popen(
                command,
                cwd=str(source_tree),
                env=environment,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
            )
            readiness_started = time.perf_counter()
            http["models"] = wait_for_models(
                process,
                base_url,
                timeout=startup_timeout,
                log_path=log_path,
            )
            http["startup_seconds"] = time.perf_counter() - readiness_started

            payload = {
                "model": MODEL_NAME,
                "messages": [
                    {"role": "system", "content": "You are Aureon. Follow the user's format exactly."},
                    {"role": "user", "content": FIXED_PROMPT},
                ],
                "max_tokens": max_new_tokens,
                "temperature": 0.0,
            }
            http["request"] = payload
            for run_index in range(2):
                request_started = time.perf_counter()
                response = http_json(
                    "POST",
                    base_url + "/v1/chat/completions",
                    payload=payload,
                    timeout=request_timeout,
                )
                elapsed = time.perf_counter() - request_started
                require(process.poll() is None, "chat server exited during completion")
                require(response.get("model") == MODEL_NAME, "HTTP response model mismatch")
                try:
                    content = response["choices"][0]["message"]["content"]
                except (KeyError, IndexError, TypeError) as exc:
                    raise ValidationError("HTTP response lacks assistant content") from exc
                require(isinstance(content, str), "assistant content is not text")
                http["responses"].append(
                    {"run": run_index + 1, "seconds": elapsed, "response": copy.deepcopy(response)}
                )
                hnc["responses"].append(
                    {"run": run_index + 1, **hnc_status(response)}
                )

            first_content = http["responses"][0]["response"]["choices"][0]["message"]["content"]
            second_content = http["responses"][1]["response"]["choices"][0]["message"]["content"]
            require(first_content == second_content, "temperature-0 HTTP content differs")
            http["deterministic"] = True
            http["model"] = MODEL_NAME
            hnc["all_required_receipts_present"] = True
            http["total_seconds"] = time.perf_counter() - started
    finally:
        termination = terminate_server(process)
        http["server_termination"] = termination
        http["elapsed_before_return_seconds"] = time.perf_counter() - started
    return http, hnc


def _new_receipt(arguments: argparse.Namespace) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "success": False,
        "status": "running",
        "job_id": os.environ.get("SLURM_JOB_ID", "local"),
        "source_revision": arguments.source_revision,
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "paths": {
            "source_export": str(arguments.source),
            "metadata_overlay": str(arguments.overlay),
            "combined_model": str(arguments.model),
            "consolidated_source": str(arguments.source_tree),
            "chat_server": str(arguments.source_tree / "training" / "aureon_chat_server.py"),
            "receipt": str(arguments.receipt),
        },
        "lineage": copy.deepcopy(LINEAGE),
        "versions": {"python": platform.python_version()},
        "requirements": {
            "weight_integrity": False,
            "direct_cuda_bf16_determinism": False,
            "http_determinism_and_hnc": False,
        },
        "errors": [],
        "timings": {},
    }


def write_receipt(path: Path, receipt: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = (json.dumps(receipt, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode(
        "utf-8"
    )
    descriptor, temporary_name = tempfile.mkstemp(prefix=".validation-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except Exception:
        try:
            Path(temporary_name).unlink()
        except OSError:
            pass
        raise


def validate(arguments: argparse.Namespace) -> dict[str, Any]:
    """Run production phases and persist one honest success/failure receipt."""

    receipt = _new_receipt(arguments)
    overall_started = time.perf_counter()
    phase = "initialization"
    phase_started = overall_started
    try:
        require(
            isinstance(arguments.source_revision, str)
            and len(arguments.source_revision) == 40
            and all(character in "0123456789abcdef" for character in arguments.source_revision),
            "a full lowercase consolidated source revision is required",
        )
        phase = "weight_integrity"
        receipt["hashes"] = verify_weights(arguments.model, arguments.source, arguments.overlay)
        receipt["requirements"]["weight_integrity"] = True
        receipt["timings"][phase] = time.perf_counter() - phase_started

        phase = "direct_cuda_bf16_determinism"
        phase_started = time.perf_counter()
        direct_record: dict[str, Any] = {}
        receipt["direct"] = direct_record
        direct, versions = run_direct_validation_isolated(
            arguments.model,
            max_new_tokens=arguments.max_new_tokens,
            timeout=arguments.startup_timeout,
            direct_record=direct_record,
        )
        receipt["versions"].update(versions)
        require(direct["model_released_before_server"], "direct model was not released")
        receipt["requirements"][phase] = True
        receipt["timings"][phase] = time.perf_counter() - phase_started

        phase = "http_determinism_and_hnc"
        phase_started = time.perf_counter()
        http_record: dict[str, Any] = {}
        hnc_record: dict[str, Any] = {}
        receipt["http"] = http_record
        receipt["hnc"] = hnc_record
        run_http_validation(
            arguments.model,
            arguments.source_tree,
            arguments.receipt,
            startup_timeout=arguments.startup_timeout,
            request_timeout=arguments.request_timeout,
            max_new_tokens=arguments.max_new_tokens,
            http_record=http_record,
            hnc_record=hnc_record,
        )
        receipt["requirements"][phase] = True
        receipt["timings"][phase] = time.perf_counter() - phase_started
        receipt["success"] = True
        receipt["status"] = "passed"
    except Exception as exc:  # noqa: BLE001 - every failure belongs in the receipt
        receipt["errors"].append(
            {"phase": phase, "type": type(exc).__name__, "message": str(exc)}
        )
        receipt["status"] = "failed"
        receipt["success"] = False
    finally:
        receipt["timings"].setdefault(phase, time.perf_counter() - phase_started)
        receipt["timings"]["total"] = time.perf_counter() - overall_started
        receipt["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        write_receipt(arguments.receipt, receipt)
    return receipt


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=COMBINED_MODEL)
    parser.add_argument("--source", type=Path, default=SOURCE_EXPORT)
    parser.add_argument("--overlay", type=Path, default=OVERLAY)
    parser.add_argument("--source-tree", type=Path, default=CONSOLIDATED_SOURCE)
    parser.add_argument(
        "--source-revision", default=os.environ.get("AUREON_SOURCE_REVISION")
    )
    parser.add_argument(
        "--receipt", type=Path, default=RELEASE_ROOT / "validation-receipt.json"
    )
    parser.add_argument("--startup-timeout", type=float, default=900.0)
    parser.add_argument("--request-timeout", type=float, default=600.0)
    parser.add_argument("--max-new-tokens", type=int, default=64)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _argument_parser().parse_args(argv)
    try:
        receipt = validate(arguments)
    except Exception as exc:  # receipt write failures are also nonzero
        print(f"validation could not write its receipt: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {"success": receipt["success"], "receipt": str(arguments.receipt)},
            sort_keys=True,
        )
    )
    return 0 if receipt["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
