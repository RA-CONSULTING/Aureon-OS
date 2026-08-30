"""Tests for the static-website tooling: auditor, packager, and FTP deployer.

Offline and hermetic — the auditor/packager run against tiny fixtures built in ``tmp_path`` (and
the real ``website/`` for the clean-site assertion); the FTP deployer is exercised only via its
env-gating and dry-run plan (never a real network connection).
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
import socket
import ssl
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from scripts.website import audit_site, build_package, ftp_deploy, readback

_REPO = Path(__file__).resolve().parents[1]
_TEST_COMMIT = "1" * 40

_GOOD_INDEX = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Test Site</title>
  <meta name="description" content="A test site.">
  <link rel="canonical" href="https://aureonzorzatechnologies.pl/">
  <meta property="og:url" content="https://aureonzorzatechnologies.pl/">
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <a class="skip-link" href="#main-content">Skip to content</a>
  <main id="main-content">
    <h1>Hello</h1>
    <img src="assets/pic.webp" alt="A picture" loading="lazy" decoding="async">
    <a href="https://github.com/x" target="_blank" rel="noopener noreferrer">External</a>
  </main>
  <script src="script.js"></script>
</body>
</html>
"""

_SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://aureonzorzatechnologies.pl/</loc></url>
</urlset>
"""

_ROBOTS = "User-agent: *\nAllow: /\n\nSitemap: https://aureonzorzatechnologies.pl/sitemap.xml\n"


def _make_good_site(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "index.html").write_text(_GOOD_INDEX, encoding="utf-8")
    (root / "styles.css").write_text("body{color:#000}\n", encoding="utf-8")
    (root / "script.js").write_text("// noop\n", encoding="utf-8")
    (root / "robots.txt").write_text(_ROBOTS, encoding="utf-8")
    (root / "sitemap.xml").write_text(_SITEMAP, encoding="utf-8")
    (root / "assets").mkdir()
    (root / "assets" / "pic.webp").write_bytes(b"RIFF0000WEBP")
    return root


def _errors(root: Path) -> list[audit_site.Finding]:
    return [f for f in audit_site.audit(root) if f.level == "ERROR"]


# ---------------------------------------------------------------------------
# auditor
# ---------------------------------------------------------------------------


def test_good_site_has_no_errors(tmp_path):
    root = _make_good_site(tmp_path / "site")
    assert _errors(root) == []


def test_real_website_is_clean():
    root = _REPO / "website"
    if not root.is_dir():
        pytest.skip("website/ not present")
    errs = _errors(root)
    assert errs == [], f"real site has audit errors: {[(e.page, e.check) for e in errs]}"


def test_public_footprint_snapshot_matches_marked_surfaces():
    root = _REPO / "website"
    snapshot = json.loads((root / "data" / "public-attention-snapshot.json").read_text(encoding="utf-8"))
    assert snapshot["as_of"] == "2026-08-21"
    signals = {signal["metric"]: signal for signal in snapshot["signals"]}
    pages = {
        "home": (root / "index.html").read_text(encoding="utf-8"),
        "research": (root / "research" / "index.html").read_text(encoding="utf-8"),
        "investor": (root / "funding" / "investor-deck" / "index.html").read_text(encoding="utf-8"),
    }

    required_pages = {
        "public_work_groups": ("home", "research", "investor"),
        "main_branch_commits": ("home",),
        "research_reads": ("home", "investor"),
    }
    for metric, page_names in required_pages.items():
        formatted = f"{signals[metric]['value']:,}"
        marker = re.compile(rf'data-footprint-value="{re.escape(metric)}">{re.escape(formatted)}<')
        for page_name in page_names:
            assert marker.search(pages[page_name]), f"{page_name} fallback drifted from {metric}={formatted}"

    github = signals["main_branch_commits"]
    github_summary = (
        f"{github['value']:,} commits &middot; "
        f"{github['secondary_metrics']['stars']} stars &middot; "
        f"{github['secondary_metrics']['forks']} forks"
    )
    assert github_summary in pages["investor"]
    assert github["measurement_window"] == "public repository snapshot on 2026-08-21"
    assert "32 stars &middot; 11 forks &middot; 21 Aug 2026" in pages["home"]
    assert "GitHub &middot; public repository snapshot &middot; 21 Aug 2026" in pages["investor"]

    updates = json.loads((root / "data" / "updates.json").read_text(encoding="utf-8"))
    github_updates = [item for item in updates if item["id"].startswith("github-public-engineering-")]
    assert len(github_updates) == 1
    assert github_updates[0]["id"] == "github-public-engineering-20260821"
    assert github_updates[0]["date"] == "2026-08-21"
    assert "as of 21 August 2026" in github_updates[0]["summary"]
    assert "checked 21 Aug 2026" in github_updates[0]["source_name"]

    script = (root / "script.js").read_text(encoding="utf-8")
    assert 'loadJson("data/public-attention-snapshot.json")' in script
    assert "forks · 21 Aug 2026`" in script


def test_portfolio_cards_bind_public_sources_and_keep_claim_boundaries():
    page = (_REPO / "website" / "projects" / "index.html").read_text(encoding="utf-8")

    def card(title: str) -> str:
        title_index = page.index(f"<h4>{title}</h4>")
        start = page.rfind('<article class="portfolio-card">', 0, title_index)
        end = page.index("</article>", title_index) + len("</article>")
        return html.unescape(page[start:end])

    materials = card("Auditable materials and signal authentication")
    assert "https://zenodo.org/records/17531249" in materials
    assert "https://github.com/RA-CONSULTING/Aureon-OS" in materials
    assert "software and simulation only, with independent reproduction still open" in materials
    assert "This is software and simulation research." in materials
    assert "independently reproduced result" in materials

    fipam = card("HNC-FIPAM photonic integration")
    assert "https://garyleckey.substack.com/p/can-you-replace-a-laser-mirror-with" in fipam
    assert "https://zenodo.org/records/21540072" in fipam
    assert "HNC-FIPAM remains a company-authored, unmeasured design study." in fipam
    assert "No hardware has been built." in fipam
    assert "No measured device performance" in fipam
    assert "design calculator" not in fipam.casefold()
    assert "partner brief" not in fipam.casefold()


def test_investor_validated_route_signals_match_bounded_public_contract():
    page = (_REPO / "website" / "funding" / "investor-deck" / "index.html").read_text(encoding="utf-8")
    match = re.search(
        r'<section class="band validated-route-signals".*?</section>',
        page,
        flags=re.DOTALL,
    )
    assert match, "investor brief is missing the validated route-signals block"
    block = html.unescape(match.group(0)).replace("\u2019", "'")

    expected_claims = (
        "EPCC's commercial manager invited a meeting to discuss how the parties could work together on an application to the EPSRC Future Computing Paradigms Network Plus call; a meeting time was accepted.",
        "The University of Edinburgh's business-development route introduced Dr Michio Honda and arranged a discussion about the potential for Aureon Zorza Technologies to participate as an industry partner in an EPSRC bid.",
        "InterTradeIreland approved R&A Consulting and Brokerage Services Ltd for the first-stage Trade Export Pathway Export On-boarding.",
        "Invest NI completed an initial review and referred the company to its Belfast Regional Office for follow-up.",
    )
    assert block.count('class="route-signal-card"') == 4
    for claim in expected_claims:
        assert claim in block

    required_boundary = (
        "These are verified route-progress signals, not grants, partnerships, customers, "
        "funding awards or investment."
    )
    assert required_boundary in block
    for private_detail in ("message id", "thread id", "@", "£", "€"):
        assert private_detail not in block.casefold()


def test_missing_alt_is_error(tmp_path):
    root = _make_good_site(tmp_path / "site")
    html = (
        (root / "index.html")
        .read_text()
        .replace(
            '<img src="assets/pic.webp" alt="A picture" loading="lazy" decoding="async">',
            '<img src="assets/pic.webp" loading="lazy">',
        )
    )
    (root / "index.html").write_text(html)
    assert any(e.check == "a11y-img-alt" for e in _errors(root))


def test_dead_asset_is_error(tmp_path):
    root = _make_good_site(tmp_path / "site")
    html = (root / "index.html").read_text().replace("assets/pic.webp", "assets/missing.webp")
    (root / "index.html").write_text(html)
    assert any(e.check == "dead-asset" for e in _errors(root))


def test_og_url_mismatch_is_error(tmp_path):
    root = _make_good_site(tmp_path / "site")
    html = (
        (root / "index.html")
        .read_text()
        .replace(
            '<meta property="og:url" content="https://aureonzorzatechnologies.pl/">',
            '<meta property="og:url" content="https://aureonzorzatechnologies.pl/other/">',
        )
    )
    (root / "index.html").write_text(html)
    assert any(e.check == "seo-og-url" for e in _errors(root))


def test_sitemap_drift_is_error(tmp_path):
    root = _make_good_site(tmp_path / "site")
    (root / "about").mkdir()
    (root / "about" / "index.html").write_text(
        _GOOD_INDEX.replace(
            "https://aureonzorzatechnologies.pl/", "https://aureonzorzatechnologies.pl/about/"
        ),
        encoding="utf-8",
    )
    # about/ is indexable but not in the sitemap → drift
    assert any(e.check == "sitemap-missing" for e in _errors(root))


def test_blank_link_without_noopener_is_error(tmp_path):
    root = _make_good_site(tmp_path / "site")
    html = (
        (root / "index.html")
        .read_text()
        .replace(
            '<a href="https://github.com/x" target="_blank" rel="noopener noreferrer">External</a>',
            '<a href="https://github.com/x" target="_blank">External</a>',
        )
    )
    (root / "index.html").write_text(html)
    assert any(e.check == "a11y-noopener" for e in _errors(root))


def test_broken_skip_target_is_error(tmp_path):
    root = _make_good_site(tmp_path / "site")
    html = (root / "index.html").read_text().replace('<main id="main-content">', "<main>")
    (root / "index.html").write_text(html)
    assert any(e.check == "a11y-skip-target" for e in _errors(root))


# ---------------------------------------------------------------------------
# packager
# ---------------------------------------------------------------------------


def test_build_is_deterministic_and_checksum_matches(tmp_path):
    root = _make_good_site(tmp_path / "site")
    a = build_package.build(
        root,
        tmp_path / "out_a",
        created_at="2026-01-01T00:00:00Z",
        source_commit=_TEST_COMMIT,
    )
    b = build_package.build(
        root,
        tmp_path / "out_b",
        created_at="2026-01-01T00:00:00Z",
        source_commit=_TEST_COMMIT,
    )

    zip_a = Path(a["zip_path"]).read_bytes()
    zip_b = Path(b["zip_path"]).read_bytes()
    assert zip_a == zip_b, "two builds at the same created-at must be byte-identical"
    assert a["zip_sha256"] == hashlib.sha256(zip_a).hexdigest() == b["zip_sha256"]

    pkg = Path(a["package_dir"])
    assert (pkg / "index.html").is_file()  # index.html at package root
    manifest = (pkg / build_package.MANIFEST_NAME).read_text()
    package_files = [p for p in pkg.rglob("*") if p.is_file()]
    assert f"TOTAL_FILE_COUNT: {len(package_files):06d}" in manifest
    assert f"SOURCE_COMMIT: {_TEST_COMMIT}" in manifest
    assert "HTACCESS_SECURITY_CONFIGURATION_INCLUDED: NO" in manifest
    assert "HTACCESS_REQUIRED" not in manifest
    file_hashes, file_hash_bytes = readback.load_file_hash_manifest(pkg)
    assert file_hashes.source_commit == _TEST_COMMIT
    assert [record.path for record in file_hashes.records] == sorted(
        record.path for record in file_hashes.records
    )
    assert build_package.FILE_HASH_MANIFEST_NAME not in {record.path for record in file_hashes.records}
    assert build_package.MANIFEST_NAME in {record.path for record in file_hashes.records}
    assert len(file_hashes.records) == len(package_files) - 1
    companion = Path(a["companion"]).read_text()
    assert a["zip_sha256"] in companion and str(a["zip_size"]) in companion
    assert hashlib.sha256(file_hash_bytes).hexdigest() in companion
    assert f"SOURCE_COMMIT: {_TEST_COMMIT}" in companion


def test_build_requires_a_complete_explicit_source_commit(tmp_path):
    root = _make_good_site(tmp_path / "site")
    for invalid in ("", "abc", "g" * 40, "1" * 39, "1" * 41):
        with pytest.raises(RuntimeError, match="source commit"):
            build_package.build(
                root,
                tmp_path / f"out-{len(invalid)}",
                created_at="2026-01-01T00:00:00Z",
                source_commit=invalid,
            )
    with pytest.raises(SystemExit) as exc:
        build_package.main(["--root", str(root), "--out", str(tmp_path / "cli-out")])
    assert exc.value.code == 2


def test_repository_build_binds_head_and_rejects_mismatch_or_dirty_site(tmp_path, monkeypatch):
    repository = tmp_path / "repo"
    site = _make_good_site(repository / "website")
    head = "a" * 40
    status_output = {"value": ""}

    def fake_git(_root, *args):
        if args == ("rev-parse", "--show-toplevel"):
            return subprocess.CompletedProcess(args, 0, stdout=str(repository), stderr="")
        if args == ("rev-parse", "HEAD"):
            return subprocess.CompletedProcess(args, 0, stdout=head, stderr="")
        if args[:3] == ("status", "--porcelain=v1", "--untracked-files=all"):
            return subprocess.CompletedProcess(args, 0, stdout=status_output["value"], stderr="")
        raise AssertionError(f"unexpected git arguments: {args}")

    monkeypatch.setattr(build_package, "_git", fake_git)

    result = build_package.build(
        site,
        tmp_path / "clean-out",
        created_at="2026-01-01T00:00:00Z",
        source_commit=head,
    )
    assert result["source_commit_verification"] == "verified-git-head-clean-site"
    with pytest.raises(RuntimeError, match="does not match checked-out HEAD"):
        build_package.build(
            site,
            tmp_path / "mismatch-out",
            created_at="2026-01-01T00:00:00Z",
            source_commit="0" * 40,
        )

    status_output["value"] = " M website/styles.css\n"
    with pytest.raises(RuntimeError, match="changes not represented"):
        build_package.build(
            site,
            tmp_path / "dirty-out",
            created_at="2026-01-01T00:00:00Z",
            source_commit=head,
        )


def test_directory_and_http_readback_compare_exact_bytes_without_secret_material(tmp_path):
    site = _make_good_site(tmp_path / "site")
    result = build_package.build(
        site,
        tmp_path / "release",
        created_at="2026-01-01T00:00:00Z",
        source_commit=_TEST_COMMIT,
    )
    package = Path(result["package_dir"])
    downloaded = tmp_path / "downloaded"
    shutil.copytree(package, downloaded)

    directory_report = readback.compare_readback_directory(package, downloaded)
    assert directory_report.passed is True
    assert directory_report.expected_file_count == directory_report.observed_file_count

    manifest, manifest_bytes = readback.load_file_hash_manifest(package)
    observations = {
        readback.FILE_HASH_MANIFEST_NAME: readback.HttpObservation(200, manifest_bytes),
        **{
            record.path: readback.HttpObservation(200, (package / record.path).read_bytes())
            for record in manifest.records
        },
    }
    http_report = readback.compare_http_observations(package, observations)
    assert http_report.passed is True
    serialised = json.dumps(http_report.to_dict(), sort_keys=True)
    assert "SECRET" not in serialised
    assert '"network_access_performed": false' in serialised
    assert '"credentials_recorded": false' in serialised

    (downloaded / "index.html").write_bytes(b"tampered")
    mismatch = readback.compare_readback_directory(package, downloaded)
    assert mismatch.passed is False
    assert {(item.path, item.check) for item in mismatch.findings} >= {
        ("index.html", "bytes"),
        ("index.html", "sha256"),
    }
    observations["index.html"] = readback.HttpObservation(404, b"SECRET-RESPONSE-BODY")
    http_mismatch = readback.compare_http_observations(package, observations)
    assert http_mismatch.passed is False
    mismatch_text = json.dumps(http_mismatch.to_dict(), sort_keys=True)
    assert "SECRET-RESPONSE-BODY" not in mismatch_text
    assert any(item.check == "http-status" for item in http_mismatch.findings)

    (downloaded / "stale-july-route.html").write_text("old public file", encoding="utf-8")
    stale_file = readback.compare_readback_directory(package, downloaded)
    assert stale_file.passed is False
    assert any(
        item.path == "stale-july-route.html" and item.check == "unexpected-file"
        for item in stale_file.findings
    )
    assert stale_file.observed_file_count == stale_file.expected_file_count + 1


def test_file_hash_manifest_rejects_unsafe_self_or_unsorted_records():
    record = {"path": "index.html", "bytes": 1, "sha256": "0" * 64}
    base = {
        "algorithm": "sha256",
        "manifest_self_included": False,
        "record_count": 1,
        "records": [record],
        "schema": readback.FILE_HASH_MANIFEST_SCHEMA,
        "source_commit": _TEST_COMMIT,
    }
    assert readback.parse_file_hash_manifest(json.dumps(base)).records[0].path == "index.html"
    for unsafe in ("../index.html", "/index.html", readback.FILE_HASH_MANIFEST_NAME):
        mutated = {**base, "records": [{**record, "path": unsafe}]}
        with pytest.raises(readback.ReadbackInputError):
            readback.parse_file_hash_manifest(json.dumps(mutated))
    unsorted = {
        **base,
        "record_count": 2,
        "records": [
            {**record, "path": "z.html"},
            {**record, "path": "a.html"},
        ],
    }
    with pytest.raises(readback.ReadbackInputError, match="unique and sorted"):
        readback.parse_file_hash_manifest(json.dumps(unsorted))


def test_build_aborts_on_audit_error(tmp_path):
    root = _make_good_site(tmp_path / "site")
    (root / "index.html").write_text(
        (root / "index.html").read_text().replace("assets/pic.webp", "assets/missing.webp")
    )
    with pytest.raises(RuntimeError):
        build_package.build(
            root,
            tmp_path / "out",
            created_at="2026-01-01T00:00:00Z",
            source_commit=_TEST_COMMIT,
        )


def test_build_excludes_working_surfaces_and_unreferenced_assets(tmp_path):
    root = _make_good_site(tmp_path / "site")
    (root / "archive").mkdir()
    (root / "archive" / "private.txt").write_text("working archive")
    (root / "styleguide.html").write_text("working style guide")
    (root / "data").mkdir()
    (root / "data" / "projects.json").write_text("[]")
    (root / "data" / "company-platform.json").write_text("[]")
    (root / "data" / "project-graph.json").write_text("{}")
    (root / "assets" / "css").mkdir()
    (root / "assets" / "css" / "aureon-zorza-backgrounds.css").write_text(".legacy{}")
    (root / "operator-notes.md").write_text("not a public runtime file")
    (root / "deploy-helper.ps1").write_text("Write-Output private")
    (root / ".env").write_text("SECRET=must-not-ship")
    (root / ".env.production").write_text("SECRET=must-not-ship")
    (root / "server.key").write_text("must-not-ship")
    (root / "certificate.pem").write_text("must-not-ship")
    (root / "identity.pfx").write_text("must-not-ship")
    (root / "identity.p12").write_text("must-not-ship")
    (root / "assets" / "unreferenced.png").write_bytes(b"not shipped")

    pkg = tmp_path / "website_package"
    build_package._copy_tree(root, pkg)

    assert (pkg / "assets" / "pic.webp").is_file()
    assert not (pkg / "assets" / "unreferenced.png").exists()
    assert not (pkg / "archive").exists()
    assert not (pkg / "styleguide.html").exists()
    assert not (pkg / "data" / "projects.json").exists()
    assert not (pkg / "data" / "company-platform.json").exists()
    assert not (pkg / "data" / "project-graph.json").exists()
    assert not (pkg / "assets" / "css" / "aureon-zorza-backgrounds.css").exists()
    assert not (pkg / "operator-notes.md").exists()
    assert not (pkg / "deploy-helper.ps1").exists()
    assert not (pkg / ".env").exists()
    assert not (pkg / ".env.production").exists()
    assert not (pkg / "server.key").exists()
    assert not (pkg / "certificate.pem").exists()
    assert not (pkg / "identity.pfx").exists()
    assert not (pkg / "identity.p12").exists()


def test_build_excludes_common_secret_bearing_names_directories_and_suffixes(tmp_path):
    root = _make_good_site(tmp_path / "site")
    secret_paths = (
        ".env.local",
        ".envrc",
        ".git-credentials",
        ".htpasswd",
        ".netrc",
        ".npmrc",
        ".pgpass",
        ".pypirc",
        ".aws/credentials",
        ".ssh/id_rsa",
        "Credentials.JSON",
        "auth.json",
        "client_secret_google.json",
        "firebase-adminsdk-prod.json",
        "google-services.json",
        "prod-service-account.json",
        "prod_credentials.json",
        "prod-secrets.json",
        "secrets.toml",
        "signing.jks",
        "signing.keystore",
        "passwords.kdbx",
        "ssh-private.ppk",
        "identity.pkcs8",
        "private-network.ovpn",
        "distribution.mobileprovision",
    )
    for relative in secret_paths:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("must-not-ship", encoding="utf-8")

    (root / ".htaccess").write_text("Options -Indexes", encoding="utf-8")
    (root / "tokens.css").write_text(":root { --safe-token: #fff; }", encoding="utf-8")
    pkg = tmp_path / "website_package"
    build_package._copy_tree(root, pkg)

    assert (pkg / ".htaccess").is_file()
    assert (pkg / "tokens.css").is_file()
    assert all(not (pkg / relative).exists() for relative in secret_paths)
    build_package._write_manifest(
        pkg,
        "2026-08-21T00:00:00Z",
        build_package.SourceBinding(_TEST_COMMIT, "declared-only-isolated-source"),
    )
    manifest = (pkg / build_package.MANIFEST_NAME).read_text(encoding="utf-8")
    assert "HTACCESS_SECURITY_CONFIGURATION_INCLUDED: YES" in manifest
    assert "HTACCESS_REQUIRED" not in manifest


# ---------------------------------------------------------------------------
# FTP deployer (env-gate + dry-run plan; no network)
# ---------------------------------------------------------------------------


def test_load_config_requires_all_env():
    with pytest.raises(KeyError):
        ftp_deploy.load_config(env={"HOMEPL_FTPS_HOST": "h"})  # missing user/password/root


def test_load_config_requires_explicit_mode_and_port_without_exposing_password():
    cfg = ftp_deploy.load_config(
        env={
            "HOMEPL_FTPS_HOST": "ftp.example.pl",
            "HOMEPL_FTPS_USER": "u",
            "HOMEPL_FTPS_PASSWORD": "SECRETpw123",
            "HOMEPL_FTPS_REMOTE_ROOT": "/public_html/",
            "HOMEPL_FTPS_PORT": "21",
            "HOMEPL_FTPS_MODE": "explicit",
        }
    )
    assert cfg.mode == "explicit" and cfg.port == 21 and cfg.remote_dir == "/public_html"
    assert "SECRETpw123" not in cfg.safe_summary  # password never in the printable summary


def test_config_accepts_named_implicit_mode_and_rejects_invalid_mode_or_port():
    env = {
        "HOMEPL_FTPS_HOST": "serwer.example.invalid",
        "HOMEPL_FTPS_USER": "u",
        "HOMEPL_FTPS_PASSWORD": "SECRETpw123",
        "HOMEPL_FTPS_REMOTE_ROOT": "/",
        "HOMEPL_FTPS_PORT": "990",
        "HOMEPL_FTPS_MODE": "implicit",
    }
    cfg = ftp_deploy.load_config(env=env)
    assert cfg.mode == "implicit" and cfg.port == 990
    assert "FTPS-implicit" in cfg.safe_summary and "SECRETpw123" not in cfg.safe_summary
    with pytest.raises(ValueError, match="explicit.*implicit"):
        ftp_deploy.load_config(env={**env, "HOMEPL_FTPS_MODE": "guess"})
    for invalid_port in ("0", "65536", "not-a-port"):
        with pytest.raises(ValueError):
            ftp_deploy.load_config(env={**env, "HOMEPL_FTPS_PORT": invalid_port})
    for invalid_host in (" server.example.invalid", "server example.invalid", "server\r\ninvalid"):
        with pytest.raises(ValueError, match="HOST"):
            ftp_deploy.load_config(env={**env, "HOMEPL_FTPS_HOST": invalid_host})


def test_implicit_control_socket_is_wrapped_before_welcome_and_login_skips_auth(monkeypatch):
    events: list[object] = []

    class FakeFile:
        def close(self):
            events.append("file-close")

    class FakeWrappedSocket:
        def makefile(self, mode, *, encoding):
            events.append(("makefile", mode, encoding))
            return FakeFile()

        def close(self):
            events.append("wrapped-close")

    class FakeRawSocket:
        family = socket.AF_INET

        def close(self):
            events.append("raw-close")

    raw_socket = FakeRawSocket()
    wrapped_socket = FakeWrappedSocket()

    class FakeContext:
        verify_mode = ssl.CERT_REQUIRED
        check_hostname = True

        def wrap_socket(self, sock, *, server_hostname):
            assert sock is raw_socket
            events.append(("wrap", server_hostname))
            return wrapped_socket

    class ObservedImplicit(ftp_deploy.ImplicitFTP_TLS):
        def getresp(self):
            events.append("welcome")
            return "220 ready"

    def fake_create_connection(address, *, timeout, source_address):
        events.append(("create", address, timeout, source_address))
        return raw_socket

    monkeypatch.setattr(ftp_deploy.socket, "create_connection", fake_create_connection)
    client = ObservedImplicit(context=FakeContext())
    welcome = client.connect_implicit(
        "serwer.example.invalid",
        990,
        timeout=12.5,
        source_address=("127.0.0.1", 0),
    )

    assert welcome == "220 ready"
    assert events[:4] == [
        ("create", ("serwer.example.invalid", 990), 12.5, ("127.0.0.1", 0)),
        ("wrap", "serwer.example.invalid"),
        ("makefile", "r", "utf-8"),
        "welcome",
    ]

    def fake_base_login(self, user="", passwd="", acct=""):
        assert self is client and user == "u" and passwd == "SECRETpw123" and acct == ""
        events.append("base-ftp-login")
        return "230 logged in"

    monkeypatch.setattr(ftp_deploy.FTP, "login", fake_base_login)
    assert client.login("u", "SECRETpw123") == "230 logged in"
    assert "base-ftp-login" in events
    with pytest.raises(RuntimeError, match="AUTH TLS"):
        client.auth()
    client.close()


def test_implicit_transport_closes_resources_on_wrap_or_welcome_failure(monkeypatch):
    events: list[str] = []

    class FakeFile:
        def close(self):
            events.append("file-close")

    class FakeWrappedSocket:
        def makefile(self, mode, *, encoding):
            assert mode == "r" and encoding == "utf-8"
            events.append("makefile")
            return FakeFile()

        def close(self):
            events.append("wrapped-close")

    class FakeRawSocket:
        family = socket.AF_INET

        def close(self):
            events.append("raw-close")

    raw_socket = FakeRawSocket()
    monkeypatch.setattr(
        ftp_deploy.socket,
        "create_connection",
        lambda *_args, **_kwargs: raw_socket,
    )

    class WrapFailureContext:
        def wrap_socket(self, sock, *, server_hostname):
            assert sock is raw_socket and server_hostname == "server.example.invalid"
            raise RuntimeError("wrap failed")

    with pytest.raises(RuntimeError, match="wrap failed"):
        ftp_deploy.ImplicitFTP_TLS(context=WrapFailureContext()).connect_implicit(
            "server.example.invalid", 990, timeout=30.0, source_address=None
        )
    assert events == ["raw-close"]

    events.clear()

    class WelcomeFailureContext:
        def wrap_socket(self, sock, *, server_hostname):
            assert sock is raw_socket and server_hostname == "server.example.invalid"
            return FakeWrappedSocket()

    class WelcomeFailureClient(ftp_deploy.ImplicitFTP_TLS):
        def getresp(self):
            raise RuntimeError("welcome failed")

    with pytest.raises(RuntimeError, match="welcome failed"):
        WelcomeFailureClient(context=WelcomeFailureContext()).connect_implicit(
            "server.example.invalid", 990, timeout=30.0, source_address=None
        )
    assert events == ["makefile", "file-close", "wrapped-close"]


def test_explicit_connect_negotiates_then_requires_private_data_channel(monkeypatch):
    events: list[object] = []
    context = object()

    class FakeExplicit:
        def __init__(self, *, context):
            events.append(("init", context))

        def connect(self, host, port, *, timeout, source_address):
            events.append(("connect", host, port, timeout, source_address))

        def login(self, user, password):
            assert user == "u" and password == "SECRETpw123"
            events.append("login-auth-tls")

        def prot_p(self):
            events.append("prot-p")

        def close(self):
            events.append("close")

    monkeypatch.setattr(ftp_deploy, "_new_tls_context", lambda: context)
    monkeypatch.setattr(ftp_deploy, "FTP_TLS", FakeExplicit)
    cfg = ftp_deploy.FtpConfig("ftp.example.pl", "u", "SECRETpw123", "/public_html", 21, "explicit")
    result = ftp_deploy._connect(cfg, timeout=9.0, source_address=("127.0.0.1", 0))
    assert isinstance(result, FakeExplicit)
    assert events == [
        ("init", context),
        ("connect", "ftp.example.pl", 21, 9.0, ("127.0.0.1", 0)),
        "login-auth-tls",
        "prot-p",
    ]


def test_implicit_connect_uses_separate_transport_then_requires_private_data_channel(monkeypatch):
    events: list[object] = []
    context = object()

    class FakeImplicit:
        def __init__(self, *, context):
            events.append(("init", context))

        def connect_implicit(self, host, port, *, timeout, source_address):
            events.append(("implicit-connect", host, port, timeout, source_address))

        def login(self, user, password):
            assert user == "u" and password == "SECRETpw123"
            events.append("login-inside-tls")

        def prot_p(self):
            events.append("prot-p")

        def close(self):
            events.append("close")

    monkeypatch.setattr(ftp_deploy, "_new_tls_context", lambda: context)
    monkeypatch.setattr(ftp_deploy, "ImplicitFTP_TLS", FakeImplicit)
    cfg = ftp_deploy.FtpConfig("ftp.example.pl", "u", "SECRETpw123", "/public_html", 990, "implicit")
    result = ftp_deploy._connect(cfg)
    assert isinstance(result, FakeImplicit)
    assert events == [
        ("init", context),
        ("implicit-connect", "ftp.example.pl", 990, 30.0, None),
        "login-inside-tls",
        "prot-p",
    ]


def test_tls_context_and_socket_options_fail_closed_before_connection(monkeypatch):
    cfg = ftp_deploy.FtpConfig("ftp.example.pl", "u", "p", "/", 990, "implicit")
    socket_called = False

    def forbidden_socket(*_args, **_kwargs):
        nonlocal socket_called
        socket_called = True
        raise AssertionError("socket must not be opened")

    monkeypatch.setattr(ftp_deploy.socket, "create_connection", forbidden_socket)
    with pytest.raises(ValueError, match="mode"):
        ftp_deploy._connect(ftp_deploy.FtpConfig("h", "u", "p", "/", 990, "guess"))
    with pytest.raises(ValueError, match="port"):
        ftp_deploy._connect(ftp_deploy.FtpConfig("h", "u", "p", "/", 0, "implicit"))
    with pytest.raises(ValueError, match="timeout"):
        ftp_deploy._connect(cfg, timeout=0)
    with pytest.raises(ValueError, match="source address"):
        ftp_deploy._connect(cfg, source_address=("127.0.0.1", 65536))
    with pytest.raises(ValueError, match="source address"):
        ftp_deploy._connect(cfg, source_address=("127.0.0.1",))  # type: ignore[arg-type]
    assert socket_called is False

    class InsecureContext:
        verify_mode = ssl.CERT_NONE
        check_hostname = False

    monkeypatch.setattr(ftp_deploy.ssl, "create_default_context", InsecureContext)
    with pytest.raises(RuntimeError, match="certificate and hostname"):
        ftp_deploy._connect(cfg)
    assert socket_called is False


def test_plan_uploads_maps_remote_paths(tmp_path):
    pkg = tmp_path / "website_package"
    (pkg / "assets").mkdir(parents=True)
    (pkg / "index.html").write_text("x")
    (pkg / "assets" / "a.webp").write_bytes(b"x")
    plan = ftp_deploy.plan_uploads(pkg, "/public_html")
    remotes = [r for _l, r in plan]
    assert remotes == ["/public_html/assets/a.webp", "/public_html/index.html"]


def test_dry_run_exits_zero_and_hides_password(tmp_path, capsys, monkeypatch):
    pkg = tmp_path / "website_package"
    pkg.mkdir()
    (pkg / "index.html").write_text("x")
    for k, v in {
        "HOMEPL_FTPS_HOST": "ftp.example.pl",
        "HOMEPL_FTPS_USER": "u",
        "HOMEPL_FTPS_PASSWORD": "SECRETXYZ",
        "HOMEPL_FTPS_REMOTE_ROOT": "/public_html",
        "HOMEPL_FTPS_PORT": "990",
        "HOMEPL_FTPS_MODE": "implicit",
    }.items():
        monkeypatch.setenv(k, v)
    rc = ftp_deploy.main(["--package", str(pkg), "--dry-run"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "/public_html/index.html" in out
    assert "SECRETXYZ" not in out
    assert out.isascii(), "deploy diagnostics must remain safe on default Windows consoles"


def test_deploy_refuses_without_env(tmp_path, monkeypatch, capsys):
    pkg = tmp_path / "website_package"
    pkg.mkdir()
    (pkg / "index.html").write_text("x")
    for k in ftp_deploy._REQUIRED_ENV:
        monkeypatch.delenv(k, raising=False)
    rc = ftp_deploy.main(["--package", str(pkg)])
    assert rc == 1
    assert "refused" in capsys.readouterr().err.lower()


def test_backup_receipt_is_fresh_nonempty_root_bound_and_manifest_bound(tmp_path):
    now = datetime(2026, 8, 21, 0, 0, tzinfo=UTC)
    backup_directory = tmp_path / "remote-backup"
    backup_directory.mkdir()
    backed_up_index = backup_directory / "index.html"
    backed_up_index.write_bytes(b"x")
    manifest = tmp_path / "remote-backup-manifest.csv"
    index_digest = hashlib.sha256(backed_up_index.read_bytes()).hexdigest()
    manifest.write_text(
        f"Path,Bytes,Sha256\nindex.html,1,{index_digest}\n",
        encoding="utf-8",
    )
    backup_script = _REPO / "website" / "backup-homepl-ftps.ps1"
    receipt = tmp_path / "backup-transfer.json"
    payload = {
        "schema": "aureon.homepl-backup-transfer.v1",
        "state": "backup-complete",
        "method": "homepl-ftps",
        "source_assertion": "Authenticated Home.pl document-root download",
        "source_tool": "repo-read-only-ftps-script",
        "completed_at": (now - timedelta(minutes=3)).isoformat(),
        "remote_root": "/public_html",
        "backup_directory": str(backup_directory.resolve()),
        "manifest": str(manifest.resolve()),
        "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        "backup_script": str(backup_script.resolve()),
        "backup_script_sha256": hashlib.sha256(backup_script.read_bytes()).hexdigest(),
        "file_count": 1,
        "total_bytes": 1,
        "remote_write_methods_used": False,
        "credentials_recorded": False,
    }
    receipt.write_text(json.dumps(payload), encoding="utf-8")

    parsed = ftp_deploy.load_backup_receipt(receipt, "/public_html/", now=now)
    assert parsed.file_count == 1 and parsed.total_bytes == 1
    assert parsed.remote_root == "/public_html"
    assert "password" not in repr(parsed).casefold()

    stale = {**payload, "completed_at": (now - timedelta(hours=25)).isoformat()}
    receipt.write_text(json.dumps(stale), encoding="utf-8")
    with pytest.raises(ValueError, match="stale"):
        ftp_deploy.load_backup_receipt(receipt, "/public_html", now=now)
    receipt.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="remote root"):
        ftp_deploy.load_backup_receipt(receipt, "/", now=now)
    (backup_directory / "unmanifested.txt").write_text("stale", encoding="utf-8")
    with pytest.raises(ValueError, match="file sets differ"):
        ftp_deploy.load_backup_receipt(receipt, "/public_html", now=now)
    (backup_directory / "unmanifested.txt").unlink()
    manifest.write_text("tampered", encoding="utf-8")
    with pytest.raises(ValueError, match="hash"):
        ftp_deploy.load_backup_receipt(receipt, "/public_html", now=now)


def test_deployer_never_allows_prune_or_live_upload_without_backup(tmp_path, capsys, monkeypatch):
    pkg = tmp_path / "website_package"
    pkg.mkdir()
    (pkg / "index.html").write_text("x", encoding="utf-8")
    for key, value in {
        "HOMEPL_FTPS_HOST": "ftp.example.pl",
        "HOMEPL_FTPS_USER": "u",
        "HOMEPL_FTPS_PASSWORD": "SECRETXYZ",
        "HOMEPL_FTPS_REMOTE_ROOT": "/public_html",
        "HOMEPL_FTPS_PORT": "990",
        "HOMEPL_FTPS_MODE": "implicit",
    }.items():
        monkeypatch.setenv(key, value)
    called = False

    def forbidden_upload(*_args, **_kwargs):
        nonlocal called
        called = True
        raise AssertionError("network upload must not be reached")

    monkeypatch.setattr(ftp_deploy, "_upload", forbidden_upload)
    monkeypatch.setattr(ftp_deploy.socket, "create_connection", forbidden_upload)
    assert ftp_deploy.main(["--package", str(pkg), "--prune"]) == 1
    assert "pruning is disabled" in capsys.readouterr().err
    assert ftp_deploy.main(["--package", str(pkg)]) == 1
    assert "backup-receipt" in capsys.readouterr().err
    assert called is False
