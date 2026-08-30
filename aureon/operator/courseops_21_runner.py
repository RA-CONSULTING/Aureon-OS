"""End-to-end runner for Aureon's sealed CourseOps-21 ScreenReel benchmark."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import secrets
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, Mapping, Sequence

from aureon.operator.course_benchmark_ledger import CourseBenchmarkLedger
from aureon.operator.courseops_21_harness import (
    EXPECTED_WINDOW_TITLE,
    ControlledBrowser,
    CourseOps21Harness,
)
from aureon.operator.local_gui_organism import (
    ACTOR_ID,
    RUNTIME_SCHEMA,
    LocalGUIOrganismConfig,
    build_local_organism,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "courseops_21"
DEFAULT_STATE_ROOT = REPO_ROOT / "state" / "course_benchmarks"
DEFAULT_EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
DEFAULT_TESSERACT = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
RUNNER_SCHEMA = "aureon-courseops-21-runner-v1"
COURSEOPS_COMPLETION_MARKER = "COURSEOPS 21 OF 21 COMPLETE"


class CourseOps21RunError(RuntimeError):
    """The sealed synthetic benchmark could not produce verified completion."""


@dataclass(frozen=True)
class VerifiedSyntheticCertificate:
    code: str
    path: str
    sha256: str
    size_bytes: int

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "path": self.path,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "classification": "synthetic_test_only",
        }


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _load_course_codes(asset_root: Path) -> tuple[str, ...]:
    try:
        manifest = json.loads((asset_root / "benchmark_manifest.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CourseOps21RunError("courseops_manifest_unreadable") from exc
    codes = manifest.get("course_codes") if isinstance(manifest, Mapping) else None
    if (
        not isinstance(codes, list)
        or len(codes) != 21
        or len(set(codes)) != 21
        or not all(isinstance(code, str) and code for code in codes)
    ):
        raise CourseOps21RunError("courseops_manifest_codes_invalid")
    return tuple(codes)


def prepare_isolated_browser_directories(
    workspace: Path,
) -> tuple[Path, Path]:
    """Create a fresh profile with an exact automatic-download preference."""

    root = Path(workspace).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=False)
    if root.is_symlink() or str(root).startswith("\\\\"):
        raise CourseOps21RunError("browser_workspace_must_be_local_and_fresh")
    profile = root / "profile"
    downloads = root / "downloads"
    default_profile = profile / "Default"
    default_profile.mkdir(parents=True)
    downloads.mkdir()
    preferences = {
        "download": {
            "default_directory": str(downloads),
            "directory_upgrade": True,
            "prompt_for_download": False,
        },
        "profile": {
            "default_content_setting_values": {
                "automatic_downloads": 1,
                "notifications": 2,
                "popups": 2,
            }
        },
        "safebrowsing": {"enabled": True},
    }
    encoded = (_canonical_json(preferences) + "\n").encode("utf-8")
    preference_path = default_profile / "Preferences"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    try:
        descriptor = os.open(preference_path, flags, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise CourseOps21RunError("browser_preferences_not_committed") from exc
    return profile, downloads


def foreground_controlled_browser(browser: ControlledBrowser, *, timeout_seconds: float = 5.0) -> None:
    """Bring only the exact controlled benchmark HWND to the foreground."""

    if sys.platform != "win32":
        raise CourseOps21RunError("controlled_browser_foreground_requires_windows")
    handle = int(browser.context.window_handle)
    if handle <= 0:
        raise CourseOps21RunError("controlled_browser_window_handle_invalid")
    user32 = ctypes.windll.user32
    if not user32.IsWindow(handle):
        raise CourseOps21RunError("controlled_browser_window_missing")
    user32.ShowWindow(handle, 9)
    user32.SetForegroundWindow(handle)
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if int(user32.GetForegroundWindow()) == handle:
            return
        time.sleep(0.05)
    raise CourseOps21RunError("controlled_browser_did_not_become_foreground")


def verify_synthetic_certificates(
    download_directory: Path,
    course_codes: Sequence[str],
) -> tuple[VerifiedSyntheticCertificate, ...]:
    root = Path(download_directory).resolve(strict=True)
    if not root.is_dir() or root.is_symlink():
        raise CourseOps21RunError("synthetic_download_directory_invalid")
    expected = {f"SYNTHETIC-TEST-ONLY-{code}.pdf": code for code in course_codes}
    actual = {path.name: path for path in root.glob("*.pdf") if path.is_file()}
    if set(actual) != set(expected):
        raise CourseOps21RunError(
            f"synthetic_certificate_set_mismatch:{len(actual)}_of_{len(expected)}"
        )
    verified: list[VerifiedSyntheticCertificate] = []
    for name in sorted(expected):
        candidate = actual[name]
        if candidate.is_symlink() or candidate.resolve().parent != root:
            raise CourseOps21RunError("synthetic_certificate_path_invalid")
        payload = candidate.read_bytes()
        if not 256 <= len(payload) <= 2 * 1024 * 1024:
            raise CourseOps21RunError("synthetic_certificate_size_invalid")
        required = (
            b"%PDF-1.4",
            b"%%EOF",
            b"SYNTHETIC TEST ONLY",
            b"Synthetic persona: John Brown",
            expected[name].encode("ascii"),
            b"No real-world qualification or provider validity",
        )
        if not payload.startswith(required[0]) or not payload.rstrip().endswith(required[1]):
            raise CourseOps21RunError("synthetic_certificate_pdf_envelope_invalid")
        if any(marker not in payload for marker in required[2:]):
            raise CourseOps21RunError("synthetic_certificate_watermark_invalid")
        verified.append(
            VerifiedSyntheticCertificate(
                code=expected[name],
                path=str(candidate),
                sha256=hashlib.sha256(payload).hexdigest(),
                size_bytes=len(payload),
            )
        )
    return tuple(verified)


def _wait_for_certificates(
    download_directory: Path,
    course_codes: Sequence[str],
    *,
    timeout_seconds: float,
) -> tuple[VerifiedSyntheticCertificate, ...]:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            return verify_synthetic_certificates(download_directory, course_codes)
        except CourseOps21RunError as exc:
            last_error = exc
            time.sleep(0.1)
    raise CourseOps21RunError("synthetic_certificates_not_settled") from last_error


def _write_summary(path: Path, payload: Mapping[str, object]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise CourseOps21RunError("runner_summary_already_exists")
    encoded = (_canonical_json(dict(payload)) + "\n").encode("utf-8")
    temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def run_courseops_21(
    *,
    browser_executable: Path = DEFAULT_EDGE,
    tesseract_executable: Path = DEFAULT_TESSERACT,
    fixture_root: Path = DEFAULT_FIXTURE_ROOT,
    state_root: Path = DEFAULT_STATE_ROOT,
    planner_kind: str = "courseops",
    model: str = "llama3:latest",
    run_id: str | None = None,
    max_steps: int = 400,
    max_seconds: float = 7_200.0,
    browser_foreground: Callable[[ControlledBrowser], None] = foreground_controlled_browser,
) -> dict[str, object]:
    """Launch the sealed fixture and let Aureon operate it end to end."""

    identifier = run_id or f"courseops21-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    state = Path(state_root).expanduser().resolve()
    state.mkdir(parents=True, exist_ok=True)
    workspace = state / f"{identifier}.workspace"
    profile, downloads = prepare_isolated_browser_directories(workspace)
    course_codes = _load_course_codes(Path(fixture_root).resolve(strict=True))
    summary_path = state / f"{identifier}.summary.json"
    browser: ControlledBrowser | None = None
    harness = CourseOps21Harness(fixture_root)
    result_payload: dict[str, object]
    try:
        server = harness.start()
        browser = harness.launch_browser(
            browser_executable,
            profile_dir=profile,
            download_dir=downloads,
            expected_window_title=EXPECTED_WINDOW_TITLE,
            window_timeout_seconds=30.0,
        )
        browser_foreground(browser)
        lease_ttl = min(24 * 60 * 60, float(max_seconds) + 300.0)
        config = LocalGUIOrganismConfig(
            goal=(
                "Using only the visible CourseOps screen, complete all 21 courses for "
                "the sealed synthetic John Brown persona, read each lesson, answer each "
                "synthetic knowledge check, download every test-only certificate, and "
                f"finish only when {COURSEOPS_COMPLETION_MARKER} is visible."
            ),
            expected_window_title=browser.context.window_title,
            expected_process_id=browser.context.browser_pid,
            allowed_actions=("move", "click", "scroll", "press", "type"),
            model=model,
            planner_kind=planner_kind,
            authorization_label="sandbox_test",
            live=True,
            lease_ttl_seconds=lease_ttl,
            max_steps=max_steps,
            max_retries_per_action=3,
            max_consecutive_unchanged=8,
            max_seconds=max_seconds,
            gateway_max_actions_per_window=300,
            run_id=identifier,
            state_directory=state,
            synthetic_assessment_asset_root=Path(fixture_root),
            synthetic_assessment_loopback_port=server.port,
            synthetic_assessment_server_pid=server.server_pid,
            synthetic_assessment_nonce=f"{identifier}:{secrets.token_hex(16)}",
            synthetic_assessment_max_actions=max_steps,
        )
        organism = build_local_organism(
            config,
            capability_token=secrets.token_urlsafe(48),
            synthetic_assessment_secret=secrets.token_bytes(48),
            tesseract_executable=tesseract_executable,
        )
        runtime_result = organism.run()
        certificates: tuple[VerifiedSyntheticCertificate, ...] = ()
        if runtime_result.success:
            certificates = _wait_for_certificates(
                downloads,
                course_codes,
                timeout_seconds=30.0,
            )
            for certificate in certificates:
                organism.ledger.record_artifact_proof(
                    certificate.path,
                    artifact_kind="certificate",
                    authorization_label="sandbox_test",
                    provider="Aureon-CourseOps-21-Synthetic",
                )
        ledger_entries = CourseBenchmarkLedger.verify(config.ledger_path)
        complete = bool(runtime_result.success and len(certificates) == 21)
        result_payload = {
            "schema_version": RUNNER_SCHEMA,
            "run_id": identifier,
            "actor": ACTOR_ID,
            "runtime_schema": RUNTIME_SCHEMA,
            "status": "completed" if complete else runtime_result.status,
            "success": complete,
            "synthetic_persona": "john-brown-synthetic-v1",
            "synthetic_test_only": True,
            "cloud_used": False,
            "planner_kind": planner_kind,
            "action_count": runtime_result.action_count,
            "verified_changed_transitions": runtime_result.verified_changed_transitions,
            "certificate_count": len(certificates),
            "certificates": [item.to_dict() for item in certificates],
            "ledger_path": str(config.ledger_path),
            "ledger_entry_count": len(ledger_entries),
            "desktop_evidence_path": str(config.desktop_evidence_path),
            "frame_artifact_directory": str(config.frame_artifact_directory),
            "download_directory": str(downloads),
            "asset_manifest_root_sha256": server.asset_manifest.root_sha256,
            "synthetic_assessment_grant_sha256": (
                organism.synthetic_assessment_controller.grant_sha256
                if organism.synthetic_assessment_controller is not None
                else ""
            ),
        }
        _write_summary(summary_path, result_payload)
        return result_payload
    finally:
        if browser is not None:
            browser.stop()
        harness.stop()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Aureon's sealed CourseOps-21 benchmark")
    parser.add_argument("--browser", type=Path, default=DEFAULT_EDGE)
    parser.add_argument("--tesseract", type=Path, default=DEFAULT_TESSERACT)
    parser.add_argument("--fixture-root", type=Path, default=DEFAULT_FIXTURE_ROOT)
    parser.add_argument("--state-root", type=Path, default=DEFAULT_STATE_ROOT)
    parser.add_argument("--planner", choices=("courseops", "ollama"), default="courseops")
    parser.add_argument("--model", default="llama3:latest")
    parser.add_argument("--run-id")
    parser.add_argument("--max-steps", type=int, default=400)
    parser.add_argument("--max-seconds", type=float, default=7_200.0)
    parser.add_argument("--live", action="store_true", help="required to launch browser and GUI")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if not args.live:
        print(_canonical_json({"ok": False, "error": "live_flag_required"}), file=sys.stderr)
        return 2
    try:
        result = run_courseops_21(
            browser_executable=args.browser,
            tesseract_executable=args.tesseract,
            fixture_root=args.fixture_root,
            state_root=args.state_root,
            planner_kind=args.planner,
            model=args.model,
            run_id=args.run_id,
            max_steps=args.max_steps,
            max_seconds=args.max_seconds,
        )
    except Exception as exc:  # noqa: BLE001 - CLI boundary prints no raw payload
        print(
            _canonical_json(
                {
                    "ok": False,
                    "error_type": type(exc).__name__,
                    "error_sha256": hashlib.sha256(str(exc).encode()).hexdigest(),
                }
            ),
            file=sys.stderr,
        )
        return 4
    print(_canonical_json(result))
    return 0 if result.get("success") is True else 4


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "COURSEOPS_COMPLETION_MARKER",
    "CourseOps21RunError",
    "VerifiedSyntheticCertificate",
    "main",
    "prepare_isolated_browser_directories",
    "run_courseops_21",
    "verify_synthetic_certificates",
]
