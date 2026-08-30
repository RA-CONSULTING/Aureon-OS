#!/usr/bin/env python3
"""
tests/integrations/test_ollama_bridge.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

OllamaBridge + OllamaLLMAdapter tests. These tests NEVER hit a real
Ollama server — they stub out the HTTP session so the checks pass in
CI regardless of whether localhost:11434 is up.

Covers:
  1. Bridge instantiates with env-driven defaults
  2. health_check() caches correctly and returns False when the server
     is unreachable
  3. chat() / generate() / embed() return well-formed fallbacks on error
  4. list_models() / ps() / show_model() parse valid JSON shapes
  5. OllamaLLMAdapter exposes the LLMAdapter interface
  6. OllamaLLMAdapter.prompt() routes through the bridge and returns
     an LLMResponse even when the bridge errors
"""

import json
import os
import sys
import time

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from aureon.inhouse_ai.llm_adapter import LLMAdapter, LLMResponse
from aureon.integrations.ollama import (
    OllamaBridge,
    OllamaLLMAdapter,
    OllamaModel,
    OllamaPsEntry,
)


PASS = 0
FAIL = 0


def check(condition, msg):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [OK] {msg}")
    else:
        FAIL += 1
        print(f"  [!!] {msg}")


# ─────────────────────────────────────────────────────────────────────────────
# Fake HTTP session so we don't depend on a live Ollama server
# ─────────────────────────────────────────────────────────────────────────────


class FakeResponse:
    def __init__(self, status_code=200, json_body=None, text_body="", stream_lines=None):
        self.status_code = status_code
        self._json_body = json_body
        self.text = text_body
        self._stream_lines = stream_lines or []

    def raise_for_status(self):
        if not (200 <= self.status_code < 300):
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        if self._json_body is None:
            raise ValueError("no json body")
        return self._json_body

    def iter_lines(self):
        for line in self._stream_lines:
            if isinstance(line, str):
                yield line.encode("utf-8")
            else:
                yield line


class FakeSession:
    """Programmable stub. Each call consumes from `responses`."""

    def __init__(self, responses=None):
        self.responses = list(responses or [])
        self.calls = []

    def get(self, url, timeout=None, headers=None, params=None, verify=None, stream=False):
        self.calls.append(("GET", url))
        if not self.responses:
            return FakeResponse(status_code=500, json_body={})
        return self.responses.pop(0)

    def post(self, url, json=None, timeout=None, headers=None, stream=False, params=None, data=None, verify=None):
        self.calls.append(("POST", url, json))
        if not self.responses:
            return FakeResponse(status_code=500, json_body={})
        return self.responses.pop(0)

    def request(self, method, url, data=None, headers=None, timeout=None, verify=None):
        self.calls.append((method, url))
        if not self.responses:
            return FakeResponse(status_code=500, json_body={})
        return self.responses.pop(0)

    def patch(self, url, data=None, headers=None, verify=None, timeout=None):
        self.calls.append(("PATCH", url))
        if not self.responses:
            return FakeResponse(status_code=500)
        return self.responses.pop(0)


def _install_fake(bridge, responses):
    fake = FakeSession(responses)
    bridge._session = fake
    bridge._requests_available = True
    return fake


# ─────────────────────────────────────────────────────────────────────────────
# 1. Construction
# ─────────────────────────────────────────────────────────────────────────────


def test_construction_defaults():
    print("\n[1] OllamaBridge construction + env defaults")
    os.environ.pop("AUREON_OLLAMA_BASE_URL", None)
    prior_compatible_url = os.environ.pop("AUREON_LLM_BASE_URL", None)
    bridge = OllamaBridge()
    check(bridge.base_url == "http://localhost:11434",
          f"default base_url = {bridge.base_url}")
    check(bridge.chat_model, f"chat_model defaults to {bridge.chat_model}")
    check(bridge.embed_model, f"embed_model defaults to {bridge.embed_model}")
    check(bridge.keep_alive, f"keep_alive defaults to {bridge.keep_alive}")

    os.environ["AUREON_OLLAMA_BASE_URL"] = "http://example.com:9999/"
    bridge2 = OllamaBridge()
    check(
        bridge2.base_url == "http://example.com:9999",
        f"env override respected: {bridge2.base_url}",
    )
    os.environ.pop("AUREON_OLLAMA_BASE_URL")
    if prior_compatible_url is not None:
        os.environ["AUREON_LLM_BASE_URL"] = prior_compatible_url


