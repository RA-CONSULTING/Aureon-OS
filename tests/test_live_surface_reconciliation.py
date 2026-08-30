"""Focused safety guarantees for read-only public live-surface reconciliation."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from email.message import Message
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError

import pytest

from aureon.operator.live_surface_reconciliation import (
    LiveSurfaceReconciliationError,
    reconcile_live_surface,
    write_live_surface_reconciliation,
)


class FakeResponse:
    """Small urllib-compatible response used to keep the contract fully offline."""

    def __init__(
        self,
        body: bytes,
        url: str,
        *,
        status: int = 200,
        content_type: str = "text/html; charset=utf-8",
    ) -> None:
        self._body = body
        self._url = url
        self.status = status
        self.headers = {"Content-Type": content_type}
        self.closed = False

    def geturl(self) -> str:
        return self._url

    def read(self, amount: int = -1) -> bytes:
        return self._body if amount < 0 else self._body[:amount]

    def close(self) -> None:
        self.closed = True


def _html(*, title: str = "Aureon", description: str = "Research-led systems", body: str = "Evidence") -> bytes:
    return f"""<!doctype html>
<html lang="en-GB">
  <head>
    <meta charset="utf-8">
    <title>{title}</title>
    <meta name="description" content="{description}">
    <link rel="canonical" href="https://example.test/">
  </head>
  <body><main><h1>{body}</h1><p>Public record.</p></main></body>
</html>
""".encode()


def _repo(tmp_path: Path, content: bytes | None = None) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    site = repo / "website"
    site.mkdir(parents=True)
    (repo / "pyproject.toml").write_text("[project]\nname = 'fixture'\n", encoding="utf-8")
    (site / "index.html").write_bytes(content or _html())
    return repo, site


def _opener(responses: dict[str, FakeResponse | Exception]):
    def open_response(request: Any, timeout: float) -> FakeResponse:
        assert timeout == 15.0
        response = responses[request.full_url]
        if isinstance(response, Exception):
            raise response
        return response

    return open_response


def _reconcile(repo: Path, site: Path, opener) -> dict:
    return reconcile_live_surface(
        repo_root=repo,
        site_root=site,
        base_url="https://example.test/",
        routes=["index.html"],
        now=datetime(2026, 7, 28, 12, 0, tzinfo=UTC),
        opener=opener,
    )


def _redirect(url: str, target: str) -> HTTPError:
    headers = Message()
    headers["Location"] = target
    return HTTPError(url, 302, "Found", headers, None)


def test_semantic_alignment_is_read_only_and_never_release_authority(tmp_path: Path) -> None:
    repo, site = _repo(tmp_path)
    local_before = (site / "index.html").read_bytes()
    live = b"""<!doctype html><html lang='en-GB'><head>
