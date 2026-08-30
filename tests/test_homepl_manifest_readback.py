"""Focused live-readback contract tests for the Home.pl release manifest."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import subprocess
import threading
import zipfile
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import pytest

POWERSHELL = shutil.which("pwsh") or shutil.which("powershell")
SCRIPT = Path(__file__).parents[1] / "tools" / "aureon_homepl_manifest_readback.ps1"
pytestmark = pytest.mark.skipif(POWERSHELL is None, reason="PowerShell is unavailable")

SITE_ROUTE_MATRIX = {
    "/": "index.html",
    "/about/": "about/index.html",
    "/community/": "community/index.html",
    "/contact/": "contact/index.html",
    "/diligence/": "diligence/index.html",
    "/downloads/": "downloads/index.html",
    "/downloads/validation-metrics-ledger/": (
        "downloads/validation-metrics-ledger/index.html"
    ),
    "/funding/": "funding/index.html",
    "/funding/investor-deck/": "funding/investor-deck/index.html",
    "/live/": "live/index.html",
    "/projects/": "projects/index.html",
    "/projects/aureon-trading-system/": "projects/aureon-trading-system/index.html",
    "/publications/": "publications/index.html",
    "/research/": "research/index.html",
    "/research/journal/": "research/journal/index.html",
    "/updates/": "updates/index.html",
    "/vision/": "vision/index.html",
}

SENSITIVE_PATHS = {
    "/.htaccess",
    "/.env",
    "/.env1",
    "/.git/config",
    "/archive/",
    "/backup/",
    "/public_html/",
    "/styleguide.html",
    "/release.zip",
    "/deployment.log",
    "/tools/aureon_homepl_manifest_readback.ps1",
}

SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; object-src 'none'; frame-ancestors 'none'"
    ),
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), geolocation=(), microphone=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
}


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def _release_fixture(
    tmp_path: Path,
    *,
    public_bytes: bytes = b"public\n",
    package_htaccess_bytes: bytes | None = None,
) -> tuple[Path, Path, Path, Path, bytes]:
    source_root = tmp_path / "website"
    source_root.mkdir()
    htaccess_bytes = b"Options -Indexes\n"
    (source_root / ".htaccess").write_bytes(htaccess_bytes)
    (source_root / "index.html").write_bytes(public_bytes)

    manifest_path = tmp_path / "manifest.csv"
    with manifest_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=("Path", "Bytes", "Sha256"))
        writer.writeheader()
        for relative, content in (
            (".htaccess", htaccess_bytes),
            ("index.html", public_bytes),
        ):
            writer.writerow(
                {
                    "Path": relative,
                    "Bytes": len(content),
                    "Sha256": _sha(content),
                }
            )

    package_path = tmp_path / "release.zip"
    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            ".htaccess",
            htaccess_bytes if package_htaccess_bytes is None else package_htaccess_bytes,
        )
        archive.writestr("index.html", public_bytes)
    return source_root, manifest_path, package_path, tmp_path / "report.json", htaccess_bytes


def _site_contract_fixture(
    tmp_path: Path,
) -> tuple[Path, Path, Path, Path, dict[str, bytes]]:
    source_root = tmp_path / "website"
    source_root.mkdir()
    payloads = {
        ".htaccess": b"Options -Indexes\n",
        "404.html": b"custom missing page\n",
        "styles.css": b":root { color: #fff; }\n",
        "data/publications.json": b'{"records":[]}\n',
    }
    for manifest_path in SITE_ROUTE_MATRIX.values():
        payloads.setdefault(manifest_path, f"route:{manifest_path}\n".encode())

    for relative, content in payloads.items():
        destination = source_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)

    manifest_path = tmp_path / "manifest.csv"
    with manifest_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=("Path", "Bytes", "Sha256"))
        writer.writeheader()
        for relative in sorted(payloads):
            content = payloads[relative]
            writer.writerow(
                {
                    "Path": relative,
                    "Bytes": len(content),
                    "Sha256": _sha(content),
                }
            )

    package_path = tmp_path / "release.zip"
    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative in sorted(payloads):
            archive.writestr(relative, payloads[relative])
    return source_root, manifest_path, package_path, tmp_path / "report.json", payloads


@contextmanager
def _readback_server(
    *,
    protected_status: int,
    protected_bytes: bytes,
    public_status: int = 200,
    public_bytes: bytes = b"public\n",
):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - stdlib callback name
            path = urlsplit(self.path).path
            if path == "/.htaccess":
                status = protected_status
                body = protected_bytes if status == 200 else b"not public"
                self.send_response(status)
                if status == 302:
                    self.send_header("Location", "/index.html")
            elif path == "/index.html":
                status = public_status
                body = public_bytes if status == 200 else b"missing"
                self.send_response(status)
            else:
                status = 404
                body = b"missing"
                self.send_response(status)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@contextmanager
def _site_contract_server(
    *,
    payloads: dict[str, bytes],
    missing_header: str | None = None,
    route_failure: str | None = None,
    exposed_sensitive_path: str | None = None,
):
    lower_missing_header = (missing_header or "").lower()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - stdlib callback name
            path = urlsplit(self.path).path
            status = 200
            if path in SENSITIVE_PATHS:
                if path == exposed_sensitive_path:
                    body = b"unexpectedly public sensitive content"
                else:
                    status = 404
                    body = payloads["404.html"]
            elif path.startswith("/__aureon-release-probe__/"):
                status = 404
                body = payloads["404.html"]
            elif path in SITE_ROUTE_MATRIX:
                if path == route_failure:
                    status = 404
                    body = payloads["404.html"]
                else:
                    body = payloads[SITE_ROUTE_MATRIX[path]]
            else:
                manifest_path = path.lstrip("/")
                if manifest_path in payloads:
                    body = payloads[manifest_path]
                else:
                    status = 404
                    body = payloads["404.html"]

            self.send_response(status)
            for name, value in SECURITY_HEADERS.items():
                if name.lower() != lower_missing_header:
                    self.send_header(name, value)
            if path == "/styles.css":
                self.send_header(
                    "Cache-Control",
                    "public, max-age=31536000, immutable",
                )
                self.send_header("Content-Type", "text/css")
            elif path == "/data/publications.json":
                self.send_header(
                    "Cache-Control",
                    "public, max-age=3600, must-revalidate",
                )
                self.send_header("Content-Type", "application/json")
            else:
                self.send_header(
                    "Cache-Control",
                    "no-cache, no-store, must-revalidate",
                )
                self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _run_readback(
    source_root: Path,
    manifest_path: Path,
    package_path: Path,
    output_path: Path,
    base_url: str,
    *,
    skip_site_contract: bool = True,
) -> subprocess.CompletedProcess[str]:
    command = [
        str(POWERSHELL),
        "-NoLogo",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(SCRIPT),
        "-ManifestPath",
        str(manifest_path),
        "-SourceRoot",
        str(source_root),
        "-PackagePath",
        str(package_path),
        "-OutputPath",
        str(output_path),
        "-BaseUrl",
        base_url,
    ]
    if skip_site_contract:
        command.append("-SkipSiteContract")
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=45,
        check=False,
    )


@pytest.mark.parametrize("protected_status", [403, 404])
def test_htaccess_package_hash_and_public_denial_are_both_required(
    tmp_path: Path,
    protected_status: int,
) -> None:
    source, manifest, package, output, htaccess_bytes = _release_fixture(tmp_path)
    with _readback_server(
        protected_status=protected_status,
        protected_bytes=htaccess_bytes,
    ) as base_url:
        result = _run_readback(source, manifest, package, output, base_url)

    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(output.read_text(encoding="utf-8-sig"))
    assert report["summary"]["successful"] == 2
    assert report["summary"]["exact"] == 1
    assert report["summary"]["protected_non_public"] == 1
    assert report["summary"]["failures"] == 0
    assert report["protected_file_proof"]["package_manifest_exact"] is True
    protected = next(item for item in report["results"] if item["path"] == ".htaccess")
    assert protected["mode"] == "package_exact_http_denied"
    assert protected["status"] == protected_status


def test_publicly_exposed_htaccess_fails_even_when_bytes_are_exact(tmp_path: Path) -> None:
    source, manifest, package, output, htaccess_bytes = _release_fixture(tmp_path)
    with _readback_server(
        protected_status=200,
        protected_bytes=htaccess_bytes,
    ) as base_url:
        result = _run_readback(source, manifest, package, output, base_url)

    assert result.returncode == 1
    report = json.loads(output.read_text(encoding="utf-8-sig"))
    failure = next(item for item in report["failures"] if item["path"] == ".htaccess")
    assert failure["status"] == 200
    assert "expected HTTP 403 or 404" in failure["reason"]


def test_htaccess_redirect_is_not_treated_as_denial(tmp_path: Path) -> None:
    source, manifest, package, output, htaccess_bytes = _release_fixture(tmp_path)
    with _readback_server(
        protected_status=302,
        protected_bytes=htaccess_bytes,
    ) as base_url:
        result = _run_readback(source, manifest, package, output, base_url)

    assert result.returncode == 1
    report = json.loads(output.read_text(encoding="utf-8-sig"))
    failure = next(item for item in report["failures"] if item["path"] == ".htaccess")
    assert failure["status"] == 302


def test_other_manifest_paths_still_require_exact_http_hash(tmp_path: Path) -> None:
    source, manifest, package, output, htaccess_bytes = _release_fixture(tmp_path)
    with _readback_server(
        protected_status=403,
        protected_bytes=htaccess_bytes,
        public_bytes=b"Public\n",
    ) as base_url:
        result = _run_readback(source, manifest, package, output, base_url)

    assert result.returncode == 1
    report = json.loads(output.read_text(encoding="utf-8-sig"))
    failure = next(item for item in report["failures"] if item["path"] == "index.html")
    assert failure["status"] == 200
    assert failure["reason"] == "HTTP content SHA-256 mismatch"


def test_other_manifest_paths_still_require_public_http_200(tmp_path: Path) -> None:
    source, manifest, package, output, htaccess_bytes = _release_fixture(tmp_path)
    with _readback_server(
        protected_status=403,
        protected_bytes=htaccess_bytes,
        public_status=404,
    ) as base_url:
        result = _run_readback(source, manifest, package, output, base_url)

    assert result.returncode == 1
    report = json.loads(output.read_text(encoding="utf-8-sig"))
    failure = next(item for item in report["failures"] if item["path"] == "index.html")
    assert failure["status"] == 404
    assert failure["reason"] == "HTTP 404"


def test_htaccess_manifest_hash_must_match_the_package_entry(tmp_path: Path) -> None:
    source, manifest, package, output, htaccess_bytes = _release_fixture(
        tmp_path,
        package_htaccess_bytes=b"Options +Indexes\n",
    )
    with _readback_server(
        protected_status=403,
        protected_bytes=htaccess_bytes,
    ) as base_url:
        result = _run_readback(source, manifest, package, output, base_url)

    assert result.returncode != 0
    assert not output.exists()
    assert ".htaccess package bytes do not match its manifest hash" in (
        result.stdout + result.stderr
    )


def test_full_site_contract_proves_routes_404_sensitive_paths_and_headers(
    tmp_path: Path,
) -> None:
    source, manifest, package, output, payloads = _site_contract_fixture(tmp_path)
    with _site_contract_server(payloads=payloads) as base_url:
        result = _run_readback(
            source,
            manifest,
            package,
            output,
            base_url,
            skip_site_contract=False,
        )

    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(output.read_text(encoding="utf-8-sig"))
    assert report["summary"]["manifest_failures"] == 0
    assert report["summary"]["site_contract_enabled"] is True
    assert report["summary"]["site_contract_checks"] == 41
    assert report["summary"]["site_contract_failures"] == 0
    assert report["summary"]["failures"] == 0
    modes = {item["mode"] for item in report["site_contract"]["results"]}
    assert {
        "friendly_route_exact",
        "custom_404_exact",
        "sensitive_path_denied",
        "required_header_present",
        "cache_policy_present",
    }.issubset(modes)


def test_full_site_contract_fails_when_security_header_is_missing(
    tmp_path: Path,
) -> None:
    source, manifest, package, output, payloads = _site_contract_fixture(tmp_path)
    with _site_contract_server(
        payloads=payloads,
        missing_header="Content-Security-Policy",
    ) as base_url:
        result = _run_readback(
            source,
            manifest,
            package,
            output,
            base_url,
            skip_site_contract=False,
        )

    assert result.returncode == 1
    report = json.loads(output.read_text(encoding="utf-8-sig"))
    failure = next(
        item
        for item in report["site_contract"]["failures"]
        if item["kind"] == "root-header"
    )
    assert "content-security-policy" in failure["reason"]


def test_full_site_contract_fails_when_friendly_route_is_not_exact(
    tmp_path: Path,
) -> None:
    source, manifest, package, output, payloads = _site_contract_fixture(tmp_path)
    with _site_contract_server(
        payloads=payloads,
        route_failure="/research/",
    ) as base_url:
        result = _run_readback(
            source,
            manifest,
            package,
            output,
            base_url,
            skip_site_contract=False,
        )

    assert result.returncode == 1
    report = json.loads(output.read_text(encoding="utf-8-sig"))
    failure = next(
        item
        for item in report["site_contract"]["failures"]
        if item["kind"] == "friendly-route" and item["path"] == "/research/"
    )
    assert failure["status"] == 404


def test_full_site_contract_fails_when_sensitive_path_is_public(
    tmp_path: Path,
) -> None:
    source, manifest, package, output, payloads = _site_contract_fixture(tmp_path)
    with _site_contract_server(
        payloads=payloads,
        exposed_sensitive_path="/.env",
    ) as base_url:
        result = _run_readback(
            source,
            manifest,
            package,
            output,
            base_url,
            skip_site_contract=False,
        )

    assert result.returncode == 1
    report = json.loads(output.read_text(encoding="utf-8-sig"))
    failure = next(
        item
        for item in report["site_contract"]["failures"]
        if item["kind"] == "sensitive-path" and item["path"] == "/.env"
    )
    assert failure["status"] == 200
