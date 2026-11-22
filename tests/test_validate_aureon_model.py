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


if __name__ == "__main__":
    unittest.main(verbosity=2)
