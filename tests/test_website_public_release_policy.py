"""Fail-closed tests for the public website disclosure and release boundary."""

from __future__ import annotations

import csv
import json
import re
import shutil
import subprocess
import zipfile
from collections.abc import Callable
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[1]
WEBSITE_ROOT = REPO_ROOT / "website"
AUDIT_SCRIPT = REPO_ROOT / "tools" / "aureon_website_audit.ps1"
BUILD_SCRIPT = REPO_ROOT / "tools" / "build-homepl-v28-narrow-release.ps1"
POWERSHELL = shutil.which("pwsh") or shutil.which("powershell")

FORBIDDEN_RELEASE_PATHS = {
    "HOMEPL_PACKAGE_MANIFEST.txt",
    "HOMEPL_UPLOAD_README.md",
    "OWNER_CONTROL.md",
    "CHANGES.md",
    "styleguide.html",
    "backup-homepl-ftps.ps1",
    "build-homepl-package.ps1",
    "publish-homepl-ftps.ps1",
    "refresh-operator-evidence.ps1",
}

FORBIDDEN_RELEASE_DIRECTORY_NAMES = {
    "archive",
    "deployment",
    "internal",
    "source",
}

FORBIDDEN_RELEASE_DIRECTORY_PATHS = {
    "archive/index.html",
    "archive/under-review/index.html",
    "deployment/release-notes.html",
    "internal/operator-notes.html",
    "source/source-map.html",
}

FORBIDDEN_RELEASE_FILE_PATHS = {
    "assets/styleguide.html",
}

PUBLIC_DISCLOSURE_DATA_FILES = (
    "funding-status.json",
    "company-platform.json",
    "publications.json",
    "blades.json",
    "innovation-map.json",
    "operator-evidence.json",
    "research-catalogue.json",
    "research.json",
    "substack-research-index.json",
    "updates.json",
)

LEGACY_DISCLOSURE_KEYS = {
    "registry_id",
    "published_at",
    "release",
    "reviewed_at",
    "reviewed_on",
    "checked_at",
    "checked_on",
    "last_updated",
    "last_modified_at",
    "status_tone",
    "applications",
    "internal_records",
    "decision_or_use_case",
    "current_evidence_state",
    "controlled_evidence",
    "controlled_diligence",
    "grant_or_provider_evidence",
    "partner_evidence",
    "security_boundary",
    "not_public",
    "claim_boundary",
    "next_proof",
    "awards_or_investment_claimed",
    "archive_entry_count",
    "direct_entry_count",
    "public_work_groups",
    "current_records",
    "unique_dois",
    "preprints",
    "technical_notes",
    "records_dated_2026_07_24",
    "site_view",
    "counting_note",
    "public_research_records",
    "selected_register_records",
    "independently_validated_records",
    "zenodo_records_listed",
    "additional_indexed_record_count",
    "unique_public_records_listed",
    "orcid_public_work_groups",
    "zenodo_current_records",
    "full_public_research_view",
}

UPDATE_REQUIRED_FIELDS = {
    "id",
    "date",
    "title",
    "summary",
    "category",
    "investor_relevance",
    "source_name",
    "source_label",
    "source_url",
    "next_validation",
}

UPDATE_ALLOWED_CATEGORIES = {
    "Research authority",
    "Platform",
    "Sector reach",
    "Public recognition",
}

UPDATE_LEGACY_LEDGER_FIELDS = {
    "evidence_state",
    "deployment_state",
    "public_boundary",
    "status",
    "completed",
    "next_gate",
    "application_number",
    "application_id",
    "provider_reference",
    "request_amount",
    "monitor_run_id",
    "correspondence",
}

