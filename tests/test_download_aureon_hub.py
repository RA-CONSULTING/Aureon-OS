"""Offline tests for the anonymous pinned Hub download helper."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPOSITORY = Path(__file__).resolve().parents[1]
TEST_TEMP_ROOT = REPOSITORY / ".test-tmp"
TEST_TEMP_ROOT.mkdir(exist_ok=True)
sys.path.insert(0, str(REPOSITORY / "huggingface"))

import download_aureon_hub as download  # noqa: E402


class FakeApi:
    def __init__(self, **overrides: object) -> None:
        self.values = {
            "private": False,
            "gated": False,
            "sha": download.HUB_REVISION,
            **overrides,
        }
        self.calls: list[dict] = []

    def repo_info(self, **kwargs: object) -> dict:
        self.calls.append(kwargs)
        return self.values


class HubDownloadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory(
            prefix="download-aureon-", dir=TEST_TEMP_ROOT
        )
        self.root = Path(self.temporary_directory.name)
        self.payloads = {name: f"fresh {name}\n".encode() for name in download.MODEL_FILES}
        self.receipt = self.root / "public.json"
        self.write_receipt()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def write_receipt(self, **overrides: object) -> None:
        value = {
            "repository": download.HUB_REPOSITORY,
            "revision": download.HUB_REVISION,
            "visibility": "public",
            "files": [
                {
                    "path": name,
                    "size_bytes": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                }
                for name, payload in self.payloads.items()
            ],
            **overrides,
        }
        self.receipt.write_text(json.dumps(value), encoding="utf-8")

    def fake_download(self, **kwargs: object) -> str:
        destination = Path(kwargs["local_dir"]) / str(kwargs["filename"])
        destination.write_bytes(self.payloads[str(kwargs["filename"])])
        return str(destination)

    def test_downloads_only_nine_allowlisted_files_at_anonymous_pinned_head(self) -> None:
        api = FakeApi()
        calls: list[dict] = []

        def fetch(**kwargs: object) -> str:
            calls.append(kwargs)
            return self.fake_download(**kwargs)

        result = download.download_fresh_model(
            self.root / "new-download", self.receipt, api=api, download_file=fetch
        )

        self.assertTrue(result["fresh_hub_download"])
        self.assertEqual(result["files"], list(download.MODEL_FILES))
        self.assertEqual(len(calls), 9)
        self.assertEqual({call["filename"] for call in calls}, set(download.MODEL_FILES))
        self.assertTrue(all(call["revision"] == download.HUB_REVISION for call in calls))
        self.assertTrue(all(call["token"] is False for call in calls))
        self.assertTrue(all(call["local_dir_use_symlinks"] is False for call in calls))
        self.assertTrue(all(call["local_files_only"] is False for call in calls))
        self.assertEqual(api.calls[0]["revision"], "main")
        self.assertIs(api.calls[0]["token"], False)

    def test_public_ungated_exact_head_is_required(self) -> None:
        for index, overrides in enumerate(
            ({"private": True}, {"gated": "auto"}, {"sha": "0" * 40})
        ):
            with self.subTest(overrides=overrides), self.assertRaises(download.DownloadError):
                download.download_fresh_model(
                    self.root / f"bad-head-{index}",
                    self.receipt,
                    api=FakeApi(**overrides),
                    download_file=self.fake_download,
                )

    def test_existing_download_directory_is_never_reused(self) -> None:
        for name in ("empty", "nonempty"):
            destination = self.root / name
            destination.mkdir()
            if name == "nonempty":
                (destination / "old-file").write_text("old", encoding="utf-8")
            api = FakeApi()
            with (
                mock.patch.object(api, "repo_info", wraps=api.repo_info) as repo_info,
                self.assertRaisesRegex(download.DownloadError, "already exists"),
            ):
                download.download_fresh_model(
                    destination, self.receipt, api=api, download_file=self.fake_download
                )
            repo_info.assert_not_called()

    def test_every_file_is_checked_against_public_receipt(self) -> None:
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        receipt["files"][0]["sha256"] = "0" * 64
        self.receipt.write_text(json.dumps(receipt), encoding="utf-8")

        with self.assertRaisesRegex(download.DownloadError, "SHA-256 mismatch"):
            download.download_fresh_model(
                self.root / "bad-hash",
                self.receipt,
                api=FakeApi(),
                download_file=self.fake_download,
            )

    def test_receipt_must_cover_exact_allowlist(self) -> None:
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        receipt["files"].pop()
        self.receipt.write_text(json.dumps(receipt), encoding="utf-8")

        with self.assertRaisesRegex(download.DownloadError, "all nine files"):
            download.download_fresh_model(
                self.root / "incomplete-receipt",
                self.receipt,
                api=FakeApi(),
                download_file=self.fake_download,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
