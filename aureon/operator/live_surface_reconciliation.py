"""Read-only reconciliation between Aureon's canonical source and public website.

The WebsiteOperator's package-bound live read-back proves an explicit release
*after* deployment.  This module supplies an earlier sensing control: it
observes the configured public HTTPS routes, fingerprints their public
presentation, and compares that evidence with the current canonical static
source.  It never accesses hosting credentials, a backup account, a package,
or the canonical website tree for mutation.

A detected difference is not an automatic error in production.  It is a
truthful signal that an owner must reconcile before treating the local tree as
an adequate representation of the live company record or scoping a successor
candidate.  A matching presentation is similarly only an observation; neither
outcome can authorise promotion, packaging, backup, or deployment.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

RECONCILIATION_SCHEMA = "aureon.live-surface-reconciliation.v1"
MAX_RESPONSE_BYTES = 5 * 1024 * 1024
DEFAULT_TIMEOUT_SECONDS = 15.0
MAX_REDIRECTS = 5
ROUTE_MAPPING_ALGORITHM = "index.html -> /; */index.html -> */; other HTML files -> exact path"

AUTHORITY = {
    "scope": "read-only canonical-source to public-HTTPS presentation reconciliation",
    "canonical_website_mutation": "never by this reconciliation or a design agent",
    "credential_access": "none",
    "backup_authority": "none",
    "candidate_promotion_authority": "none",
    "release_eligible": False,
    "package_authority": "none",
    "deployment_authority": "none",
    "release_authority": "WebsiteOperator owner gate only",
}

_WHITESPACE = re.compile(r"\s+")
_SHA256 = re.compile(r"^[A-F0-9]{64}$")
_ROUTE_ALIGNMENTS = {"exact-source", "semantic-aligned", "diverged", "unavailable"}
_RECONCILIATION_STATES = {
    "live-surface-semantically-aligned",
    "live-drift-detected",
    "live-observation-incomplete",
}


class LiveSurfaceReconciliationError(ValueError):
    """A live-surface observation cannot be carried out safely."""


class _PresentationParser(HTMLParser):
    """Extract only stable, public presentation fields from one HTML document."""

    _IGNORED_TAGS = {"script", "style", "template", "noscript"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._ignored_depth = 0
        self._in_title = False
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self.interaction_parts: list[tuple[str, tuple[str, ...]]] = []
        self.description = ""
        self.canonical = ""

    @staticmethod
    def _attributes(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
        return {str(name).lower(): str(value or "") for name, value in attrs}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attributes = self._attributes(attrs)
        if tag in self._IGNORED_TAGS:
            self._ignored_depth += 1
            return
        if tag == "title":
            self._in_title = True
        elif tag == "meta" and attributes.get("name", "").strip().lower() == "description":
            self.description = _normalise_text(attributes.get("content", ""))
        elif tag == "link":
            rel_tokens = {token.lower() for token in attributes.get("rel", "").split()}
            if "canonical" in rel_tokens:
                self.canonical = attributes.get("href", "").strip()
        self._record_interaction(tag, attributes)

    def _record_interaction(self, tag: str, attributes: Mapping[str, str]) -> None:
        """Capture bounded, public action and accessibility semantics only.

        This intentionally avoids class names, generated IDs and layout details,
        but it catches changes to navigation targets, CTA labels, form actions,
        image alternatives and other visitor-facing interaction contracts.
        """

        if tag == "a":
            self.interaction_parts.append(
                (
                    "a",
                    tuple(
                        attributes.get(name, "") for name in ("href", "aria-label", "title", "target", "role")
                    ),
                )
            )
        elif tag in {"button", "input", "select", "textarea", "form"}:
            self.interaction_parts.append(
                (
                    tag,
                    tuple(
                        attributes.get(name, "")
                        for name in ("action", "type", "name", "aria-label", "title", "role")
                    ),
                )
            )
        elif tag in {"img", "source"}:
            self.interaction_parts.append(
                (
                    tag,
                    tuple(
                        attributes.get(name, "")
                        for name in ("src", "srcset", "alt", "aria-label", "title", "role")
                    ),
                )
            )

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self._IGNORED_TAGS:
            self._ignored_depth = max(0, self._ignored_depth - 1)
            return
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        clean = _normalise_text(data)
        if not clean:
            return
        if self._in_title:
            self.title_parts.append(clean)
        self.text_parts.append(clean)

    def presentation_text(self) -> str:
        return _normalise_text(" ".join(self.text_parts))


def _normalise_text(value: object) -> str:
    return _WHITESPACE.sub(" ", str(value or "")).strip()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            block = stream.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest().upper()


def _utc_iso(value: datetime | None = None) -> str:
    return (value or datetime.now(UTC)).astimezone(UTC).isoformat().replace("+00:00", "Z")


def _find_repo_root(start: Path | None = None) -> Path:
    candidate = (start or Path.cwd()).resolve()
    for root in (candidate, *candidate.parents):
        if (root / "pyproject.toml").is_file() and (root / "website").is_dir():
            return root
    raise LiveSurfaceReconciliationError(
        "Could not locate an Aureon repository with pyproject.toml and website/."
    )


def _safe_relative_html_path(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LiveSurfaceReconciliationError("A configured live-surface route is empty.")
    normalised = unquote(value).replace("\\", "/").lstrip("/")
    path = Path(normalised)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise LiveSurfaceReconciliationError(f"Unsafe live-surface route: {value}")
    if path.suffix.lower() != ".html":
        raise LiveSurfaceReconciliationError(f"Live-surface routes must name local HTML files: {value}")
    return path.as_posix()


def _safe_path_under(root: Path, relative: str, *, label: str) -> Path:
    path = (root / relative).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise LiveSurfaceReconciliationError(f"{label} escapes its allowed root: {relative}") from exc
    return path


def _origin(value: str) -> tuple[str, str, int]:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise LiveSurfaceReconciliationError(
            "Live reconciliation requires a credential-free absolute HTTPS URL."
        )
    try:
        port = parsed.port
    except ValueError as exc:
        raise LiveSurfaceReconciliationError(
            "Live reconciliation URL contains an invalid HTTPS port."
        ) from exc
    return parsed.scheme.lower(), parsed.hostname.lower(), port or 443


def _public_url(base_url: str, local_path: str, overrides: Mapping[str, object]) -> str:
    base_origin = _origin(base_url)
    override = overrides.get(local_path)
    if override is not None:
        if not isinstance(override, str) or not override.strip():
            raise LiveSurfaceReconciliationError(
                f"Live-surface override for {local_path} must be a non-empty HTTPS URL."
            )
        target = override.strip()
    elif local_path == "index.html":
        target = urljoin(base_url, "/")
    elif local_path.endswith("/index.html"):
        target = urljoin(base_url, local_path[: -len("index.html")])
    else:
        target = urljoin(base_url, local_path)
    if _origin(target) != base_origin:
        raise LiveSurfaceReconciliationError(
            f"Live-surface route must remain on the configured HTTPS origin: {local_path}"
        )
    return target


def _normalise_public_reference(value: object, document_url: str, *, keep_fragment: bool) -> str:
    """Normalise a public URL without treating a relative/absolute form as drift."""

    raw = _normalise_text(value)
    if not raw:
        return ""
    parsed = urlparse(raw)
    if raw.startswith("#") or parsed.scheme.lower() in {"data", "javascript", "mailto", "tel"}:
        return raw
    target = urljoin(document_url, raw)
    parsed_target = urlparse(target)
    if not parsed_target.scheme or not parsed_target.hostname:
        return target
    try:
        port = parsed_target.port
    except ValueError:
        return target
    netloc = parsed_target.hostname.lower()
    if port is not None and not (
        (parsed_target.scheme.lower() == "https" and port == 443)
        or (parsed_target.scheme.lower() == "http" and port == 80)
    ):
        netloc = f"{netloc}:{port}"
    normalised = parsed_target._replace(
        scheme=parsed_target.scheme.lower(),
        netloc=netloc,
        fragment=parsed_target.fragment if keep_fragment else "",
    )
    return normalised.geturl()


def _interaction_surface(parser: _PresentationParser, document_url: str) -> str:
    rows = []
    for tag, values in parser.interaction_parts:
        normalised = []
        for index, value in enumerate(values):
            if (
                (tag == "a" and index == 0)
                or (tag == "form" and index == 0)
                or (tag in {"img", "source"} and index in {0, 1})
            ):
                normalised.append(_normalise_public_reference(value, document_url, keep_fragment=True))
            else:
                normalised.append(_normalise_text(value))
        rows.append("\u001f".join((tag, *normalised)))
    return "\n".join(rows)


def _fingerprint_html(raw: bytes, *, document_url: str) -> dict[str, Any]:
    text = raw.decode("utf-8-sig", errors="replace")
    parser = _PresentationParser()
    try:
        parser.feed(text)
        parser.close()
    except Exception as exc:  # HTMLParser is permissive, but preserve a controlled receipt if it fails.
        raise LiveSurfaceReconciliationError(
            f"Could not parse public HTML presentation: {type(exc).__name__}: {exc}"
        ) from exc
    presentation_text = parser.presentation_text()
    interactions = _interaction_surface(parser, document_url)
    return {
        "bytes": len(raw),
        "sha256": _sha256_bytes(raw),
        "title": _normalise_text(" ".join(parser.title_parts)),
        "description": parser.description,
        "canonical": _normalise_public_reference(parser.canonical, document_url, keep_fragment=False),
        "presentation_text_sha256": _sha256_bytes(presentation_text.encode("utf-8")),
        "presentation_text_characters": len(presentation_text),
        "interaction_surface_sha256": _sha256_bytes(interactions.encode("utf-8")),
        "interaction_surface_items": len(parser.interaction_parts),
    }


def _response_status(response: Any) -> int:
    value = getattr(response, "status", None)
    if isinstance(value, int):
        return value
    getter = getattr(response, "getcode", None)
    observed = getter() if callable(getter) else None
    return int(observed) if isinstance(observed, int) else 200


def _response_content_type(response: Any) -> str:
    headers = getattr(response, "headers", None)
    getter = getattr(headers, "get_content_type", None)
    if callable(getter):
        observed = getter()
        return str(observed or "").lower()
    getter = getattr(headers, "get", None)
    observed = getter("Content-Type", "") if callable(getter) else ""
    return str(observed or "").split(";", 1)[0].strip().lower()


class _NoRedirectHandler(HTTPRedirectHandler):
    """Expose each redirect location to the reconciliation safety check."""

    def redirect_request(self, request, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


def _open_without_redirect(request: Request, *, timeout: float) -> Any:
    """Open one HTTPS response without allowing urllib to follow a redirect."""

    return build_opener(_NoRedirectHandler()).open(request, timeout=timeout)


def _header_value(headers: Any, name: str) -> str:
    getter = getattr(headers, "get", None)
    value = getter(name, "") if callable(getter) else ""
    return str(value or "").strip()


def _redirect_target(
    current_url: str,
    headers: Any,
    *,
    expected_origin: tuple[str, str, int],
) -> str:
    location = _header_value(headers, "Location")
    if not location:
        raise LiveSurfaceReconciliationError("Public redirect omitted a Location header.")
    target = urljoin(current_url, location)
    if _origin(target) != expected_origin:
        raise LiveSurfaceReconciliationError("Public HTTPS redirect target leaves the configured origin.")
    return target


def _close_response(response: Any) -> None:
    closer = getattr(response, "close", None)
    if callable(closer):
        closer()


def _fetch_public_html(
    url: str,
    *,
    expected_origin: tuple[str, str, int],
    timeout_seconds: float,
    opener: Callable[..., Any] | None,
) -> tuple[dict[str, Any], bytes]:
    active_opener = opener or _open_without_redirect
    current_url = url
    seen_urls = {current_url}
    redirect_chain: list[dict[str, Any]] = []
    for _hop in range(MAX_REDIRECTS + 1):
        request = Request(
            current_url,
            headers={
                "Accept": "text/html,application/xhtml+xml",
                "User-Agent": "Aureon-Live-Surface-Reconciliation/1.0",
            },
        )
        try:
            response = active_opener(request, timeout=timeout_seconds)
        except HTTPError as exc:
            try:
                status = int(exc.code)
                if not 300 <= status < 400:
                    raise
                target = _redirect_target(
                    current_url,
                    exc.headers,
                    expected_origin=expected_origin,
                )
            finally:
                _close_response(exc)
            if len(redirect_chain) >= MAX_REDIRECTS:
                raise LiveSurfaceReconciliationError(
                    f"Public HTTPS route exceeded the maximum of {MAX_REDIRECTS} redirects."
                ) from exc
            if target in seen_urls:
                raise LiveSurfaceReconciliationError("Public HTTPS redirect loop detected.") from exc
            seen_urls.add(target)
            redirect_chain.append({"from": current_url, "to": target, "http_status": status})
            current_url = target
            continue

        target = ""
        try:
            final_url = str(response.geturl() if hasattr(response, "geturl") else current_url)
            if _origin(final_url) != expected_origin:
                raise LiveSurfaceReconciliationError(
                    "Public HTTPS request redirected outside the configured origin."
                )
            status = _response_status(response)
            content_type = _response_content_type(response)
            if 300 <= status < 400:
                target = _redirect_target(
                    current_url,
                    getattr(response, "headers", None),
                    expected_origin=expected_origin,
                )
                raw = b""
            else:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
        finally:
            _close_response(response)

        if target:
            if len(redirect_chain) >= MAX_REDIRECTS:
                raise LiveSurfaceReconciliationError(
                    f"Public HTTPS route exceeded the maximum of {MAX_REDIRECTS} redirects."
                )
            if target in seen_urls:
                raise LiveSurfaceReconciliationError("Public HTTPS redirect loop detected.")
            seen_urls.add(target)
            redirect_chain.append({"from": current_url, "to": target, "http_status": status})
            current_url = target
            continue
        if not 200 <= status < 300:
            raise LiveSurfaceReconciliationError(
                f"Public route returned unexpected non-success HTTP status: {status}"
            )
        if len(raw) > MAX_RESPONSE_BYTES:
            raise LiveSurfaceReconciliationError(
                f"Public response exceeds the {MAX_RESPONSE_BYTES} byte observation limit."
            )
        if content_type and content_type not in {"text/html", "application/xhtml+xml"}:
            raise LiveSurfaceReconciliationError(
                f"Public route returned unexpected content type: {content_type}"
            )
        return {
            "final_url": final_url,
            "http_status": status,
            "content_type": content_type,
            "redirect_chain": redirect_chain,
        }, raw
    raise LiveSurfaceReconciliationError(
        f"Public HTTPS route exceeded the maximum of {MAX_REDIRECTS} redirects."
    )


def _snapshot_tree_hash(paths: Sequence[tuple[str, str]]) -> str:
    """Hash the exact local route bytes already captured for this observation."""

    digest = hashlib.sha256()
    for relative, sha256 in sorted(paths, key=lambda item: item[0].lower()):
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest().upper()


def _difference_signals(local: Mapping[str, Any], live: Mapping[str, Any]) -> list[str]:
    signals = []
    for field in (
        "title",
        "description",
        "canonical",
        "presentation_text_sha256",
        "interaction_surface_sha256",
    ):
        if local.get(field) != live.get(field):
            signals.append(field)
    return signals


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise LiveSurfaceReconciliationError(f"{label} must be an object.")
    return value


def _exact_keys(
    value: Mapping[str, Any],
    *,
    required: set[str],
    allowed: set[str],
    label: str,
) -> None:
    missing = required.difference(value)
    unexpected = set(value).difference(allowed)
    if missing:
        raise LiveSurfaceReconciliationError(
            f"{label} is missing required fields: {', '.join(sorted(missing))}."
        )
    if unexpected:
        raise LiveSurfaceReconciliationError(
            f"{label} contains unsupported fields: {', '.join(sorted(unexpected))}."
        )


def _validate_sha256(value: object, label: str) -> None:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise LiveSurfaceReconciliationError(f"{label} must be an uppercase SHA-256 value.")


def _validate_fingerprint(value: object, label: str) -> Mapping[str, Any]:
    fingerprint = _mapping(value, label)
    expected = {
        "bytes",
        "sha256",
        "title",
        "description",
        "canonical",
        "presentation_text_sha256",
        "presentation_text_characters",
        "interaction_surface_sha256",
        "interaction_surface_items",
    }
    _exact_keys(fingerprint, required=expected, allowed=expected, label=label)
    if not isinstance(fingerprint["bytes"], int) or fingerprint["bytes"] < 0:
        raise LiveSurfaceReconciliationError(f"{label}.bytes must be a non-negative integer.")
    _validate_sha256(fingerprint["sha256"], f"{label}.sha256")
    _validate_sha256(fingerprint["presentation_text_sha256"], f"{label}.presentation_text_sha256")
    _validate_sha256(fingerprint["interaction_surface_sha256"], f"{label}.interaction_surface_sha256")
    for field in ("title", "description", "canonical"):
        if not isinstance(fingerprint[field], str):
            raise LiveSurfaceReconciliationError(f"{label}.{field} must be a string.")
    for field in ("presentation_text_characters", "interaction_surface_items"):
        if not isinstance(fingerprint[field], int) or fingerprint[field] < 0:
            raise LiveSurfaceReconciliationError(f"{label}.{field} must be a non-negative integer.")
    return fingerprint


def validate_live_surface_reconciliation(receipt: Mapping[str, Any]) -> None:
    """Validate the receipt contract and its non-authoritative invariants.

    JSON Schema documents the portable contract. This stdlib validator is used
    at the write boundary as well so a forged or incomplete mapping cannot be
    recorded as immutable operator evidence merely because it is serialisable.
    """

    document = _mapping(receipt, "Live-surface reconciliation receipt")
    required = {
        "schema",
        "observed_at",
        "state",
        "passed",
        "release_eligible",
        "package_authority",
        "deployment_authority",
        "authority",
        "canonical",
        "public_surface",
        "routes",
        "summary",
        "next_gate",
    }
    _exact_keys(document, required=required, allowed=required, label="Live-surface reconciliation receipt")
    if document["schema"] != RECONCILIATION_SCHEMA:
        raise LiveSurfaceReconciliationError("Live-surface reconciliation receipt has an unexpected schema.")
    if not isinstance(document["observed_at"], str):
        raise LiveSurfaceReconciliationError(
            "Live-surface reconciliation receipt observed_at must be a string."
        )
    try:
        datetime.fromisoformat(document["observed_at"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise LiveSurfaceReconciliationError(
            "Live-surface reconciliation receipt observed_at must be ISO-8601."
        ) from exc
    state = document["state"]
    if state not in _RECONCILIATION_STATES:
        raise LiveSurfaceReconciliationError("Live-surface reconciliation receipt has an unsupported state.")
    if not isinstance(document["passed"], bool):
        raise LiveSurfaceReconciliationError("Live-surface reconciliation receipt passed must be boolean.")
    if document["release_eligible"] is not False:
        raise LiveSurfaceReconciliationError("Live-surface reconciliation must never be release eligible.")
    if document["package_authority"] != "none" or document["deployment_authority"] != "none":
        raise LiveSurfaceReconciliationError(
            "Live-surface reconciliation must never carry package or deployment authority."
        )
    authority = _mapping(document["authority"], "Live-surface reconciliation authority")
    if dict(authority) != AUTHORITY:
        raise LiveSurfaceReconciliationError(
            "Live-surface reconciliation authority must match the non-authoritative contract."
        )

    canonical = _mapping(document["canonical"], "Live-surface reconciliation canonical snapshot")
    canonical_fields = {
        "repository_root",
        "site_root",
        "selected_tree_sha256",
        "route_mapping_algorithm",
    }
    _exact_keys(canonical, required=canonical_fields, allowed=canonical_fields, label="Canonical snapshot")
    if not isinstance(canonical["repository_root"], str) or not isinstance(canonical["site_root"], str):
        raise LiveSurfaceReconciliationError("Canonical snapshot paths must be strings.")
    _validate_sha256(canonical["selected_tree_sha256"], "Canonical snapshot selected_tree_sha256")
    if canonical["route_mapping_algorithm"] != ROUTE_MAPPING_ALGORITHM:
        raise LiveSurfaceReconciliationError("Canonical snapshot route mapping algorithm is not recognised.")

    public_surface = _mapping(document["public_surface"], "Public surface")
    public_fields = {"base_url", "origin", "timeout_seconds", "max_response_bytes"}
    _exact_keys(public_surface, required=public_fields, allowed=public_fields, label="Public surface")
    if not isinstance(public_surface["base_url"], str) or not isinstance(public_surface["origin"], str):
        raise LiveSurfaceReconciliationError("Public surface URLs must be strings.")
    origin = _origin(public_surface["base_url"])
    expected_origin = f"{origin[0]}://{origin[1]}:{origin[2]}"
    if public_surface["origin"] != expected_origin:
        raise LiveSurfaceReconciliationError("Public surface origin does not match its base URL.")
    if (
        not isinstance(public_surface["timeout_seconds"], (int, float))
        or not 0 < float(public_surface["timeout_seconds"]) <= 60
    ):
        raise LiveSurfaceReconciliationError("Public surface timeout is outside the allowed range.")
    if public_surface["max_response_bytes"] != MAX_RESPONSE_BYTES:
        raise LiveSurfaceReconciliationError("Public surface response limit does not match the contract.")

    routes = document["routes"]
    if not isinstance(routes, list) or not routes:
        raise LiveSurfaceReconciliationError(
            "Live-surface reconciliation receipt must contain at least one route."
        )
    expected_counts = {"exact-source": 0, "semantic-aligned": 0, "diverged": 0, "unavailable": 0}
    allowed_route_fields = {
        "local_path",
        "public_url",
        "final_url",
        "http_status",
        "content_type",
        "redirect_chain",
        "alignment",
        "difference_signals",
        "error",
        "local",
        "live",
    }
    for index, route_value in enumerate(routes):
        route = _mapping(route_value, f"Route {index}")
        _exact_keys(
            route,
            required={"local_path", "public_url", "alignment", "difference_signals"},
            allowed=allowed_route_fields,
            label=f"Route {index}",
        )
        _safe_relative_html_path(route["local_path"])
        if not isinstance(route["public_url"], str) or _origin(route["public_url"]) != origin:
            raise LiveSurfaceReconciliationError(
                f"Route {index} public_url leaves the configured HTTPS origin."
            )
        alignment = route["alignment"]
        if alignment not in _ROUTE_ALIGNMENTS:
            raise LiveSurfaceReconciliationError(f"Route {index} has an unsupported alignment state.")
        expected_counts[str(alignment)] += 1
        signals = route["difference_signals"]
        if not isinstance(signals, list) or any(
            signal
            not in {
                "title",
                "description",
                "canonical",
                "presentation_text_sha256",
                "interaction_surface_sha256",
            }
            for signal in signals
        ):
            raise LiveSurfaceReconciliationError(f"Route {index} has invalid difference signals.")
        if len(signals) != len(set(signals)):
            raise LiveSurfaceReconciliationError(f"Route {index} repeats a difference signal.")
        if "local" in route:
            _validate_fingerprint(route["local"], f"Route {index} local fingerprint")
        if "live" in route:
            _validate_fingerprint(route["live"], f"Route {index} live fingerprint")
        if "http_status" in route and (
            not isinstance(route["http_status"], int) or not 100 <= route["http_status"] <= 599
        ):
            raise LiveSurfaceReconciliationError(f"Route {index} has an invalid HTTP status.")
        if "final_url" in route and (
            not isinstance(route["final_url"], str) or _origin(route["final_url"]) != origin
        ):
            raise LiveSurfaceReconciliationError(
                f"Route {index} final_url leaves the configured HTTPS origin."
            )
        if "redirect_chain" in route:
            chain = route["redirect_chain"]
            if not isinstance(chain, list) or len(chain) > MAX_REDIRECTS:
                raise LiveSurfaceReconciliationError(f"Route {index} has an invalid redirect chain.")
            for redirect in chain:
                record = _mapping(redirect, f"Route {index} redirect")
                _exact_keys(
                    record,
                    required={"from", "to", "http_status"},
                    allowed={"from", "to", "http_status"},
                    label=f"Route {index} redirect",
                )
                if _origin(record["from"]) != origin or _origin(record["to"]) != origin:
                    raise LiveSurfaceReconciliationError(
                        f"Route {index} redirect leaves the configured origin."
                    )
                if not isinstance(record["http_status"], int) or not 300 <= record["http_status"] < 400:
                    raise LiveSurfaceReconciliationError(f"Route {index} redirect status must be 3xx.")

        if alignment == "unavailable":
            if not isinstance(route.get("error"), str) or not route["error"].strip():
                raise LiveSurfaceReconciliationError(
                    f"Route {index} unavailable observation must preserve an error."
                )
            if signals or "live" in route:
                raise LiveSurfaceReconciliationError(
                    f"Route {index} unavailable observation cannot claim live alignment evidence."
                )
            continue
        for field in ("final_url", "http_status", "content_type", "local", "live"):
            if field not in route:
                raise LiveSurfaceReconciliationError(f"Route {index} aligned observation is missing {field}.")
        if not 200 <= route["http_status"] < 300:
            raise LiveSurfaceReconciliationError(f"Route {index} aligned observation must have a 2xx status.")
        if not isinstance(route["content_type"], str) or route["content_type"] not in {
            "text/html",
            "application/xhtml+xml",
        }:
            raise LiveSurfaceReconciliationError(f"Route {index} aligned observation must be HTML.")
        expected_signals = _difference_signals(route["local"], route["live"])
        if signals != expected_signals:
            raise LiveSurfaceReconciliationError(
                f"Route {index} difference signals do not match its fingerprints."
            )
        if alignment in {"exact-source", "semantic-aligned"} and signals:
            raise LiveSurfaceReconciliationError(
                f"Route {index} aligned observation cannot contain drift signals."
            )
        if alignment == "diverged" and not signals:
            raise LiveSurfaceReconciliationError(
                f"Route {index} divergence requires a material difference signal."
            )
        if alignment == "exact-source" and route["local"]["sha256"] != route["live"]["sha256"]:
            raise LiveSurfaceReconciliationError(
                f"Route {index} exact-source alignment has unequal byte hashes."
            )
        if alignment == "semantic-aligned" and route["local"]["sha256"] == route["live"]["sha256"]:
            raise LiveSurfaceReconciliationError(
                f"Route {index} semantic alignment must differ at byte level."
            )

    summary = _mapping(document["summary"], "Live-surface reconciliation summary")
    summary_fields = {"selected_routes", "exact_source", "semantic_aligned", "diverged", "unavailable"}
    _exact_keys(
        summary, required=summary_fields, allowed=summary_fields, label="Live-surface reconciliation summary"
    )
    expected_summary = {
        "selected_routes": len(routes),
        "exact_source": expected_counts["exact-source"],
        "semantic_aligned": expected_counts["semantic-aligned"],
        "diverged": expected_counts["diverged"],
        "unavailable": expected_counts["unavailable"],
    }
    if dict(summary) != expected_summary:
        raise LiveSurfaceReconciliationError(
            "Live-surface reconciliation summary does not match route evidence."
        )
    expected_state = (
        "live-observation-incomplete"
        if expected_counts["unavailable"]
        else "live-drift-detected"
        if expected_counts["diverged"]
        else "live-surface-semantically-aligned"
    )
    if state != expected_state or document["passed"] is not (state == "live-surface-semantically-aligned"):
        raise LiveSurfaceReconciliationError(
            "Live-surface reconciliation state and pass flag do not match route evidence."
        )
    if not isinstance(document["next_gate"], str) or not document["next_gate"].strip():
        raise LiveSurfaceReconciliationError(
            "Live-surface reconciliation receipt must describe its next gate."
        )


def reconcile_live_surface(
    *,
    repo_root: Path | None,
    site_root: Path,
    base_url: str,
    routes: Sequence[str],
    canonical_overrides: Mapping[str, object] | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    now: datetime | None = None,
    opener: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Observe local and public surfaces without altering either one.

    The receipt uses semantic presentation fingerprints instead of declaring an
    exact file match. CDN/server newline rewriting is harmless to the public
    experience, whereas title, description, canonical URL or visible-text
    differences are material live-drift signals.
    """

    root = _find_repo_root(repo_root)
    resolved_site_root = site_root.resolve() if site_root.is_absolute() else (root / site_root).resolve()
    try:
        resolved_site_root.relative_to(root)
    except ValueError as exc:
        raise LiveSurfaceReconciliationError(
            "Canonical website root must stay inside the repository."
        ) from exc
    if not resolved_site_root.is_dir():
        raise LiveSurfaceReconciliationError(f"Canonical website root is missing: {resolved_site_root}")
    expected_origin = _origin(base_url)
    if not isinstance(timeout_seconds, (int, float)) or not 0 < float(timeout_seconds) <= 60:
        raise LiveSurfaceReconciliationError(
            "Live-surface timeout must be greater than zero and at most 60 seconds."
        )
    overrides = dict(canonical_overrides or {})
    selected_routes = []
    for route in routes:
        normalised = _safe_relative_html_path(route)
        if normalised not in selected_routes:
            selected_routes.append(normalised)
    if not selected_routes:
        raise LiveSurfaceReconciliationError("At least one configured HTML route is required.")

    route_rows: list[dict[str, Any]] = []
    local_snapshots: list[tuple[str, str]] = []
    for local_path in selected_routes:
        local_file = _safe_path_under(resolved_site_root, local_path, label="Canonical website route")
        public_url = _public_url(base_url, local_path, overrides)
        row: dict[str, Any] = {
            "local_path": local_path,
            "public_url": public_url,
            "alignment": "unavailable",
            "difference_signals": [],
        }
        if not local_file.is_file():
            row["error"] = "Local canonical HTML route is missing."
            route_rows.append(row)
            continue
        try:
            # Capture local bytes before touching the network. The final tree
            # hash is derived from this exact snapshot, never by rereading a
            # mutable source file after a public request completes.
            local_fingerprint = _fingerprint_html(
                local_file.read_bytes(),
                document_url=public_url,
            )
            local_snapshots.append((local_path, local_fingerprint["sha256"]))
            row["local"] = local_fingerprint
            response_metadata, raw = _fetch_public_html(
                public_url,
                expected_origin=expected_origin,
                timeout_seconds=float(timeout_seconds),
                opener=opener,
            )
            live_fingerprint = _fingerprint_html(
                raw,
                document_url=response_metadata["final_url"],
            )
            signals = _difference_signals(local_fingerprint, live_fingerprint)
            row.update(
                {
                    "final_url": response_metadata["final_url"],
                    "http_status": response_metadata["http_status"],
                    "content_type": response_metadata["content_type"],
                    "live": live_fingerprint,
                    "redirect_chain": response_metadata["redirect_chain"],
                    "difference_signals": signals,
                    "alignment": (
                        "exact-source"
                        if local_fingerprint["sha256"] == live_fingerprint["sha256"]
                        else "semantic-aligned"
                        if not signals
                        else "diverged"
                    ),
                }
            )
        except HTTPError as exc:
            row.update({"http_status": exc.code, "error": f"HTTPError: {exc.reason}"})
        except URLError as exc:
            row["error"] = f"URLError: {exc.reason}"
        except (OSError, LiveSurfaceReconciliationError) as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"
        route_rows.append(row)

    has_unavailable = any(row["alignment"] == "unavailable" for row in route_rows)
    has_drift = any(row["alignment"] == "diverged" for row in route_rows)
    if has_unavailable:
        state = "live-observation-incomplete"
    elif has_drift:
        state = "live-drift-detected"
    else:
        state = "live-surface-semantically-aligned"
    return {
        "schema": RECONCILIATION_SCHEMA,
        "observed_at": _utc_iso(now),
        "state": state,
        "passed": state == "live-surface-semantically-aligned",
        "release_eligible": False,
        "package_authority": "none",
        "deployment_authority": "none",
        "authority": dict(AUTHORITY),
        "canonical": {
            "repository_root": str(root),
            "site_root": str(resolved_site_root.relative_to(root)),
            "selected_tree_sha256": _snapshot_tree_hash(local_snapshots),
            "route_mapping_algorithm": ROUTE_MAPPING_ALGORITHM,
        },
        "public_surface": {
            "base_url": base_url,
            "origin": f"{expected_origin[0]}://{expected_origin[1]}:{expected_origin[2]}",
            "timeout_seconds": float(timeout_seconds),
            "max_response_bytes": MAX_RESPONSE_BYTES,
        },
        "routes": route_rows,
        "summary": {
            "selected_routes": len(route_rows),
            "exact_source": sum(row["alignment"] == "exact-source" for row in route_rows),
            "semantic_aligned": sum(row["alignment"] == "semantic-aligned" for row in route_rows),
            "diverged": sum(row["alignment"] == "diverged" for row in route_rows),
            "unavailable": sum(row["alignment"] == "unavailable" for row in route_rows),
        },
        "next_gate": (
            "Resolve public observation errors before relying on this receipt. It cannot authorise a candidate, package, backup or deployment."
            if has_unavailable
            else "Treat the live site as a materially different production record. Preserve it, obtain a fresh verified backup, and record an owner-scoped reconciliation before a successor candidate or deployment discussion."
            if has_drift
            else "Public presentation is semantically aligned for these routes. A separate exact work order, candidate controls, backup, owner approval and package-bound live read-back remain mandatory."
        ),
    }


