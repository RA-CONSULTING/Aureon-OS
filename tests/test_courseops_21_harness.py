from __future__ import annotations

import http.client
import os
import shutil
from pathlib import Path

import pytest

from aureon.operator.courseops_21_harness import (
    SERVED_ASSETS,
    CourseOps21AssetError,
    CourseOps21BrowserError,
    CourseOps21Harness,
    CourseOps21HarnessError,
)
from aureon.operator.synthetic_assessment_grant import build_asset_manifest

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "courseops_21"


def _request(
    harness: CourseOps21Harness,
    path: str,
    *,
    method: str = "GET",
) -> tuple[int, dict[str, str], bytes]:
    context = harness.context
    connection = http.client.HTTPConnection(context.host, context.port, timeout=3.0)
    try:
        connection.request(method, path)
        response = connection.getresponse()
        return response.status, {key.casefold(): value for key, value in response.getheaders()}, response.read()
    finally:
        connection.close()


def _copy_fixture(destination: Path) -> Path:
    shutil.copytree(FIXTURE_ROOT, destination)
    return destination


def test_loopback_server_exposes_hash_bound_context_and_only_course_assets() -> None:
    harness = CourseOps21Harness(FIXTURE_ROOT)
    with harness:
        context = harness.context
        expected_manifest = build_asset_manifest(FIXTURE_ROOT)

        assert context.host == "127.0.0.1"
        assert context.port > 0
        assert context.origin == f"http://127.0.0.1:{context.port}"
        assert context.server_pid == os.getpid()
        assert Path(context.root) == FIXTURE_ROOT.resolve()
        assert context.asset_manifest == expected_manifest
        assert context.to_dict()["served_assets"] == list(SERVED_ASSETS)
        assert context.to_dict()["asset_manifest"] == expected_manifest.to_dict()

        for route, asset_name in (
            ("/", "index.html"),
            ("/index.html", "index.html"),
            ("/app.js", "app.js"),
            ("/styles.css", "styles.css"),
            ("/benchmark_manifest.json", "benchmark_manifest.json"),
        ):
            status, headers, body = _request(harness, route)
            entry = next(item for item in expected_manifest.files if item.path == asset_name)
            assert status == http.client.OK
            assert body == (FIXTURE_ROOT / asset_name).read_bytes()
            assert headers["etag"] == f'"sha256:{entry.sha256}"'
            assert headers["cache-control"] == "no-store, max-age=0"
            assert headers["x-content-type-options"] == "nosniff"
            assert headers["x-frame-options"] == "DENY"
            assert headers["referrer-policy"] == "no-referrer"
            assert "connect-src 'none'" in headers["content-security-policy"]
            assert "frame-ancestors 'none'" in headers["content-security-policy"]

        status, headers, body = _request(harness, "/index.html", method="HEAD")
        assert status == http.client.OK
        assert int(headers["content-length"]) == (FIXTURE_ROOT / "index.html").stat().st_size
        assert body == b""

    with pytest.raises(CourseOps21HarnessError, match="not running"):
        _ = harness.context


@pytest.mark.parametrize(
    "path",
    [
        "/README.md",
        "/../README.md",
        "/%2e%2e/README.md",
        "/index%2ehtml",
        "/index.html?cache=1",
        "/app.js/extra",
        "//example.invalid/index.html",
    ],
)
def test_server_rejects_unlisted_nonliteral_and_traversal_routes(path: str) -> None:
    with CourseOps21Harness(FIXTURE_ROOT) as harness:
        status, headers, body = _request(harness, path)

    assert status == http.client.NOT_FOUND
    assert body == b"not found\n"
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["cache-control"] == "no-store, max-age=0"


def test_server_rejects_mutating_http_methods() -> None:
    with CourseOps21Harness(FIXTURE_ROOT) as harness:
        status, headers, body = _request(harness, "/index.html", method="POST")

    assert status == http.client.METHOD_NOT_ALLOWED
    assert headers["allow"] == "GET, HEAD"
    assert body == b"method not allowed\n"


