"""OpenAI-compatible server for the Aureon checkpoint.

The HNC-5000 worker speaks POST /v1/chat/completions. This process serves that
route from runs/aureon-7b-v65k/hf and from nowhere else. The config copied
from Qwen still names eos ids 151643 and 151645, which are outside the
65,536-row embedding, so generation uses the tokenizer's own <eos> id.

    python aureon_chat_server.py --self-test
    python aureon_chat_server.py --model runs/aureon-7b-v65k/hf --port 8000
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


MAX_POSITIONS = 8192


def format_prompt(messages: list[dict]) -> str:
    lines = []
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


def _with_gears(body: dict, text: str) -> dict:
    """Run the HNC gears. A gear that cannot be imported is reported, not hidden."""
    import sys
    roots = (
        Path("/projects/u6vs/Aureon-OS"),
        Path(__file__).resolve().parents[1],
    )
    for root in roots:
        if (root / "aureon" / "core" / "hnc_llm_gears.py").is_file() and str(root) not in sys.path:
            sys.path.insert(0, str(root))
    try:
        from aureon.core.hnc_llm_gears import attach_gears
    except Exception as exc:  # noqa: BLE001
        out = dict(body)
        out["hnc_gears"] = {
            "all_turned": False,
            "parsed": False,
            "gears": [{"name": "load", "turned": False, "error": f"{type(exc).__name__}: {exc}"}],
        }
        return out
    return attach_gears(body, text)


def completion_body(text: str, prompt_tokens: int, completion_tokens: int, model: str) -> dict:
    return {
        "model": model,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens, "total_tokens": prompt_tokens + completion_tokens},
    }


def self_test() -> int:
    prompt = format_prompt([
        {"role": "system", "content": "Return JSON."},
        {"role": "user", "content": "PATH: demo.py"},
    ])
    if "system: Return JSON." not in prompt or not prompt.endswith("assistant:"):
        raise SystemExit("prompt format lost a role")
    body = completion_body("{}", 3, 1, "aureon-7b-v65k")
    if body["choices"][0]["message"]["content"] != "{}":
        raise SystemExit("completion body dropped the text")
    print(json.dumps({"self_test": "pass", "model": "aureon-7b-v65k"}, sort_keys=True))
    return 0


def serve(model_dir: str, port: int, model_name: str) -> int:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(model_dir)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = AutoModelForCausalLM.from_pretrained(
        model_dir, dtype=torch.bfloat16, attn_implementation="sdpa"
    ).to(device).eval()
    eos_id = tok.convert_tokens_to_ids(tok.eos_token) if tok.eos_token else None
    vocab = int(model.config.vocab_size)
    if not isinstance(eos_id, int) or eos_id < 0 or eos_id >= vocab:
        raise SystemExit(f"eos id {eos_id} is outside vocab {vocab}")
    model.config.eos_token_id = eos_id
    model.config.bos_token_id = eos_id
    model.generation_config.eos_token_id = eos_id
    model.generation_config.pad_token_id = eos_id
    lock = threading.Lock()
    print(json.dumps({
        "ready": True, "model": model_name, "params": sum(p.numel() for p in model.parameters()),
        "vocab_size": vocab, "eos_id": eos_id, "device": device, "max_positions": MAX_POSITIONS,
    }), flush=True)

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt: str, *args) -> None:
            print("[chat]", self.address_string(), fmt % args, flush=True)

        def _send(self, code: int, payload: dict) -> None:
            raw = json.dumps(payload).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self) -> None:  # noqa: N802
            if self.path.split("?", 1)[0].rstrip("/") == "/v1/models":
                self._send(200, {"data": [{"id": model_name}]})
                return
            self._send(404, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            if self.path.split("?", 1)[0].rstrip("/") != "/v1/chat/completions":
                self._send(404, {"error": "not found"})
                return
            length = int(self.headers.get("Content-Length", "0") or 0)
            try:
                request = json.loads(self.rfile.read(length).decode("utf-8"))
                messages = request.get("messages") or []
                requested = int(request.get("max_tokens") or 256)
                temperature = float(request.get("temperature") or 0.0)
                prompt = format_prompt(messages)
                encoded = tok(prompt, return_tensors="pt")
                input_ids = encoded.input_ids
                if input_ids.shape[1] >= MAX_POSITIONS - 8:
                    input_ids = input_ids[:, -(MAX_POSITIONS - 8):]
                room = MAX_POSITIONS - int(input_ids.shape[1])
                new_tokens = max(1, min(requested, room))
                input_ids = input_ids.to(device)
                with lock, torch.no_grad():
                    if temperature <= 0:
                        output = model.generate(
                            input_ids, max_new_tokens=new_tokens, do_sample=False,
                            pad_token_id=eos_id, eos_token_id=eos_id,
                        )
                    else:
                        output = model.generate(
                            input_ids, max_new_tokens=new_tokens, do_sample=True,
                            temperature=temperature, top_p=0.95,
                            pad_token_id=eos_id, eos_token_id=eos_id,
                        )
                text = tok.decode(output[0, input_ids.shape[1]:], skip_special_tokens=True)
                body = completion_body(text, int(input_ids.shape[1]), new_tokens, model_name)
                self._send(200, _with_gears(body, text))
            except Exception as exc:  # noqa: BLE001 — the worker records a failed request
                self._send(500, {"error": f"{type(exc).__name__}: {exc}"})

    ThreadingHTTPServer.allow_reuse_address = True
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"[chat] listening on 127.0.0.1:{port}", flush=True)
    server.serve_forever()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="")
    parser.add_argument("--model-name", default="aureon-7b-v65k")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if not args.model:
        parser.error("--model is required")
    return serve(args.model, args.port, args.model_name)


if __name__ == "__main__":
    sys.exit(main())