INVESTOR_SURFACE_REQUIRED_SIGNALS = {
    "about/index.html": (
        "Companies House is the authoritative source",
        "Gary Anthony Leckey",
        "What Aureon will prove next",
    ),
    "diligence/index.html": (
        "Public investor evidence",
        "What Aureon will prove next",
        "Talk to the founder",
    ),
    "publications/index.html": (
        "Research you can inspect at source",
        "Research proposition",
        "Next validation",
    ),
    "contact/index.html": (
        "Start an investor conversation",
        "mailto:gary@aureonzorzatechnologies.com",
        "Four details are enough to start well.",
        "<strong>Who:</strong>",
        "<strong>Thesis:</strong>",
        "<strong>Question:</strong>",
        "<strong>Next step:</strong>",
    ),
    "funding/investor-deck/index.html": (
        "Investment thesis",
        "Measured public attention",
        "What will Aureon prove next?",
    ),
}

INVESTOR_SURFACE_BLOCKED_PATTERNS = (
    r"\b(?:valuation|runway|fundraising target|raise target|annual recurring revenue|ARR|committed capital)\b",
    r"\binternal (?:company |operating )?records?\b",
    r"\bapplication values?\b",
    r"\bgrant (?:reference|application|value)\b",
    r"\bportal records?\b",
    r"\bfinancing (?:requirements?|assumptions?|forecasts?)\b",
    r"\bcurrent revenue\b",
    r"\bopen evidence gaps\b",
    r"\bdo not send\b",
    r"\bprovider receipt\b",
    r"\bsubmission receipt\b",
    r"\brecord path\s*/\s*v\d+\b",
    r"\bdoes not submit a form\b",
    r"\bpromise a reply\b",
    r"\b75%\s+or\s+more\b",
    r"\bcontrolled (?:investor materials|diligence)\b",
    r"\b(?:operator|deployment|hosting|correspondence) (?:record|receipt|reference|run|log|account|quota|figure|value|status)\b",
    r"\b(?:application|grant|provider|correspondence|operator|deployment|hosting)_(?:id|number|reference|receipt|record|run|log|account|quota)\b",
)

RELEASE_VISIBLE_LEGACY_PATTERNS = (
    r"\bCompany-recorded\b",
    r"\bProvider-confirmed\b",
    r"\bprivate route records?\b",
    r"\bFinancing requirements\b",
)

pytestmark = pytest.mark.skipif(POWERSHELL is None, reason="PowerShell is unavailable")


def _powershell_array(script: str, variable: str) -> list[str]:
    match = re.search(
        rf"(?ms)^\${re.escape(variable)}\s*=\s*@\(\s*(.*?)^\)",
        script,
    )
    assert match is not None, f"Could not find ${variable} in {BUILD_SCRIPT}"
    return re.findall(r"'([^']+)'", match.group(1))


def _release_entry_paths() -> list[str]:
    script = BUILD_SCRIPT.read_text(encoding="utf-8-sig")
    return [
        *_powershell_array(script, "releaseFiles"),
        *_powershell_array(script, "supplementalEntryFiles"),
    ]


def _entry_content(path: str) -> str:
    suffix = Path(path).suffix.lower()
    if suffix == ".html":
        return "<!doctype html><html><head><title>Fixture</title></head><body></body></html>"
    if suffix in {".json", ".webmanifest"}:
        return "{}"
    if suffix == ".xml":
        return "<?xml version=\"1.0\" encoding=\"UTF-8\"?><urlset/>"
    if path == ".htaccess":
        return "Options -Indexes\n"
    return "fixture\n"


def _iter_json_keys(value: object) -> list[str]:
    keys: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            keys.append(key)
            keys.extend(_iter_json_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.extend(_iter_json_keys(child))
    return keys


def _release_fixture(tmp_path: Path) -> Path:
    website = tmp_path / "website"
    website.mkdir()
    for relative in _release_entry_paths():
        target = website / Path(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_entry_content(relative), encoding="utf-8")
    for relative in (
        FORBIDDEN_RELEASE_PATHS
        | FORBIDDEN_RELEASE_DIRECTORY_PATHS
        | FORBIDDEN_RELEASE_FILE_PATHS
    ):
        target = website / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("internal operator material\n", encoding="utf-8")
    return website


def _run_release(
    website: Path,
    output: Path,
    *,
    verify_only: bool,
) -> subprocess.CompletedProcess[str]:
    command = [
        str(POWERSHELL),
        "-NoLogo",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(BUILD_SCRIPT),
        "-WebsiteRoot",
        str(website),
        "-OutputDirectory",
        str(output),
    ]
    if verify_only:
        command.append("-VerifyOnly")
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=90,
        check=False,
    )