<title>Aureon</title><meta content='Research-led systems' name='description'>
<link href='https://example.test/' rel='canonical'></head>
<body> <main> <h1>Evidence</h1> <p>Public record.</p> </main> </body></html>"""

    receipt = _reconcile(
        repo,
        site,
        _opener({"https://example.test/": FakeResponse(live, "https://example.test/")}),
    )

    assert receipt["state"] == "live-surface-semantically-aligned"
    assert receipt["passed"] is True
    assert receipt["release_eligible"] is False
    assert receipt["package_authority"] == "none"
    assert receipt["deployment_authority"] == "none"
    assert receipt["routes"][0]["alignment"] == "semantic-aligned"
    assert receipt["routes"][0]["difference_signals"] == []
    assert (site / "index.html").read_bytes() == local_before


def test_detects_material_public_presentation_drift_without_mutation(tmp_path: Path) -> None:
    repo, site = _repo(tmp_path)
    local_before = (site / "index.html").read_bytes()
    live = _html(title="Different production proposition", body="Different live record")

    receipt = _reconcile(
        repo,
        site,
        _opener({"https://example.test/": FakeResponse(live, "https://example.test/")}),
    )

    row = receipt["routes"][0]
    assert receipt["state"] == "live-drift-detected"
    assert receipt["passed"] is False
    assert row["alignment"] == "diverged"
    assert {"title", "presentation_text_sha256"}.issubset(row["difference_signals"])
    assert "owner-scoped reconciliation" in receipt["next_gate"]
    assert (site / "index.html").read_bytes() == local_before


def test_cross_origin_redirect_is_incomplete_and_cannot_authorise_release(tmp_path: Path) -> None:
    repo, site = _repo(tmp_path)

    receipt = _reconcile(
        repo,
        site,
        _opener({"https://example.test/": _redirect("https://example.test/", "https://other.example/")}),
    )

    row = receipt["routes"][0]
    assert receipt["state"] == "live-observation-incomplete"
    assert receipt["passed"] is False
    assert row["alignment"] == "unavailable"
    assert "redirect target leaves" in row["error"]
    assert receipt["release_eligible"] is False
    assert receipt["deployment_authority"] == "none"


def test_network_failure_is_preserved_as_an_incomplete_observation(tmp_path: Path) -> None:
    repo, site = _repo(tmp_path)

    receipt = _reconcile(
        repo,
        site,
        _opener({"https://example.test/": URLError("offline fixture")}),
    )

    assert receipt["state"] == "live-observation-incomplete"
    assert receipt["summary"]["unavailable"] == 1
    assert receipt["routes"][0]["error"] == "URLError: offline fixture"


def test_non_success_html_cannot_be_recorded_as_aligned(tmp_path: Path) -> None:
    repo, site = _repo(tmp_path)

    receipt = _reconcile(
        repo,
        site,
        _opener({"https://example.test/": FakeResponse(_html(), "https://example.test/", status=404)}),
    )

    assert receipt["state"] == "live-observation-incomplete"
    assert receipt["passed"] is False
    assert receipt["routes"][0]["alignment"] == "unavailable"
    assert "non-success HTTP status: 404" in receipt["routes"][0]["error"]


def test_same_origin_redirect_is_explicitly_recorded_before_the_final_fetch(tmp_path: Path) -> None:
    repo, site = _repo(tmp_path)
    calls: list[str] = []

    def opener(request: Any, timeout: float) -> FakeResponse:
        assert timeout == 15.0
        calls.append(request.full_url)
        if request.full_url == "https://example.test/":
            raise _redirect(request.full_url, "/resolved/")
        return FakeResponse(_html(), request.full_url)

    receipt = _reconcile(repo, site, opener)

    row = receipt["routes"][0]
    assert calls == ["https://example.test/", "https://example.test/resolved/"]
    assert row["alignment"] == "exact-source"
    assert row["redirect_chain"] == [
        {
            "from": "https://example.test/",
            "to": "https://example.test/resolved/",
            "http_status": 302,
        }
    ]


def test_relative_and_absolute_canonicals_are_semantically_equivalent(tmp_path: Path) -> None:
    local = _html().replace(b'href="https://example.test/"', b'href="/"')
    repo, site = _repo(tmp_path, local)

    receipt = _reconcile(
        repo,
        site,
        _opener({"https://example.test/": FakeResponse(_html(), "https://example.test/")}),
    )

    assert receipt["state"] == "live-surface-semantically-aligned"
    assert receipt["routes"][0]["alignment"] == "semantic-aligned"
    assert "canonical" not in receipt["routes"][0]["difference_signals"]


def test_cta_target_change_is_material_presentation_drift(tmp_path: Path) -> None:
    local = _html().replace(
        b"<p>Public record.</p>",
        b'<a href="/contact/" aria-label="Contact Aureon">Public record.</a>',
    )
    live = local.replace(b'href="/contact/"', b'href="/different-route/"')
    repo, site = _repo(tmp_path, local)

    receipt = _reconcile(
        repo,
        site,
        _opener({"https://example.test/": FakeResponse(live, "https://example.test/")}),
    )

    assert receipt["state"] == "live-drift-detected"
    assert receipt["routes"][0]["difference_signals"] == ["interaction_surface_sha256"]


def test_local_snapshot_remains_coherent_if_source_changes_during_public_fetch(tmp_path: Path) -> None:
    original = _html()
    repo, site = _repo(tmp_path, original)

    def opener(request: Any, timeout: float) -> FakeResponse:
        (site / "index.html").write_bytes(_html(body="Changed after snapshot"))
        return FakeResponse(original, request.full_url)

    receipt = _reconcile(repo, site, opener)
    original_sha = hashlib.sha256(original).hexdigest().upper()
    expected_tree_sha = hashlib.sha256(
        b"index.html\0" + original_sha.encode("ascii") + b"\n"
    ).hexdigest().upper()

    assert receipt["routes"][0]["local"]["sha256"] == original_sha
    assert receipt["canonical"]["selected_tree_sha256"] == expected_tree_sha
    assert (site / "index.html").read_bytes() != original


def test_reconciliation_rejects_unsafe_routes_and_external_overrides(tmp_path: Path) -> None:
    repo, site = _repo(tmp_path)

    with pytest.raises(LiveSurfaceReconciliationError, match="Unsafe live-surface route"):
        reconcile_live_surface(
            repo_root=repo,
            site_root=site,
            base_url="https://example.test/",
            routes=["../private.html"],
        )

    with pytest.raises(LiveSurfaceReconciliationError, match="configured HTTPS origin"):
        reconcile_live_surface(
            repo_root=repo,
            site_root=site,
            base_url="https://example.test/",
            routes=["index.html"],
            canonical_overrides={"index.html": "https://other.example/"},
        )

    with pytest.raises(LiveSurfaceReconciliationError, match="invalid HTTPS port"):
        reconcile_live_surface(
            repo_root=repo,
            site_root=site,
            base_url="https://example.test:99999/",
            routes=["index.html"],
        )


def test_receipts_are_append_only_and_stay_under_operator_artifacts(tmp_path: Path) -> None:
    repo, site = _repo(tmp_path)
    receipt = _reconcile(
        repo,
        site,
        _opener({"https://example.test/": FakeResponse(_html(body="Different record"), "https://example.test/")}),
    )
    target = repo / "artifacts" / "website-operator" / "reconciliation.json"

    written = write_live_surface_reconciliation(receipt, target, repo_root=repo)

    assert written == target
    assert json.loads(target.read_text(encoding="utf-8")) == receipt
    with pytest.raises(LiveSurfaceReconciliationError, match="Refusing to overwrite"):
        write_live_surface_reconciliation(receipt, target, repo_root=repo)
    with pytest.raises(LiveSurfaceReconciliationError, match="must remain below"):
        write_live_surface_reconciliation(receipt, repo / "outside.json", repo_root=repo)
    with pytest.raises(LiveSurfaceReconciliationError, match="missing required fields"):
        write_live_surface_reconciliation(
            {"schema": "aureon.live-surface-reconciliation.v1", "state": "live-drift-detected"},
            repo / "artifacts" / "website-operator" / "forged.json",
            repo_root=repo,
        )