# ─────────────────────────────────────────────────────────────────────────────
# 2. Health check
# ─────────────────────────────────────────────────────────────────────────────


def test_health_check():
    print("\n[2] health_check + caching")
    bridge = OllamaBridge()
    _install_fake(bridge, [FakeResponse(json_body={"version": "0.3.0"})])
    check(bridge.health_check() is True, "reachable server → health_check True")
    check(bridge._last_version == "0.3.0", "cached version string")

    # Cache hit — no extra HTTP call
    calls_before = len(bridge._session.calls)
    bridge.health_check()
    check(len(bridge._session.calls) == calls_before, "cache hit avoids HTTP")

    # Unreachable
    bridge2 = OllamaBridge()
    _install_fake(bridge2, [FakeResponse(status_code=500, json_body={})])
    check(bridge2.health_check() is False, "HTTP 500 → False")


# ─────────────────────────────────────────────────────────────────────────────
# 3. list_models + ps + show
# ─────────────────────────────────────────────────────────────────────────────


def test_model_enumeration():
    print("\n[3] list_models + ps + show_model")
    bridge = OllamaBridge()
    _install_fake(
        bridge,
        [
            FakeResponse(
                json_body={
                    "models": [
                        {
                            "name": "llama3:8b",
                            "model": "llama3:8b",
                            "size": 4_700_000_000,
                            "digest": "abc123",
                            "modified_at": "2026-01-01T00:00:00Z",
                            "details": {"family": "llama"},
                        }
                    ]
                }
            )
        ],
    )
    models = bridge.list_models()
    check(len(models) == 1, "list_models parsed one entry")
    check(isinstance(models[0], OllamaModel), "entry is OllamaModel")
    check(models[0].size_bytes == 4_700_000_000, "size parsed")
    check(models[0].details["family"] == "llama", "details preserved")

    bridge2 = OllamaBridge()
    _install_fake(
        bridge2,
        [
            FakeResponse(
                json_body={
                    "models": [
                        {
                            "name": "llama3:8b",
                            "size": 4_700_000_000,
                            "size_vram": 5_000_000_000,
                            "expires_at": "2026-01-01T00:05:00Z",
                        }
                    ]
                }
            )
        ],
    )
    running = bridge2.ps()
    check(len(running) == 1 and isinstance(running[0], OllamaPsEntry), "ps entry")
    check(running[0].size_vram_bytes == 5_000_000_000, "ps vram size")


# ─────────────────────────────────────────────────────────────────────────────
# 4. Chat + generate + embed
# ─────────────────────────────────────────────────────────────────────────────


def test_chat_generate_embed():
    print("\n[4] chat / generate / embed")
    # Happy chat
    bridge = OllamaBridge()
    _install_fake(
        bridge,
        [
            FakeResponse(
                json_body={
                    "model": "llama3",
                    "message": {"role": "assistant", "content": "hello, world"},
                    "done": True,
                    "prompt_eval_count": 8,
                    "eval_count": 12,
                }
            )
        ],
    )
    out = bridge.chat([{"role": "user", "content": "hi"}])
    check(out["message"]["content"] == "hello, world", "chat happy path")

    # Chat error path
    bridge2 = OllamaBridge()
    _install_fake(bridge2, [FakeResponse(status_code=500)])
    out2 = bridge2.chat([{"role": "user", "content": "hi"}])
    check(out2.get("error"), f"chat error carries 'error' key: {out2.get('error')}")
    check(out2["message"]["content"] == "", "chat error still returns shape")

    # Generate
    bridge3 = OllamaBridge()
    _install_fake(
        bridge3, [FakeResponse(json_body={"model": "llama3", "response": "ok", "done": True})]
    )
    out3 = bridge3.generate("hi")
    check(out3["response"] == "ok", "generate happy path")

    # Embed — /api/embed
    bridge4 = OllamaBridge()
    _install_fake(
        bridge4,
        [
            FakeResponse(
                json_body={
                    "model": "nomic-embed-text",
                    "embeddings": [[0.1, 0.2, 0.3]],
                }
            )
        ],
    )
    vecs = bridge4.embed("hello")
    check(len(vecs) == 1 and vecs[0] == [0.1, 0.2, 0.3], "embed happy path")

    # Embed fallback to /api/embeddings
    bridge5 = OllamaBridge()
    _install_fake(
        bridge5,
        [
            FakeResponse(status_code=404),
            FakeResponse(json_body={"embedding": [0.4, 0.5]}),
        ],
    )
    vecs5 = bridge5.embed("hi")
    check(len(vecs5) == 1 and vecs5[0] == [0.4, 0.5], "embed legacy fallback")


