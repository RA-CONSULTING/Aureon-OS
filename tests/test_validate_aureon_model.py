"""Lightweight tests for production Aureon validation orchestration."""

from __future__ import annotations

import contextlib
import copy
import gc
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import types
import unittest
import weakref
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

REPOSITORY = Path(__file__).resolve().parents[1]
TEST_TEMP_ROOT = REPOSITORY / ".test-tmp"
TEST_TEMP_ROOT.mkdir(exist_ok=True)
sys.path.insert(0, str(REPOSITORY / "huggingface"))

import validate_aureon_model as validation  # noqa: E402


class FakeProcess:
    def __init__(self, return_code: int | None = None) -> None:
        self.return_code = return_code
        self.terminated = False
        self.killed = False

    def poll(self) -> int | None:
        return self.return_code

    def terminate(self) -> None:
        self.terminated = True
        self.return_code = -15

    def kill(self) -> None:
        self.killed = True
        self.return_code = -9

    def wait(self, timeout: float | None = None) -> int:
        assert self.return_code is not None
        return self.return_code


class FakeDevice:
    type = "cuda"


class FakeParameter:
    def __init__(self, count: int, dtype: object) -> None:
        self._count = count
        self.dtype = dtype
        self.device = FakeDevice()

    def numel(self) -> int:
        return self._count


class FakeTensor:
    def __init__(self, token_ids: list[int]) -> None:
        self.token_ids = list(token_ids)
        self.shape = (1, len(token_ids))

    def to(self, device: str) -> FakeTensor:
        assert device == "cuda"
        return self

    def __getitem__(self, key: object) -> FakeTensor:
        row, selection = key
        assert row == 0
        return FakeTensor(self.token_ids[selection])

    def detach(self) -> FakeTensor:
        return self

    def cpu(self) -> FakeTensor:
        return self

    def tolist(self) -> list[int]:
        return list(self.token_ids)


class FakeModel:
    load_calls: list[dict] = []

    def __init__(self, torch: object) -> None:
        self.config = types.SimpleNamespace(
            vocab_size=65_536, eos_token_id=1, bos_token_id=1
        )
        self.generation_config = types.SimpleNamespace(eos_token_id=1, bos_token_id=1)
        self._parameters = [FakeParameter(6_995_383_808, torch.bfloat16)]
        self.generate_calls: list[dict] = []

    def to(self, device: str) -> FakeModel:
        assert device == "cuda"
        return self

    def eval(self) -> FakeModel:
        return self

    def parameters(self) -> list[FakeParameter]:
        return self._parameters

    def generate(self, **kwargs: object) -> FakeTensor:
        self.generate_calls.append(kwargs)
        assert kwargs["do_sample"] is False
        assert kwargs["eos_token_id"] == 1
        input_ids = kwargs["input_ids"]
        assert isinstance(input_ids, FakeTensor)
        return FakeTensor(input_ids.token_ids + [10, 11])


class FakeAutoModel:
    @classmethod
    def from_pretrained(cls, path: str, **kwargs: object) -> FakeModel:
        FakeModel.load_calls.append({"path": path, **kwargs})
        return FakeModel(FakeTorch)


class FakeTokenizer:
    load_calls: list[dict] = []
    eos_token = "<eos>"
    bos_token = "<eos>"

    def __len__(self) -> int:
        return 65_536

    @classmethod
    def from_pretrained(cls, path: str, **kwargs: object) -> FakeTokenizer:
        cls.load_calls.append({"path": path, **kwargs})
        return cls()

    def convert_tokens_to_ids(self, token: str) -> int:
        assert token == "<eos>"
        return 1

    def encode(self, text: str, add_special_tokens: bool) -> list[int]:
        assert add_special_tokens is False
        return [ord(character) for character in text]

    def decode(self, token_ids: list[int], skip_special_tokens: bool) -> str:
        assert skip_special_tokens is False
        return "".join(chr(token_id) for token_id in token_ids)

    def __call__(self, text: str, return_tensors: str) -> dict[str, FakeTensor]:
        assert return_tensors == "pt"
        token_ids = [ord(character) for character in text]
        return {
            "input_ids": FakeTensor(token_ids),
            "attention_mask": FakeTensor([1] * len(token_ids)),
        }