def _funding_fixture(
    tmp_path: Path,
    mutate: Callable[[dict[str, object]], None] | None = None,
) -> Path:
    site = tmp_path / "site"
    (site / "funding").mkdir(parents=True)
    (site / "data").mkdir()
    shutil.copy2(WEBSITE_ROOT / "funding" / "index.html", site / "funding" / "index.html")
    data = json.loads((WEBSITE_ROOT / "data" / "funding-status.json").read_text(encoding="utf-8"))
    if mutate is not None:
        mutate(data)
    (site / "data" / "funding-status.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return site


def _updates_fixture(
    tmp_path: Path,
    mutate: Callable[[list[dict[str, object]]], None] | None = None,
) -> Path:
    site = tmp_path / "site"
    (site / "updates").mkdir(parents=True)
    (site / "data").mkdir()
    shutil.copy2(WEBSITE_ROOT / "updates" / "index.html", site / "updates" / "index.html")
    data = json.loads((WEBSITE_ROOT / "data" / "updates.json").read_text(encoding="utf-8"))
    if mutate is not None:
        mutate(data)
    (site / "data" / "updates.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return site


def _run_funding_audit(site: Path, output: Path) -> dict[str, object]:
    result = subprocess.run(
        [
            str(POWERSHELL),
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(AUDIT_SCRIPT),
            "-SiteRoot",
            str(site),
            "-OutputDirectory",
            str(output),
            "-RunId",
            "public_disclosure_policy",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=90,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report_path = output / "AUREON_WEBSITE_AUDIT_public_disclosure_policy.json"
    return json.loads(report_path.read_text(encoding="utf-8-sig"))


def test_website_audit_bare_invocation_resolves_default_repo_paths(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    tools = repo / "tools"
    website = repo / "website"
    data = website / "data"
    tools.mkdir(parents=True)
    data.mkdir(parents=True)
    script = tools / AUDIT_SCRIPT.name
    shutil.copy2(AUDIT_SCRIPT, script)

    result = subprocess.run(
        [
            str(POWERSHELL),
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
        ],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=90,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "AUDIT_STATUS=ACTION_REQUIRED" in result.stdout
    reports = list((repo / "docs" / "audits").glob("AUREON_WEBSITE_AUDIT_*.json"))
    assert len(reports) == 1
    raw_report = reports[0].read_text(encoding="utf-8")
    assert not raw_report.startswith("\ufeff")
    report = json.loads(raw_report)
    assert Path(report["site_root"]) == website.resolve()
    assert report["status"] == "ACTION_REQUIRED"


def test_narrow_release_package_excludes_operator_and_source_control_files(
    tmp_path: Path,
) -> None:
    website = _release_fixture(tmp_path)
    output = tmp_path / "release"
    result = _run_release(website, output, verify_only=False)

    assert result.returncode == 0, result.stdout + result.stderr
    package = next(output.glob("*.zip"))
    manifest = next(output.glob("*-manifest.csv"))
    receipt = json.loads(next(output.glob("*-receipt.json")).read_text(encoding="utf-8-sig"))

    with zipfile.ZipFile(package) as archive:
        package_paths = {name.replace("\\", "/") for name in archive.namelist()}
    with manifest.open(encoding="utf-8-sig", newline="") as stream:
        manifest_paths = {row["Path"].replace("\\", "/") for row in csv.DictReader(stream)}
    receipt_paths = {item["Path"].replace("\\", "/") for item in receipt["files"]}

    for actual_paths in (package_paths, manifest_paths, receipt_paths):
        assert actual_paths.isdisjoint(FORBIDDEN_RELEASE_PATHS)
        for actual_path in actual_paths:
            assert actual_path.rsplit("/", 1)[-1].casefold() != "styleguide.html"
            assert not (
                set(actual_path.split("/")) & FORBIDDEN_RELEASE_DIRECTORY_NAMES
            )


@pytest.mark.parametrize(
    "forbidden_path",
    sorted(
        FORBIDDEN_RELEASE_PATHS
        | FORBIDDEN_RELEASE_DIRECTORY_PATHS
        | FORBIDDEN_RELEASE_FILE_PATHS
    ),
)
def test_narrow_release_blocks_reference_to_forbidden_file(
    tmp_path: Path,
    forbidden_path: str,
) -> None:
    website = _release_fixture(tmp_path)
    (website / "index.html").write_text(
        f'<!doctype html><html><body><a href="/{forbidden_path}">Internal</a></body></html>',
        encoding="utf-8",
    )

    result = _run_release(website, tmp_path / "release", verify_only=True)

    assert result.returncode != 0
    combined_output = result.stdout + result.stderr
    assert forbidden_path in combined_output
    assert (
        "Source-control or deployment-only file cannot enter the public release"
        in combined_output
        or "Blocked public release dependency" in combined_output
    )


def test_server_rules_404_legacy_design_and_archive_surfaces_only() -> None:
    rules = (WEBSITE_ROOT / ".htaccess").read_text(encoding="utf-8")
    patterns: list[re.Pattern[str]] = []

    for line in rules.splitlines():
        match = re.match(
            r"^\s*RewriteRule\s+(\S+)\s+\S+\s+\[([^\]]+)\]\s*$",
            line,
            flags=re.IGNORECASE,
        )
        if match is None:
            continue
        flags = {flag.strip().casefold() for flag in match.group(2).split(",")}
        if "r=404" not in flags:
            continue
        compile_flags = re.IGNORECASE if "nc" in flags else 0
        patterns.append(re.compile(match.group(1), compile_flags))

    def is_404(path: str) -> bool:
        return any(pattern.search(path) is not None for pattern in patterns)

    for blocked_path in (
        "styleguide.html",
        "styleguide.html/preview",
        "STYLEGUIDE.HTML",
        "archive",
        "archive/",
        "archive/under-review/",
        "archive/aqts/index.html",
    ):
        assert is_404(blocked_path), blocked_path

    for public_path in (
        "index.html",
        "assets/css/aureon-zorza-backgrounds.css",
        "archive-publications/index.html",
        "data/blades.json",
        "funding/investor-deck/",
        "projects/",
        "publications/",
        "research/",
    ):
        assert not is_404(public_path), public_path


def test_current_public_routes_do_not_reference_legacy_archive() -> None:
    sitemap = (WEBSITE_ROOT / "sitemap.xml").read_text(encoding="utf-8").casefold()
    assert "/archive" not in sitemap
    assert "styleguide.html" not in sitemap

    for path in WEBSITE_ROOT.rglob("*.html"):
        relative = path.relative_to(WEBSITE_ROOT)
        if path.name == "styleguide.html" or "archive" in relative.parts:
            continue
        content = path.read_text(encoding="utf-8").casefold()
        assert "styleguide.html" not in content, relative
        assert 'href="/archive' not in content, relative
        assert "href='/archive" not in content, relative
        assert 'href="archive/' not in content, relative
        assert "href='archive/" not in content, relative


def test_release_html_excludes_legacy_public_policy_framing() -> None:
    for relative in _release_entry_paths():
        if not relative.casefold().endswith(".html"):
            continue
        content = (WEBSITE_ROOT / relative).read_text(encoding="utf-8")
        for blocked_pattern in RELEASE_VISIBLE_LEGACY_PATTERNS:
            assert re.search(blocked_pattern, content, flags=re.IGNORECASE) is None, (
                relative,
                blocked_pattern,
            )


def test_final_investor_message_regressions_stay_closed() -> None:
    home = (WEBSITE_ROOT / "index.html").read_text(encoding="utf-8")
    for state in (
        "Source-linked",
        "Company-built",
        "Research proposition",
        "Independently reviewed",
        "Next validation",
    ):
        assert state in home
    assert "private route mechanics" not in home

    funding = (WEBSITE_ROOT / "funding" / "index.html").read_text(encoding="utf-8")
    assert "through a publicly scoped strategy map" in funding
    assert "controlled company records" not in funding
    assert "founder-led and at an early stage" in funding

    script = (WEBSITE_ROOT / "script.js").read_text(encoding="utf-8")
    assert '["publications", "Evidence", "publications/"]' in script
    assert '["diligence", "Evidence", "diligence/"]' not in script
    assert 'liveLink.textContent = "Public proof"' in script

    company_platform = (
        WEBSITE_ROOT / "data" / "company-platform.json"
    ).read_text(encoding="utf-8")
    legacy_projects = (WEBSITE_ROOT / "data" / "projects.json").read_text(
        encoding="utf-8"
    )
    platform_page = (
        WEBSITE_ROOT / "projects" / "aureon-trading-system" / "index.html"
    ).read_text(encoding="utf-8")
    for content in (company_platform, legacy_projects, platform_page):
        assert "GitHub metadata view" not in content
        assert "Live Evidence" not in content
        assert "live evidence" not in content
        assert "dated signals" not in content

    updates = (WEBSITE_ROOT / "data" / "updates.json").read_text(encoding="utf-8")
    assert "sustained access" not in updates
    assert "Formal research records show public repository access" in updates

    projects = (WEBSITE_ROOT / "projects" / "index.html").read_text(encoding="utf-8")
    assert "electro-optical materials and technology (EOMT)" in projects
    assert "a mission-endorsed instrument" in projects
    assert "mission endorsed" not in projects

    live_page = (WEBSITE_ROOT / "live" / "index.html").read_text(encoding="utf-8")
    live_script = (WEBSITE_ROOT / "live" / "live.js").read_text(encoding="utf-8")
    for content in (live_page, live_script):
        assert "does not imply release" in content
        assert "does not infer release" not in content


def test_current_public_funding_route_map_passes_disclosure_policy(tmp_path: Path) -> None:
    site = _funding_fixture(tmp_path)

    report = _run_funding_audit(site, tmp_path / "audit")

    assert report["summary"]["funding_state_findings"] == 0
    assert report["funding_state_findings"] == []


def test_investor_surfaces_lead_with_thesis_and_keep_internal_records_off_site() -> None:
    for relative, required_signals in INVESTOR_SURFACE_REQUIRED_SIGNALS.items():
        page = (WEBSITE_ROOT / relative).read_text(encoding="utf-8")
        for required_signal in required_signals:
            assert required_signal in page, (relative, required_signal)
        for blocked_pattern in INVESTOR_SURFACE_BLOCKED_PATTERNS:
            assert re.search(blocked_pattern, page, flags=re.IGNORECASE) is None, (
                relative,
                blocked_pattern,
            )


def test_audit_rejects_internal_investor_surface_disclosure(tmp_path: Path) -> None:
    site = tmp_path / "site"
    (site / "data").mkdir(parents=True)
    for relative in INVESTOR_SURFACE_REQUIRED_SIGNALS:
        source = WEBSITE_ROOT / relative
        target = site / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    about = site / "about" / "index.html"
    about.write_text(
        about.read_text(encoding="utf-8").replace(
            "</main>",
            "<p>Internal company records include a fundraising target and runway.</p></main>",
        ),
        encoding="utf-8",
    )
    report = _run_funding_audit(site, tmp_path / "audit")

    assert any(
        finding.get("issue") == "investor_surface_disclosure_or_residue"
        and finding.get("file") == "about\\index.html"
        for finding in report["blocked_claim_findings"]
    )


def test_current_updates_surface_passes_investor_milestone_policy(tmp_path: Path) -> None:
    site = _updates_fixture(tmp_path)

    report = _run_funding_audit(site, tmp_path / "audit")

    assert report["summary"]["updates_schema_findings"] == 0
    assert report["summary"]["updates_sort_findings"] == 0
    assert report["summary"]["missing_required_update_states"] == 0
    assert report["updates_schema_findings"] == []
    assert report["updates_sort_findings"] == []
    assert report["missing_required_update_states"] == []


def test_updates_are_investor_milestones_not_public_operating_ledger() -> None:
    updates = json.loads(
        (WEBSITE_ROOT / "data" / "updates.json").read_text(encoding="utf-8")
    )
    assert updates
    assert {record["category"] for record in updates} == UPDATE_ALLOWED_CATEGORIES
    assert [record["date"] for record in updates] == sorted(
        (record["date"] for record in updates),
        reverse=True,
    )

    for record in updates:
        assert UPDATE_REQUIRED_FIELDS.issubset(record)
        assert not UPDATE_LEGACY_LEDGER_FIELDS.intersection(record)
        assert all(str(record[field]).strip() for field in UPDATE_REQUIRED_FIELDS)

    page = (WEBSITE_ROOT / "updates" / "index.html").read_text(encoding="utf-8")
    for required_signal in (
        "Investor milestone brief",
        "Research authority",
        "Shared platform",
        "Sector reach",
        "Public recognition",
        "Next validation",
    ):
        assert required_signal in page
    for legacy_term in (
        "Evidence state",
        "Company-recorded",
        "Provider-confirmed",
        "Implementation ledger",
        "Public boundary",
        "Permitted reading",
        "data-update-evidence",
    ):
        assert legacy_term not in page

    script = (WEBSITE_ROOT / "script.js").read_text(encoding="utf-8")
    for legacy_renderer_term in (
        "data-update-total",
        "data-update-current",
        "data-update-provider",
        "data-update-evidence",
        "updateEvidenceBadge",
        "updateDeploymentBadge",
        "updatePermittedReading",
    ):
        assert legacy_renderer_term not in script


def test_updates_audit_rejects_legacy_ledger_field(tmp_path: Path) -> None:
    def add_legacy_field(data: list[dict[str, object]]) -> None:
        data[0]["deployment_state"] = "Public company record"

    site = _updates_fixture(tmp_path, mutate=add_legacy_field)
    report = _run_funding_audit(site, tmp_path / "audit")

    assert any(
        finding["issue"] == "legacy_ledger_field_publicly_exposed"
        and finding.get("field") == "deployment_state"
        for finding in report["updates_schema_findings"]
    )


def test_public_data_uses_qualitative_disclosure_schema() -> None:
    for filename in PUBLIC_DISCLOSURE_DATA_FILES:
        path = WEBSITE_ROOT / "data" / filename
        data = json.loads(path.read_text(encoding="utf-8"))
        exposed_keys = LEGACY_DISCLOSURE_KEYS.intersection(_iter_json_keys(data))
        assert not exposed_keys, f"{filename} exposes legacy disclosure keys: {sorted(exposed_keys)}"

        serialized = json.dumps(data, ensure_ascii=False)
        for forbidden_phrase in (
            "908c4c4",
            "remote HEAD",
            "operator snapshot",
            "redacted operator snapshot",
            '"V28"',
        ):
            assert forbidden_phrase.casefold() not in serialized.casefold(), (
                f"{filename} exposes legacy disclosure framing: {forbidden_phrase}"
            )


def test_public_route_map_describes_strategy_not_route_activity() -> None:
    data = json.loads(
        (WEBSITE_ROOT / "data" / "funding-status.json").read_text(encoding="utf-8")
    )
    routes = data["routes"]
    assert routes
    assert {route["state_group"] for route in routes} == {"strategic-theme"}

    serialized = json.dumps(routes, ensure_ascii=False)
    for route_state_phrase in (
        "routes are active",
        "routes are being developed",
        "routes have been engaged",
        "engagement exists",
        "route developed",
        "route explored",
        "route-fit potential identified",
        "is pursuing",
    ):
        assert route_state_phrase.casefold() not in serialized.casefold()


def test_public_research_orientation_preserves_identity_and_sources() -> None:
    catalogue = json.loads(
        (WEBSITE_ROOT / "data" / "research-catalogue.json").read_text(encoding="utf-8")
    )
    assert catalogue["record_type"] == "public_research_orientation"
    assert catalogue["orcid"]["id"] == "0009-0004-2792-4649"
    assert catalogue["orcid"]["url"].startswith("https://orcid.org/")
    assert catalogue["zenodo"]["url"].startswith("https://zenodo.org/")
    assert len(catalogue["research_breadth"]["themes"]) >= 3
    assert catalogue["recent_records"]
    assert all(
        record["doi_url"].startswith("https://doi.org/")
        for record in catalogue["recent_records"]
    )


def test_research_to_application_map_preserves_roles_and_blade_boundaries() -> None:
    innovation_map = json.loads(
        (WEBSITE_ROOT / "data" / "innovation-map.json").read_text(encoding="utf-8")
    )
    blades = json.loads(
        (WEBSITE_ROOT / "data" / "blades.json").read_text(encoding="utf-8")
    )

    assert innovation_map["schema"] == "aureon-research-to-application-map-v1"
    assert len(innovation_map["paths"]) >= 3
    assert set(innovation_map["artifact_roles"]) == {
        "formal_record",
        "public_explanation",
        "company_implementation",
        "application_route",
    }

    known_blade_ids = {blade["id"] for blade in blades["blades"]}
    mapped_blade_ids: set[str] = set()
    for path in innovation_map["paths"]:
        assert path["research_question"]
        assert path["hnc_method"]
        assert path["formal_records"]
        assert path["public_explanations"]
        assert path["aureon_os_capability"]["artifact_role"] == "company_implementation"
        assert path["next_validation"]
        assert path["public_boundary"]

        path_blades = set(path["application_blades"])
        assert path_blades <= known_blade_ids
        mapped_blade_ids.update(path_blades)

        assert all(
            record["artifact_role"] == "formal_record"
            for record in path["formal_records"]
        )
        assert all(
            note["artifact_role"] == "public_explanation"
            for note in path["public_explanations"]
        )

    assert mapped_blade_ids == known_blade_ids


def _set_first_route_value(data: dict[str, object], value: str) -> None:
    routes = data["routes"]
    assert isinstance(routes, list)
    first_route = routes[0]
    assert isinstance(first_route, dict)
    first_route["status_detail"] = value


@pytest.mark.parametrize(
    ("exposed_value", "expected_match"),
    [
        ("Internal application 13086425", "13086425"),
        ("Requested £50,000", "£"),
        ("Budget EUR 50000", "EUR 5"),
        ("Review the Gmail thread", "Gmail"),
        ("Use the Calendly meeting record", "Calendly"),
        (
            "AUREON_CONTINUOUS_FUNDING_MONITOR_20260720_20260720_002423",
            "AUREON_CONTINUOUS_FUNDING_MONITOR",
        ),
        ("Internal run 0e7bd96b-2f97-4dc5-93f1-4cf34f940f8d", "0e7bd96b"),
    ],
)
def test_public_funding_route_map_rejects_internal_value_patterns(
    tmp_path: Path,
    exposed_value: str,
    expected_match: str,
) -> None:
    site = _funding_fixture(
        tmp_path,
        mutate=lambda data: _set_first_route_value(data, exposed_value),
    )

    report = _run_funding_audit(site, tmp_path / "audit")
    findings = report["funding_state_findings"]

    assert any(
        finding["issue"] == "internal_value_pattern_publicly_exposed"
        and expected_match.casefold() in str(finding.get("value", "")).casefold()
        for finding in findings
    )


@pytest.mark.parametrize(
    "internal_field",
    [
        "application_number",
        "application_id",
        "provider_reference",
        "request_amount",
        "monitor_run_id",
    ],
)
def test_public_funding_route_map_rejects_internal_fields(
    tmp_path: Path,
    internal_field: str,
) -> None:
    def add_internal_field(data: dict[str, object]) -> None:
        routes = data["routes"]
        assert isinstance(routes, list)
        first_route = routes[0]
        assert isinstance(first_route, dict)
        first_route[internal_field] = "controlled"

    site = _funding_fixture(tmp_path, mutate=add_internal_field)

    report = _run_funding_audit(site, tmp_path / "audit")
    findings = report["funding_state_findings"]

    assert any(
        finding["issue"] == "internal_field_publicly_exposed"
        and finding.get("field") == internal_field
        for finding in findings
    )
