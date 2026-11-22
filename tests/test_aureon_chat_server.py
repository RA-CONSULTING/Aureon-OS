"""Focused fake-runtime tests for strict Aureon chat startup and HTTP bounds.

No real model, Transformers installation, CUDA device, or network socket is used.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import sys
import types
from unittest import mock

import pytest

from training import aureon_chat_server as server_module

REVISION = "b" * 40


class FakeTensor:
    def __init__(self, token_ids: list[int]) -> None:
        self.token_ids = list(token_ids)
        self.shape = (1, len(token_ids))

    def to(self, device: str) -> FakeTensor:
        assert device == "cuda"
        return self

    def __getitem__(self, key: object) -> FakeTensor:
        if isinstance(key, tuple):
            row, selection = key
            assert row == 0
            return FakeTensor(self.token_ids[selection])
        return FakeTensor(self.token_ids[key])

    def detach(self) -> FakeTensor:
        return self

    def cpu(self) -> FakeTensor:
        return self

    def tolist(self) -> list[int]:
        return list(self.token_ids)


class FakeParameter:
    def numel(self) -> int:
        return server_module.EXPECTED_PARAMETERS


class FakeModel:
    def __init__(self, events: list[tuple]) -> None:
        self.events = events
        self.config = types.SimpleNamespace(vocab_size=server_module.EXPECTED_VOCAB_SIZE)
        self.generation_config = types.SimpleNamespace()
        self.generate_calls: list[dict] = []

    def to(self, device: str) -> FakeModel:
        assert device == "cuda"
        return self

    def eval(self) -> FakeModel:
        return self

    def parameters(self) -> list[FakeParameter]:
        return [FakeParameter()]

    def generate(self, *args: object, **kwargs: object) -> FakeTensor:
        input_ids = kwargs.get("input_ids", args[0] if args else None)
        assert isinstance(input_ids, FakeTensor)
        new_tokens = int(kwargs["max_new_tokens"])
        self.generate_calls.append(dict(kwargs))
        self.events.append(("generation", new_tokens))
        return FakeTensor(input_ids.token_ids + [7] * new_tokens)


class FakeTokenizer:
    eos_token = "<eos>"
    bos_token = "<eos>"

    def convert_tokens_to_ids(self, token: str) -> int:
        assert token == "<eos>"
        return 1

    def __call__(self, text: str, return_tensors: str) -> types.SimpleNamespace:
        assert return_tensors == "pt"
        return types.SimpleNamespace(
            input_ids=FakeTensor([2, 3, 4]),
            attention_mask=FakeTensor([1, 1, 1]),
        )

    def decode(self, token_ids: list[int], skip_special_tokens: bool) -> str:
        assert skip_special_tokens is True
        return "x" * len(token_ids)


class FakeCuda:
    def __init__(self, events: list[tuple]) -> None:
        self.events = events
        self.available = True

    def is_available(self) -> bool:
        return self.available

    def synchronize(self) -> None:
        self.events.append(("synchronize",))


@pytest.fixture
def fake_runtime(monkeypatch):
    events: list[tuple] = []
    model = FakeModel(events)
    tokenizer = FakeTokenizer()
    torch = types.ModuleType("torch")
    torch.bfloat16 = object()
    torch.cuda = FakeCuda(events)
    torch.inference_mode = contextlib.nullcontext
    auto_tokenizer = mock.Mock(return_value=tokenizer)
    auto_model = mock.Mock(return_value=model)
    transformers = types.ModuleType("transformers")
    transformers.AutoTokenizer = types.SimpleNamespace(from_pretrained=auto_tokenizer)
    transformers.AutoModelForCausalLM = types.SimpleNamespace(from_pretrained=auto_model)
    monkeypatch.setitem(sys.modules, "torch", torch)
    monkeypatch.setitem(sys.modules, "transformers", transformers)
    return types.SimpleNamespace(
        events=events,
        model=model,
        tokenizer=tokenizer,
        torch=torch,
        auto_tokenizer=auto_tokenizer,
        auto_model=auto_model,
    )


def _strict_arguments() -> dict:
    return {
        "require_cuda": True,
        "strict_startup": True,
        "expected_weight_sha256": server_module.EXPECTED_WEIGHT_SHA256,
        "expected_weight_size": server_module.EXPECTED_WEIGHT_SIZE,
        "model_revision": REVISION,
    }


def _run_strict_server(fake_runtime, monkeypatch):
    holder = {}
    integrity = {
        "path": "fake/model.safetensors",
        "sha256": server_module.EXPECTED_WEIGHT_SHA256,
        "size_bytes": server_module.EXPECTED_WEIGHT_SIZE,
        "verified": True,
    }
    verify = mock.Mock(return_value=integrity)
    monkeypatch.setattr(server_module, "verify_weight_file", verify)

    class FakeHTTPServer:
        def __init__(self, address, handler) -> None:
            fake_runtime.events.append(("socket", address))
            holder["address"] = address
            holder["handler"] = handler

        def serve_forever(self) -> None:
            fake_runtime.events.append(("serve",))

        def server_close(self) -> None:
            fake_runtime.events.append(("close",))

    monkeypatch.setattr(server_module, "ThreadingHTTPServer", FakeHTTPServer)
    assert server_module.serve(
        "fake-model", 8000, "aureon-7b-v65k", "127.0.0.1", **_strict_arguments()
    ) == 0
    holder["verify"] = verify
    return holder


def _handler_without_socket(handler_type, path: str):
    handler = object.__new__(handler_type)
    handler.path = path
    handler.responses = []
    handler._send = lambda code, payload: handler.responses.append((code, payload))
    return handler


def test_verify_weight_file_size_failure_is_independent_of_hash(tmp_path) -> None:
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    weight = b"canonical fake bytes"
    (model_dir / "model.safetensors").write_bytes(weight)

    with pytest.raises(RuntimeError, match="model weight size"):
        server_module.verify_weight_file(
            model_dir,
            expected_sha256=hashlib.sha256(weight).hexdigest(),
            expected_size=len(weight) + 1,
        )


def test_verify_weight_file_hash_failure_is_independent_of_size(tmp_path) -> None:
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    weight = b"canonical fake bytes"
    (model_dir / "model.safetensors").write_bytes(weight)

    with pytest.raises(RuntimeError, match="SHA-256"):
        server_module.verify_weight_file(
            model_dir,
            expected_sha256="0" * 64,
            expected_size=len(weight),
        )


def test_verify_weight_file_accepts_matching_hash_and_size(tmp_path) -> None:
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    weight = b"canonical fake bytes"
    (model_dir / "model.safetensors").write_bytes(weight)
    digest = hashlib.sha256(weight).hexdigest()

    result = server_module.verify_weight_file(
        model_dir, expected_sha256=digest, expected_size=len(weight)
    )

    assert result["sha256"] == digest
    assert result["size_bytes"] == len(weight)
    assert result["verified"] is True


@pytest.mark.parametrize("require_cuda", [True, False])
def test_strict_startup_refuses_cpu_before_loading_or_binding(
    fake_runtime, monkeypatch, require_cuda
) -> None:
    fake_runtime.torch.cuda.available = False
    monkeypatch.setattr(server_module, "verify_weight_file", mock.Mock(return_value={
        "sha256": server_module.EXPECTED_WEIGHT_SHA256,
        "size_bytes": server_module.EXPECTED_WEIGHT_SIZE,
    }))
    bind = mock.Mock()
    monkeypatch.setattr(server_module, "ThreadingHTTPServer", bind)
    arguments = _strict_arguments()
    arguments["require_cuda"] = require_cuda

    with pytest.raises(SystemExit, match="CPU fallback is refused"):
        server_module.serve(
            "fake-model", 8000, "aureon-7b-v65k", "127.0.0.1", **arguments
        )

    fake_runtime.auto_tokenizer.assert_not_called()
    fake_runtime.auto_model.assert_not_called()
    bind.assert_not_called()


@pytest.mark.parametrize(
    "changes",
    [
        {"model_revision": "main"},
        {"model_revision": "B" * 40},
        {"expected_weight_sha256": "0" * 64},
        {"expected_weight_size": 1},
    ],
)
def test_strict_startup_rejects_noncanonical_identity_before_hash_or_load(
    fake_runtime, monkeypatch, changes
) -> None:
    verify = mock.Mock()
    bind = mock.Mock()
    monkeypatch.setattr(server_module, "verify_weight_file", verify)
    monkeypatch.setattr(server_module, "ThreadingHTTPServer", bind)
    arguments = _strict_arguments()
    arguments.update(changes)

    with pytest.raises(SystemExit):
        server_module.serve(
            "fake-model", 8000, "aureon-7b-v65k", "127.0.0.1", **arguments
        )

    verify.assert_not_called()
    fake_runtime.auto_model.assert_not_called()
    bind.assert_not_called()


def test_strict_startup_rejects_noncanonical_model_name(fake_runtime, monkeypatch) -> None:
    verify = mock.Mock()
    monkeypatch.setattr(server_module, "verify_weight_file", verify)

    with pytest.raises(SystemExit, match="canonical Aureon model name"):
        server_module.serve("fake-model", 8000, "borrowed", "127.0.0.1", **_strict_arguments())

    verify.assert_not_called()
    fake_runtime.auto_model.assert_not_called()


def test_strict_startup_generates_before_socket_binding(fake_runtime, monkeypatch) -> None:
    holder = _run_strict_server(fake_runtime, monkeypatch)

    event_names = [event[0] for event in fake_runtime.events]
    assert event_names.index("generation") < event_names.index("socket")
    assert fake_runtime.model.generate_calls[0]["max_new_tokens"] == 16
    assert fake_runtime.model.generate_calls[0]["do_sample"] is False
    assert fake_runtime.auto_tokenizer.call_args.kwargs["local_files_only"] is True
    assert fake_runtime.auto_model.call_args.kwargs["local_files_only"] is True
    assert holder["verify"].call_args.kwargs == {
        "expected_sha256": server_module.EXPECTED_WEIGHT_SHA256,
        "expected_size": server_module.EXPECTED_WEIGHT_SIZE,
    }
    assert event_names[-2:] == ["serve", "close"]


def test_readyz_reports_own_provider_and_startup_evidence(fake_runtime, monkeypatch) -> None:
    holder = _run_strict_server(fake_runtime, monkeypatch)
    handler = _handler_without_socket(holder["handler"], "/readyz")

    handler.do_GET()

    assert len(handler.responses) == 1
    status, readiness = handler.responses[0]
    assert status == 200
    assert readiness["ready"] is True
    assert readiness["provider_mode"] == server_module.OWN_PROVIDER
    assert readiness["model_revision"] == REVISION
    assert readiness["weight_sha256"] == server_module.EXPECTED_WEIGHT_SHA256
    assert readiness["weight_size_bytes"] == server_module.EXPECTED_WEIGHT_SIZE
    assert readiness["startup_generation_verified"] is True
    assert readiness["startup_generation"]["generated_tokens"] == 16
    assert readiness["device"] == "cuda"  # FakeCuda, not a claim of real GPU coverage.


def test_request_body_limit_rejects_before_read_or_generation(fake_runtime, monkeypatch) -> None:
    holder = _run_strict_server(fake_runtime, monkeypatch)
    handler = _handler_without_socket(holder["handler"], "/v1/chat/completions")
    handler.headers = {"Content-Length": str(server_module.MAX_REQUEST_BYTES + 1)}
    handler.rfile = mock.Mock()
    calls_before = len(fake_runtime.model.generate_calls)

    handler.do_POST()

    assert handler.responses[0][0] == 413
    handler.rfile.read.assert_not_called()
    assert len(fake_runtime.model.generate_calls) == calls_before


def test_generation_is_capped_and_usage_counts_actual_tokens(fake_runtime, monkeypatch) -> None:
    holder = _run_strict_server(fake_runtime, monkeypatch)
    monkeypatch.setattr(server_module, "_capture_organism", lambda: {"all_turned": True})
    monkeypatch.setattr(server_module, "_with_gears", lambda body, text, organism=None: body)
    handler = _handler_without_socket(holder["handler"], "/v1/chat/completions")
    body = json.dumps({
        "messages": [{"role": "user", "content": "Return JSON."}],
        "max_tokens": 10_000,
        "temperature": 0,
    }).encode()
    handler.headers = {"Content-Length": str(len(body))}
    handler.rfile = io.BytesIO(body)

    handler.do_POST()

    assert handler.responses[0][0] == 200
    response = handler.responses[0][1]
    generation = fake_runtime.model.generate_calls[-1]
    assert generation["max_new_tokens"] == server_module.MAX_NEW_TOKENS
    assert generation["do_sample"] is False
    assert response["usage"]["completion_tokens"] == server_module.MAX_NEW_TOKENS
    assert response["usage"]["total_tokens"] == 3 + server_module.MAX_NEW_TOKENS
    assert response["choices"][0]["finish_reason"] == "length"
    assert response["provider_mode"] == server_module.OWN_PROVIDER