class FakeCuda:
    available = True

    def is_available(self) -> bool:
        return self.available

    def reset_peak_memory_stats(self) -> None:
        pass

    def memory_allocated(self) -> int:
        return 0

    def memory_reserved(self) -> int:
        return 0

    def max_memory_allocated(self) -> int:
        return 0

    def max_memory_reserved(self) -> int:
        return 0

    def synchronize(self) -> None:
        pass

    def empty_cache(self) -> None:
        pass

    def get_device_name(self, index: int) -> str:
        assert index == 0
        return "fake CUDA GPU"


class FakeTorch:
    bfloat16 = "bf16"
    cuda = FakeCuda()
    __version__ = "fake-torch"
    version = types.SimpleNamespace(cuda="fake-cuda")

    @staticmethod
    def inference_mode() -> contextlib.AbstractContextManager:
        return contextlib.nullcontext()


FAKE_TRANSFORMERS = types.SimpleNamespace(
    AutoTokenizer=FakeTokenizer,
    AutoModelForCausalLM=FakeAutoModel,
    __version__="fake-transformers",
)


def hnc_receipt() -> dict:
    field = {
        "name": "field",
        "turned": True,
        "engaged": False,
        "available": False,
        "receipt_id": "pre-inference-field-1",
        "blocker": "fresh_canonical_field_unavailable",
    }
    auris = {
        "name": "auris",
        "turned": False,
        "engaged": False,
        "grounded_inputs": 0,
        "blocker": "no_grounded_auris_inputs",
    }
    qgita = {
        "name": "qgita",
        "turned": True,
        "engaged": False,
        "blocker": "fresh_canonical_field_unavailable",
    }
    return {
        "all_turned": False,
        "parsed": True,
        "gears": [
            {"name": "parse", "turned": True, "engaged": True},
            field,
            auris,
            qgita,
        ],
        "organism_snapshot": {"gears": [copy.deepcopy(field), auris, qgita]},
    }


class FakeChatServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, *, different_content: bool = False) -> None:
        super().__init__(("127.0.0.1", 0), FakeChatHandler)
        self.different_content = different_content
        self.requests: list[dict] = []


class FakeChatHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass

    def send_json(self, value: dict) -> None:
        raw = json.dumps(value).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/v1/models":
            self.send_json({"data": [{"id": "aureon-7b-v65k"}]})
        else:
            self.send_error(404)

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        request = json.loads(self.rfile.read(length))
        self.server.requests.append(request)
        content = "real deterministic fixture response"
        if self.server.different_content and len(self.server.requests) == 2:
            content = "different"
        self.send_json(
            {
                "model": "aureon-7b-v65k",
                "choices": [
                    {"message": {"role": "assistant", "content": content}}
                ],
                "hnc_gears": hnc_receipt(),
            }
        )


class ValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory(
            prefix="validate-aureon-", dir=TEST_TEMP_ROOT
        )
        self.root = Path(self.temporary_directory.name)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def start_server(self, *, different_content: bool = False) -> FakeChatServer:
        server = FakeChatServer(different_content=different_content)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 2)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return server

    def source_tree(self) -> Path:
        source = self.root / "consolidated"
        server = source / "training" / "aureon_chat_server.py"
        server.parent.mkdir(parents=True)
        server.write_text("# test fixture\n", encoding="utf-8")
        return source

    def test_weight_hash_matches_preparation_and_handoff(self) -> None:
        source = self.root / "source"
        overlay = self.root / "overlay"
        combined = self.root / "combined"
        source.mkdir()
        overlay.mkdir()
        combined.mkdir()
        payload = b"lightweight fake weights"
        source_weight = source / "model.safetensors"
        source_weight.write_bytes(payload)
        os.link(source_weight, combined / "model.safetensors")
        digest = hashlib.sha256(payload).hexdigest()
        receipt = {"source_hashes": {"model.safetensors": digest}}
        raw = json.dumps(receipt).encode("utf-8")
        (overlay / "preparation_receipt.json").write_bytes(raw)
        (combined / "preparation_receipt.json").write_bytes(raw)

        result = validation.verify_weights(
            combined,
            source,
            overlay,
            expected_sha256=digest,
            expected_size=len(payload),
        )

        self.assertTrue(result["hash_matches"])
        self.assertTrue(result["same_file_as_source"])
        self.assertEqual(result["actual_size"], len(payload))

    def test_weight_hash_mismatch_fails(self) -> None:
        source = self.root / "source"
        overlay = self.root / "overlay"
        combined = self.root / "combined"
        source.mkdir()
        overlay.mkdir()
        combined.mkdir()
        source_weight = source / "model.safetensors"
        source_weight.write_bytes(b"actual")
        os.link(source_weight, combined / "model.safetensors")
        expected = "0" * 64
        raw = json.dumps({"source_hashes": {"model.safetensors": expected}}).encode()
        (overlay / "preparation_receipt.json").write_bytes(raw)
        (combined / "preparation_receipt.json").write_bytes(raw)

        with self.assertRaisesRegex(validation.ValidationError, "independent weight hash"):
            validation.verify_weights(
                combined, source, overlay, expected_sha256=expected, expected_size=6
            )

    def test_fresh_hub_weight_uses_only_downloaded_regular_files(self) -> None:
        downloaded = self.root / "downloaded"
        downloaded.mkdir()
        payload = b"fresh lightweight fake weights"
        (downloaded / "model.safetensors").write_bytes(payload)
        digest = hashlib.sha256(payload).hexdigest()
        (downloaded / "preparation_receipt.json").write_text(
            json.dumps({"source_hashes": {"model.safetensors": digest}}),
            encoding="utf-8",
        )

        result = validation.verify_fresh_hub_weights(
            downloaded,
            hub_repository=validation.HUB_REPOSITORY,
            hub_revision=validation.HUB_REVISION,
            expected_sha256=digest,
            expected_size=len(payload),
        )

        self.assertTrue(result["fresh_hub_download"])
        self.assertTrue(result["hash_matches"])
        self.assertNotIn("source_weight_path", result)
        self.assertNotIn("same_file_as_source", result)

    def test_fresh_hub_weight_rejects_non_regular_weight(self) -> None:
        downloaded = self.root / "downloaded"
        downloaded.mkdir()
        (downloaded / "model.safetensors").write_bytes(b"fake")
        with (
            mock.patch.object(validation.stat, "S_ISREG", return_value=False),
            self.assertRaisesRegex(validation.ValidationError, "regular non-symlink"),
        ):
            validation.verify_fresh_hub_weights(
                downloaded,
                hub_repository=validation.HUB_REPOSITORY,
                hub_revision=validation.HUB_REVISION,
            )

    def test_fresh_hub_identity_is_fixed_to_public_release(self) -> None:
        for repository, revision, message in (
            ("other/repository", validation.HUB_REVISION, "Hub repository"),
            (validation.HUB_REPOSITORY, "0" * 40, "exact revision"),
            (validation.HUB_REPOSITORY, "MAIN", "exact revision"),
        ):
            with self.subTest(repository=repository, revision=revision), self.assertRaisesRegex(
                validation.ValidationError, message
            ):
                validation.verify_fresh_hub_weights(
                    self.root / "missing",
                    hub_repository=repository,
                    hub_revision=revision,
                )

    def test_direct_validation_uses_cuda_bf16_and_equal_greedy_runs(self) -> None:
        FakeModel.load_calls.clear()
        FakeTokenizer.load_calls.clear()

        result, versions = validation.run_direct_validation(
            self.root,
            max_new_tokens=8,
            torch_module=FakeTorch,
            transformers_module=FAKE_TRANSFORMERS,
        )

        self.assertTrue(result["deterministic"])
        self.assertTrue(result["model_released_before_server"])
        self.assertEqual(result["parameter_count"], 6_995_383_808)
        self.assertEqual(result["vocab_size"], 65_536)
        self.assertEqual(result["eos_token_id"], 1)
        self.assertEqual(result["bos_token_id"], 1)
        self.assertEqual(len(result["round_trips"]), 3)
        self.assertTrue(all(item["exact"] for item in result["round_trips"]))
        self.assertEqual(result["generations"][0]["token_ids"], [10, 11])
        self.assertEqual(
            result["generations"][0]["text"], result["generations"][1]["text"]
        )
        self.assertTrue(FakeTokenizer.load_calls[0]["local_files_only"])
        self.assertTrue(FakeModel.load_calls[0]["local_files_only"])
        self.assertEqual(FakeModel.load_calls[0]["dtype"], "bf16")
        self.assertEqual(versions["gpu"], "fake CUDA GPU")

    def test_direct_validation_releases_model_and_parameter_references(self) -> None:
        references = {}

        def load_model(path: str, **kwargs: object) -> FakeModel:
            model = FakeModel(FakeTorch)
            references["model"] = weakref.ref(model)
            references["parameter"] = weakref.ref(model._parameters[0])
            return model

        with mock.patch.object(FakeAutoModel, "from_pretrained", side_effect=load_model):
            validation.run_direct_validation(
                self.root,
                max_new_tokens=8,
                torch_module=FakeTorch,
                transformers_module=FAKE_TRANSFORMERS,
            )
        gc.collect()
        self.assertIsNone(references["model"]())
        self.assertIsNone(references["parameter"]())

    def test_direct_validation_fails_on_residual_cuda_allocation(self) -> None:
        class ResidualCuda(FakeCuda):
            released = False

            def memory_allocated(self) -> int:
                return 4096 if self.released else 0

            def empty_cache(self) -> None:
                self.released = True

        class ResidualTorch(FakeTorch):
            cuda = ResidualCuda()

        direct_record = {}
        with self.assertRaisesRegex(
            validation.ValidationError, r"allocated_bytes=4096, reserved_bytes=0"
        ):
            validation.run_direct_validation(
                self.root,
                max_new_tokens=8,
                torch_module=ResidualTorch,
                transformers_module=FAKE_TRANSFORMERS,
                direct_record=direct_record,
            )

        self.assertTrue(direct_record["deterministic"])
        self.assertEqual(len(direct_record["generations"]), 2)
        self.assertFalse(direct_record["model_released_before_server"])
        self.assertEqual(direct_record["memory_after_release"]["allocated_bytes"], 4096)
        self.assertTrue(direct_record["cleanup"]["generation_scope_exited"])
        self.assertTrue(direct_record["cleanup"]["cuda_cache_emptied"])
        self.assertTrue(direct_record["cleanup"]["cuda_synchronized"])
        self.assertEqual(direct_record["cleanup"]["errors"], [])

        ResidualTorch.cuda.released = False
        deferred_record = {}
        deferred, _ = validation.run_direct_validation(
            self.root,
            max_new_tokens=8,
            torch_module=ResidualTorch,
            transformers_module=FAKE_TRANSFORMERS,
            direct_record=deferred_record,
            require_zero_allocation=False,
        )
        self.assertIs(deferred, deferred_record)
        self.assertTrue(deferred["deterministic"])
        self.assertFalse(deferred["model_released_before_server"])
        self.assertTrue(deferred["zero_allocation_deferred_to_process_exit"])
        self.assertEqual(deferred["memory_after_release"]["allocated_bytes"], 4096)

    def test_isolated_direct_validation_uses_worker_exit_and_zero_parent_memory(self) -> None:
        class CompletedProcess:
            def __init__(self, *args: object, **kwargs: object) -> None:
                self.kwargs = kwargs
                self.exitcode = None
                self.closed = False

            def start(self) -> None:
                result_path = self.kwargs["kwargs"]["result_path"]
                validation.write_receipt(
                    result_path,
                    {
                        "direct": {
                            "deterministic": True,
                            "model_released_before_server": False,
                            "memory_after_release": {
                                "allocated_bytes": 33_554_432,
                                "reserved_bytes": 33_554_432,
                                "peak_allocated_bytes": 14_076_548_096,
                                "peak_reserved_bytes": 14_212_399_104,
                            },
                        },
                        "versions": {"torch": "worker-torch"},
                        "error": None,
                    },
                )
                self.exitcode = 0

            def join(self, timeout: float | None = None) -> None:
                assert timeout is not None

            def close(self) -> None:
                self.closed = True

        class CompletedContext:
            process = None

            def Process(self, *args: object, **kwargs: object) -> CompletedProcess:
                self.process = CompletedProcess(*args, **kwargs)
                return self.process

        context = CompletedContext()
        direct_record = {}
        with (
            mock.patch.object(validation.multiprocessing, "get_context", return_value=context) as get_context,
            mock.patch.dict(sys.modules, {"torch": FakeTorch}),
        ):
            direct, versions = validation.run_direct_validation_isolated(
                self.root, max_new_tokens=8, timeout=12, direct_record=direct_record
            )

        process = context.process
        get_context.assert_called_once_with("spawn")
        self.assertIs(direct, direct_record)
        self.assertTrue(process.closed)
        self.assertEqual(versions["torch"], "worker-torch")
        self.assertEqual(direct["worker_memory_before_exit"]["allocated_bytes"], 33_554_432)
        self.assertEqual(direct["parent_memory_before_server"]["allocated_bytes"], 0)
        self.assertEqual(direct["memory_after_release"]["allocated_bytes"], 0)
        self.assertEqual(direct["release_mechanism"], "spawned_worker_exit")
        self.assertEqual(
            direct["worker_process"], {"started": True, "joined": True, "exit_code": 0}
        )
        self.assertTrue(direct["model_released_before_server"])

    def test_isolated_direct_validation_terminates_a_timed_out_worker(self) -> None:
        class HangingProcess:
            def __init__(self, *args: object, **kwargs: object) -> None:
                self.exitcode = None
                self.terminated = False
                self.killed = False
                self.closed = False

            def start(self) -> None:
                pass

            def join(self, timeout: float | None = None) -> None:
                pass

            def terminate(self) -> None:
                self.terminated = True
                self.exitcode = -15

            def kill(self) -> None:
                self.killed = True
                self.exitcode = -9

            def close(self) -> None:
                self.closed = True

        process = HangingProcess()
        context = mock.Mock()
        context.Process.return_value = process
        with (
            mock.patch.object(validation.multiprocessing, "get_context", return_value=context),
            self.assertRaisesRegex(validation.ValidationError, "exceeded 0.1s"),
        ):
            validation.run_direct_validation_isolated(self.root, timeout=0.1)
        self.assertTrue(process.terminated)
        self.assertFalse(process.killed)
        self.assertTrue(process.closed)

    def test_direct_validation_cleanup_does_not_mask_generation_error(self) -> None:
        class CleanupFailureCuda(FakeCuda):
            def empty_cache(self) -> None:
                raise RuntimeError("cleanup sentinel")

        class CleanupFailureTorch(FakeTorch):
            cuda = CleanupFailureCuda()

        class ExplodingModel(FakeModel):
            def generate(self, **kwargs: object) -> FakeTensor:
                output = super().generate(**kwargs)
                if len(self.generate_calls) == 2:
                    raise LookupError("generation sentinel")
                return output

        def load_model(path: str, **kwargs: object) -> FakeModel:
            return ExplodingModel(FakeTorch)

        direct_record = {}
        with (
            mock.patch.object(FakeAutoModel, "from_pretrained", side_effect=load_model),
            self.assertRaisesRegex(LookupError, "generation sentinel"),
        ):
            validation.run_direct_validation(
                self.root,
                max_new_tokens=8,
                torch_module=CleanupFailureTorch,
                transformers_module=FAKE_TRANSFORMERS,
                direct_record=direct_record,
            )

        self.assertEqual(len(direct_record["generations"]), 1)
        self.assertFalse(direct_record["deterministic"])
        self.assertFalse(direct_record["model_released_before_server"])
        self.assertFalse(direct_record["cleanup"]["generation_scope_exited"])
        self.assertFalse(direct_record["cleanup"]["cuda_cache_emptied"])
        self.assertTrue(direct_record["cleanup"]["cuda_synchronized"])
        self.assertEqual(
            direct_record["cleanup"]["errors"],
            [
                {
                    "step": "cuda.empty_cache",
                    "type": "RuntimeError",
                    "message": "cleanup sentinel",
                }
            ],
        )
        self.assertIn("memory_after_release", direct_record)

    def test_fresh_hub_receipt_retains_direct_http_and_hnc_checks(self) -> None:
        receipt_path = self.root / "fresh-receipt.json"
        arguments = validation._argument_parser().parse_args(
            [
                "--model",
                str(self.root / "downloaded"),
                "--fresh-hub-download",
                "--source-revision",
                "0" * 40,
                "--receipt",
                str(receipt_path),
            ]
        )
        direct = {"model_released_before_server": True}
        with (
            mock.patch.object(validation, "verify_weights") as source_weights,
            mock.patch.object(
                validation, "verify_fresh_hub_weights", return_value={"fresh_hub_download": True}
            ) as fresh_weights,
            mock.patch.object(
                validation,
                "run_direct_validation_isolated",
                return_value=(direct, {"torch": "fake"}),
            ) as direct_validation,
            mock.patch.object(validation, "run_http_validation") as http_validation,
        ):
            receipt = validation.validate(arguments)

        self.assertTrue(receipt["success"])
        self.assertTrue(receipt["fresh_hub_download"])
        self.assertEqual(receipt["hub"]["repository"], validation.HUB_REPOSITORY)
        self.assertEqual(receipt["hub"]["revision"], validation.HUB_REVISION)
        self.assertNotIn("source_export", receipt["paths"])
        self.assertNotIn("metadata_overlay", receipt["paths"])
        self.assertEqual(receipt["paths"]["downloaded_model"], str(self.root / "downloaded"))
        self.assertTrue(receipt["requirements"]["direct_cuda_bf16_determinism"])
        self.assertTrue(receipt["requirements"]["http_determinism_and_hnc"])
        source_weights.assert_not_called()
        fresh_weights.assert_called_once()
        direct_validation.assert_called_once()
        http_validation.assert_called_once()

    def test_failed_receipt_retains_partial_direct_record(self) -> None:
        receipt_path = self.root / "direct-failure-receipt.json"
        arguments = validation._argument_parser().parse_args(
            [
                "--model",
                str(self.root),
                "--source-revision",
                "0" * 40,
                "--receipt",
                str(receipt_path),
            ]
        )

        def fail_direct(
            model_directory: Path, *, max_new_tokens: int, timeout: float, direct_record: dict
        ) -> None:
            direct_record.update(
                deterministic=False,
                generations=[{"run": 1, "token_ids": [10, 11]}],
                memory_after_release={"allocated_bytes": 4096, "reserved_bytes": 8192},
                cleanup={
                    "generation_scope_exited": True,
                    "gc_collected": 3,
                    "cuda_cache_emptied": True,
                    "cuda_synchronized": True,
                    "errors": [],
                },
            )
            raise validation.ValidationError("direct validation sentinel")

        with (
            mock.patch.object(validation, "verify_weights", return_value={}),
            mock.patch.object(validation, "run_direct_validation_isolated", side_effect=fail_direct),
            mock.patch.object(validation, "run_http_validation") as http_validation,
        ):
            receipt = validation.validate(arguments)

        self.assertFalse(receipt["success"])
        self.assertEqual(receipt["errors"][0]["phase"], "direct_cuda_bf16_determinism")
        self.assertEqual(receipt["errors"][0]["message"], "direct validation sentinel")
        self.assertFalse(receipt["requirements"]["direct_cuda_bf16_determinism"])
        self.assertEqual(receipt["direct"]["generations"][0]["token_ids"], [10, 11])
        self.assertEqual(receipt["direct"]["memory_after_release"]["allocated_bytes"], 4096)
        self.assertEqual(receipt["direct"]["cleanup"]["gc_collected"], 3)
        self.assertEqual(
            json.loads(receipt_path.read_text(encoding="utf-8"))["direct"],
            receipt["direct"],
        )
        http_validation.assert_not_called()

    def test_hnc_allows_unavailable_field_and_records_blockers(self) -> None:
        response = {
            "hnc_gears": hnc_receipt(),
            "model": "aureon-7b-v65k",
        }
        status = validation.hnc_status(response)
        self.assertTrue(status["required_gears_present"])
        self.assertFalse(status["all_turned"])
        self.assertFalse(status["engagement"]["field"]["engaged"])
        self.assertEqual(len(status["blockers"]), 3)
        self.assertTrue(status["snapshot_reuse"]["verified"])

    def test_hnc_missing_required_gear_fails(self) -> None:
        response = {"hnc_gears": hnc_receipt()}
        response["hnc_gears"]["gears"] = [
            gear for gear in response["hnc_gears"]["gears"] if gear["name"] != "qgita"
        ]
        with self.assertRaisesRegex(validation.ValidationError, "requires one qgita"):
            validation.hnc_status(response)

    def test_exposed_snapshot_identity_mismatch_fails(self) -> None:
        response = {"hnc_gears": hnc_receipt()}
        response["hnc_gears"]["organism_snapshot"]["gears"][0]["receipt_id"] = "other"
        with self.assertRaisesRegex(validation.ValidationError, "does not reuse"):
            validation.verify_snapshot_reuse(response)

    def test_real_loopback_http_determinism_and_cleanup(self) -> None:
        server = self.start_server()
        process = FakeProcess()
        source_tree = self.source_tree()
        receipt_path = self.root / "receipt.json"
        with mock.patch.object(validation.subprocess, "Popen", return_value=process) as popen:
            http, hnc = validation.run_http_validation(
                self.root,
                source_tree,
                receipt_path,
                startup_timeout=2,
                request_timeout=2,
                port=server.server_port,
            )

        self.assertTrue(http["deterministic"])
        self.assertEqual(len(http["responses"]), 2)
        self.assertEqual(len(server.requests), 2)
        self.assertEqual(server.requests[0], server.requests[1])
        self.assertEqual(server.requests[0]["temperature"], 0.0)
        self.assertTrue(hnc["all_required_receipts_present"])
        self.assertTrue(process.terminated)
        command = popen.call_args.args[0]
        self.assertIn("--host", command)
        self.assertIn("127.0.0.1", command)
        self.assertEqual(popen.call_args.kwargs["env"]["HF_HUB_OFFLINE"], "1")
        self.assertIn(str(source_tree), popen.call_args.kwargs["env"]["PYTHONPATH"])

    def test_http_mismatch_still_terminates_server(self) -> None:
        server = self.start_server(different_content=True)
        process = FakeProcess()
        with (
            mock.patch.object(validation.subprocess, "Popen", return_value=process),
            self.assertRaisesRegex(validation.ValidationError, "HTTP content differs"),
        ):
            validation.run_http_validation(
                self.root,
                self.source_tree(),
                self.root / "receipt.json",
                startup_timeout=2,
                request_timeout=2,
                port=server.server_port,
            )
        self.assertTrue(process.terminated)

    def test_readiness_detects_process_failure(self) -> None:
        process = FakeProcess(return_code=17)
        with self.assertRaisesRegex(validation.ValidationError, "exited with 17"):
            validation.wait_for_models(
                process,
                "http://127.0.0.1:1",
                timeout=1,
                log_path=self.root / "missing.log",
            )

    def test_main_returns_nonzero_and_writes_failed_receipt(self) -> None:
        receipt_path = self.root / "failed-receipt.json"
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            result = validation.main(
                [
                    "--model",
                    str(self.root / "missing-model"),
                    "--source",
                    str(self.root / "missing-source"),
                    "--overlay",
                    str(self.root / "missing-overlay"),
                    "--source-tree",
                    str(self.root / "missing-tree"),
                    "--source-revision",
                    "0" * 40,
                    "--receipt",
                    str(receipt_path),
                ]
            )
        self.assertEqual(result, 1)
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertFalse(receipt["success"])
        self.assertEqual(receipt["status"], "failed")
        self.assertEqual(receipt["errors"][0]["phase"], "weight_integrity")
        self.assertIn("missing combined weight", receipt["errors"][0]["message"])

    def test_sbatch_is_single_gpu_offline_validation_only(self) -> None:
        script = (REPOSITORY / "huggingface" / "validate_aureon_model.sbatch").read_text(
            encoding="utf-8"
        )
        self.assertIn("#SBATCH --gpus-per-node=1", script)
        self.assertIn("#SBATCH --time=00:40:00", script)
        self.assertIn("#SBATCH --no-requeue", script)
        self.assertIn("#SBATCH --account=brics.u6vs", script)
        self.assertIn("#SBATCH --partition=workq", script)
        self.assertIn("ln -sfn", script)
        self.assertIn("source-revision", script)
        self.assertIn("--source-revision", script)
        self.assertIn("apptainer exec --nv --cleanenv", script)
        self.assertIn("HF_HUB_OFFLINE=1", script)
        self.assertIn("TRANSFORMERS_OFFLINE=1", script)
        self.assertNotIn("train_lora.py", script)
        self.assertNotIn("pretrain.py", script)

    def test_hub_sbatch_is_bounded_anonymous_fresh_download(self) -> None:
        script = (REPOSITORY / "huggingface" / "validate_aureon_hub.sbatch").read_text(
            encoding="utf-8"
        )
        self.assertIn("#SBATCH --gpus-per-node=1", script)
        self.assertIn("#SBATCH --time=01:00:00", script)
        self.assertIn("#SBATCH --no-requeue", script)
        self.assertIn("source-revision", script)
        self.assertIn("--fresh-hub-download", script)
        self.assertIn(validation.HUB_REPOSITORY, script)
        self.assertIn(validation.HUB_REVISION, script)
        self.assertIn("HF_VENV=$RELEASE/private/hf-venv", script)
        self.assertIn("HF_HUB_OFFLINE=0", script)
        self.assertIn("HF_HUB_OFFLINE=1", script)
        self.assertIn("model-public-receipt.json", script)
        self.assertIn("refusing to reuse download path", script)
        self.assertNotIn("--source ", script)
        self.assertNotIn("--overlay ", script)
        self.assertNotIn("HF_TOKEN", script)
        self.assertNotIn("HUGGING_FACE_HUB_TOKEN", script)


if __name__ == "__main__":
    unittest.main(verbosity=2)