def write_live_surface_reconciliation(
    receipt: Mapping[str, Any],
    output_path: Path,
    *,
    repo_root: Path | None = None,
) -> Path:
    """Persist a local, append-only reconciliation receipt under operator artifacts."""

    validate_live_surface_reconciliation(receipt)
    root = _find_repo_root(repo_root)
    target = output_path.resolve() if output_path.is_absolute() else (root / output_path).resolve()
    allowed_root = (root / "artifacts" / "website-operator").resolve()
    try:
        target.relative_to(allowed_root)
    except ValueError as exc:
        raise LiveSurfaceReconciliationError(
            "Live-surface reconciliation evidence must remain below artifacts/website-operator/."
        ) from exc
    if target.suffix.lower() != ".json":
        raise LiveSurfaceReconciliationError("Live-surface reconciliation output must use a .json filename.")
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        handle = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    except FileExistsError as exc:
        raise LiveSurfaceReconciliationError(
            f"Refusing to overwrite reconciliation evidence: {target}"
        ) from exc
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(dict(receipt), stream, indent=2, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        try:
            target.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    return target


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aureon-live-surface-reconciliation",
        description="Read-only canonical-source to public-HTTPS website reconciliation.",
    )
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--site-root", type=Path, default=Path("website"))
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--route", action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    try:
        receipt = reconcile_live_surface(
            repo_root=args.repo_root,
            site_root=args.site_root,
            base_url=args.base_url,
            routes=args.route,
        )
        output = write_live_surface_reconciliation(receipt, args.output, repo_root=args.repo_root)
        print(
            json.dumps(
                {
                    "state": receipt["state"],
                    "passed": receipt["passed"],
                    "output": str(output),
                    "release_eligible": False,
                    "deployment_authority": "none",
                },
                indent=2,
            )
        )
        return 0 if receipt["passed"] else 2
    except LiveSurfaceReconciliationError as exc:
        print(json.dumps({"state": "blocked", "error": str(exc)}, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
