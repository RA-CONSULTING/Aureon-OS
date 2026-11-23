"""Focused regression tests for the stdlib Aureon metadata preparation tool."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
TEST_TEMP_ROOT = REPOSITORY / ".test-tmp"
TEST_TEMP_ROOT.mkdir(exist_ok=True)
sys.path.insert(0, str(REPOSITORY / "huggingface"))

import prepare_aureon_model as preparation  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, separators=(",", ":")), encoding="utf-8")


def make_tokenizer(vocab_size: int, eos_id: int = 1) -> dict:
    special = {"<bos>": 0, "<eos>": eos_id}
    vocab = dict(special)
    for token_id in range(vocab_size):
        if token_id not in special.values():
            vocab[f"token_{token_id}"] = token_id
    return {
        "version": "1.0",
        "added_tokens": [
            {"id": token_id, "content": token, "special": True}
            for token, token_id in special.items()
        ],
        "model": {"type": "BPE", "vocab": vocab, "merges": []},
    }


def valid_config() -> dict:
    return {
        "architectures": ["Qwen2ForCausalLM"],
        "model_type": "qwen2",
        "torch_dtype": "bfloat16",
        "vocab_size": 65_536,
        "num_hidden_layers": 28,
        "hidden_size": 3584,
        "max_position_embeddings": 32_768,
        "rope_theta": 1_000_000.0,
        "use_sliding_window": False,
        "bos_token_id": 151_643,
        "eos_token_id": 151_645,
    }


def write_export(
    source: Path,
    *,
    config: dict | None = None,
    tokenizer: dict | None = None,
    include_generation: bool = True,
    include_weights: bool = True,
) -> None:
    source.mkdir(parents=True)
    write_json(source / "config.json", config or valid_config())
    write_json(
        source / "aureon_export.json",
        {
            "source_checkpoint": "sft_0001578.pt",
            "step": 1578,
            "tokens": 62_658_432,
            "params": 6_995_383_808,
            "params_b": 6.995,
            "vocab_size": 65_536,
            "eos_token": "<eos>",
        },
    )
    write_json(
        source / "tokenizer_config.json",
        {
            "tokenizer_class": "PreTrainedTokenizerFast",
            "model_max_length": 4096,
            "bos_token": "<eos>",
            "eos_token": "<eos>",
            "additional_setting": "preserved",
        },
    )
    write_json(
        source / "tokenizer.json",
        tokenizer if tokenizer is not None else make_tokenizer(65_536),
    )
    if include_generation:
        write_json(
            source / "generation_config.json",
            {
                "bos_token_id": 151_643,
                "eos_token_id": 151_645,
                "do_sample": False,
                "temperature": 0.7,
            },
        )
    if include_weights:
        (source / "model.safetensors").write_bytes(b"small test fixture, not real weights")


class PreparationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory(
            prefix="prepare-aureon-", dir=TEST_TEMP_ROOT
        )
        self.root = Path(self.temporary_directory.name)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_writes_verified_overlay_and_preserves_source(self) -> None:
        source = self.root / "source"
        output = self.root / "overlay"
        write_export(source)
        source_hashes_before = {
            path.name: sha256(path) for path in source.iterdir() if path.is_file()
        }

        receipt = preparation.prepare_aureon_model(source, output)

        source_hashes_after = {
            path.name: sha256(path) for path in source.iterdir() if path.is_file()
        }
        self.assertEqual(source_hashes_after, source_hashes_before)
        self.assertFalse((output / "model.safetensors").exists())
        self.assertEqual(
            {path.name for path in output.iterdir()},
            set(preparation.OUTPUT_FILENAMES) | {preparation.RECEIPT_FILENAME},
        )

        config = json.loads((output / "config.json").read_text(encoding="utf-8"))
        expected_config = valid_config()
        expected_config.update(bos_token_id=1, eos_token_id=1)
        self.assertEqual(config, expected_config)
        self.assertEqual(config["max_position_embeddings"], 32_768)

        generation = json.loads(
            (output / "generation_config.json").read_text(encoding="utf-8")
        )
        self.assertEqual(generation["bos_token_id"], 1)
        self.assertEqual(generation["eos_token_id"], 1)
        self.assertFalse(generation["do_sample"])
        self.assertEqual(generation["temperature"], 0.7)

        tokenizer_config = json.loads(
            (output / "tokenizer_config.json").read_text(encoding="utf-8")
        )
        self.assertEqual(tokenizer_config["eos_token"], "<eos>")
        self.assertEqual(tokenizer_config["bos_token"], "<eos>")
        self.assertEqual(tokenizer_config["model_max_length"], 4096)
        self.assertEqual(tokenizer_config["additional_setting"], "preserved")
        self.assertEqual(
            json.loads((output / "tokenizer.json").read_text(encoding="utf-8")),
            json.loads((source / "tokenizer.json").read_text(encoding="utf-8")),
        )

        manifest = json.loads(
            (output / "aureon_export.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["parameters"], 6_995_383_808)
        self.assertEqual(manifest["params"], 6_995_383_808)
        self.assertEqual(manifest["params_b"], 6.995)
        self.assertEqual(manifest["source_checkpoint"], "sft_0001578.pt")
        self.assertEqual(
            manifest["base_checkpoint"], "runs/aureon-7b-v65k/pinned/ckpt_0017000.pt"
        )
        self.assertEqual(manifest["base_source_step"], 17_000)
        self.assertEqual(manifest["vocab_size"], 65_536)
        self.assertEqual(manifest["sft_step"], 1578)
        self.assertEqual(manifest["supervised_tokens"], 62_658_432)
        self.assertTrue(manifest["random_initialization"])
        self.assertFalse(manifest["weights"]["copied"])
        self.assertEqual(manifest["evaluation"], preparation.EVALUATION)

        self.assertEqual(receipt["derived_eos_token_id"], 1)
        self.assertFalse(receipt["weights_copied"])
        self.assertEqual(receipt["source_hashes"], source_hashes_before)
        for name, digest in receipt["output_hashes"].items():
            self.assertEqual(sha256(output / name), digest)
        on_disk_receipt = json.loads(
            (output / preparation.RECEIPT_FILENAME).read_text(encoding="utf-8")
        )
        self.assertEqual(on_disk_receipt, receipt)

    def test_generation_config_is_optional_and_eos_bos_is_honored(self) -> None:
        source = self.root / "source"
        output = self.root / "overlay"
        tokenizer = make_tokenizer(65_536)
        del tokenizer["model"]["vocab"]["<bos>"]
        tokenizer["added_tokens"] = [
            entry for entry in tokenizer["added_tokens"] if entry["content"] != "<bos>"
        ]
        # Replace ID 0 so the vocabulary remains exactly 0..65535.
        tokenizer["model"]["vocab"]["token_0"] = 0
        write_export(source, tokenizer=tokenizer, include_generation=False)

        preparation.prepare_aureon_model(source, output)

        config = json.loads((output / "config.json").read_text(encoding="utf-8"))
        generation = json.loads(
            (output / "generation_config.json").read_text(encoding="utf-8")
        )
        tokenizer_config = json.loads(
            (output / "tokenizer_config.json").read_text(encoding="utf-8")
        )
        self.assertEqual(config["bos_token_id"], 1)
        self.assertEqual(config["eos_token_id"], 1)
        self.assertEqual(generation, {"bos_token_id": 1, "eos_token_id": 1})
        self.assertEqual(tokenizer_config["bos_token"], "<eos>")

    def test_missing_weights_fail_without_output(self) -> None:
        source = self.root / "source"
        output = self.root / "overlay"
        write_export(source, include_weights=False)

        with self.assertRaisesRegex(
            preparation.PreparationError, "required non-empty model.safetensors"
        ):
            preparation.prepare_aureon_model(source, output)
        self.assertFalse(output.exists())

    def test_invalid_export_receipt_fails_without_output(self) -> None:
        source = self.root / "source"
        output = self.root / "overlay"
        write_export(source)
        export = json.loads((source / "aureon_export.json").read_text(encoding="utf-8"))
        export["params"] = 1
        write_json(source / "aureon_export.json", export)

        with self.assertRaisesRegex(
            preparation.PreparationError, "invalid aureon_export.json params"
        ):
            preparation.prepare_aureon_model(source, output)
        self.assertFalse(output.exists())

    def test_missing_eos_fails_without_output(self) -> None:
        source = self.root / "source"
        output = self.root / "overlay"
        tokenizer = make_tokenizer(8)
        del tokenizer["model"]["vocab"]["<eos>"]
        tokenizer["added_tokens"] = [
            entry for entry in tokenizer["added_tokens"] if entry["content"] != "<eos>"
        ]
        write_export(source, tokenizer=tokenizer)

        with self.assertRaisesRegex(preparation.PreparationError, "missing '<eos>'"):
            preparation.prepare_aureon_model(source, output)
        self.assertFalse(output.exists())

    def test_conflicting_eos_ids_are_ambiguous(self) -> None:
        source = self.root / "source"
        output = self.root / "overlay"
        tokenizer = make_tokenizer(8)
        tokenizer["added_tokens"].append(
            {"id": 2, "content": "<eos>", "special": True}
        )
        write_export(source, tokenizer=tokenizer)

        with self.assertRaisesRegex(preparation.PreparationError, "ambiguous EOS IDs"):
            preparation.prepare_aureon_model(source, output)
        self.assertFalse(output.exists())

    def test_derived_eos_must_match_handoff(self) -> None:
        source = self.root / "source"
        output = self.root / "overlay"
        write_export(source, tokenizer=make_tokenizer(8, eos_id=2))

        with self.assertRaisesRegex(
            preparation.PreparationError, "does not match the verified handoff ID 1"
        ):
            preparation.prepare_aureon_model(source, output)
        self.assertFalse(output.exists())

    def test_tokenizer_vocabulary_mismatch_fails(self) -> None:
        source = self.root / "source"
        output = self.root / "overlay"
        write_export(source, tokenizer=make_tokenizer(8))

        with self.assertRaisesRegex(
            preparation.PreparationError, "tokenizer vocabulary mismatch"
        ):
            preparation.prepare_aureon_model(source, output)
        self.assertFalse(output.exists())

    def test_invalid_native_export_parameters_fail(self) -> None:
        invalid_changes = (
            ("vocab_size", 32_768),
            ("num_hidden_layers", 27),
            ("hidden_size", 4096),
            ("max_position_embeddings", 4096),
            ("torch_dtype", "float32"),
        )
        for index, (key, value) in enumerate(invalid_changes):
            with self.subTest(key=key):
                source = self.root / f"source-{index}"
                output = self.root / f"overlay-{index}"
                config = valid_config()
                config[key] = value
                write_export(source, config=config, tokenizer=make_tokenizer(8))

                with self.assertRaisesRegex(
                    preparation.PreparationError, "invalid export"
                ):
                    preparation.prepare_aureon_model(source, output)
                self.assertFalse(output.exists())

    def test_non_qwen2_architecture_fails(self) -> None:
        source = self.root / "source"
        output = self.root / "overlay"
        config = valid_config()
        config["architectures"] = ["LlamaForCausalLM"]
        write_export(source, config=config, tokenizer=make_tokenizer(8))

        with self.assertRaisesRegex(
            preparation.PreparationError, "invalid export architectures"
        ):
            preparation.prepare_aureon_model(source, output)
        self.assertFalse(output.exists())

    def test_output_equal_to_source_fails_before_modification(self) -> None:
        source = self.root / "source"
        write_export(source, tokenizer=make_tokenizer(8))
        before = {path.name: sha256(path) for path in source.iterdir()}

        with self.assertRaisesRegex(
            preparation.PreparationError, "must be different from the source"
        ):
            preparation.prepare_aureon_model(source, source)

        after = {path.name: sha256(path) for path in source.iterdir()}
        self.assertEqual(after, before)
        self.assertFalse((source / preparation.RECEIPT_FILENAME).exists())

    def test_output_inside_source_fails_before_modification(self) -> None:
        source = self.root / "source"
        write_export(source)
        before = {path.name: sha256(path) for path in source.iterdir()}

        with self.assertRaisesRegex(
            preparation.PreparationError, "must not be inside the source export"
        ):
            preparation.prepare_aureon_model(source, source / "overlay")

        after = {path.name: sha256(path) for path in source.iterdir()}
        self.assertEqual(after, before)
        self.assertFalse((source / "overlay").exists())


class ModelCardTests(unittest.TestCase):
    def test_model_card_has_hub_metadata_and_only_validated_claims(self) -> None:
        card = (REPOSITORY / "huggingface" / "aureon-7b" / "README.md").read_text(
            encoding="utf-8"
        )
        self.assertTrue(card.startswith("---\n"))
        self.assertIn("license: mit", card)
        self.assertIn("library_name: transformers", card)
        self.assertIn("random initialization", card)
        self.assertIn("AutoModelForCausalLM", card)
        self.assertIn("0.4624183006535948", card)
        self.assertIn("0.2411196294744682", card)
        self.assertIn("0.30049261083743845", card)
        self.assertIn("0.035554558485818205", card)
        self.assertIn("0.016413346611668555", card)
        self.assertIn("0.061392267344648296", card)
        self.assertIn("0.19042254384675905", card)
        self.assertIn("1,125", card)
        self.assertIn("66 explain rows", card)
        self.assertIn("4096` (preserved)", card)
        self.assertIn("GaryLeckey/aureon-7b", card)
        self.assertIn("No HumanEval result is reported or claimed", card)
        self.assertIn(preparation.CANONICAL_SOURCE.as_posix(), card)
        self.assertIn("huggingface/aureon-7b/", card)
        self.assertIn("Neither setting is a claim", card)

    def test_evaluation_summary_matches_the_real_exported_aggregate(self) -> None:
        summary_path = (
            REPOSITORY / "huggingface" / "aureon-7b" / "evaluation_summary.json"
        )
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        self.assertEqual(summary["evaluation_job_id"], "8602611")
        self.assertEqual(summary["rows"], 1125)
        self.assertEqual(
            summary["source_sha256"],
            "e5c5614348d4ffb8facbeb6e347aad81343de03170d7a08f38ee5a3c74e12ac4",
        )
        for key, value in preparation.EVALUATION.items():
            if key != "file":
                self.assertEqual(summary["aggregate"][key], value)


if __name__ == "__main__":
    unittest.main(verbosity=2)
