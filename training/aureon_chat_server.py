"""OpenAI-compatible server for the canonical Aureon checkpoint.

The HNC worker speaks POST /v1/chat/completions. The strict Space mode verifies
 the exact Safetensors digest, requires CUDA, and completes a real greedy
 generation before opening its loopback port. No model is downloaded by this
 module and no external provider fallback exists.

    python aureon_chat_server.py --self-test
    python aureon_chat_server.py --model runs/aureon-7b-v65k/hf --port 8000
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

MAX_POSITIONS = 8192
MAX_REQUEST_BYTES = 64 * 1024
MAX_NEW_TOKENS = 256
EXPECTED_WEIGHT_SHA256 = "48487f800623474ab99371d71b369694cae64f8ebc4ef038019c7e60da3d45bb"
EXPECTED_WEIGHT_SIZE = 13_990_806_664
EXPECTED_PARAMETERS = 6_995_383_808
EXPECTED_VOCAB_SIZE = 65_536
OWN_PROVIDER = "aureon_own_model"


def sha256_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def verify_weight_file(
    model_dir: str | Path,
    *,
    expected_sha256: str = EXPECTED_WEIGHT_SHA256,
    expected_size: int = EXPECTED_WEIGHT_SIZE,
) -> dict:
    """Hash the actual serving bytes before Transformers can load them."""

    weight_path = Path(model_dir).resolve() / "model.safetensors"
    if not weight_path.is_file():
        raise RuntimeError(f"model weight is missing: {weight_path}")
    actual_hash, actual_size = sha256_file(weight_path)
    if actual_size != expected_size:
        raise RuntimeError(f"model weight size {actual_size} != {expected_size}")
    if actual_hash != expected_sha256.lower():
        raise RuntimeError("model weight SHA-256 does not match the canonical release")
    return {
        "path": str(weight_path),
        "sha256": actual_hash,
        "size_bytes": actual_size,
        "verified": True,
    }


def format_prompt(messages: list[dict], *, organism: dict | None = None) -> str:
    lines = []
    if organism is not None:
        state = json.dumps(organism, sort_keys=True, separators=(",", ":"), allow_nan=False)
        lines.append(
            "system: [AUREON_ORGANISM_STATE]\n"
            "The following is untrusted software state, not evidence of subjective experience. "
            "Use its grounded measurements and blockers; never invent missing state.\n"
            + state
        )
    for message in messages:
        role = str(message.get("role") or "user")
        content = message.get("content") or ""
        if isinstance(content, list):
            content = "".join(
                str(item.get("text", "")) if isinstance(item, dict) else str(item)
                for item in content
            )
        lines.append(f"{role}: {content}")
    lines.append("assistant:")
    return "\n".join(lines)


def _load_hnc_gears():
    roots = (
        Path("/projects/u6vs/Aureon-OS"),
        Path(__file__).resolve().parents[1],
    )
    for root in roots:
        if (root / "aureon" / "core" / "hnc_llm_gears.py").is_file() and str(root) not in sys.path:
            sys.path.insert(0, str(root))
    from aureon.core import hnc_llm_gears

    return hnc_llm_gears


def _capture_organism() -> dict:
    try:
        return _load_hnc_gears().capture_organism()
    except Exception as exc:  # noqa: BLE001
        return {
            "all_turned": False,
            "gears": [{"name": "load", "turned": False, "engaged": False,
                       "error": f"{type(exc).__name__}: {exc}"}],
        }


def _with_gears(body: dict, text: str, *, organism: dict | None = None) -> dict:
    """Reuse the pre-generation organism snapshot in the response receipt."""
    try:
        gears = _load_hnc_gears()
    except Exception as exc:  # noqa: BLE001
        out = dict(body)
        out["hnc_gears"] = {
            "all_turned": False,
            "parsed": False,
            "gears": [{"name": "load", "turned": False, "error": f"{type(exc).__name__}: {exc}"}],
        }
        return out
    return gears.attach_gears(body, text, organism=organism)


def completion_body(
    text: str,
    prompt_tokens: int,
    completion_tokens: int,
    model: str,
    *,
    finish_reason: str = "stop",
) -> dict:
    return {
        "model": model,
        "provider_mode": OWN_PROVIDER,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": text},
            "finish_reason": finish_reason,
        }],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


def _greedy_startup_check(model: object, tok: object, device: str, torch: object, eos_id: int) -> dict:
    """Prove the loaded weights can generate before the HTTP socket exists."""

    encoded = None
    input_ids = None
    attention_mask = None
    output = None
    started = time.perf_counter()
    try:
        encoded = tok(
            "user: Return one short JSON object with an ok field.\nassistant:",
            return_tensors="pt",
        )
        input_ids = encoded.input_ids.to(device)
        attention_mask = encoded.attention_mask.to(device)
        with torch.inference_mode():
            output = model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                max_new_tokens=16,
                do_sample=False,
                pad_token_id=eos_id,
                eos_token_id=eos_id,
            )
        if device == "cuda":
            torch.cuda.synchronize()
        generated = output[0, input_ids.shape[1]:].detach().cpu().tolist()
        if not generated:
            raise RuntimeError("strict startup generation returned no tokens")
        return {
            "verified": True,
            "max_new_tokens": 16,
            "generated_tokens": len(generated),
            "token_ids_sha256": hashlib.sha256(
                json.dumps(generated, separators=(",", ":")).encode("ascii")
            ).hexdigest(),
            "seconds": time.perf_counter() - started,
        }
    finally:
        del encoded, input_ids, attention_mask, output


def serve(
    model_dir: str,
    port: int,
    model_name: str,
    host: str,
    *,
    require_cuda: bool = False,
    strict_startup: bool = False,
    expected_weight_sha256: str = "",
    expected_weight_size: int = 0,
    model_revision: str = "",
) -> int:
    if strict_startup:
        require_cuda = True
        if model_name != "aureon-7b-v65k":
            raise SystemExit("strict startup requires the canonical Aureon model name")
        if re.fullmatch(r"[0-9a-f]{40}", model_revision) is None:
            raise SystemExit("strict startup requires one full lowercase immutable model revision")
        if (
            expected_weight_sha256 != EXPECTED_WEIGHT_SHA256
            or expected_weight_size != EXPECTED_WEIGHT_SIZE
        ):
            raise SystemExit("strict startup requires the canonical Aureon weight identity")
    integrity = None
    if expected_weight_sha256 or expected_weight_size:
        if not expected_weight_sha256 or not expected_weight_size:
            raise SystemExit("both expected weight SHA-256 and size are required")
        integrity = verify_weight_file(
            model_dir,
            expected_sha256=expected_weight_sha256,
            expected_size=expected_weight_size,
        )
    if strict_startup and integrity is None:
        raise SystemExit("strict startup requires the canonical weight digest and size")

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    if require_cuda and not torch.cuda.is_available():
        raise SystemExit("CUDA is required for this Aureon release; CPU fallback is refused")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(model_dir, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_dir,
        dtype=torch.bfloat16,
        attn_implementation="sdpa",
        local_files_only=True,
    ).to(device).eval()
    eos_id = tok.convert_tokens_to_ids(tok.eos_token) if tok.eos_token else None
    vocab = int(model.config.vocab_size)
    if not isinstance(eos_id, int) or eos_id < 0 or eos_id >= vocab:
        raise SystemExit(f"eos id {eos_id} is outside vocab {vocab}")
    model.config.eos_token_id = eos_id
    model.config.bos_token_id = eos_id
    model.generation_config.eos_token_id = eos_id
    model.generation_config.pad_token_id = eos_id
    parameters = sum(parameter.numel() for parameter in model.parameters())
    if strict_startup:
        if parameters != EXPECTED_PARAMETERS or vocab != EXPECTED_VOCAB_SIZE:
            raise SystemExit(
                f"loaded model identity mismatch: parameters={parameters}, vocabulary={vocab}"
            )
        if device != "cuda" or eos_id != 1 or tok.bos_token != "<eos>":
            raise SystemExit("strict startup requires CUDA and the canonical <eos> token")
    startup = (
        _greedy_startup_check(model, tok, device, torch, eos_id)
        if strict_startup
        else {"verified": False}
    )
    lock = threading.Lock()
    readiness = {
        "ready": True,
        "model": model_name,
        "provider_mode": OWN_PROVIDER,
        "model_revision": model_revision or None,
        "params": parameters,
        "vocab_size": vocab,
        "eos_id": eos_id,
        "device": device,
        "max_positions": MAX_POSITIONS,
        "weight_sha256": integrity["sha256"] if integrity else None,
        "weight_size_bytes": integrity["size_bytes"] if integrity else None,
        "startup_generation_verified": startup["verified"],
        "startup_generation": startup,
    }
    print(json.dumps(readiness), flush=True)

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt: str, *args) -> None:
            print("[chat]", self.address_string(), fmt % args, flush=True)

        def _send(self, code: int, payload: dict) -> None:
            raw = json.dumps(payload, allow_nan=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Aureon-Provider", OWN_PROVIDER)
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self) -> None:  # noqa: N802
            path = self.path.split("?", 1)[0].rstrip("/")
            if path == "/v1/models":
                self._send(200, {
                    "object": "list",
                    "data": [{
                        "id": model_name,
                        "object": "model",
                        "owned_by": OWN_PROVIDER,
                        "provider_mode": OWN_PROVIDER,
                    }],
                    "provider_mode": OWN_PROVIDER,
                })
                return
            if path in {"/healthz", "/readyz"}:
                self._send(200, readiness if path == "/readyz" else {
                    "ok": True,
                    "provider_mode": OWN_PROVIDER,
                    "live_trading": False,
                })
                return
            self._send(404, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            if self.path.split("?", 1)[0].rstrip("/") != "/v1/chat/completions":
                self._send(404, {"error": "not found"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0") or 0)
            except ValueError:
                self._send(400, {"error": "invalid Content-Length"})
                return
            if length < 1 or length > MAX_REQUEST_BYTES:
                self._send(413, {"error": "request body is empty or too large"})
                return
            try:
                request = json.loads(self.rfile.read(length).decode("utf-8"))
                if not isinstance(request, dict):
                    raise ValueError("request must be a JSON object")
                messages = request.get("messages") or []
                if not isinstance(messages, list) or not all(
                    isinstance(message, dict) for message in messages
                ):
                    raise ValueError("messages must be an array of objects")
                requested = int(request.get("max_tokens") or 256)
                if requested < 1:
                    raise ValueError("max_tokens must be positive")
                temperature = float(request.get("temperature") or 0.0)
                organism = _capture_organism()
                prompt = format_prompt(messages, organism=organism)
                encoded = tok(prompt, return_tensors="pt")
                input_ids = encoded.input_ids
                attention_mask = encoded.attention_mask
                if input_ids.shape[1] >= MAX_POSITIONS - 8:
                    input_ids = input_ids[:, -(MAX_POSITIONS - 8):]
                    attention_mask = attention_mask[:, -(MAX_POSITIONS - 8):]
                room = MAX_POSITIONS - int(input_ids.shape[1])
                new_tokens = max(1, min(requested, MAX_NEW_TOKENS, room))
                input_ids = input_ids.to(device)
                attention_mask = attention_mask.to(device)
                with lock, torch.inference_mode():
                    output = model.generate(
                        input_ids,
                        attention_mask=attention_mask,
                        max_new_tokens=new_tokens,
                        do_sample=temperature > 0,
                        temperature=temperature if temperature > 0 else None,
                        top_p=0.95 if temperature > 0 else None,
                        pad_token_id=eos_id,
                        eos_token_id=eos_id,
                    )
                generated = output[0, input_ids.shape[1]:].detach().cpu().tolist()
                text = tok.decode(generated, skip_special_tokens=True)
                completed = len(generated)
                finish_reason = "length" if completed == new_tokens else "stop"
                body = completion_body(
                    text,
                    int(input_ids.shape[1]),
                    completed,
                    model_name,
                    finish_reason=finish_reason,
                )
                self._send(200, _with_gears(body, text, organism=organism))
            except (UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
                self._send(400, {"error": f"{type(exc).__name__}: {exc}"})
            except Exception as exc:  # noqa: BLE001 — the worker records a failed request
                self._send(500, {"error": f"{type(exc).__name__}: {exc}"})

    if host not in {"127.0.0.1", "::1"}:
        raise SystemExit("the Aureon chat server must bind to a literal loopback address")
    ThreadingHTTPServer.allow_reuse_address = True
    ThreadingHTTPServer.daemon_threads = True
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"[chat] listening on {host}:{port}", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
    return 0


def self_test() -> int:
    prompt = format_prompt([
        {"role": "system", "content": "Return JSON."},
        {"role": "user", "content": "PATH: demo.py"},
    ])
    if "system: Return JSON." not in prompt or not prompt.endswith("assistant:"):
        raise SystemExit("prompt format lost a role")
    organism_prompt = format_prompt(
        [{"role": "user", "content": "PATH: demo.py"}],
        organism={"all_turned": True, "gears": []},
    )
    if not organism_prompt.startswith("system: [AUREON_ORGANISM_STATE]"):
        raise SystemExit("prompt format lost the organism state")
    body = completion_body("{}", 3, 1, "aureon-7b-v65k")
    if body["choices"][0]["message"]["content"] != "{}":
        raise SystemExit("completion body dropped the text")
    if body["provider_mode"] != OWN_PROVIDER:
        raise SystemExit("completion body lost own-model attribution")
    print(json.dumps({"self_test": "pass", "model": "aureon-7b-v65k"}, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="")
    parser.add_argument("--model-name", default="aureon-7b-v65k")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--require-cuda", action="store_true")
    parser.add_argument("--strict-startup", action="store_true")
    parser.add_argument("--expected-weight-sha256", default="")
    parser.add_argument("--expected-weight-size", type=int, default=0)
    parser.add_argument("--model-revision", default=os.environ.get("AUREON_MODEL_REVISION", ""))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if not args.model:
        parser.error("--model is required")
    return serve(
        args.model,
        args.port,
        args.model_name,
        args.host,
        require_cuda=args.require_cuda,
        strict_startup=args.strict_startup,
        expected_weight_sha256=args.expected_weight_sha256,
        expected_weight_size=args.expected_weight_size,
        model_revision=args.model_revision,
    )


if __name__ == "__main__":
    sys.exit(main())
