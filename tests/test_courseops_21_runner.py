from __future__ import annotations

import json
from pathlib import Path

import pytest

from aureon.operator.courseops_21_runner import (
    CourseOps21RunError,
    main,
    prepare_isolated_browser_directories,
    verify_synthetic_certificates,
)

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "courseops_21"


def _codes() -> tuple[str, ...]:
    manifest = json.loads((FIXTURE_ROOT / "benchmark_manifest.json").read_text(encoding="utf-8"))
    return tuple(manifest["course_codes"])


def _pdf(code: str) -> bytes:
    body = (
        "%PDF-1.4\n"
        "1 0 obj << /Type /Catalog >> endobj\n"
        "SYNTHETIC TEST ONLY\n"
        "Synthetic persona: John Brown\n"
        f"Course: {code}\n"
        "No real-world qualification or provider validity\n"
        + ("synthetic-evidence-padding\n" * 8)
        + "%%EOF\n"
    )
    return body.encode("ascii")


def test_prepare_browser_workspace_is_fresh_and_pins_download_preferences(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    profile, downloads = prepare_isolated_browser_directories(workspace)

    assert profile == workspace.resolve() / "profile"
    assert downloads == workspace.resolve() / "downloads"
    preferences = json.loads((profile / "Default" / "Preferences").read_text(encoding="utf-8"))
    assert preferences["download"] == {
        "default_directory": str(downloads),
        "directory_upgrade": True,
        "prompt_for_download": False,
    }
    assert preferences["profile"]["default_content_setting_values"][
        "automatic_downloads"
    ] == 1
    with pytest.raises(FileExistsError):
        prepare_isolated_browser_directories(workspace)


def test_verify_requires_exactly_twenty_one_watermarked_synthetic_pdfs(tmp_path: Path) -> None:
    codes = _codes()
    for code in codes:
        (tmp_path / f"SYNTHETIC-TEST-ONLY-{code}.pdf").write_bytes(_pdf(code))

    verified = verify_synthetic_certificates(tmp_path, codes)

    assert len(verified) == 21
    assert {item.code for item in verified} == set(codes)
    assert all(len(item.sha256) == 64 and item.size_bytes >= 256 for item in verified)
    assert all(item.to_dict()["classification"] == "synthetic_test_only" for item in verified)


def test_verify_rejects_missing_extra_or_invalid_certificate(tmp_path: Path) -> None:
    codes = _codes()
    for code in codes:
        (tmp_path / f"SYNTHETIC-TEST-ONLY-{code}.pdf").write_bytes(_pdf(code))

    missing = tmp_path / f"SYNTHETIC-TEST-ONLY-{codes[0]}.pdf"
    missing.unlink()
    with pytest.raises(CourseOps21RunError, match="set_mismatch"):
        verify_synthetic_certificates(tmp_path, codes)
    missing.write_bytes(_pdf(codes[0]))

    extra = tmp_path / "unexpected.pdf"
    extra.write_bytes(_pdf("EXTRA"))
    with pytest.raises(CourseOps21RunError, match="set_mismatch"):
        verify_synthetic_certificates(tmp_path, codes)
    extra.unlink()

    tampered = tmp_path / f"SYNTHETIC-TEST-ONLY-{codes[1]}.pdf"
    tampered.write_bytes(b"%PDF-1.4\nnot a certificate\n%%EOF\n")
    with pytest.raises(CourseOps21RunError, match="size_invalid"):
        verify_synthetic_certificates(tmp_path, codes)


def test_runner_cli_requires_explicit_live_flag(capsys) -> None:
    assert main([]) == 2
    assert "live_flag_required" in capsys.readouterr().err
