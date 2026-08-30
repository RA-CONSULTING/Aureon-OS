from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

import pytest

from aureon.operator import design_candidate_static_qa as qa


def _config(*, total_bytes: int = 2_000_000, per_html: int = 200_000) -> dict[str, object]:
    return {
        "schema": qa.CONFIG_SCHEMA,
        "site": {
            "root": "website",
            "base_url": "https://aureonzorzatechnologies.pl/",
            "canonical_overrides": {},
            "critical_routes": ["index.html"],
        },
        "ethos": {
            "principles": ["Evidence before claims."],
            "required_site_signals": [
                {
                    "id": "evidence",
                    "pattern": r"\bevidence\b",
                    "severity": "error",
                    "message": "missing",
                },
                {
                    "id": "research",
                    "pattern": r"\bresearch\b",
                    "severity": "error",
                    "message": "missing",
                },
                {
                    "id": "human-authority",
                    "pattern": r"\bhuman (?:authority|review)\b",
                    "severity": "error",
                    "message": "missing",
                },
                {
                    "id": "boundary",
                    "pattern": r"\bboundary\b",
                    "severity": "error",
                    "message": "missing",
                },
            ],
            "prohibited_claim_patterns": [
                {
                    "id": "guaranteed-outcome",
                    "pattern": r"\bguaranteed success\b",
                    "severity": "error",
                    "message": "unsafe",
                }
            ],
            "claim_inputs": [
                {
                    "path": "website/data/blades.json",
                    "schema": "aureon-sector-blades-v1",
                    "required": True,
                },
                {"path": "website/data/research-catalogue.json", "required": True},
                {"path": "website/data/funding-status.json", "required": True},
                {"path": "website/data/operator-evidence.json", "required": True},
            ],
        },
        "budgets": {
            "policy": "fixed",
            "site_total_bytes": total_bytes,
            "site_file_count": 200,
            "critical_page_direct_bytes": 500_000,
            "per_file_bytes": {
                ".html": per_html,
                ".css": 200_000,
                ".js": 200_000,
                ".json": 200_000,
                ".svg": 200_000,
                ".webmanifest": 200_000,
            },
        },
        "checks": {"require_reduced_motion": True, "external": []},
        "packaging": {
            "required_release_paths": [
                "index.html",
                "script.js",
                "styles.css",
                "tokens.css",
                "funding/funding-status.js",
                "live/live.js",
                "data/blades.json",
            ],
            "blocked_file_names": [".env", "id_rsa"],
            "blocked_extensions": [".env", ".key", ".pem"],
            "allowed_file_names": [".htaccess"],
            "allowed_extensions": [".html", ".css", ".js", ".json", ".svg", ".webmanifest"],
            "secret_patterns": [
                r"-----BEGIN (?:RSA )?PRIVATE KEY-----",
                r"\bsk-[A-Za-z0-9_-]{20,}\b",
                r"\bpassword\s*[:=]\s*[\"'][^\"']{8,}[\"']",
            ],
        },
    }


def _html(*, body_suffix: str = "", bad_reference: str = "") -> str:
    reference = f'<a href="{bad_reference}">Bad</a>' if bad_reference else ""
    description = (
        "Research-led evidence infrastructure with explicit human review, "
        "claim boundaries and inspectable public sources for serious decisions."
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{description}">
<meta name="robots" content="index, follow, max-image-preview:large">
<meta name="theme-color" content="#101010">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Aureon Zorza Technologies">
<meta property="og:locale" content="en_GB">
<meta property="og:title" content="Aureon Evidence and Research Systems">
<meta property="og:description" content="{description}">
<meta property="og:url" content="https://aureonzorzatechnologies.pl/">
<meta property="og:image" content="https://aureonzorzatechnologies.pl/assets/share.svg">
<meta property="og:image:alt" content="Aureon evidence system">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Aureon Evidence and Research Systems">
<meta name="twitter:description" content="{description}">
<meta name="twitter:image" content="https://aureonzorzatechnologies.pl/assets/share.svg">
<meta name="twitter:image:alt" content="Aureon evidence system">
<title>Aureon Evidence and Research Systems</title>
<link rel="canonical" href="https://aureonzorzatechnologies.pl/">
<link rel="manifest" href="./site.webmanifest">
<link rel="icon" href="./assets/icon.svg">
<link rel="stylesheet" href="./styles.css?v=static-v1">
<link rel="stylesheet" href="./tokens.css?v=static-v1">
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"Organization"}}</script>
<script src="./script.js?v=static-v1" defer></script>
</head>
<body>
<a href="#main" class="skip-link">Skip</a>
<nav aria-label="Primary"></nav>
<main id="main">
<h1>Evidence-led research systems</h1>
<p>Research and evidence retain a visible claim boundary and human authority.</p>
<img src="./assets/share.svg" alt="Evidence graph">
{reference}{body_suffix}
</main>
</body>
</html>
"""


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )


def _make_repo(tmp_path: Path, *, config: dict[str, object] | None = None) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    operator = repo / "aureon" / "operator"
    operator.mkdir(parents=True)
    (repo / "pyproject.toml").write_text("[project]\nname='test'\n", encoding="utf-8")
    _write_json(operator / "website_operator.defaults.json", config or _config())
    (repo / "website").mkdir()
    root = repo / "artifacts" / "website-candidates" / "qa-run-1" / "website"
    root.mkdir(parents=True)
    (root / "index.html").write_text(_html(), encoding="utf-8")
    (root / "styles.css").write_text(
        "@media (prefers-reduced-motion: reduce) { * { animation: none !important; } }\n",
        encoding="utf-8",
    )
    (root / "tokens.css").write_text(":root { --space: 1rem; }\n", encoding="utf-8")
    (root / "script.js").write_text(
        'if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) { console.info("still"); }\n',
        encoding="utf-8",
    )
    (root / "funding").mkdir()
    (root / "funding" / "funding-status.js").write_text('"use strict";\n', encoding="utf-8")
    (root / "live").mkdir()
    (root / "live" / "live.js").write_text('"use strict";\n', encoding="utf-8")
    (root / "assets").mkdir()
    (root / "assets" / "share.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630"></svg>\n',
        encoding="utf-8",
    )
    (root / "assets" / "icon.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64"></svg>\n',
        encoding="utf-8",
    )
    _write_json(
        root / "site.webmanifest",
        {
            "name": "Aureon",
            "short_name": "Aureon",
            "start_url": "/",
            "display": "standalone",
            "icons": [{"src": "assets/icon.svg", "sizes": "64x64", "type": "image/svg+xml"}],
        },
    )
    _write_json(root / "data" / "blades.json", {"schema": "aureon-sector-blades-v1"})
    _write_json(root / "data" / "research-catalogue.json", {"records": []})
    _write_json(root / "data" / "funding-status.json", {"state": "public"})
    _write_json(root / "data" / "operator-evidence.json", {"state": "bounded"})
    return repo, root


def _bind_repo(monkeypatch: pytest.MonkeyPatch, repo: Path) -> None:
    monkeypatch.setattr(qa, "_repo_root_from_file", lambda: repo)


@pytest.mark.parametrize("mode", qa.MODES)
def test_valid_candidate_is_deterministic_and_non_authoritative(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    before = qa._snapshot_tree(root)
    first = qa.audit_candidate_static(root, mode=mode)
    second = qa.audit_candidate_static(root, mode=mode)
    assert first == second
    assert qa._canonical_bytes(first) == qa._canonical_bytes(second)
    assert first["schema"] == qa.SCHEMA
    assert set(first) == {
        "schema",
        "mode",
        "source",
        "checks",
        "findings",
        "decision",
        "limitations",
        "authority",
    }
    assert set(first["source"]) == {"root", "tree_sha256", "file_count", "total_bytes"}
    assert first["source"]["root"] == "artifacts/website-candidates/qa-run-1/website"
    assert first["source"]["tree_sha256"] == before["tree_sha256"]
    assert first["authority"]["release_eligible"] is False
    assert first["authority"]["deployment_authority"] == "none"
    assert "v28-composite-visual-release-gate-not-satisfied" in first["limitations"]
    assert qa._snapshot_tree(root) == before
    serialised = qa._canonical_bytes(first).decode("utf-8")
    assert str(root) not in serialised
    assert "generated_at" not in serialised


def test_canonical_root_substitution_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo, _ = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    with pytest.raises(qa.CandidateStaticQABoundaryError):
        qa.audit_candidate_static(repo / "website", mode="website-operator-static")


@pytest.mark.parametrize(
    "value",
    [
        "../website",
        r"\\server\share\website",
        "file:///tmp/website",
        "https://example.test/website",
    ],
)
def test_traversal_unc_and_urls_are_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    value: str,
) -> None:
    repo, _ = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    with pytest.raises(qa.CandidateStaticQABoundaryError):
        qa.audit_candidate_static(value, mode="website-operator-static")


def test_wrong_staged_layout_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo, _ = _make_repo(tmp_path)
    root = repo / "artifacts" / "website-candidates" / "qa-run-1" / "nested" / "website"
    root.mkdir(parents=True)
    _bind_repo(monkeypatch, repo)
    with pytest.raises(qa.CandidateStaticQABoundaryError, match="candidate-root-layout-invalid"):
        qa.audit_candidate_static(root, mode="website-operator-static")


def test_symlink_and_hardlink_are_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    os.link(root / "script.js", root / "hardlink.js")
    with pytest.raises(qa.CandidateStaticQABoundaryError, match="candidate-tree-hardlink"):
        qa.audit_candidate_static(root, mode="website-operator-static")
    (root / "hardlink.js").unlink()
    try:
        (root / "linked.js").symlink_to(root / "script.js")
    except OSError:
        pytest.skip("Symbolic links are unavailable for this test account.")
    with pytest.raises(qa.CandidateStaticQABoundaryError, match="candidate-tree-link-or-reparse"):
        qa.audit_candidate_static(root, mode="website-operator-static")


@pytest.mark.parametrize(
    ("relative", "payload", "code"),
    [
        ("data/blades.json", b"\xff", "candidate-text-invalid-utf8"),
        ("data/blades.json", b'{"schema":"a","schema":"b"}', "candidate-public-json-invalid"),
        ("data/blades.json", b'{"value":NaN}', "candidate-public-json-invalid"),
        ("script.js", b"\xef\xbb\xbfconst ok = true;", "candidate-text-invalid-utf8"),
    ],
)
def test_invalid_utf8_duplicate_json_and_nonfinite_json_fail_the_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    relative: str,
    payload: bytes,
    code: str,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    (root / relative).write_bytes(payload)
    with pytest.raises(qa.CandidateStaticQABoundaryError, match=code):
        qa.audit_candidate_static(root, mode="website-operator-static")


def test_missing_local_reference_and_fragment_are_blockers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    (root / "index.html").write_text(
        _html(bad_reference="./missing.html#absent").replace('href="#main"', 'href="#absent"'),
        encoding="utf-8",
    )
    receipt = qa.audit_candidate_static(root, mode="v28-design-system-static")
    codes = {item["code"] for item in receipt["findings"]}
    assert "local-reference-target-missing" in codes
    assert "fragment-target-missing" in codes
    assert receipt["decision"]["status"] == "blocked"


def test_accessibility_and_reduced_motion_findings_are_static_blockers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    html = _html().replace(' alt="Evidence graph"', "").replace("<main", "<div").replace("</main>", "</div>")
    html = html.replace("</body>", '<video autoplay src="./assets/share.svg"></video></body>')
    (root / "index.html").write_text(html, encoding="utf-8")
    (root / "styles.css").write_text("body { color: white; }\n", encoding="utf-8")
    (root / "script.js").write_text('"use strict";\n', encoding="utf-8")
    receipt = qa.audit_candidate_static(root, mode="v28-design-system-static")
    codes = {item["code"] for item in receipt["findings"]}
    assert {
        "main-landmark-missing",
        "image-alt-missing",
        "autoplay-media",
        "reduced-motion-css-missing",
        "reduced-motion-javascript-gate-missing",
    }.issubset(codes)


def test_metadata_jsonld_and_ethos_findings_do_not_echo_raw_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    unsafe = "guaranteed success"
    html = _html(body_suffix=f"<p>{unsafe}</p>")
    html = html.replace('content="https://aureonzorzatechnologies.pl/"', 'content="https://wrong.test/"', 1)
    html = html.replace('{"@context":"https://schema.org","@type":"Organization"}', '{"@type":NaN}')
    (root / "index.html").write_text(html, encoding="utf-8")
    receipt = qa.audit_candidate_static(root, mode="v28-metadata-ethos-static")
    serialised = qa._canonical_bytes(receipt).decode("utf-8")
    codes = {item["code"] for item in receipt["findings"]}
    assert "jsonld-invalid" in codes
    assert "prohibited-public-claim-pattern" in codes
    assert unsafe not in serialised
    assert "wrong.test" not in serialised


def test_secret_and_budget_evidence_is_hash_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = _config(total_bytes=300, per_html=100)
    repo, root = _make_repo(tmp_path, config=config)
    _bind_repo(monkeypatch, repo)
    secret = "sk-" + "A" * 28
    (root / "script.js").write_text(f'const token = "{secret}";\n', encoding="utf-8")
    receipt = qa.audit_candidate_static(root, mode="website-operator-static")
    codes = {item["code"] for item in receipt["findings"]}
    assert "site-total-byte-budget-exceeded" in codes
    assert "per-file-byte-budget-exceeded" in codes
    assert "public-secret-pattern" in codes
    serialised = qa._canonical_bytes(receipt).decode("utf-8")
    assert secret not in serialised
    assert str(root) not in serialised


def test_tree_mutation_between_endpoints_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    original = qa._snapshot_tree
    calls = 0

    def mutating_snapshot(candidate: Path) -> dict[str, object]:
        nonlocal calls
        result = original(candidate)
        calls += 1
        if calls == 1:
            (candidate / "script.js").write_text('"mutated";\n', encoding="utf-8")
        return result

    monkeypatch.setattr(qa, "_snapshot_tree", mutating_snapshot)
    with pytest.raises(qa.CandidateStaticQABoundaryError, match="candidate-tree-mutated-during-audit"):
        qa.audit_candidate_static(root, mode="website-operator-static")


def test_cli_contract_rejects_duplicate_unknown_and_write_arguments(
    capsys: pytest.CaptureFixture[str],
) -> None:
    cases = [
        ["--mode", qa.MODES[0], "--mode", qa.MODES[1]],
        ["--mode", "unknown", "--candidate-root", r"C:\candidate"],
        ["--mode", qa.MODES[0], "--candidate-root", r"C:\candidate", "--output", "report.json"],
        ["--mode", qa.MODES[0], "--candidate-root", r"C:\candidate", "--write"],
    ]
    for arguments in cases:
        assert qa.main(arguments) == 3
        payload = json.loads(capsys.readouterr().out)
        assert payload["decision"]["status"] == "invalid"
        assert payload["authority"]["candidate_mutation"] == "none"


def test_cli_outputs_one_canonical_line_and_ignores_output_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    injected = tmp_path / "injected-report.json"
    monkeypatch.setenv("AUREON_OUTPUT", str(injected))
    exit_code = qa.main(
        [
            "--mode",
            "website-operator-static",
            "--candidate-root",
            str(root),
        ]
    )
    output = capsys.readouterr().out
    payload = json.loads(output)
    assert exit_code == 0
    assert output == qa._canonical_bytes(payload).decode("utf-8") + "\n"
    assert not injected.exists()


def test_findings_exit_two_without_writing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    (root / "data" / "operator-evidence.json").unlink()
    before = qa._snapshot_tree(root)
    assert (
        qa.main(
            [
                "--mode",
                "website-operator-static",
                "--candidate-root",
                str(root),
            ]
        )
        == 2
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["decision"]["status"] == "blocked"
    assert qa._snapshot_tree(root) == before


def test_referenced_extra_malformed_javascript_cannot_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    (root / "extra.js").write_text("function malformed( {\n", encoding="utf-8")
    html = (root / "index.html").read_text(encoding="utf-8")
    (root / "index.html").write_text(
        html.replace("</body>", '<script src="./extra.js"></script></body>'),
        encoding="utf-8",
    )
    receipt = qa.audit_candidate_static(root, mode="v28-design-system-static")
    codes = {item["code"] for item in receipt["findings"]}
    assert "unreviewed-javascript-file" in codes
    assert "unreviewed-executable-script-source" in codes
    assert receipt["decision"]["status"] == "blocked"


def test_inline_executable_javascript_is_rejected_while_jsonld_remains_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    html = (root / "index.html").read_text(encoding="utf-8")
    (root / "index.html").write_text(
        html.replace("</body>", "<script>function malformed( {</script></body>"),
        encoding="utf-8",
    )
    receipt = qa.audit_candidate_static(root, mode="v28-design-system-static")
    matching = [item for item in receipt["findings"] if item["code"] == "inline-executable-script-rejected"]
    assert len(matching) == 1
    assert matching[0]["path"] == "index.html"


def test_html_base_cannot_retarget_an_allowlisted_relative_script(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    html = (root / "index.html").read_text(encoding="utf-8")
    (root / "index.html").write_text(
        html.replace("<head>", '<head><base href="https://attacker.invalid/">'),
        encoding="utf-8",
    )
    receipt = qa.audit_candidate_static(root, mode="v28-design-system-static")
    assert "html-base-element-rejected" in {item["code"] for item in receipt["findings"]}


@pytest.mark.parametrize(
    "replacement",
    [
        '<html lang="en" lang="fr">',
        '<link rel="canonical" rel="alternate" href="https://aureonzorzatechnologies.pl/">',
        '<meta name="description" content="first" content="second">',
    ],
)
def test_duplicate_html_attributes_fail_before_semantic_audit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    replacement: str,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    html = (root / "index.html").read_text(encoding="utf-8")
    if replacement.startswith("<html"):
        html = html.replace('<html lang="en">', replacement)
    elif replacement.startswith("<link"):
        html = re.sub(r"<link rel=\"canonical\"[^>]+>", replacement, html, count=1)
    else:
        html = re.sub(r"<meta name=\"description\"[^>]+>", replacement, html, count=1)
    (root / "index.html").write_text(html, encoding="utf-8")
    with pytest.raises(
        qa.CandidateStaticQABoundaryError,
        match="candidate-html-duplicate-attribute",
    ):
        qa.audit_candidate_static(root, mode="v28-metadata-ethos-static")


def test_duplicate_canonical_and_meta_elements_are_not_collapsed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    html = (root / "index.html").read_text(encoding="utf-8")
    duplicate = """