def test_server_fails_closed_if_a_frozen_asset_changes(tmp_path: Path) -> None:
    root = _copy_fixture(tmp_path / "suite")
    harness = CourseOps21Harness(root)
    with harness:
        frozen_hash = harness.context.asset_manifest.root_sha256
        (root / "app.js").write_text(
            (root / "app.js").read_text(encoding="utf-8") + "\n// changed after seal\n",
            encoding="utf-8",
        )
        status, _headers, body = _request(harness, "/app.js")

        assert harness.context.asset_manifest.root_sha256 == frozen_hash

    assert status == http.client.SERVICE_UNAVAILABLE
    assert body == b"asset integrity check failed\n"
    assert b"changed after seal" not in body


def test_server_rejects_a_symlinked_served_asset(tmp_path: Path) -> None:
    root = _copy_fixture(tmp_path / "suite")
    outside = tmp_path / "outside.js"
    outside.write_bytes((root / "app.js").read_bytes())
    (root / "app.js").unlink()
    try:
        os.symlink(outside, root / "app.js")
    except OSError as exc:
        pytest.skip(f"file symlink unavailable: {type(exc).__name__}")

    with pytest.raises(CourseOps21AssetError, match="safe asset root"):
        CourseOps21Harness(root).start()


def test_server_rejects_non_synthetic_or_incomplete_manifest(tmp_path: Path) -> None:
    root = _copy_fixture(tmp_path / "suite")
    manifest_path = root / "benchmark_manifest.json"
    text = manifest_path.read_text(encoding="utf-8")
    manifest_path.write_text(text.replace('"synthetic": true', '"synthetic": false'), encoding="utf-8")

    with pytest.raises(CourseOps21AssetError, match="explicitly synthetic"):
        CourseOps21Harness(root).start()


def test_browser_plan_is_side_effect_free_and_pins_loopback_profile_and_downloads(
    tmp_path: Path,
) -> None:
    executable = tmp_path / "msedge.exe"
    executable.write_bytes(b"not launched by this test")
    profile = tmp_path / "isolated-profile"
    downloads = tmp_path / "synthetic-downloads"

    with CourseOps21Harness(FIXTURE_ROOT) as harness:
        plan = harness.build_browser_launch_plan(
            executable,
            profile_dir=profile,
            download_dir=downloads,
        )
        context = harness.context

    assert plan.executable == str(executable.resolve())
    assert plan.profile_dir == str(profile.resolve())
    assert plan.download_dir == str(downloads.resolve())
    assert plan.url == context.origin
    assert plan.server_pid == os.getpid()
    assert plan.asset_manifest_root_sha256 == context.asset_manifest.root_sha256
    assert f"--user-data-dir={profile.resolve()}" in plan.command
    assert f"--download-default-directory={downloads.resolve()}" in plan.command
    assert "--host-resolver-rules=MAP * 0.0.0.0, EXCLUDE 127.0.0.1" in plan.command
    assert plan.command[-1] == context.origin
    assert not profile.exists()
    assert not downloads.exists()


def test_browser_plan_rejects_non_edge_or_chrome_executable(tmp_path: Path) -> None:
    executable = tmp_path / "firefox.exe"
    executable.write_bytes(b"not a permitted browser")

    with (
        CourseOps21Harness(FIXTURE_ROOT) as harness,
        pytest.raises(CourseOps21BrowserError, match="Chrome or Edge"),
    ):
        harness.build_browser_launch_plan(
            executable,
            profile_dir=tmp_path / "profile",
            download_dir=tmp_path / "downloads",
        )


def test_start_is_single_use_until_stopped() -> None:
    harness = CourseOps21Harness(FIXTURE_ROOT)
    harness.start()
    try:
        with pytest.raises(CourseOps21HarnessError, match="already running"):
            harness.start()
    finally:
        harness.stop()
    harness.stop()