# ─────────────────────────────────────────────────────────────────────────────
# 5. Adapter
# ─────────────────────────────────────────────────────────────────────────────


def test_adapter_interface():
    print("\n[5] OllamaLLMAdapter interface")
    bridge = OllamaBridge()
    _install_fake(
        bridge,
        [
            FakeResponse(
                json_body={
                    "model": "llama3",
                    "message": {"role": "assistant", "content": "I see you"},
                    "done": True,
                    "prompt_eval_count": 5,
                    "eval_count": 7,
                }
            )
        ],
    )
    adapter = OllamaLLMAdapter(bridge=bridge)
    check(isinstance(adapter, LLMAdapter), "adapter isinstance LLMAdapter")
    resp = adapter.prompt(
        messages=[{"role": "user", "content": "hi"}],
        system="you are helpful",
        max_tokens=32,
        temperature=0.3,
    )
    check(isinstance(resp, LLMResponse), "adapter.prompt returns LLMResponse")
    check(resp.text == "I see you", f"adapter text: {resp.text}")
    check(resp.stop_reason == "end_turn", f"stop_reason: {resp.stop_reason}")
    check(resp.usage.get("total_tokens") == 12, "usage.total_tokens summed")


def test_adapter_error_path():
    print("\n[6] OllamaLLMAdapter survives bridge errors")
    bridge = OllamaBridge()
    _install_fake(bridge, [FakeResponse(status_code=500)])
    adapter = OllamaLLMAdapter(bridge=bridge)
    resp = adapter.prompt(messages=[{"role": "user", "content": "x"}])
    check(isinstance(resp, LLMResponse), "error → still LLMResponse")
    check(resp.stop_reason == "error", f"stop_reason: {resp.stop_reason}")


def test_adapter_normalises_content_blocks():
    print("\n[7] OllamaLLMAdapter normalises list-of-blocks content")
    bridge = OllamaBridge()
    captured = {}

    original_post = bridge._post

    def capture(path, body, timeout=None):
        captured["body"] = body
        return {"model": "x", "message": {"role": "assistant", "content": "ok"}, "done": True}

    bridge._post = capture  # type: ignore[method-assign]
    adapter = OllamaLLMAdapter(bridge=bridge)
    adapter.prompt(
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "part one"},
                    {"type": "text", "text": "part two"},
                ],
            }
        ],
        system="sys",
    )
    bridge._post = original_post  # type: ignore[method-assign]
    sent = captured.get("body", {})
    msgs = sent.get("messages", [])
    check(msgs and msgs[0].get("role") == "system", "system message injected")
    check(
        any("part one" in m.get("content", "") and "part two" in m.get("content", "") for m in msgs),
        "content blocks flattened to a single string",
    )


# ─────────────────────────────────────────────────────────────────────────────
# 8. Snapshot
# ─────────────────────────────────────────────────────────────────────────────


def test_snapshot():
    print("\n[8] OllamaBridge.snapshot() for audit trail")
    bridge = OllamaBridge()
    _install_fake(
        bridge,
        [
            FakeResponse(json_body={"version": "0.3.0"}),
            FakeResponse(json_body={"models": [{"name": "llama3"}]}),
            FakeResponse(json_body={"models": []}),
        ],
    )
    snap = bridge.snapshot()
    check(snap["reachable"] is True, "snapshot reachable")
    check("llama3" in snap["models"], "snapshot models list")
    check(snap["running"] == [], "snapshot running list")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────


def main():
    test_construction_defaults()
    test_health_check()
    test_model_enumeration()
    test_chat_generate_embed()
    test_adapter_interface()
    test_adapter_error_path()
    test_adapter_normalises_content_blocks()
    test_snapshot()

    print(f"\n{'═' * 60}")
    print(f"OllamaBridge tests: {PASS} passed, {FAIL} failed")
    print(f"{'═' * 60}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