<link rel="canonical" href="https://aureonzorzatechnologies.pl/">
<meta name="description" content="A second metadata value must not be silently selected.">
"""
    (root / "index.html").write_text(
        html.replace("</head>", f"{duplicate}</head>"),
        encoding="utf-8",
    )
    receipt = qa.audit_candidate_static(root, mode="v28-metadata-ethos-static")
    codes = {item["code"] for item in receipt["findings"]}
    assert "canonical-count-invalid" in codes
    assert "duplicate-meta-identity" in codes


def test_env_variant_and_unapproved_extension_fail_closed_without_secret_echo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    secret = "sk-" + "Z" * 28
    (root / ".env.local").write_text(f"API_TOKEN={secret}\n", encoding="utf-8")
    receipt = qa.audit_candidate_static(root, mode="website-operator-static")
    codes = {item["code"] for item in receipt["findings"]}
    assert "blocked-public-file" in codes
    assert "public-secret-pattern" in codes
    assert secret not in qa._canonical_bytes(receipt).decode("utf-8")


def test_unapproved_type_is_a_blocker_only_when_selected_by_public_closure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    (root / "operator-notes.md").write_text("Non-public source note.\n", encoding="utf-8")
    clean = qa.audit_candidate_static(root, mode="website-operator-static")
    assert "unapproved-public-file-type" not in {item["code"] for item in clean["findings"]}
    (root / "public.payload").write_text("referenced", encoding="utf-8")
    html = (root / "index.html").read_text(encoding="utf-8")
    (root / "index.html").write_text(
        html.replace("</body>", '<a href="./public.payload">Public payload</a></body>'),
        encoding="utf-8",
    )
    blocked = qa.audit_candidate_static(root, mode="website-operator-static")
    assert "unapproved-public-file-type" in {item["code"] for item in blocked["findings"]}


def test_reduced_motion_markers_in_comments_or_strings_do_not_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    (root / "styles.css").write_text(
        "/* @media (prefers-reduced-motion: reduce) {} */\n"
        'body::before { content: "@media (prefers-reduced-motion: reduce)"; }\n',
        encoding="utf-8",
    )
    (root / "script.js").write_text(
        '// matchMedia("(prefers-reduced-motion: reduce)")\n'
        'const decoy = "matchMedia(\\"(prefers-reduced-motion: reduce)\\")";\n',
        encoding="utf-8",
    )
    receipt = qa.audit_candidate_static(root, mode="v28-design-system-static")
    codes = {item["code"] for item in receipt["findings"]}
    assert "reduced-motion-css-missing" in codes
    assert "reduced-motion-javascript-gate-missing" in codes


@pytest.mark.parametrize(
    "wrapper",
    [
        "<!-- {} -->",
        "<template>{}</template>",
        "<noscript>{}</noscript>",
    ],
)
def test_inert_jsonld_is_not_structural_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    wrapper: str,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    html = (root / "index.html").read_text(encoding="utf-8")
    block = (
        '<script type="application/ld+json">{"@context":"https://schema.org","@type":"Organization"}</script>'
    )
    assert block in html
    (root / "index.html").write_text(
        html.replace(block, wrapper.format(block)),
        encoding="utf-8",
    )
    receipt = qa.audit_candidate_static(root, mode="v28-metadata-ethos-static")
    codes = {item["code"] for item in receipt["findings"]}
    assert "jsonld-missing" in codes
    assert "homepage-organization-schema-missing" not in codes


@pytest.mark.parametrize(
    "source",
    [
        "https://aureonzorzatechnologies.pl/script.js?v=static-v1",
        "//aureonzorzatechnologies.pl/script.js?v=static-v1",
    ],
)
def test_reviewed_javascript_must_use_a_staged_local_url(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source: str,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    html = (root / "index.html").read_text(encoding="utf-8")
    (root / "index.html").write_text(
        html.replace("./script.js?v=static-v1", source),
        encoding="utf-8",
    )
    receipt = qa.audit_candidate_static(root, mode="v28-design-system-static")
    assert "remote-executable-script-rejected" in {item["code"] for item in receipt["findings"]}


@pytest.mark.parametrize(
    "surface",
    [
        '<iframe title="Active child" src="data:text/html,&lt;script&gt;alert(1)&lt;/script&gt;"></iframe>',
        '<object data="data:text/html,active"></object>',
        '<embed src="https://attacker.invalid/payload.html">',
        '<form action="javascript:alert(1)"><button type="submit">Go</button></form>',
        '<button type="submit" formaction="blob:https://attacker.invalid/id">Go</button>',
        '<input type="submit" formaction="data:text/html,active">',
        '<img src="data:image/svg+xml,%3Csvg/%3E" alt="Inline payload">',
        '<svg><use xlink:href="javascript:alert(1)"></use></svg>',
        '<meta http-equiv="refresh" content="0; url=javascript:alert(1)">',
    ],
)
def test_active_url_surfaces_reject_embedded_code_and_remote_active_content(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    surface: str,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    html = (root / "index.html").read_text(encoding="utf-8")
    (root / "index.html").write_text(
        html.replace("</body>", f"{surface}</body>"),
        encoding="utf-8",
    )
    receipt = qa.audit_candidate_static(root, mode="v28-design-system-static")
    assert "active-content-url-rejected" in {item["code"] for item in receipt["findings"]}


def test_active_content_local_target_is_validated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    html = (root / "index.html").read_text(encoding="utf-8")
    (root / "index.html").write_text(
        html.replace(
            "</body>",
            '<iframe title="Missing child" src="./missing-active.html"></iframe></body>',
        ),
        encoding="utf-8",
    )
    receipt = qa.audit_candidate_static(root, mode="v28-design-system-static")
    assert "local-reference-target-missing" in {item["code"] for item in receipt["findings"]}


@pytest.mark.parametrize(
    "css",
    [
        "@media (prefers-reduced-motion: reduce) {}\n",
        "@media (prefers-reduced-motion: reduce) { body { color: white; } }\n",
    ],
)
@pytest.mark.parametrize(
    "javascript",
    [
        'void window.matchMedia("(prefers-reduced-motion: reduce)").matches;\n',
        'if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {}\n',
        'if (window.matchMedia("(prefers-reduced-motion: reduce)").matches);\n',
    ],
)
def test_reduced_motion_requires_a_disabling_rule_and_a_real_branch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    css: str,
    javascript: str,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    (root / "styles.css").write_text(css, encoding="utf-8")
    (root / "script.js").write_text(javascript, encoding="utf-8")
    receipt = qa.audit_candidate_static(root, mode="v28-design-system-static")
    codes = {item["code"] for item in receipt["findings"]}
    assert "reduced-motion-css-effect-missing" in codes
    assert "reduced-motion-javascript-gate-missing" in codes


@pytest.mark.parametrize(
    ("opening", "closing"),
    [
        ("<template>", "</template>"),
        ("<noscript>", "</noscript>"),
        ("<section inert>", "</section>"),
    ],
)
def test_inert_descendants_do_not_supply_structure_ids_or_fragments(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    opening: str,
    closing: str,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    html = (root / "index.html").read_text(encoding="utf-8")
    html = html.replace('<main id="main">', f'{opening}<main id="main">')
    html = html.replace("</main>", f"</main>{closing}")
    (root / "index.html").write_text(html, encoding="utf-8")
    receipt = qa.audit_candidate_static(root, mode="v28-design-system-static")
    codes = {item["code"] for item in receipt["findings"]}
    assert "h1-count-invalid" in codes
    assert "main-landmark-missing" in codes
    assert "fragment-target-missing" in codes


def test_noscript_copy_does_not_supply_public_ethos(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    phrase = "Research and evidence retain a visible claim boundary and human authority."
    html = (root / "index.html").read_text(encoding="utf-8")
    (root / "index.html").write_text(
        html.replace(f"<p>{phrase}</p>", f"<noscript><p>{phrase}</p></noscript>"),
        encoding="utf-8",
    )
    receipt = qa.audit_candidate_static(root, mode="v28-metadata-ethos-static")
    assert "required-ethos-signal-missing" in {item["code"] for item in receipt["findings"]}


def test_critical_route_robots_noindex_nofollow_is_blocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    html = (root / "index.html").read_text(encoding="utf-8")
    (root / "index.html").write_text(
        html.replace(
            'content="index, follow, max-image-preview:large"',
            'content="noindex, nofollow"',
        ),
        encoding="utf-8",
    )
    receipt = qa.audit_candidate_static(root, mode="v28-metadata-ethos-static")
    codes = {item["code"] for item in receipt["findings"]}
    assert "critical-route-noindex" in codes
    assert "critical-route-nofollow" in codes


@pytest.mark.parametrize(
    "surface",
    [
        "manifest",
        "social",
        "object",
        "embed",
        "iframe",
        "track",
        "input",
        "svg",
        "form",
        "refresh",
        "ping",
        "style-attribute",
        "style-block",
        "css-import",
    ],
)
def test_every_browser_loadable_reference_enters_release_type_policy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    surface: str,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    target = root / "assets" / "payload.ps1"
    target.write_text("Write-Output 'not a public asset'\n", encoding="utf-8")
    html = (root / "index.html").read_text(encoding="utf-8")
    body_surfaces = {
        "object": '<object data="./assets/payload.ps1"></object>',
        "embed": '<embed src="./assets/payload.ps1">',
        "iframe": '<iframe title="Payload" src="./assets/payload.ps1"></iframe>',
        "track": '<video><track src="./assets/payload.ps1"></video>',
        "input": '<input type="image" src="./assets/payload.ps1" alt="Submit">',
        "svg": '<svg><use href="./assets/payload.ps1"></use></svg>',
        "form": '<form action="./assets/payload.ps1"></form>',
        "refresh": '<meta http-equiv="refresh" content="0; url=./assets/payload.ps1">',
        "ping": '<a href="#main" ping="./assets/payload.ps1">Ping</a>',
        "style-attribute": ("<div style=\"background-image:url('./assets/payload.ps1')\">Styled</div>"),
        "style-block": '<style>@import "./assets/payload.ps1";</style>',
    }
    if surface == "manifest":
        manifest = json.loads((root / "site.webmanifest").read_text(encoding="utf-8"))
        manifest["icons"][0]["src"] = "assets/payload.ps1"
        _write_json(root / "site.webmanifest", manifest)
    elif surface == "social":
        html = html.replace(
            "https://aureonzorzatechnologies.pl/assets/share.svg",
            "https://aureonzorzatechnologies.pl/assets/payload.ps1",
        )
        (root / "index.html").write_text(html, encoding="utf-8")
    elif surface == "css-import":
        css = (root / "styles.css").read_text(encoding="utf-8")
        (root / "styles.css").write_text(
            '@import "./assets/payload.ps1";\n' + css,
            encoding="utf-8",
        )
    else:
        (root / "index.html").write_text(
            html.replace("</body>", f"{body_surfaces[surface]}</body>"),
            encoding="utf-8",
        )
    receipt = qa.audit_candidate_static(root, mode="website-operator-static")
    assert "unapproved-public-file-type" in {item["code"] for item in receipt["findings"]}


@pytest.mark.parametrize(
    "surface",
    [
        "start-url",
        "scope",
        "shortcut-url",
        "shortcut-icon",
        "share-target",
        "protocol-handler",
        "file-handler",
        "serviceworker",
    ],
)
def test_every_webmanifest_url_field_enters_the_typed_release_closure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    surface: str,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    (root / "assets" / "payload.ps1").write_text(
        "Write-Output 'not public'\n",
        encoding="utf-8",
    )
    manifest = json.loads((root / "site.webmanifest").read_text(encoding="utf-8"))
    target = "assets/payload.ps1"
    if surface == "start-url":
        manifest["start_url"] = target
    elif surface == "scope":
        manifest["scope"] = target
    elif surface == "shortcut-url":
        manifest["shortcuts"] = [{"name": "x", "url": target}]
    elif surface == "shortcut-icon":
        manifest["shortcuts"] = [{"name": "x", "url": "/", "icons": [{"src": target}]}]
    elif surface == "share-target":
        manifest["share_target"] = {
            "action": target,
            "method": "GET",
            "params": {"text": "text"},
        }
    elif surface == "protocol-handler":
        manifest["protocol_handlers"] = [{"protocol": "web+x", "url": target}]
    elif surface == "file-handler":
        manifest["file_handlers"] = [{"action": target, "accept": {"text/plain": [".txt"]}}]
    else:
        manifest["serviceworker"] = {"src": target}
    _write_json(root / "site.webmanifest", manifest)
    website = qa.audit_candidate_static(root, mode="website-operator-static")
    metadata = qa.audit_candidate_static(root, mode="v28-metadata-ethos-static")
    assert "unapproved-public-file-type" in {item["code"] for item in website["findings"]}
    assert any(
        item["code"]
        in {
            "webmanifest-asset-target-type-invalid",
            "webmanifest-executable-target-rejected",
            "webmanifest-navigation-target-type-invalid",
        }
        for item in metadata["findings"]
    )


@pytest.mark.parametrize(
    ("reference", "expected"),
    [
        ("assets/missing.png", "webmanifest-local-target-missing"),
        (
            "https://attacker.invalid/screenshot.png",
            "webmanifest-active-or-remote-url-rejected",
        ),
        ("data:image/png;base64,AA==", "webmanifest-active-or-remote-url-rejected"),
    ],
)
def test_webmanifest_screenshots_must_be_local_ordinary_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    reference: str,
    expected: str,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    manifest = json.loads((root / "site.webmanifest").read_text(encoding="utf-8"))
    manifest["screenshots"] = [{"src": reference, "sizes": "1200x630"}]
    _write_json(root / "site.webmanifest", manifest)
    website = qa.audit_candidate_static(root, mode="website-operator-static")
    metadata = qa.audit_candidate_static(root, mode="v28-metadata-ethos-static")
    assert website["decision"]["status"] == "blocked"
    assert expected in {item["code"] for item in metadata["findings"]}


@pytest.mark.parametrize("opening", ["<template/>", "<section inert/>"])
def test_nonvoid_self_closing_html_cannot_create_a_parser_differential(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    opening: str,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    html = (root / "index.html").read_text(encoding="utf-8")
    (root / "index.html").write_text(
        html.replace("<body>", f"<body>{opening}"),
        encoding="utf-8",
    )
    receipt = qa.audit_candidate_static(root, mode="v28-design-system-static")
    codes = {item["code"] for item in receipt["findings"]}
    assert "nonvoid-self-closing-html-tag" in codes
    assert "h1-count-invalid" in codes
    assert "main-landmark-missing" in codes


@pytest.mark.parametrize("context", ["hidden", "inline-style", "textarea", "select"])
def test_nonrendered_descendants_cannot_supply_live_structure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    context: str,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    html = (root / "index.html").read_text(encoding="utf-8")
    if context == "hidden":
        html = html.replace('<main id="main">', '<main id="main" hidden>')
    elif context == "inline-style":
        html = html.replace(
            '<main id="main">',
            '<main id="main" style="display: none">',
        )
    else:
        html = html.replace('<main id="main">', f'<{context}><main id="main">')
        html = html.replace("</main>", f"</main></{context}>")
    (root / "index.html").write_text(html, encoding="utf-8")
    receipt = qa.audit_candidate_static(root, mode="v28-design-system-static")
    codes = {item["code"] for item in receipt["findings"]}
    assert "h1-count-invalid" in codes
    assert "main-landmark-missing" in codes
    assert "fragment-target-missing" in codes


@pytest.mark.parametrize(
    ("opening", "closing"),
    [
        ("<div hidden>", "</div>"),
        ("<textarea hidden>", "</textarea>"),
        ("<select>", "</select>"),
        ("<style>", "</style>"),
        ("<script>", "</script>"),
    ],
)
def test_nonrendered_copy_cannot_supply_public_ethos(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    opening: str,
    closing: str,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    phrase = "Research and evidence retain a visible claim boundary and human authority."
    html = (root / "index.html").read_text(encoding="utf-8")
    (root / "index.html").write_text(
        html.replace(f"<p>{phrase}</p>", f"{opening}{phrase}{closing}"),
        encoding="utf-8",
    )
    receipt = qa.audit_candidate_static(root, mode="v28-metadata-ethos-static")
    assert "required-ethos-signal-missing" in {item["code"] for item in receipt["findings"]}


@pytest.mark.parametrize(
    "meta",
    [
        '<meta name="robots" content="none">',
        '<meta name="googlebot" content="noindex, nofollow">',
        '<meta name="bingbot" content="nosnippet">',
        '<meta http-equiv="X-Robots-Tag" content="noindex">',
    ],
)
def test_critical_routes_reject_all_meta_indexing_suppression_aliases(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    meta: str,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    html = (root / "index.html").read_text(encoding="utf-8")
    html = re.sub(r'<meta name="robots"[^>]+>', meta, html, count=1)
    (root / "index.html").write_text(html, encoding="utf-8")
    receipt = qa.audit_candidate_static(root, mode="v28-metadata-ethos-static")
    assert receipt["decision"]["status"] == "blocked"
    assert any(str(item["code"]).startswith("critical-route-") for item in receipt["findings"])


def test_htaccess_x_robots_tag_cannot_suppress_critical_routes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    (root / ".htaccess").write_text(
        'Header set X-Robots-Tag "noindex, nofollow"\n',
        encoding="utf-8",
    )
    receipt = qa.audit_candidate_static(root, mode="v28-metadata-ethos-static")
    assert "critical-route-htaccess-indexing-suppression" in {item["code"] for item in receipt["findings"]}


@pytest.mark.parametrize("disallow", ["/", "/*", "/index.html", "/$"])
def test_robots_txt_cannot_disallow_a_critical_route(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    disallow: str,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    (root / "robots.txt").write_text(
        f"User-agent: *\nDisallow: {disallow}\n",
        encoding="utf-8",
    )
    receipt = qa.audit_candidate_static(root, mode="v28-metadata-ethos-static")
    assert "critical-route-robots-txt-disallow" in {item["code"] for item in receipt["findings"]}


@pytest.mark.parametrize(
    ("css", "javascript", "expected"),
    [
        (
            "@media (prefers-reduced-motion: reduce) { .x { --animation: none; } }\n",
            'if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;\n',
            "reduced-motion-css-effect-missing",
        ),
        (
            "@media (prefers-reduced-motion: reduce) {"
            " @media (prefers-reduced-motion: no-preference) {"
            " .x { animation: none; } } }\n",
            'if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;\n',
            "reduced-motion-css-effect-missing",
        ),
        (
            "@media (prefers-reduced-motion: reduce) { .x { animation: none; } }\n",
            'if (matchMedia("(prefers-reduced-motion: reduce)").matches) { void 0; }\n',
            "reduced-motion-javascript-gate-missing",
        ),
        (
            "@media (prefers-reduced-motion: reduce) { .x { animation: none; } }\n",
            'if (false) { if (matchMedia("(prefers-reduced-motion: reduce)").matches) return; }\n',
            "reduced-motion-javascript-proof-unavailable",
        ),
    ],
)
def test_reduced_motion_decoys_are_not_effective_or_reachable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    css: str,
    javascript: str,
    expected: str,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    (root / "styles.css").write_text(css, encoding="utf-8")
    (root / "script.js").write_text(javascript, encoding="utf-8")
    receipt = qa.audit_candidate_static(root, mode="v28-design-system-static")
    assert expected in {item["code"] for item in receipt["findings"]}


def test_referenced_svg_active_content_is_recursively_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    (root / "assets" / "active.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"><script>alert(1)</script></svg>',
        encoding="utf-8",
    )
    html = (root / "index.html").read_text(encoding="utf-8")
    (root / "index.html").write_text(
        html.replace(
            "</body>",
            '<object data="./assets/active.svg"></object></body>',
        ),
        encoding="utf-8",
    )
    receipt = qa.audit_candidate_static(root, mode="v28-design-system-static")
    codes = {item["code"] for item in receipt["findings"]}
    assert "active-resource-event-handler-rejected" in codes
    assert "active-resource-script-rejected" in codes


def test_svg_use_dependency_is_recursively_inspected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    (root / "assets" / "inner.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><script>bad()</script></svg>',
        encoding="utf-8",
    )
    (root / "assets" / "outer.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><use href="./inner.svg#shape"/></svg>',
        encoding="utf-8",
    )
    html = (root / "index.html").read_text(encoding="utf-8")
    (root / "index.html").write_text(
        html.replace(
            "</body>",
            '<svg><use href="./assets/outer.svg#shape"></use></svg></body>',
        ),
        encoding="utf-8",
    )
    receipt = qa.audit_candidate_static(root, mode="v28-design-system-static")
    assert "active-resource-script-rejected" in {item["code"] for item in receipt["findings"]}


@pytest.mark.parametrize("function", ["image-set", "-webkit-image-set"])
def test_css_image_set_references_enter_release_and_executable_policy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    function: str,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    (root / "assets" / "payload.ps1").write_text("Write-Output bad\n", encoding="utf-8")
    css = (root / "styles.css").read_text(encoding="utf-8")
    (root / "styles.css").write_text(
        css + f'\n.x {{ background-image: {function}("./assets/payload.ps1" 1x); }}\n',
        encoding="utf-8",
    )
    website = qa.audit_candidate_static(root, mode="website-operator-static")
    design = qa.audit_candidate_static(root, mode="v28-design-system-static")
    assert "unapproved-public-file-type" in {item["code"] for item in website["findings"]}
    assert "active-resource-executable-target-rejected" in {item["code"] for item in design["findings"]}


@pytest.mark.parametrize(
    "surface",
    [
        '<meta http-equiv="refresh" content="0; https://attacker.invalid/">',
        '<meta http-equiv="refresh" content="0; data:text/html,active">',
        '<link rel="prefetch" href="data:text/html,x">',
        '<link rel="preload" href="https://attacker.invalid/x.js" as="script">',
        '<link rel="modulepreload" href="blob:https://attacker.invalid/id">',
        '<link rel="preconnect" href="https://attacker.invalid/">',
        '<link rel="prefetch" href="file:///C:/payload.html">',
    ],
)
def test_refresh_shorthand_and_active_link_rel_urls_are_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    surface: str,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    html = (root / "index.html").read_text(encoding="utf-8")
    (root / "index.html").write_text(
        html.replace("</head>", f"{surface}</head>"),
        encoding="utf-8",
    )
    receipt = qa.audit_candidate_static(root, mode="v28-design-system-static")
    assert "active-content-url-rejected" in {item["code"] for item in receipt["findings"]}


@pytest.mark.parametrize(
    "htaccess",
    [
        'Define ROBOTS_BLOCK noindex\nHeader set X-Robots-Tag "${ROBOTS_BLOCK}"\n',
        'SetEnvIf Request_URI ".*" ROBOT_VALUE=noindex\nHeader set X-Robots-Tag "%{ROBOT_VALUE}e"\n',
        'Define INNER nofollow\nDefine OUTER "${INNER}"\nHeader always set X-Robots-Tag "${OUTER}"\n',
    ],
)
def test_htaccess_indirection_cannot_hide_indexing_suppression(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    htaccess: str,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    (root / ".htaccess").write_text(htaccess, encoding="utf-8")
    receipt = qa.audit_candidate_static(root, mode="v28-metadata-ethos-static")
    assert "critical-route-htaccess-indexing-suppression" in {item["code"] for item in receipt["findings"]}


@pytest.mark.parametrize(
    "disallow",
    [
        "/%69ndex.html",
        "/%2569ndex.html",
        "/%252569ndex.html",
        "/%25252569ndex.html",
        "/%2525252569ndex.html",
    ],
)
def test_robots_txt_percent_encoded_critical_paths_are_canonicalised(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    disallow: str,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    (root / "robots.txt").write_text(
        f"User-agent: *\nDisallow: {disallow}\n",
        encoding="utf-8",
    )
    receipt = qa.audit_candidate_static(root, mode="v28-metadata-ethos-static")
    assert "critical-route-robots-txt-disallow" in {item["code"] for item in receipt["findings"]}


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("/%69ndex.html", "/index.html"),
        ("/%2569ndex.html", "/index.html"),
        ("/%252569ndex.html", "/index.html"),
        ("/%25252569ndex.html", "/index.html"),
        ("/%2525252569ndex.html", None),
        ("/%", None),
        ("/%2", None),
        ("/%GGindex.html", None),
        ("/%C0%AFindex.html", None),
        ("/%00index.html", None),
        ("/%2525255Cindex.html", "/index.html"),
    ],
)
def test_robots_path_canonicalisation_is_strict_and_four_pass_bounded(
    raw: str,
    expected: str | None,
) -> None:
    assert qa._canonical_robots_path(raw) == expected


@pytest.mark.parametrize(
    ("css", "javascript", "expected"),
    [
        (
            "@media (prefers-reduced-motion: reduce) { @media print { .x { animation: none; } } }\n",
            'if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;\n',
            "reduced-motion-css-effect-missing",
        ),
        (
            "@media (prefers-reduced-motion: reduce) {"
            " @supports not (display: block) { .x { animation: none; } } }\n",
            'if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;\n',
            "reduced-motion-css-effect-missing",
        ),
        (
            "@media (prefers-reduced-motion: reduce) { .x { animation: none; } }\n",
            'if (!true) { if (matchMedia("(prefers-reduced-motion: reduce)").matches) return; }\n',
            "reduced-motion-javascript-proof-unavailable",
        ),
        (
            "@media (prefers-reduced-motion: reduce) { .x { animation: none; } }\n",
            'while (false) { if (matchMedia("(prefers-reduced-motion: reduce)").matches) return; }\n',
            "reduced-motion-javascript-proof-unavailable",
        ),
        (
            "@media (prefers-reduced-motion: reduce) { .x { animation: none; } }\n",
            'if(1 > 2){if(matchMedia("(prefers-reduced-motion: reduce)").matches){'
            'document.documentElement.classList.add("reduced");}}\n',
            "reduced-motion-javascript-proof-unavailable",
        ),
    ],
)
def test_reduced_motion_nested_conditionals_and_dead_loops_fail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    css: str,
    javascript: str,
    expected: str,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    (root / "styles.css").write_text(css, encoding="utf-8")
    (root / "script.js").write_text(javascript, encoding="utf-8")
    receipt = qa.audit_candidate_static(root, mode="v28-design-system-static")
    assert expected in {item["code"] for item in receipt["findings"]}


@pytest.mark.parametrize(
    "payload",
    [
        r'.x { background: u\72l("./assets/payload.ps1"); }',
        '.x { background: url/**/("./assets/payload.ps1"); }',
        r'@\69mport "./assets/payload.ps1";',
    ],
)
def test_css_identifier_escapes_and_comments_cannot_hide_release_references(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    payload: str,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    (root / "assets" / "payload.ps1").write_text(
        "Write-Output bad\n",
        encoding="utf-8",
    )
    css = (root / "styles.css").read_text(encoding="utf-8")
    (root / "styles.css").write_text(f"{payload}\n{css}", encoding="utf-8")
    website = qa.audit_candidate_static(root, mode="website-operator-static")
    design = qa.audit_candidate_static(root, mode="v28-design-system-static")
    assert "unapproved-public-file-type" in {item["code"] for item in website["findings"]}
    assert "active-resource-executable-target-rejected" in {item["code"] for item in design["findings"]}


@pytest.mark.parametrize(
    ("svg", "expected"),
    [
        (
            '<?xml-stylesheet href="https://attacker.invalid/x.css"?>'
            '<svg xmlns="http://www.w3.org/2000/svg"></svg>',
            "active-resource-xml-stylesheet-rejected",
        ),
        (
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<set attributeName="href" to="javascript:alert(1)"/></svg>',
            "active-resource-smil-url-mutation-rejected",
        ),
        (
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<path fill="url(https://attacker.invalid/x.svg#p)"/></svg>',
            "active-resource-url-rejected",
        ),
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'xml:base="https://attacker.invalid/"><image href="pixel.svg"/></svg>',
            "active-resource-xml-base-rejected",
        ),
        (
            '<svg xmlns="http://www.w3.org/2000/svg"><g xml:base="../assets/">'
            '<image href="pixel.svg"/></g></svg>',
            "active-resource-xml-base-rejected",
        ),
        (
            '<svg xmlns="http://www.w3.org/2000/svg" xml:base=""></svg>',
            "active-resource-xml-base-rejected",
        ),
    ],
)
def test_svg_processing_instructions_smil_and_paint_urls_are_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    svg: str,
    expected: str,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    (root / "assets" / "active.svg").write_text(svg, encoding="utf-8")
    html = (root / "index.html").read_text(encoding="utf-8")
    (root / "index.html").write_text(
        html.replace(
            "</body>",
            '<object data="./assets/active.svg"></object></body>',
        ),
        encoding="utf-8",
    )
    receipt = qa.audit_candidate_static(root, mode="v28-design-system-static")
    assert expected in {item["code"] for item in receipt["findings"]}


@pytest.mark.parametrize(
    "surface",
    ["external-class", "dialog", "noembed", "plaintext", "xmp"],
)
def test_css_visibility_dialog_and_raw_text_cannot_supply_live_structure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    surface: str,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    html = (root / "index.html").read_text(encoding="utf-8")
    if surface == "external-class":
        css = (root / "styles.css").read_text(encoding="utf-8")
        (root / "styles.css").write_text(
            ".stealth { display: none; }\n" + css,
            encoding="utf-8",
        )
        html = html.replace('<main id="main">', '<main id="main" class="stealth">')
    else:
        html = html.replace('<main id="main">', f'<{surface}><main id="main">')
        html = html.replace("</main>", f"</main></{surface}>")
    (root / "index.html").write_text(html, encoding="utf-8")
    receipt = qa.audit_candidate_static(root, mode="v28-design-system-static")
    codes = {item["code"] for item in receipt["findings"]}
    assert "h1-count-invalid" in codes
    assert "main-landmark-missing" in codes
    assert "fragment-target-missing" in codes


@pytest.mark.parametrize(
    "tag",
    ["iframe", "noembed", "noframes", "plaintext", "textarea", "xmp"],
)
def test_browser_parser_differential_elements_are_categorically_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tag: str,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    html = (root / "index.html").read_text(encoding="utf-8")
    (root / "index.html").write_text(
        html.replace('<main id="main">', f'<{tag}></{tag}><main id="main">'),
        encoding="utf-8",
    )
    receipt = qa.audit_candidate_static(root, mode="v28-design-system-static")
    assert "parser-differential-html-element-rejected" in {item["code"] for item in receipt["findings"]}


@pytest.mark.parametrize("tag", ["noembed", "plaintext"])
def test_parser_differential_nonvoid_self_closing_syntax_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tag: str,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    html = (root / "index.html").read_text(encoding="utf-8")
    (root / "index.html").write_text(
        html.replace('<main id="main">', f'<{tag}/><main id="main">'),
        encoding="utf-8",
    )
    receipt = qa.audit_candidate_static(root, mode="v28-design-system-static")
    codes = {item["code"] for item in receipt["findings"]}
    assert "parser-differential-html-element-rejected" in codes
    assert "nonvoid-self-closing-html-tag" in codes


@pytest.mark.parametrize(
    "rule",
    [
        "@media (min-width:1px){body > main{display:none}}\n",
        "@supports(display:grid){main:is(main){opacity:0}}\n",
    ],
)
def test_conditional_compound_selectors_cannot_hide_the_only_live_main(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    rule: str,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    css = (root / "styles.css").read_text(encoding="utf-8")
    (root / "styles.css").write_text(
        rule + css,
        encoding="utf-8",
    )
    receipt = qa.audit_candidate_static(root, mode="v28-design-system-static")
    codes = {item["code"] for item in receipt["findings"]}
    assert "h1-count-invalid" in codes
    assert "main-landmark-missing" in codes
    assert "fragment-target-missing" in codes


@pytest.mark.parametrize(
    "declaration",
    [
        "display: none",
        "visibility: hidden",
        "content-visibility: hidden",
        "opacity: 0",
    ],
)
def test_conditional_css_cannot_hide_the_only_live_main(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    declaration: str,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    css = (root / "styles.css").read_text(encoding="utf-8")
    (root / "styles.css").write_text(
        f"@media (min-width: 1px) {{ .stealth {{ {declaration}; }} }}\n{css}",
        encoding="utf-8",
    )
    html = (root / "index.html").read_text(encoding="utf-8")
    (root / "index.html").write_text(
        html.replace('<main id="main">', '<main id="main" class="stealth">'),
        encoding="utf-8",
    )
    receipt = qa.audit_candidate_static(root, mode="v28-design-system-static")
    codes = {item["code"] for item in receipt["findings"]}
    assert "h1-count-invalid" in codes
    assert "main-landmark-missing" in codes


def test_large_css_security_scans_have_a_bounded_runtime() -> None:
    stylesheet = "\n".join(f".surface-{index} {{ color: rgb({index % 255} 0 0); }}" for index in range(5_000))
    stylesheet += "\n" + "\n".join(
        f"@media (prefers-reduced-motion: reduce) {{ .motion-{index} {{ animation: none; }} }}"
        for index in range(600)
    )
    stylesheet += (
        "\n@supports (display: grid) {"
        " @media (min-width: 1px) {"
        " .stealth { opacity: 0; }"
        " body > main { display: none; }"
        " main:is(main) { opacity: 0; }"
        " } }\n"
    )
    audit = qa._Audit(
        mode="v28-design-system-static",
        root=Path("."),
        config=_config(),
        snapshot={"files": [{"path": "index.html"}, {"path": "script.js"}]},
    )
    audit.text = {
        "styles.css": stylesheet,
        "script.js": 'if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;\n',
    }
    audit.html = {
        "index.html": qa._parse_html(
            '<script src="./script.js"></script>',
            hidden_classes=set(),
            hidden_ids=set(),
            hidden_tags=set(),
        )
    }
    started = time.monotonic()
    classes, identifiers, tags = qa._css_hidden_selectors([stylesheet])
    audit.reduced_motion()
    elapsed = time.monotonic() - started
    assert classes == {"stealth"}
    assert identifiers == set()
    assert tags == {"main"}
    assert audit.findings == []
    assert elapsed < 5.0


@pytest.mark.parametrize(
    "source",
    [
        "https://aureonzorzatechnologies.pl/styles.css?v=static-v1",
        "//aureonzorzatechnologies.pl/styles.css?v=static-v1",
    ],
)
def test_stylesheets_must_use_staged_local_relative_urls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source: str,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    html = (root / "index.html").read_text(encoding="utf-8")
    (root / "index.html").write_text(
        html.replace("./styles.css?v=static-v1", source),
        encoding="utf-8",
    )
    receipt = qa.audit_candidate_static(root, mode="v28-design-system-static")
    assert "active-content-url-rejected" in {item["code"] for item in receipt["findings"]}


@pytest.mark.parametrize("surface", ["note-taking", "tab-strip"])
def test_additional_manifest_navigation_fields_enter_release_closure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    surface: str,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    (root / "assets" / "payload.ps1").write_text(
        "Write-Output bad\n",
        encoding="utf-8",
    )
    manifest = json.loads((root / "site.webmanifest").read_text(encoding="utf-8"))
    if surface == "note-taking":
        manifest["note_taking"] = {"new_note_url": "./assets/payload.ps1"}
    else:
        manifest["tab_strip"] = {"new_tab_button": {"url": "./assets/payload.ps1"}}
    _write_json(root / "site.webmanifest", manifest)
    website = qa.audit_candidate_static(root, mode="website-operator-static")
    metadata = qa.audit_candidate_static(root, mode="v28-metadata-ethos-static")
    assert "unapproved-public-file-type" in {item["code"] for item in website["findings"]}
    assert "webmanifest-navigation-target-type-invalid" in {item["code"] for item in metadata["findings"]}


@pytest.mark.parametrize(
    ("rule", "main_attributes"),
    [
        ("@media (min-width:1px){main#main{display:none}}", ""),
        (
            "@layer audit{@supports(display:grid){@media(min-width:1px){"
            "html/**/>body/**/ main#main{d\\69 splay:none}}}}",
            "",
        ),
        ('@supports(display:grid){main[id="main"]{visibility:hidden}}', ""),
        ("main#main{display:var(--never-defined, none)}", ""),
        ("main#main{display:var(--never-defined)}", ""),
        ("main#main{opacity:calc(1 - 1)}", ""),
        ("main#main{opacity:calc(0 * 1%)}", ""),
        ("main#main{opacity:min(0, 1)}", ""),
        ("main#main{opacity:clamp(0, env(--conceal), 1)}", ""),
        (":root{--conceal:none}main#main{display:var(--conceal)}", ""),
        ("main#main{filter:opacity(0)}", ""),
        ("main#main{-webkit-filter:opacity(var(--conceal))}", ""),
        ("main#main{transform:scale(0)}", ""),
        ("main#main{clip-path:inset(50%)}", ""),
        ("main#main{position:absolute;left:-9999px}", ""),
        (":root{display:none}", ""),
        (":not(#irrelevant){display:none}", ""),
        ("[data-hide]{display:none}", "data-hide"),
        ("[id^=ma]{display:none}", ""),
        ("[id$=ain]{display:none}", ""),
        ("[id*=ai]{display:none}", ""),
        (":nth-child(1){display:none}", ""),
        (":has(*){display:none}", ""),
        ("body>*{display:none}", ""),
        ("[id=main]{display:none}", ""),
        (":is(main,#x){display:none}", ""),
        (":where(main).x{display:none}", 'class="x"'),
        ("main{&{display:none}}", ""),
        ("main{@media all{display:none}}", ""),
        ("@future audit{main{display:none}}", ""),
    ],
)
def test_candidate_aware_css_concealment_cannot_hide_critical_semantics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    rule: str,
    main_attributes: str,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    css = (root / "styles.css").read_text(encoding="utf-8")
    (root / "styles.css").write_text(f"{rule}\n{css}", encoding="utf-8")
    if main_attributes:
        html = (root / "index.html").read_text(encoding="utf-8")
        (root / "index.html").write_text(
            html.replace('<main id="main">', f'<main id="main" {main_attributes}>'),
            encoding="utf-8",
        )
    receipt = qa.audit_candidate_static(root, mode="v28-design-system-static")
    codes = {item["code"] for item in receipt["findings"]}
    assert "main-landmark-missing" in codes
    assert "h1-count-invalid" in codes


@pytest.mark.parametrize(
    "rule",
    [
        "main#main{transform:matrix(0,0,0,0,0,0)}",
        "main#main{transform:matrix(1, 2, 2, 4, 0, 0)}",
        "main#main{transform:matrix(0,0,0,1,0,0)}",
        "main#main{transform:matrix(1,0,0,0,0,0)}",
        "main#main{transform:matrix(1,0,0,1,+1e4,0)}",
        ("main#main{transform:matrix3d(0,0,0,0, 0,0,0,0, 0,0,0,0, 0,0,0,0)}"),
        ("main#main{transform:matrix3d(1,0,0,0, 0,1,0,0, 0,0,0,0, 0,0,0,1)}"),
        ("main#main{transform:matrix3d(1,0,0,0, 2,0,0,0, 0,0,1,0, 0,0,0,1)}"),
        ("main#main{transform:matrix3d(1,0,0,0, 0,1,0,0, 0,0,1,0, 0,-9999,0,1)}"),
        "main#main{transform:translateX(+100vw)}",
        "main#main{transform:translateY( -100vh )}",
        "main#main{transform:translate(0, +1e4px)}",
        "main#main{transform:translate3d(-100lvw, 0, 0)}",
        "main#main{translate:-9999px 0}",
        "main#main{translate:0 +100dvh}",
        "main#main{translate:+100vi 0 1px}",
        "main#main{position:absolute;inset:-9999px auto auto -9999px}",
        "main#main{position:fixed;inset-inline-start:-9999px}",
        "main#main{position:absolute;inset-block:+100svh auto}",
        "main#main{position:absolute;inset:0 0 0 +100vw}",
        "main#main{position:absolute} main#main{inset-inline-start:-9999px}",
        "main#main{position:fixed} main#main{top:+100dvh}",
        "main#main{position:absolute;clip:rect(1px,1px,1px,1px)}",
        "main#main{clip:rect(2rem 10rem 2rem 0)}",
        "main#main{clip:rect(0, 96px, 10px, 1in)}",
        "main#main{clip:rect(-1px, 1px, 1px, 2px)}",
    ],
    ids=[
        "matrix-all-zero",
        "matrix-nonzero-singular-determinant",
        "matrix-x-axis-collapse",
        "matrix-y-axis-collapse",
        "matrix-positive-scientific-x-translation",
        "matrix3d-all-zero-whitespace",
        "matrix3d-singular-z-axis",
        "matrix3d-zero-area-xy-plane",
        "matrix3d-negative-y-translation",
        "translate-x-positive-viewport-unit",
        "translate-y-negative-viewport-unit-whitespace",
        "translate-positive-y-scientific-pixels",
        "translate3d-negative-large-viewport-unit",
        "individual-translate-negative-x",
        "individual-translate-positive-y-dynamic-viewport",
        "individual-translate-positive-inline-axis-unit",
        "inset-four-value-negative",
        "logical-inset-negative",
        "block-inset-positive-small-viewport-unit",
        "inset-four-value-positive-width-unit",
        "position-and-logical-inset-split-rules",
        "position-and-physical-offset-split-rules",
        "clip-all-nonzero-equal",
        "clip-zero-height-whitespace-syntax",
        "clip-zero-width-equivalent-absolute-units",
        "clip-inverted-width",
    ],
)
def test_matrix_translate_inset_and_clip_concealment_fail_through_public_audit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    rule: str,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    css = (root / "styles.css").read_text(encoding="utf-8")
    (root / "styles.css").write_text(f"{rule}\n{css}", encoding="utf-8")
    receipt = qa.audit_candidate_static(root, mode="v28-design-system-static")
    codes = {item["code"] for item in receipt["findings"]}
    assert "main-landmark-missing" in codes
    assert "h1-count-invalid" in codes


@pytest.mark.parametrize(
    "rule",
    [
        "main#main{transform:matrix(1,0,0,1,0,0)}",
        "main#main{transform:matrix(0, 1, -1, 0, 10, 20)}",
        ("main#main{transform:matrix3d(1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1)}"),
        "main#main{transform:translateX(999px)}",
        "main#main{transform:translateY(-99vh)}",
        "main#main{translate:12px -20%}",
        "main#main{position:absolute;inset:10px auto auto 10px}",
        "main#main{position:fixed;inset-inline:5rem auto}",
        "main#main{clip:rect(0,100px,100px,0)}",
        "main#main{clip:rect(-2rem 10rem 2rem -1rem)}",
        "main#main{clip:rect(auto,auto,auto,auto)}",
    ],
    ids=[
        "matrix-identity",
        "matrix-rotation-nonzero-determinant",
        "matrix3d-identity",
        "translate-x-below-pixel-bound",
        "translate-y-below-viewport-bound",
        "individual-translate-small",
        "inset-small",
        "logical-inset-small",
        "clip-positive-area-comma",
        "clip-positive-area-whitespace",
        "clip-auto",
    ],
)
def test_nonconcealing_geometry_controls_pass_through_public_audit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    rule: str,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    css = (root / "styles.css").read_text(encoding="utf-8")
    (root / "styles.css").write_text(f"{rule}\n{css}", encoding="utf-8")
    receipt = qa.audit_candidate_static(root, mode="v28-design-system-static")
    assert receipt["decision"]["status"] == "pass"
    assert receipt["findings"] == []


@pytest.mark.parametrize(
    "rule",
    [
        "main#main{transform:translateX(600px) translateX(600px)}",
        "main#main{transform:translateX(-60vw) translateX(-60vw)}",
        ("main#main{transform:matrix(1,0,0,1,600,0) matrix(1,0,0,1,600,0)}"),
        ("main#main{transform:matrix(1,0,0,1,600,0) translateX(600px)}"),
        ("main#main{position:absolute;left:600px;transform:translateX(600px)}"),
        "main#main{translate:600px 0;transform:translateX(600px)}",
        "main#main{position:absolute;clip:rect(auto,1px,auto,1px)}",
        "main#main{position:absolute;clip:rect(1px,auto,1px,auto)}",
        "main#main{position:absolute;clip:rect(auto,1px,auto,2px)}",
    ],
    ids=[
        "sealed-two-transform-translations",
        "sealed-two-relative-translations",
        "sealed-two-matrix-translations",
        "sealed-matrix-and-translate",
        "sealed-layout-and-transform",
        "sealed-individual-and-transform",
        "sealed-mixed-auto-zero-width",
        "sealed-mixed-auto-zero-height",
        "sealed-mixed-auto-inverted-width",
    ],
)
def test_sealed_geometry_composition_and_mixed_auto_vectors_fail_public_audit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    rule: str,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    css = (root / "styles.css").read_text(encoding="utf-8")
    (root / "styles.css").write_text(f"{rule}\n{css}", encoding="utf-8")
    receipt = qa.audit_candidate_static(root, mode="v28-design-system-static")
    codes = {item["code"] for item in receipt["findings"]}
    assert "main-landmark-missing" in codes
    assert "h1-count-invalid" in codes


@pytest.mark.parametrize(
    "rule",
    [
        "main#main{transform:scale(2) translateX(600px)}",
        ("main#main{transform:rotate(180deg) translateX(600px) translateX(600px)}"),
        "main#main{left:600px} main#main{transform:translateX(600px)}",
        "main#main{translate:600px 0} main#main{transform:translateX(600px)}",
        "body{transform:translateX(600px)} main#main{transform:translateX(600px)}",
        ("main#main{transform:matrix3d(1,0,0,0, 0,1,0,0, 0,0,0,1, 0,0,1,0)}"),
        ("main#main{transform:matrix3d(1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,-1)}"),
        ("main#main{transform:matrix3d(1e-6,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1e-12)}"),
        "main#main{transform:translateX(60vw) translateX(60vh)}",
        ("main#main{transform:skewX(45deg) translateY(600px) translateY(600px)}"),
        "main#main{transform:rotateY(45deg) translateZ(1600px)}",
        "main#main{position:absolute;clip:rect(auto,10px,0,0)}",
    ],
    ids=[
        "scale-before-translate-amplifies",
        "rotation-maps-cumulative-sign",
        "cross-rule-layout-and-transform",
        "cross-rule-individual-and-transform",
        "ancestor-and-main-transform",
        "generated-matrix3d-zero-w-plane",
        "generated-matrix3d-negative-w-plane",
        "generated-matrix3d-near-zero-w-plane",
        "mixed-relative-units-conservative-sum",
        "skew-maps-cumulative-translation",
        "3d-rotation-maps-z-translation",
        "clip-auto-top-has-zero-semantics",
    ],
)
def test_generalized_composed_geometry_fails_through_public_audit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    rule: str,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    css = (root / "styles.css").read_text(encoding="utf-8")
    (root / "styles.css").write_text(f"{rule}\n{css}", encoding="utf-8")
    receipt = qa.audit_candidate_static(root, mode="v28-design-system-static")
    codes = {item["code"] for item in receipt["findings"]}
    assert "main-landmark-missing" in codes
    assert "h1-count-invalid" in codes


@pytest.mark.parametrize(
    "rule",
    [
        "main#main{transform:translateX(400px) translateX(400px)}",
        "main#main{transform:translateX(600px) translateX(-600px)}",
        ("main#main{transform:matrix(1,0,0,1,600,0) translateX(-600px)}"),
        ("main#main{transform:translateX(600px) rotate(180deg) translateX(600px)}"),
        "main#main{left:600px;transform:translateX(-600px)}",
        "main#main{translate:600px 0;transform:translateX(-600px)}",
        "main#main{transform:translateX(600px)} main#main{transform:translateX(600px)}",
        "main#main{transform:translateX(600px) scale(2)}",
        "main#main{position:absolute;clip:rect(auto,100px,auto,0)}",
        ("main#main{transform:matrix3d(1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1)}"),
        "main#main{transform:perspective(500px) translateZ(10px)}",
        "main#main{transform:translateY(600px) skewX(45deg)}",
        "main#main{transform:translateZ(1600px) rotateY(45deg)}",
    ],
    ids=[
        "cumulative-below-bound",
        "opposite-sign-transform-cancellation",
        "matrix-translate-cancellation",
        "ordered-rotation-cancellation",
        "layout-transform-cancellation",
        "individual-transform-cancellation",
        "same-property-cross-rule-cascade-alternatives",
        "translate-before-scale-not-amplified",
        "positive-width-mixed-auto-clip",
        "generated-matrix3d-identity",
        "generated-valid-perspective",
        "translate-before-skew-not-amplified",
        "translate-z-before-rotation-not-remapped",
    ],
)
def test_composed_geometry_nonconcealing_controls_pass_public_audit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    rule: str,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    css = (root / "styles.css").read_text(encoding="utf-8")
    (root / "styles.css").write_text(f"{rule}\n{css}", encoding="utf-8")
    receipt = qa.audit_candidate_static(root, mode="v28-design-system-static")
    assert receipt["decision"]["status"] == "pass"
    assert receipt["findings"] == []


def _wrap_only_main(root: Path, opening: str, closing: str = "</div>") -> None:
    html = (root / "index.html").read_text(encoding="utf-8")
    html = html.replace('<main id="main">', f'{opening}<main id="main">', 1)
    html = html.replace("</main>", f"</main>{closing}", 1)
    (root / "index.html").write_text(html, encoding="utf-8")


@pytest.mark.parametrize(
    "rule",
    [
        ".shell{transform:translateX(600px) translateX(600px)}",
        ".shell{transform:translateX(1200px)}",
        ".shell{position:absolute;left:600px;transform:translateX(600px)}",
        ".shell{translate:600px 0;transform:translateX(600px)}",
        ".shell{opacity:0}",
        ".shell{display:none}",
        ".shell{visibility:hidden}",
        ".shell{content-visibility:hidden}",
        ".shell{clip-path:inset(50%)}",
        ".shell{position:absolute;clip:rect(1px,1px,1px,1px)}",
    ],
    ids=[
        "wrapper-two-transform-translations",
        "wrapper-direct-transform-translation",
        "wrapper-layout-plus-transform",
        "wrapper-individual-plus-transform",
        "wrapper-transparent",
        "wrapper-display-none",
        "wrapper-visibility-hidden",
        "wrapper-content-visibility-hidden",
        "wrapper-clip-path",
        "wrapper-legacy-clip",
    ],
)
def test_sealed_wrapper_ancestor_concealment_fails_public_audit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    rule: str,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    _wrap_only_main(root, '<div class="shell">')
    css = (root / "styles.css").read_text(encoding="utf-8")
    (root / "styles.css").write_text(f"{rule}\n{css}", encoding="utf-8")
    receipt = qa.audit_candidate_static(root, mode="v28-design-system-static")
    codes = {item["code"] for item in receipt["findings"]}
    assert {"main-landmark-missing", "h1-count-invalid", "fragment-target-missing"} <= codes


@pytest.mark.parametrize(
    ("rule", "wrapper", "extra"),
    [
        (".shell{transform:translateX(999px)}", '<div class="shell">', ""),
        (".not-shell{transform:translateX(1200px)}", '<div class="shell">', ""),
        (
            ".shell,.not-shell{transform:translateX(600px)}",
            '<div class="shell">',
            "",
        ),
        (".shell::before{display:none}", '<div class="shell">', ""),
        (".shell::after{transform:translateX(1200px)}", '<div class="shell">', ""),
        (
            ".shell{transform:translateX(1200px)}",
            '<div class="visible-shell">',
            '<div class="shell"><p>Noncritical evidence note.</p></div>',
        ),
    ],
    ids=[
        "wrapper-below-bound",
        "nonmatching-wrapper-selector",
        "matching-plus-nonmatching-selector-alternative",
        "wrapper-before-pseudo",
        "wrapper-after-pseudo",
        "noncritical-wrapper-without-critical-descendant",
    ],
)
def test_wrapper_nonconcealment_controls_pass_public_audit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    rule: str,
    wrapper: str,
    extra: str,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    _wrap_only_main(root, wrapper)
    if extra:
        html = (root / "index.html").read_text(encoding="utf-8")
        (root / "index.html").write_text(
            html.replace('<div class="visible-shell">', extra + '<div class="visible-shell">', 1),
            encoding="utf-8",
        )
    css = (root / "styles.css").read_text(encoding="utf-8")
    (root / "styles.css").write_text(f"{rule}\n{css}", encoding="utf-8")
    receipt = qa.audit_candidate_static(root, mode="v28-design-system-static")
    assert receipt["decision"]["status"] == "pass"
    assert receipt["findings"] == []


@pytest.mark.parametrize(
    ("rules", "expected_hidden"),
    [
        (
            ".outer{transform:translateX(600px)}.shell{transform:translateX(600px)}",
            True,
        ),
        (
            ".shell{transform:translateX(600px)}.shell{transform:translateX(600px)}",
            False,
        ),
        (".shell{transform:translateX(600px) translateX(-600px)}", False),
        (
            ".shell{transform:translateX(600px)}main#main{transform:translateX(-600px)}",
            False,
        ),
        (
            ".shell{transform:scale(2)}main#main{transform:translateX(600px)}",
            True,
        ),
        (
            "main#main{scale:2}main#main{transform:translateX(600px)}",
            True,
        ),
    ],
    ids=[
        "two-nested-wrapper-sources-compose",
        "same-wrapper-property-rules-are-alternatives",
        "same-wrapper-signed-cancellation",
        "ancestor-child-signed-cancellation",
        "ancestor-scale-amplifies-child-translation",
        "individual-scale-and-transform-split-rules",
    ],
)
def test_nested_wrapper_and_child_geometry_composition(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    rules: str,
    expected_hidden: bool,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    _wrap_only_main(root, '<div class="outer"><div class="shell">', "</div></div>")
    css = (root / "styles.css").read_text(encoding="utf-8")
    (root / "styles.css").write_text(f"{rules}\n{css}", encoding="utf-8")
    receipt = qa.audit_candidate_static(root, mode="v28-design-system-static")
    codes = {item["code"] for item in receipt["findings"]}
    assert ("main-landmark-missing" in codes) is expected_hidden
    assert ("h1-count-invalid" in codes) is expected_hidden


@pytest.mark.parametrize(
    ("selector", "expected_hidden"),
    [
        (".outer > .shell", True),
        (".other > .shell", False),
        ("body > .shell", False),
    ],
)
def test_wrapper_selector_ancestor_constraints_preserve_child_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    selector: str,
    expected_hidden: bool,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    _wrap_only_main(root, '<div class="outer"><div class="shell">', "</div></div>")
    css = (root / "styles.css").read_text(encoding="utf-8")
    (root / "styles.css").write_text(
        f"{selector}{{display:none}}\n{css}",
        encoding="utf-8",
    )
    receipt = qa.audit_candidate_static(root, mode="v28-design-system-static")
    codes = {item["code"] for item in receipt["findings"]}
    assert ("main-landmark-missing" in codes) is expected_hidden


def test_wrapper_around_only_h1_does_not_remove_main_or_fragment_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    html = (root / "index.html").read_text(encoding="utf-8")
    html = html.replace(
        "<h1>Evidence-led research systems</h1>",
        '<div class="shell"><h1>Evidence-led research systems</h1></div>',
        1,
    )
    (root / "index.html").write_text(html, encoding="utf-8")
    css = (root / "styles.css").read_text(encoding="utf-8")
    (root / "styles.css").write_text(".shell{display:none}\n" + css, encoding="utf-8")
    receipt = qa.audit_candidate_static(root, mode="v28-design-system-static")
    codes = {item["code"] for item in receipt["findings"]}
    assert "h1-count-invalid" in codes
    assert "main-landmark-missing" not in codes
    assert "fragment-target-missing" not in codes


@pytest.mark.parametrize(
    ("style", "expected_hidden"),
    [
        ("scale:2;transform:translateX(600px)", True),
        ("transform:translateX(600px);scale:2", True),
        ("scale:0;transform:translateX(1px)", True),
        ("scale:2", False),
        ("scale:2;transform:translateX(499px)", False),
        ("scale:.5;transform:translateX(1200px)", False),
        ("scale:2;transform:scale(.5) translateX(600px)", False),
        ("scale:2;transform:translateX(600px) scale(.5)", True),
        ("translate:600px;scale:2;transform:translateX(-300px)", False),
        (
            "translate:600px;rotate:180deg;scale:2;transform:translateX(-300px)",
            True,
        ),
    ],
    ids=[
        "individual-scale-amplifies-transform",
        "declaration-order-does-not-change-individual-order",
        "individual-zero-scale",
        "individual-scale-alone",
        "individual-scale-below-bound",
        "individual-downscale-bounds-transform",
        "transform-scale-cancels-individual-scale-before-translation",
        "transform-translation-precedes-transform-scale",
        "individual-translate-scale-transform-cancellation",
        "individual-translate-rotate-scale-transform-order",
    ],
)
def test_individual_transform_properties_compose_in_css_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    style: str,
    expected_hidden: bool,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    css = (root / "styles.css").read_text(encoding="utf-8")
    (root / "styles.css").write_text(
        f"main#main{{{style}}}\n{css}",
        encoding="utf-8",
    )
    receipt = qa.audit_candidate_static(root, mode="v28-design-system-static")
    codes = {item["code"] for item in receipt["findings"]}
    assert ("main-landmark-missing" in codes) is expected_hidden
    assert ("h1-count-invalid" in codes) is expected_hidden


@pytest.mark.parametrize(
    ("inline_surface", "style"),
    [
        ("attribute", "transform:translateX(1200px)"),
        ("attribute", "scale:2;transform:translateX(600px)"),
        ("style-block", "transform:translateX(1200px)"),
    ],
)
def test_inline_wrapper_geometry_uses_the_rendered_ancestor_tree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    inline_surface: str,
    style: str,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    if inline_surface == "attribute":
        _wrap_only_main(root, f'<div class="shell" style="{style}">')
    else:
        _wrap_only_main(root, '<div class="shell">')
        html = (root / "index.html").read_text(encoding="utf-8")
        (root / "index.html").write_text(
            html.replace("</head>", f"<style>.shell{{{style}}}</style></head>", 1),
            encoding="utf-8",
        )
    receipt = qa.audit_candidate_static(root, mode="v28-design-system-static")
    codes = {item["code"] for item in receipt["findings"]}
    assert {"main-landmark-missing", "h1-count-invalid", "fragment-target-missing"} <= codes


@pytest.mark.parametrize(
    "decoy",
    [
        '<template><div class="shell"><main><h1>Decoy</h1></main></div></template>',
        '<div inert><div class="shell"><main><h1>Decoy</h1></main></div></div>',
        '<svg><g class="shell"><main><h1>Decoy</h1></main></g></svg>',
    ],
    ids=["template", "inert", "nonrendered-svg"],
)
def test_nonrendered_wrapper_branches_do_not_hide_visible_critical_semantics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    decoy: str,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    html = (root / "index.html").read_text(encoding="utf-8")
    (root / "index.html").write_text(
        html.replace('<main id="main">', decoy + '<main id="main">', 1),
        encoding="utf-8",
    )
    css = (root / "styles.css").read_text(encoding="utf-8")
    (root / "styles.css").write_text(".shell{display:none}\n" + css, encoding="utf-8")
    receipt = qa.audit_candidate_static(root, mode="v28-design-system-static")
    assert receipt["decision"]["status"] == "pass"
    assert receipt["findings"] == []


@pytest.mark.parametrize(
    ("style", "expected"),
    [
        ("display:var(--conceal,none)", True),
        ("opacity:calc(0 * 1%)", True),
        ("filter:opacity(0)", True),
        ("transform:scale(0)", True),
        ("transform:matrix(1,2,2,4,0,0)", True),
        ("translate:-9999px 0", True),
        ("clip-path:inset(50%)", True),
        ("clip:rect(1px,1px,1px,1px)", True),
        ("position:absolute;left:-9999px", True),
        ("position:absolute;inset-inline-start:-9999px", True),
        ("transform:translateX(600px) translateX(600px)", True),
        ("position:absolute;left:600px;transform:translateX(600px)", True),
        ("translate:600px 0;transform:translateX(600px)", True),
        ("position:absolute;clip:rect(auto,1px,auto,1px)", True),
        ("transform:matrix(1,0,0,1,0,0)", False),
        ("transform:translateX(600px) translateX(-600px)", False),
        ("translate:10px -5%", False),
        ("clip:rect(0,100px,100px,0)", False),
        ("opacity:1", False),
    ],
)
def test_inline_style_concealment_uses_the_same_declaration_policy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    style: str,
    expected: bool,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    html = (root / "index.html").read_text(encoding="utf-8")
    (root / "index.html").write_text(
        html.replace('<main id="main">', f'<main id="main" style="{style}">'),
        encoding="utf-8",
    )
    receipt = qa.audit_candidate_static(root, mode="v28-design-system-static")
    codes = {item["code"] for item in receipt["findings"]}
    assert ("main-landmark-missing" in codes) is expected


def test_pseudo_element_concealment_does_not_hide_its_originating_element(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    css = (root / "styles.css").read_text(encoding="utf-8")
    (root / "styles.css").write_text(
        "main::before{display:none}\n" + css,
        encoding="utf-8",
    )
    receipt = qa.audit_candidate_static(root, mode="v28-design-system-static")
    assert receipt["decision"]["status"] == "pass"


@pytest.mark.parametrize(
    ("main_class", "expected_hidden"),
    [
        ("institutional-hero", False),
        ("home-hero", True),
    ],
)
def test_css_ancestor_constraints_are_matched_against_the_candidate_tree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    main_class: str,
    expected_hidden: bool,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    css = (root / "styles.css").read_text(encoding="utf-8")
    (root / "styles.css").write_text(
        "body .home-hero h1{clip-path:inset(50%)}\n" + css,
        encoding="utf-8",
    )
    html = (root / "index.html").read_text(encoding="utf-8")
    (root / "index.html").write_text(
        html.replace('<main id="main">', f'<main id="main" class="{main_class}">'),
        encoding="utf-8",
    )
    receipt = qa.audit_candidate_static(root, mode="v28-design-system-static")
    codes = {item["code"] for item in receipt["findings"]}
    assert ("h1-count-invalid" in codes) is expected_hidden


@pytest.mark.parametrize(
    ("stylesheet", "expected_code"),
    [
        ("main#main{display:none", "candidate-css-structure-invalid"),
        (
            ("@layer audit{" * 300) + "main#main{display:none}" + ("}" * 300),
            "candidate-css-complexity-limit",
        ),
    ],
)
def test_css_structure_and_depth_fail_through_the_canonical_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stylesheet: str,
    expected_code: str,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    (root / "styles.css").write_text(stylesheet, encoding="utf-8")
    receipt = qa.audit_candidate_static(root, mode="v28-design-system-static")
    assert expected_code in {item["code"] for item in receipt["findings"]}


_EFFECTIVE_REDUCED_MOTION_GATE = (
    'if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) { console.info("gate"); }'
)


@pytest.mark.parametrize(
    ("source", "expected_code"),
    [
        (
            f"if (0 && 1) {{ {_EFFECTIVE_REDUCED_MOTION_GATE} }}",
            "reduced-motion-javascript-proof-unavailable",
        ),
        (
            f"if (1 - 1) {{ {_EFFECTIVE_REDUCED_MOTION_GATE} }}",
            "reduced-motion-javascript-proof-unavailable",
        ),
        (
            f"if (Boolean(false)) {{ {_EFFECTIVE_REDUCED_MOTION_GATE} }}",
            "reduced-motion-javascript-proof-unavailable",
        ),
        (
            f"if ('') {{ {_EFFECTIVE_REDUCED_MOTION_GATE} }}",
            "reduced-motion-javascript-proof-unavailable",
        ),
        (
            f"if (true) {{ console.info('live'); }} else {{ {_EFFECTIVE_REDUCED_MOTION_GATE} }}",
            "reduced-motion-javascript-proof-unavailable",
        ),
        (
            f"false ? (() => {{ {_EFFECTIVE_REDUCED_MOTION_GATE} }})() : 0;",
            "reduced-motion-javascript-proof-unavailable",
        ),
        (
            f"for (; false;) {{ {_EFFECTIVE_REDUCED_MOTION_GATE} }}",
            "reduced-motion-javascript-proof-unavailable",
        ),
        (
            f"function never() {{ {_EFFECTIVE_REDUCED_MOTION_GATE} }}",
            "reduced-motion-javascript-proof-unavailable",
        ),
        (
            f"(function () {{ return; {_EFFECTIVE_REDUCED_MOTION_GATE} }})();",
            "reduced-motion-javascript-proof-unavailable",
        ),
        (
            f"function outer(){{ function hidden(){{ {_EFFECTIVE_REDUCED_MOTION_GATE} }} }} hidden();",
            "reduced-motion-javascript-proof-unavailable",
        ),
        (
            f"function gatefn(){{ {_EFFECTIVE_REDUCED_MOTION_GATE} }} const never=()=>{{gatefn();}};",
            "reduced-motion-javascript-proof-unavailable",
        ),
        (
            f"function gatefn(){{ {_EFFECTIVE_REDUCED_MOTION_GATE} }} const x={{never(){{gatefn();}}}};",
            "reduced-motion-javascript-proof-unavailable",
        ),
        (
            f"function f(){{ if(true){{return;}} {_EFFECTIVE_REDUCED_MOTION_GATE} }} f();",
            "reduced-motion-javascript-proof-unavailable",
        ),
        (
            f"function gatefn(){{ {_EFFECTIVE_REDUCED_MOTION_GATE} }} false && gatefn();",
            "reduced-motion-javascript-proof-unavailable",
        ),
        (
            f"false && (function(){{{_EFFECTIVE_REDUCED_MOTION_GATE}}})();",
            "reduced-motion-javascript-proof-unavailable",
        ),
        (
            f"function f(){{return;(function(){{{_EFFECTIVE_REDUCED_MOTION_GATE}}})();}} f();",
            "reduced-motion-javascript-proof-unavailable",
        ),
        (
            f"class X {{ never(){{{_EFFECTIVE_REDUCED_MOTION_GATE}}} }}",
            "reduced-motion-javascript-proof-unavailable",
        ),
        (
            f"const x={{never(){{{_EFFECTIVE_REDUCED_MOTION_GATE}}}}};",
            "reduced-motion-javascript-proof-unavailable",
        ),
        (
            f"function* never(){{{_EFFECTIVE_REDUCED_MOTION_GATE}}}",
            "reduced-motion-javascript-proof-unavailable",
        ),
        (
            f"async function f(){{await new Promise(()=>{{}}); {_EFFECTIVE_REDUCED_MOTION_GATE}}} f();",
            "reduced-motion-javascript-proof-unavailable",
        ),
        (
            f"function gatefn(){{{_EFFECTIVE_REDUCED_MOTION_GATE}}} try{{}}catch(e){{gatefn();}}",
            "reduced-motion-javascript-proof-unavailable",
        ),
        (
            'const r=/if (matchMedia("(prefers-reduced-motion: reduce)").matches) return/;',
            "reduced-motion-javascript-gate-missing",
        ),
        (
            f"throw new Error(); {_EFFECTIVE_REDUCED_MOTION_GATE}",
            "reduced-motion-javascript-proof-unavailable",
        ),
        (
            f"if(true){{throw new Error();}} {_EFFECTIVE_REDUCED_MOTION_GATE}",
            "reduced-motion-javascript-proof-unavailable",
        ),
        (
            f"while(true){{}} {_EFFECTIVE_REDUCED_MOTION_GATE}",
            "reduced-motion-javascript-proof-unavailable",
        ),
        (
            f"for(;;){{}} {_EFFECTIVE_REDUCED_MOTION_GATE}",
            "reduced-motion-javascript-proof-unavailable",
        ),
        (
            f"do{{}}while(true); {_EFFECTIVE_REDUCED_MOTION_GATE}",
            "reduced-motion-javascript-proof-unavailable",
        ),
        (
            "const n=1 / /if (window.matchMedia("
            '"(prefers-reduced-motion: reduce)").matches) return/.test("x");',
            "reduced-motion-javascript-proof-unavailable",
        ),
    ],
)
def test_reduced_motion_successor_proof_rejects_dead_or_ambiguous_sources(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source: str,
    expected_code: str,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    (root / "script.js").write_text(source, encoding="utf-8")
    receipt = qa.audit_candidate_static(root, mode="v28-design-system-static")
    codes = {item["code"] for item in receipt["findings"]}
    assert expected_code in codes


@pytest.mark.parametrize(
    "prefix",
    [
        "",
        " \n;\n",
        "/* reviewed */\n",
        "// reviewed\n",
        "'use strict';\n",
        '"use strict";\n/* reviewed */\n',
    ],
)
def test_reduced_motion_successor_proof_accepts_only_first_executable_gate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    prefix: str,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    (root / "script.js").write_text(
        prefix + _EFFECTIVE_REDUCED_MOTION_GATE,
        encoding="utf-8",
    )
    receipt = qa.audit_candidate_static(root, mode="v28-design-system-static")
    assert receipt["decision"]["status"] == "pass"


def test_unloaded_javascript_cannot_supply_the_reduced_motion_proof(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    (root / "script.js").write_text('"use strict";\n', encoding="utf-8")
    (root / "extra.js").write_text(
        _EFFECTIVE_REDUCED_MOTION_GATE,
        encoding="utf-8",
    )
    receipt = qa.audit_candidate_static(root, mode="v28-design-system-static")
    assert "reduced-motion-javascript-gate-missing" in {item["code"] for item in receipt["findings"]}


@pytest.mark.parametrize(
    ("source", "expected_code"),
    [
        (
            'if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;',
            "reduced-motion-javascript-gate-missing",
        ),
        (
            'if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {"only";}',
            "reduced-motion-javascript-gate-missing",
        ),
        (
            f"(function(){{{_EFFECTIVE_REDUCED_MOTION_GATE}}})();",
            "reduced-motion-javascript-proof-unavailable",
        ),
    ],
)
def test_reduced_motion_gate_missing_and_proof_unavailable_are_distinct(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source: str,
    expected_code: str,
) -> None:
    repo, root = _make_repo(tmp_path)
    _bind_repo(monkeypatch, repo)
    (root / "script.js").write_text(source, encoding="utf-8")
    receipt = qa.audit_candidate_static(root, mode="v28-design-system-static")
    assert expected_code in {item["code"] for item in receipt["findings"]}


def test_python_implementation_has_no_process_network_or_filesystem_writer() -> None:
    source = Path(qa.__file__).read_text(encoding="utf-8")
    for forbidden in (
        r"^\s*(?:from|import)\s+(?:subprocess|socket|requests|http|ftplib|urllib\.request)\b",
        r"\bsubprocess\.",
        r"\b(?:urlopen|requests\.(?:get|post|put|patch|delete)|socket\.)",
        r"\b(?:write_text|write_bytes|write_file|unlink|rename|mkdir|rmdir)\s*\(",
        r"\bopen\s*\([^,\n]+,\s*[\"'][^\"']*[wax+]",
    ):
        assert re.search(forbidden, source, re.MULTILINE | re.IGNORECASE) is None
