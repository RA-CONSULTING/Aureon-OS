"""
AureonVaultUI — Flask Server for Communicating with the Vault
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

A small Flask HTTP server that exposes a HOLD-only, authenticated loopback
inspection API. Effectful requests are converted to HNC, burned, and held.
The legacy HTML/PWA assets remain checked in but are not released by this
boundary: ordinary browser navigation cannot safely attach the bearer header.

  • Watch the vault's state in real time (love, gratitude, Casimir, Λ(t),
    dominant chakra, rally status, vote consensus)
  • Read the stream of utterances as voices speak to each other
  • Send messages to the vault and get responses from a chosen voice
  • Force a specific voice to speak
  • Trigger one tick of the feedback loop on demand
  • Start/stop the background loop

Endpoints:
  GET  /                       — the chat UI (index.html)
  GET  /bridge                 — mobile / phone-side PWA bridge UI
  GET  /manifest.webmanifest   — PWA manifest for "Add to Home Screen"
  GET  /api/status             — full vault + loop status dict
  GET  /api/voices             — list of voice names
  GET  /api/utterances?n=50    — recent utterances (most recent last)
  POST /api/message            — {"text": "...", "voice": "queen"?}
                                  vault ingests + voice responds
  POST /api/speak              — {"voice": "miner"?} force a voice to speak
  POST /api/converse           — trigger one voice_engine.converse()
  POST /api/tick               — trigger one full loop.tick()
  POST /api/loop/start         — start the loop daemon
  POST /api/loop/stop          — stop the loop daemon

Phi-bridge (authenticated local inspection only while release is on HOLD):
  GET  /api/bridge/info        — bridge state, peers, cadence, desktop view
  GET  /api/bridge/peers       — coupled peers only
  POST /api/bridge/register    — register / refresh a peer
  POST /api/bridge/sync        — peer pushes state, gets desktop view back
  POST /api/bridge/drop        — explicit peer disconnect

Phi-bridge mesh (P2P mutation routes are admitted to HNC and held):
  POST /api/bridge/cards           — peers exchange VaultContent cards here
  GET  /api/bridge/mesh/info       — mesh stats (cycles, cards in/out, peers)
  GET  /api/bridge/discovery/peers — peers discovered via UDP LAN broadcast

UDP discovery, card gossip, background loops, and mutation handlers do not
start or execute while the production Magic-Star release boundary is absent.

HOLD-only API usage:
    from aureon.vault.ui import create_app, run_server
    run_server(host="127.0.0.1", port=5566)

Or programmatically:
    from aureon.vault.ui import create_app
    app = create_app()
    app.run(port=5566)
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import logging
import os
import re
import threading
import time
import uuid
from typing import Any, Dict, Optional

try:
    from flask import Flask, jsonify, request, send_from_directory
    from werkzeug.serving import WSGIRequestHandler
    _FLASK_AVAILABLE = True
except Exception:  # pragma: no cover
    Flask = None  # type: ignore[assignment,misc]
    jsonify = None  # type: ignore[assignment]
    request = None  # type: ignore[assignment]
    send_from_directory = None  # type: ignore[assignment]
    WSGIRequestHandler = object  # type: ignore[assignment,misc]
    _FLASK_AVAILABLE = False

_VaultUIFlaskBase = Flask if Flask is not None else object

from aureon.harmonic.auris_voice_filter import get_auris_voice_filter
from aureon.harmonic.hnc_quantum_packet_crypto import (
    normalize_hnc_key_material,
    packet_master_key_from_env,
)
from aureon.harmonic.phi_bridge import PhiBridge
from aureon.harmonic.phi_bridge_discovery import PhiBridgeDiscovery
from aureon.harmonic.phi_bridge_mesh import PhiBridgeMesh
from aureon.harmonic.phi_swarm_router import get_phi_swarm_router
from aureon.queen.conversation_memory import get_conversation_memory
from aureon.queen.meaning_resolver import get_meaning_resolver
from aureon.queen.queen_action_bridge import get_queen_action_bridge
from aureon.vault.self_feedback_loop import AureonSelfFeedbackLoop
from aureon.plumber.os_protection import (
    AdmittedHNC,
    LocalOSProtectionBoundary,
    QuarantinedHNC,
)

logger = logging.getLogger("aureon.vault.ui")

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
VAULT_UI_AUTH_ENV = "AUREON_VAULT_UI_BEARER_TOKEN"
VAULT_UI_MAX_REQUEST_BYTES = 64 * 1024
VAULT_UI_MAX_PATH_BYTES = 4 * 1024
VAULT_UI_MAX_QUERY_BYTES = 4 * 1024
VAULT_UI_MAX_HEADER_BYTES = 16 * 1024
VAULT_UI_MAX_AUTHORIZATION_BYTES = 1024
VAULT_UI_MAX_METHOD_BYTES = 32
VAULT_UI_MAX_CONTENT_TYPE_BYTES = 1024
VAULT_UI_MAX_REMOTE_ADDRESS_BYTES = 64
VAULT_UI_MAX_INGRESS_BYTES = (
    len(b"AUREON_VAULT_UI_HTTP_INTENT_V1\x00")
    + (9 * 4)
    + VAULT_UI_MAX_REQUEST_BYTES
    + VAULT_UI_MAX_PATH_BYTES
    + VAULT_UI_MAX_QUERY_BYTES
    + VAULT_UI_MAX_HEADER_BYTES
    + VAULT_UI_MAX_METHOD_BYTES
    + VAULT_UI_MAX_CONTENT_TYPE_BYTES
    + VAULT_UI_MAX_PATH_BYTES
    + VAULT_UI_MAX_REMOTE_ADDRESS_BYTES
    + 32
)
_VAULT_UI_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9._~-]{43,512}$")
_SAFE_READ_HTTP_METHODS = frozenset({"GET", "HEAD"})
_VAULT_UI_SAFE_READ_RULES = frozenset({
    "/api/health",
    "/api/status",
    "/api/voices",
    "/api/utterances",
    "/api/message/<job_id>",
    "/api/bridge/invite",
    "/api/bridge/mesh/info",
    "/api/bridge/discovery/peers",
})
_HTTP_INTENT_CARRIER_MAGIC = b"AUREON_VAULT_UI_HTTP_INTENT_V1\x00"


def _configured_vault_ui_token() -> Optional[str]:
    token = str(os.environ.get(VAULT_UI_AUTH_ENV, "") or "").strip()
    return token if _VAULT_UI_TOKEN_PATTERN.fullmatch(token) is not None else None


def _loopback_address(value: object) -> bool:
    candidate = str(value or "").strip()
    if candidate.casefold() == "localhost":
        return True
    try:
        return ipaddress.ip_address(candidate).is_loopback
    except ValueError:
        return False


def _hnc_master_key_configured() -> bool:
    try:
        normalize_hnc_key_material(packet_master_key_from_env() or None)
        return True
    except BaseException:
        return False


def _http_intent_carrier(*parts: bytes) -> bytes:
    carrier = bytearray(_HTTP_INTENT_CARRIER_MAGIC)
    for part in parts:
        carrier.extend(len(part).to_bytes(4, "big"))
        carrier.extend(part)
    return bytes(carrier)


def _header_bytes(value: object) -> bytes:
    return str(value or "").encode("utf-8", errors="replace")


def _canonical_non_authorization_headers(headers: object) -> bytes:
    """Bind every non-secret request header into an effect-intent carrier."""

    pairs = []
    for name, value in headers.items():
        normalized_name = str(name or "").strip().casefold()
        if normalized_name == "authorization":
            continue
        pairs.append((normalized_name, str(value or "")))
    encoded = bytearray()
    for name, value in sorted(pairs):
        name_bytes = _header_bytes(name)
        value_bytes = _header_bytes(value)
        encoded.extend(len(name_bytes).to_bytes(4, "big"))
        encoded.extend(name_bytes)
        encoded.extend(len(value_bytes).to_bytes(4, "big"))
        encoded.extend(value_bytes)
    return bytes(encoded)


def vault_ui_security_preflight(*, host: str = "127.0.0.1", debug: bool = False) -> dict[str, Any]:
    """Return a non-secret, fail-closed bind preflight for the Vault UI."""

    denial_codes: list[str] = []
    if not _loopback_address(host):
        denial_codes.append("loopback_bind_required")
    if debug is not False:
        denial_codes.append("debug_server_forbidden")
    if _configured_vault_ui_token() is None:
        denial_codes.append("vault_ui_bearer_token_unavailable_or_invalid")
    if not _hnc_master_key_configured():
        denial_codes.append("hnc_master_key_unavailable_or_invalid")
    return {
        "schema": "aureon.vault-ui.security-preflight.v1",
        "status": "READY_LOCAL_HOLD" if not denial_codes else "HOLD",
        "denial_codes": denial_codes,
        "loopback_only": True,
        "long_well_formed_bearer_required": True,
        "minimum_bearer_characters": 43,
        "effectful_ingress_hnc_required": True,
        "production_magic_star_release_available": False,
        "lan_binding_authorized": False,
        "public_tunnel_authorized": False,
        "production_ready": False,
    }


class VaultUIRedactedRequestHandler(WSGIRequestHandler):
    """Bound slow clients and never place request targets in access logs."""

    timeout = 5

    def setup(self) -> None:
        super().setup()
        try:
            self.connection.settimeout(self.timeout)
        except Exception:
            pass

    def log_request(self, code: int | str = "-", size: int | str = "-") -> None:
        self.log("info", '"[vault-target-redacted]" %s %s', str(code), str(size))

    def log_error(self, _format: str, *_args: Any) -> None:
        self.log("error", "[vault-request-error-redacted]")

    def log_message(self, _format: str, *_args: Any) -> None:
        self.log("info", "[vault-request-message-redacted]")


class VaultUIFlask(_VaultUIFlaskBase):
    """Flask app whose public run method cannot enable external/debug serving."""

    def run(
        self,
        host: str | None = None,
        port: int | None = None,
        debug: bool | None = None,
        load_dotenv: bool = False,
        **options: Any,
    ) -> None:
        requested_host = host or "127.0.0.1"
        requested_debug = bool(debug) or bool(self.debug) or any(
            bool(options.get(name))
            for name in ("use_debugger", "use_evalex", "use_reloader")
        )
        preflight = vault_ui_security_preflight(
            host=requested_host,
            debug=requested_debug,
        )
        if preflight["status"] != "READY_LOCAL_HOLD":
            codes = ",".join(preflight["denial_codes"])
            raise RuntimeError(f"vault_ui_bind_preflight_failed:{codes}")
        self.debug = False
        options.update({
            "use_debugger": False,
            "use_evalex": False,
            "use_reloader": False,
            "threaded": False,
            "processes": 1,
            "request_handler": VaultUIRedactedRequestHandler,
        })
        super().run(
            host="127.0.0.1",
            port=port,
            debug=False,
            load_dotenv=False,
            **options,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Error helper
# ─────────────────────────────────────────────────────────────────────────────


def _check_flask() -> None:
    if not _FLASK_AVAILABLE:
        raise RuntimeError(
            "Flask is not installed. Run `pip install flask` to enable the vault UI."
        )


def _stop_runtime_component(component: object, *, reason_code: str) -> None:
    """Stop inherited background state and fail if any worker survives."""

    if component is None:
        return
    stop = getattr(component, "stop", None)
    if callable(stop):
        try:
            stop()
        except Exception as exc:
            raise RuntimeError(f"{reason_code}:stop_failed") from exc
    if bool(getattr(component, "_running", False)):
        raise RuntimeError(f"{reason_code}:still_running")
    for attribute in ("_thread", "_announce_thread", "_listen_thread"):
        worker = getattr(component, attribute, None)
        is_alive = getattr(worker, "is_alive", None)
        if callable(is_alive) and is_alive():
            raise RuntimeError(f"{reason_code}:worker_survived")


def _vault_ui_loop_denial_codes(loop: object) -> list[str]:
    codes: list[str] = []
    if type(loop) is not AureonSelfFeedbackLoop:
        codes.append("canonical_feedback_loop_required")
        return codes
    worker = getattr(loop, "_thread", None)
    worker_alive = getattr(worker, "is_alive", None)
    if bool(getattr(loop, "_running", False)) or (
        callable(worker_alive) and worker_alive()
    ):
        codes.append("feedback_loop_must_be_stopped")
    if getattr(loop, "voice_engine", None) is not None:
        codes.append("voice_engine_must_be_absent")
    if bool(getattr(loop, "_enhance_enabled", False)) or getattr(
        loop, "_enhancer", None
    ) is not None:
        codes.append("self_enhancement_must_be_absent")
    casimir = getattr(loop, "casimir", None)
    if getattr(casimir, "_engine", None) is not None or getattr(
        casimir, "_engine_kind", "stub"
    ) != "stub":
        codes.append("native_casimir_must_be_absent")
    pinger = getattr(loop, "pinger", None)
    if getattr(pinger, "_chirp_bus", None) is not None:
        codes.append("chirp_bus_must_be_absent")
    if getattr(pinger, "_thought_bus", None) is not None:
        codes.append("pinger_thought_bus_must_be_absent")
    vault = getattr(loop, "vault", None)
    if bool(getattr(vault, "_subscribed", False)) or getattr(
        vault, "_thought_bus", None
    ) is not None:
        codes.append("vault_thought_bus_subscription_must_be_absent")
    return codes


# ─────────────────────────────────────────────────────────────────────────────
# App factory
# ─────────────────────────────────────────────────────────────────────────────


def create_app(
    loop: Optional[AureonSelfFeedbackLoop] = None,
    base_interval_s: float = 1.0,
    enable_voice: bool = False,
    *,
    mesh_discovery: Optional[PhiBridgeDiscovery] = None,
    mesh_port: Optional[int] = None,
    mesh_label: str = "aureon",
    mesh_kind: str = "desktop",
) -> "Flask":
    """
    Create a HOLD-only Flask app with a factory-owned inert feedback loop.

    Supplied loops are rejected because their constructors may already have
    subscribed to shared buses, probed providers, or started other effects.

    Mesh wiring is retained only as inert inspection state. UDP discovery and
    card gossip do not start here because the checked-in Plumber/Magic-Star
    boundary has no production release authority.
    """
    _check_flask()
    preflight = vault_ui_security_preflight(host="127.0.0.1", debug=False)
    if preflight["status"] != "READY_LOCAL_HOLD":
        codes = ",".join(preflight["denial_codes"])
        raise RuntimeError(f"vault_ui_factory_preflight_failed:{codes}")

    if loop is not None:
        raise RuntimeError(
            "vault_ui_supplied_feedback_loop_forbidden:factory_owned_inert_loop_required"
        )
    if mesh_discovery is not None:
        raise RuntimeError(
            "vault_ui_supplied_mesh_discovery_forbidden:app_owned_inert_mesh_required"
        )
    if enable_voice:
        raise RuntimeError(
            "vault_ui_voice_startup_hold:production_magic_star_release_unavailable"
        )
    loop = AureonSelfFeedbackLoop(
        base_interval_s=base_interval_s,
        auto_wire_bus=False,
        enable_voice=False,
        enable_self_enhancement=False,
        enable_native_casimir=False,
        enable_harmonic_buses=False,
    )
    loop_denial_codes = _vault_ui_loop_denial_codes(loop)
    if loop_denial_codes:
        raise RuntimeError(
            "vault_ui_feedback_loop_preflight_failed:"
            + ",".join(loop_denial_codes)
        )

    app = VaultUIFlask(
        "aureon_vault_ui",
        static_folder=STATIC_DIR,
        static_url_path="/static",
    )
    # Read at most one sentinel byte beyond the admitted body limit so a
    # chunked/no-Content-Length stream cannot be silently truncated.
    app.config["MAX_CONTENT_LENGTH"] = VAULT_UI_MAX_REQUEST_BYTES + 1

    bearer_token_configured = _configured_vault_ui_token() is not None
    ingress_boundary = LocalOSProtectionBoundary(
        boundary_id="aureon-vault-ui-http-ingress-v1",
        master_key_provider=lambda: packet_master_key_from_env() or None,
        max_ingress_bytes=VAULT_UI_MAX_INGRESS_BYTES,
        max_active_handles=32,
        max_active_ingress_bytes=4 * 1024 * 1024,
        max_replay_tokens=8192,
        max_quarantine_evidence=2048,
    )
    app.config["AUREON_VAULT_UI_SECURITY"] = {
        "schema": "aureon.vault-ui.runtime-security.v1",
        "authentication_configured": bearer_token_configured,
        "hnc_master_key_configured": _hnc_master_key_configured(),
        "loopback_only": True,
        "effectful_ingress_disposition": "HOLD",
        "safe_read_rules": sorted(_VAULT_UI_SAFE_READ_RULES),
        "browser_ui_status": "HOLD_API_CLIENT_ONLY",
        "production_magic_star_release_available": False,
        "production_ready": False,
    }
    app.config["AUREON_VAULT_UI_INGRESS_BOUNDARY"] = ingress_boundary

    def _presented_bearer(header: str) -> str:
        scheme, separator, token = header.partition(" ")
        if separator and scheme.casefold() == "bearer":
            return token.strip()
        return ""

    @app.before_request
    def _require_plumber_hnc_ingress():
        """Authenticate every request and burn every mutating intent on HOLD."""

        current_bearer_token = _configured_vault_ui_token()
        if current_bearer_token is None:
            return jsonify({
                "status": "HOLD",
                "reason_code": "vault_ui_authorization_not_configured",
                "request_executed": False,
                "production_ready": False,
            }), 503
        header_size = sum(
            len(_header_bytes(name)) + len(_header_bytes(value)) + 4
            for name, value in request.headers.items()
        )
        if header_size > VAULT_UI_MAX_HEADER_BYTES:
            return jsonify({
                "status": "HOLD",
                "reason_code": "request_header_limit_exceeded",
                "request_executed": False,
            }), 431
        authorization = str(request.headers.get("Authorization", "") or "")
        if len(_header_bytes(authorization)) > VAULT_UI_MAX_AUTHORIZATION_BYTES:
            return jsonify({
                "status": "HOLD",
                "reason_code": "authorization_header_limit_exceeded",
                "request_executed": False,
            }), 431
        if not _loopback_address(request.remote_addr):
            return jsonify({
                "status": "HOLD",
                "reason_code": "loopback_transport_required",
                "request_executed": False,
            }), 403
        presented = _presented_bearer(authorization)
        if (
            len(presented) > 512
            or not presented
            or not hmac.compare_digest(presented, current_bearer_token)
        ):
            return jsonify({
                "status": "HOLD",
                "reason_code": "authentication_required",
                "request_executed": False,
            }), 401
        method_bytes = str(request.method or "").encode("ascii", errors="replace")
        if not method_bytes or len(method_bytes) > VAULT_UI_MAX_METHOD_BYTES:
            return jsonify({
                "status": "HOLD",
                "reason_code": "request_method_limit_exceeded",
                "request_executed": False,
            }), 400
        content_type_bytes = _header_bytes(request.headers.get("Content-Type", ""))
        if len(content_type_bytes) > VAULT_UI_MAX_CONTENT_TYPE_BYTES:
            return jsonify({
                "status": "HOLD",
                "reason_code": "content_type_header_limit_exceeded",
                "request_executed": False,
            }), 431
        query_bytes = bytes(request.query_string or b"")
        path_bytes = str(request.path or "").encode("utf-8", errors="replace")
        if len(path_bytes) > VAULT_UI_MAX_PATH_BYTES:
            return jsonify({
                "status": "HOLD",
                "reason_code": "path_size_limit_exceeded",
                "request_executed": False,
            }), 414
        if len(query_bytes) > VAULT_UI_MAX_QUERY_BYTES:
            return jsonify({
                "status": "HOLD",
                "reason_code": "query_size_limit_exceeded",
                "request_executed": False,
            }), 414
        route_rule = str(getattr(request.url_rule, "rule", "") or "")
        route_rule_bytes = route_rule.encode("utf-8", errors="replace")
        if len(route_rule_bytes) > VAULT_UI_MAX_PATH_BYTES:
            return jsonify({
                "status": "HOLD",
                "reason_code": "route_rule_size_limit_exceeded",
                "request_executed": False,
            }), 414
        remote_address_bytes = _header_bytes(request.remote_addr)
        if len(remote_address_bytes) > VAULT_UI_MAX_REMOTE_ADDRESS_BYTES:
            return jsonify({
                "status": "HOLD",
                "reason_code": "remote_address_size_limit_exceeded",
                "request_executed": False,
            }), 400
        canonical_headers = _canonical_non_authorization_headers(request.headers)
        if len(canonical_headers) > VAULT_UI_MAX_HEADER_BYTES:
            return jsonify({
                "status": "HOLD",
                "reason_code": "canonical_header_limit_exceeded",
                "request_executed": False,
            }), 431
        authorization_fingerprint = hashlib.sha256(
            authorization.encode("utf-8", errors="replace")
        ).digest()
        raw_body = request.get_data(cache=False, as_text=False)
        if len(raw_body) > VAULT_UI_MAX_REQUEST_BYTES:
            return jsonify({
                "status": "HOLD",
                "reason_code": "request_size_limit_exceeded",
                "request_executed": False,
                "production_ready": False,
            }), 413
        safe_read = (
            request.method in _SAFE_READ_HTTP_METHODS
            and route_rule in _VAULT_UI_SAFE_READ_RULES
            and len(raw_body) == 0
        )
        if safe_read:
            if not _hnc_master_key_configured():
                return jsonify({
                    "status": "HOLD",
                    "reason_code": "hnc_master_key_unavailable_or_invalid",
                    "request_executed": False,
                    "production_ready": False,
                }), 503
            return None

        raw = _http_intent_carrier(
            method_bytes,
            path_bytes,
            query_bytes,
            content_type_bytes,
            route_rule_bytes,
            remote_address_bytes,
            canonical_headers,
            authorization_fingerprint,
            raw_body,
        )
        outcome = ingress_boundary.admit_external(
            raw,
            source_id="vault-ui-authenticated-loopback",
            ingress_kind="http-effect-intent",
            purpose="aureon.vault-ui.effect-intent.v1",
            operator_aad={
                "authenticated": True,
                "loopback_transport": True,
                "method": request.method,
                "path_sha256": hashlib.sha256(path_bytes).hexdigest(),
                "route_rule_sha256": hashlib.sha256(
                    route_rule_bytes
                ).hexdigest(),
                "query_sha256": hashlib.sha256(query_bytes).hexdigest(),
                "content_type_sha256": hashlib.sha256(content_type_bytes).hexdigest(),
            },
            content_validator=lambda view: (
                isinstance(view, memoryview)
                and bytes(view[:len(_HTTP_INTENT_CARRIER_MAGIC)])
                == _HTTP_INTENT_CARRIER_MAGIC
            ),
        )
        admission = outcome.public_summary()
        if isinstance(outcome, AdmittedHNC):
            disposal = ingress_boundary.discard_admitted(
                outcome.handle,
                reason_code="production_magic_star_release_unavailable",
            )
            return jsonify({
                "status": "HOLD",
                "reason_code": "production_magic_star_release_unavailable",
                "request_executed": False,
                "effect_attempted": False,
                "plumber_hnc_admitted": True,
                "magic_star_release_required": True,
                "admission": admission,
                "disposal": disposal,
                "production_ready": False,
            }), 423
        if not isinstance(outcome, QuarantinedHNC):  # pragma: no cover - total boundary
            raise RuntimeError("vault_ui_hnc_outcome_invalid")
        return jsonify({
            "status": "QUARANTINED_HNC",
            "reason_code": "hnc_admission_denied",
            "request_executed": False,
            "effect_attempted": False,
            "plumber_hnc_admitted": False,
            "magic_star_release_required": True,
            "admission": admission,
            "production_ready": False,
        }), 409

    @app.after_request
    def _secure_vault_ui_response(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        )
        return response

    @app.errorhandler(413)
    def _request_too_large(_error):
        return jsonify({
            "status": "HOLD",
            "reason_code": "request_size_limit_exceeded",
            "request_executed": False,
            "production_ready": False,
        }), 413

    # Expose the loop on the app config so tests can reach it
    app.config["AUREON_LOOP"] = loop

    # App-owned bridge state prevents cross-app peers, counters, and vault
    # ownership from leaking through a process singleton.
    bridge = PhiBridge(vault=loop.vault)
    app.config["AUREON_PHI_BRIDGE"] = bridge
    # Make the voice engine reachable via the vault for the bridge's
    # "last utterance" lookup. We attach a private attribute so we don't
    # collide with anything the vault already exposes.
    if loop.voice_engine is not None:
        try:
            setattr(loop.vault, "_voice_engine", loop.voice_engine)
        except Exception:
            pass

    # Pending async chat jobs fired by POST /api/message with async=true.
    # The handler returns immediately with a job_id; the phone polls
    # /api/message/{job_id} (or just watches /api/bridge/sync) for the
    # reply. This is what stops slow LLM chorus runs from blowing the
    # phone's 60s fetch timeout.
    pending_jobs: Dict[str, Dict[str, Any]] = {}
    pending_jobs_lock = threading.Lock()
    app.config["AUREON_PENDING_JOBS"] = pending_jobs

    # Model probing and warm-up egress are absent from this HOLD-only app.
    app.config["AUREON_LLM_WARMER_RUNTIME"] = {
        "status": "HOLD",
        "boot_ping_started": False,
        "keepalive_thread_started": False,
        "reason_code": "production_magic_star_release_unavailable",
        "production_ready": False,
    }

    # ─────────────────────────────────────────────────────────────────────
    # UI page
    # ─────────────────────────────────────────────────────────────────────

    @app.route("/")
    def index():
        index_path = os.path.join(STATIC_DIR, "index.html")
        if not os.path.exists(index_path):
            return (
                "<h1>Aureon Vault UI</h1>"
                "<p>index.html not found at " + index_path + "</p>"
            ), 200
        return send_from_directory(STATIC_DIR, "index.html")

    # ─────────────────────────────────────────────────────────────────────
    # Status + introspection
    # ─────────────────────────────────────────────────────────────────────

    @app.route("/api/status")
    def api_status():
        try:
            status = loop.get_status()
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500
        return jsonify({"ok": True, "status": status})

    @app.route("/api/voices")
    def api_voices():
        if loop.voice_engine is None:
            return jsonify({
                "ok": True,
                "voices": [],
                "status": "HOLD",
                "reason_code": "voice_engine_disabled",
            })
        return jsonify({
            "ok": True,
            "voices": list(loop.voice_engine.voices.keys()),
        })

    @app.route("/api/utterances")
    def api_utterances():
        if loop.voice_engine is None:
            return jsonify({"ok": True, "count": 0, "utterances": []})
        n = request.args.get("n", default=50, type=int)
        history = loop.voice_engine.history[-n:]
        return jsonify({
            "ok": True,
            "count": len(history),
            "utterances": [u.to_dict() for u in history],
        })

    # ─────────────────────────────────────────────────────────────────────
    # Interaction
    # ─────────────────────────────────────────────────────────────────────

    def _fast_human_reply(text: str, voice_name: Optional[str], peer_id: str = ""):
        """
        Single-voice fast path — REAL cognition, not templates, WITH memory.

        Uses the voice's existing LLM adapter (local Ollama by default)
        and injects the last few turns of this peer's conversation so the
        Queen actually *continues* the thread instead of re-introducing
        herself every reply.

        If the LLM dies or takes too long and the voice produces nothing,
        we fall through to the PhiSwarmRouter's template layer as a
        last-ditch backstop so the phone always gets *something*.

        max_tokens is capped at 128 to keep latency in the 2-6 second
        window that a phone fetch can survive without timing out.
        """
        engine = loop.voice_engine
        vault = loop.vault
        memory = get_conversation_memory()
        pid = (peer_id or "anon").strip() or "anon"

        # Record the human turn BEFORE we speak so the voice's prompt
        # can include it via format_as_prompt_block.
        try:
            memory.record(pid, "human", text, meta={"via": "phone_bridge"})
        except Exception:
            pass

        # Ingest the message so the voice sees it in its state extraction.
        try:
            vault.ingest(
                topic="human.message",
                payload={"text": text, "who": "human", "peer_id": pid},
                category="human_message",
            )
        except Exception:
            pass

        # ── Resolver runs FIRST so we can honour routing hints ──
        try:
            knowing_block = get_meaning_resolver().resolve(
                text,
                vault=vault,
                peer_id=pid,
                conversation_memory=memory,
            )
        except Exception as e:
            logger.debug("meaning_resolver failed: %s", e)
            knowing_block = None

        # Voice override: if the resolver detected "speak as the lover"
        # etc., swap the target voice before composing the prompt.
        if knowing_block is not None and knowing_block.voice_override:
            candidate = knowing_block.voice_override
            if candidate in engine.voices:
                voice_name = candidate

        # Chorus escalation: if the message asks for the full council,
        # promote this turn to the slow 7-voice respond_to_human path.
        # The caller (api_message) falls through to async chorus mode.
        if knowing_block is not None and knowing_block.trigger_chorus:
            try:
                utterance = engine.respond_to_human(
                    message=text, voice_name=voice_name,
                )
            except Exception as e:
                logger.debug("chorus escalation failed: %s", e)
                utterance = None
            if utterance is not None:
                # Persist the last chorus voice's reply as facts for memory.
                try:
                    resp = getattr(utterance, "response", None)
                    if resp is not None and resp.text:
                        memory.record(
                            pid,
                            getattr(utterance, "listener", "queen"),
                            resp.text,
                            meta={"via": "phone_bridge", "mode": "chorus"},
                            facts=knowing_block.to_fact_dict() if knowing_block else None,
                        )
                except Exception:
                    pass
                # Attach the knowing block to the chorus utterance so the
                # phone can render it the same way.
                try:
                    setattr(utterance, "_knowing_block", knowing_block.to_dict())
                except Exception:
                    pass
                return utterance

        name = voice_name if voice_name in engine.voices else "queen"
        if name not in engine.voices:
            name = next(iter(engine.voices.keys()))
        voice = engine.voices[name]

        # ── Queen action bridge: route intent → tools BEFORE the LLM ──
        action_bridge = get_queen_action_bridge()
        action_reply = action_bridge.handle_message(
            text,
            vault=vault,
            voice_name=name,
            coherence_report=None,  # pre-coherence pass; filter runs on the reply
        )

        def _action_summary_lines() -> list:
            if not action_reply.actions:
                return []
            lines = ["Just ran:"]
            for a in action_reply.actions[:4]:
                res = a.result or {}
                if isinstance(res, dict):
                    bits = []
                    for k in ("stdout", "message", "status", "text"):
                        v = res.get(k)
                        if v:
                            bits.append(f"{k}={str(v)[:100]}")
                    summary = " | ".join(bits) or "(no payload)"
                else:
                    summary = str(res)[:140]
                tag = "LIVE" if a.mode == "live" else "dry"
                ok = "ok" if a.ok else f"FAIL {a.error[:60]}"
                lines.append(f"  {tag} {a.tool}({a.params}) -> {ok}: {summary}")
            return lines

        # Pull recent conversation turns BEFORE overriding compose_prompt_lines.
        conv_block = memory.format_as_prompt_block(pid, n=6, max_chars_per_turn=220)
        has_memory = bool(conv_block)

        # The meaning resolver already ran at the top of the function so
        # we can honour voice_override and chorus triggers before the
        # voice was picked. Here we just reuse its output.
        # render_for_prompt() now prepends being_text + world_text (spirit
        # preamble) before the per-query fact block, so the Queen reads
        # her own state before grounded facts.
        knowing_text = ""
        _has_spirit = (
            knowing_block is not None
            and bool(knowing_block.being_text or knowing_block.world_text)
        )
        if knowing_block is not None and knowing_block.has_any():
            knowing_text = knowing_block.render_for_prompt(max_chars=1200)

        # Prompt assembly.
        # - First turn with this peer: full state preamble + meta-cog scaffold.
        # - Subsequent turns: state preamble is kept SHORT (voices still
        #   need their persona so they know who they are) + memory block +
        #   natural continuation instruction.
        original_max = getattr(voice, "max_tokens", 240)
        original_compose = voice._compose_prompt_lines

        def composed_with_memory(state):
            state_lines = original_compose(state)

            # On follow-up turns we trim the voice's own prompt to its
            # persona header + the most state-carrying lines, so the
            # small model doesn't spend all its tokens re-introducing
            # itself — memory already tells it who it is.
            if has_memory and len(state_lines) > 4:
                # Keep the first line (persona self-statement) and any
                # lines that look numeric (state values) so the Queen
                # still has current numbers to ground her reply in.
                kept = [state_lines[0]]
                for ln in state_lines[1:]:
                    if any(ch.isdigit() for ch in ln):
                        kept.append(ln)
                    if len(kept) >= 5:
                        break
                state_lines = kept

            lines = list(state_lines)
            lines.append("")

            if has_memory:
                lines.append(conv_block)
                lines.append("")

            lines.append(f'Human just said: "{text[:300]}"')

            if action_reply.actions:
                lines.extend(_action_summary_lines())

            # Put the grounded-knowledge block right before the final
            # instruction, so the small model reads it last and treats
            # it as the most recent context. If any facts were found,
            # add a directive that forces the model to use them.
            if knowing_text:
                lines.append("")
                lines.append(knowing_text)
                lines.append("")
                if knowing_block and knowing_block.math and knowing_block.math.ok:
                    lines.append(
                        f"The human asked an arithmetic question. The answer "
                        f"is {knowing_block.math.result}. State it directly."
                    )
                else:
                    if _has_spirit:
                        lines.append(
                            "Speak from your being and from the world as it is "
                            "right now. Weave the grounded knowledge into your "
                            "reply. Quote facts, don't invent new ones."
                        )
                    else:
                        lines.append(
                            "Weave the grounded knowledge above into your reply. "
                            "Quote the facts, don't invent new ones."
                        )

            if has_memory:
                lines.append(
                    "Continue naturally as yourself. Speak like you're "
                    "mid-conversation with someone you know. 1-2 sentences. "
                    "No self-introduction."
                )
            else:
                lines.append(
                    "Answer as yourself in 1-2 short sentences. No preamble, "
                    "no 'As an AI'. Speak like a person, not a report."
                )
            return lines

        statement = None

        # ── Direct-reply shortcut ──────────────────────────────────
        # If the resolver produced a confident, specific answer
        # (arithmetic is the main case today) it populates
        # ``knowing_block.direct_reply`` with a Queen-voiced sentence.
        # Small local models mangle such single-right-answer questions,
        # so we speak the direct reply as-is and skip the LLM entirely.
        if knowing_block is not None and knowing_block.direct_reply:
            try:
                from aureon.vault.voice.utterance import VoiceStatement
                fp = ""
                try:
                    fp = vault.fingerprint()
                except Exception:
                    pass
                statement = VoiceStatement(
                    voice=name,
                    text=knowing_block.direct_reply,
                    vault_fingerprint=fp,
                    prompt_used=f'direct_reply for: "{text[:200]}"',
                    system_prompt="",
                    model="meaning-resolver-direct",
                    tokens=0,
                )
            except Exception as e:
                logger.debug("direct_reply path failed: %s", e)
                statement = None

        if statement is None:
            try:
                voice.max_tokens = 128  # ~5-7s output on a warm qwen2.5:0.5b
                voice._compose_prompt_lines = composed_with_memory  # type: ignore[method-assign]
                statement = voice.speak(vault)
            except Exception as e:
                logger.debug("fast_human_reply LLM path failed: %s", e)
                statement = None
            finally:
                voice.max_tokens = original_max
                voice._compose_prompt_lines = original_compose  # type: ignore[method-assign]

        # Reject empty or error replies so we can fall through.
        def _is_bad(s) -> bool:
            if s is None:
                return True
            t = (getattr(s, "text", "") or "").strip()
            if not t:
                return True
            if t.startswith("[ERROR]") or "timed out" in t.lower():
                return True
            return False

        if _is_bad(statement):
            # Last-ditch backstop: template router. This is ONLY reached
            # if the real LLM died — we do not use it as a primary path
            # because it isn't real cognition.
            try:
                router = get_phi_swarm_router()
                original_adapter = voice.adapter
                try:
                    voice.adapter = router
                    voice._compose_prompt_lines = composed_with_memory  # type: ignore[method-assign]
                    statement = voice.speak(vault)
                finally:
                    voice.adapter = original_adapter
                    voice._compose_prompt_lines = original_compose  # type: ignore[method-assign]
            except Exception as e:
                logger.debug("fast_human_reply template backstop failed: %s", e)
                statement = None

        if statement is None or not getattr(statement, "text", "").strip():
            return None

        # Record the Queen's turn into conversation memory so the next
        # message from this peer will see it in the "Recent conversation"
        # block. This is what makes the voice sound like she's continuing
        # a thread instead of starting fresh every call.
        try:
            facts_to_persist = (
                knowing_block.to_fact_dict()
                if knowing_block is not None and knowing_block.has_any()
                else None
            )
            memory.record(
                pid,
                name,
                statement.text,
                meta={"via": "phone_bridge"},
                facts=facts_to_persist,
            )
        except Exception:
            pass

        # ── Auris coherence filter ──────────────────────────────────
        # Before we hand the reply to the vault / phone, pass it
        # through the Auris 9-node + Λ/Γ + harmonic-text filter. The
        # filter may trim the reply to its most aligned sentences if
        # it scores below the threshold, and always attaches a
        # coherence report the phone can display.
        coherence_report = None
        try:
            voice_filter = get_auris_voice_filter()
            coherence_report = voice_filter.filter(
                statement.text, vault, voice_name=name
            )
            if coherence_report.text != statement.text:
                # Replace the statement text with the filter's trimmed version.
                statement.text = coherence_report.text
        except Exception as e:
            logger.debug("AurisVoiceFilter skipped: %s", e)

        # Feed the reply back into the vault so the next sync surfaces it.
        try:
            vault.ingest(
                topic="vault.voice.utterance",
                payload={
                    "voice": name,
                    "text": statement.text,
                    "in_reply_to": text,
                    "mode": "fast",
                    "coherence": (
                        coherence_report.to_dict() if coherence_report else None
                    ),
                },
                category="vault_voice",
            )
        except Exception:
            pass

        # Also wire it into the voice engine's history so /api/bridge/sync
        # can surface it via _build_desktop_view.
        try:
            from aureon.vault.voice.utterance import Utterance

            u = Utterance(
                utterance_id=uuid.uuid4().hex[:8],
                timestamp=time.time(),
                speaker="human",
                listener=name,
                statement=None,
                response=statement,
                chosen=True,
                reasoning="fast_human_reply",
                urgency=1.0,
            )
            # Stash the coherence report on the Utterance as a private
            # attribute — the serialization wrapper picks it up and
            # merges it into the JSON payload the phone receives.
            if coherence_report is not None:
                try:
                    setattr(u, "_coherence_report", coherence_report.to_dict())
                except Exception:
                    pass
            # Same for the action log so the phone can render tool chips.
            if action_reply is not None and action_reply.actions:
                try:
                    setattr(u, "_action_reply", action_reply.to_dict())
                except Exception:
                    pass
            # And the knowing block so the phone can show what sources fired.
            if knowing_block is not None and knowing_block.has_any():
                try:
                    setattr(u, "_knowing_block", knowing_block.to_dict())
                except Exception:
                    pass
            engine._history.append(u)
            return u
        except Exception:
            return None

    def _utterance_to_payload(u) -> Dict[str, Any]:
        """
        Serialise an Utterance and merge the optional coherence + action
        + knowing-block reports the phone can render.
        """
        if u is None:
            return None
        d = u.to_dict()
        coh = getattr(u, "_coherence_report", None)
        if coh:
            d["coherence"] = coh
        actions = getattr(u, "_action_reply", None)
        if actions:
            d["actions"] = actions
        knowing = getattr(u, "_knowing_block", None)
        if knowing:
            d["knowing"] = knowing
        return d

    def _run_async_chorus(job_id: str, text: str, voice_name: Optional[str]):
        """Background worker for async chorus replies."""
        try:
            utterance = loop.voice_engine.respond_to_human(
                message=text, voice_name=voice_name,
            )
        except Exception as e:
            with pending_jobs_lock:
                pending_jobs[job_id] = {
                    "status": "error",
                    "error": str(e),
                    "finished_at": time.time(),
                }
            return
        with pending_jobs_lock:
            pending_jobs[job_id] = {
                "status": "done" if utterance is not None else "silent",
                "finished_at": time.time(),
                "utterance": _utterance_to_payload(utterance),
            }

    @app.route("/api/message", methods=["POST"])
    def api_message():
        """
        Human sends a message to the vault; a voice responds.

        Modes:
          - default: blocking full chorus (slow — only safe on LAN with
            a desktop browser that has infinite patience).
          - fast=true: single voice, reduced max_tokens, ~10-20s total.
            The phone uses this by default.
          - async=true: fire-and-forget. Returns 202 immediately with a
            job_id. The phone then either polls /api/message/{job_id}
            or just waits for last_utterance to appear in
            /api/bridge/sync. This is what prevents the phone's fetch
            from timing out on slow LLM runs.
        """
        if loop.voice_engine is None:
            return jsonify({"ok": False, "error": "voice engine disabled"}), 400

        data = request.get_json(silent=True) or {}
        text = str(data.get("text", "")).strip()
        voice_name = data.get("voice")
        fast = bool(data.get("fast", False))
        async_mode = bool(data.get("async", False))
        # Phone sends peer_id so conversation memory threads stay per-device.
        # Falls back to the remote IP if the phone forgets to send one.
        peer_id = str(data.get("peer_id") or request.remote_addr or "anon").strip() or "anon"

        if not text:
            return jsonify({"ok": False, "error": "missing text"}), 400

        # Fire-and-forget: return immediately, reply surfaces via sync.
        if async_mode:
            job_id = uuid.uuid4().hex[:10]
            with pending_jobs_lock:
                pending_jobs[job_id] = {"status": "pending", "started_at": time.time()}

            def _run():
                if fast:
                    try:
                        u = _fast_human_reply(text, voice_name, peer_id=peer_id)
                    except Exception as e:
                        with pending_jobs_lock:
                            pending_jobs[job_id] = {
                                "status": "error",
                                "error": str(e),
                                "finished_at": time.time(),
                            }
                        return
                    with pending_jobs_lock:
                        pending_jobs[job_id] = {
                            "status": "done" if u is not None else "silent",
                            "finished_at": time.time(),
                            "utterance": _utterance_to_payload(u),
                        }
                else:
                    _run_async_chorus(job_id, text, voice_name)

            threading.Thread(target=_run, daemon=True).start()
            return jsonify({"ok": True, "pending": True, "job_id": job_id}), 202

        # Synchronous fast path.
        if fast:
            try:
                utterance = _fast_human_reply(text, voice_name, peer_id=peer_id)
            except Exception as e:
                return jsonify({"ok": False, "error": str(e)}), 500
            if utterance is None:
                return jsonify({"ok": False, "error": "voice did not respond"}), 200
            return jsonify({"ok": True, "utterance": _utterance_to_payload(utterance)})

        # Synchronous full chorus (legacy path).
        try:
            utterance = loop.voice_engine.respond_to_human(
                message=text, voice_name=voice_name,
            )
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

        if utterance is None:
            return jsonify({"ok": False, "error": "voice did not respond"}), 200

        return jsonify({"ok": True, "utterance": utterance.to_dict()})

    @app.route("/api/message/<job_id>")
    def api_message_status(job_id: str):
        """Poll a pending async message job."""
        with pending_jobs_lock:
            job = pending_jobs.get(job_id)
        if job is None:
            return jsonify({"ok": False, "error": "unknown job_id"}), 404
        return jsonify({"ok": True, "job_id": job_id, **job})

    @app.route("/api/speak", methods=["POST"])
    def api_speak():
        """Force a specific voice to speak right now."""
        if loop.voice_engine is None:
            return jsonify({"ok": False, "error": "voice engine disabled"}), 400

        data = request.get_json(silent=True) or {}
        voice_name = data.get("voice")

        try:
            if voice_name:
                utterance = loop.voice_engine.speak_as(voice_name)
            else:
                utterance = loop.voice_engine.converse()
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

        if utterance is None:
            return jsonify({
                "ok": False,
                "error": "gate suppressed or voice not found",
            }), 200

        return jsonify({"ok": True, "utterance": utterance.to_dict()})

    @app.route("/api/converse", methods=["POST"])
    def api_converse():
        """Trigger one voice_engine.converse() call (respects the gate)."""
        if loop.voice_engine is None:
            return jsonify({"ok": False, "error": "voice engine disabled"}), 400
        try:
            utterance = loop.voice_engine.converse()
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

        if utterance is None:
            gate_status = loop.voice_engine.gate.get_status()
            return jsonify({
                "ok": True,
                "spoke": False,
                "gate": gate_status,
            })

        return jsonify({
            "ok": True,
            "spoke": True,
            "utterance": utterance.to_dict(),
        })

    @app.route("/api/tick", methods=["POST"])
    def api_tick():
        """Trigger one full loop.tick() (including voice, Casimir, Auris, ping)."""
        try:
            result = loop.tick()
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500
        return jsonify({"ok": True, "tick": result.to_dict()})

    # ─────────────────────────────────────────────────────────────────────
    # Loop control
    # ─────────────────────────────────────────────────────────────────────

    @app.route("/api/loop/start", methods=["POST"])
    def api_loop_start():
        try:
            loop.start()
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500
        return jsonify({"ok": True, "running": True})

    @app.route("/api/loop/stop", methods=["POST"])
    def api_loop_stop():
        try:
            loop.stop()
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500
        return jsonify({"ok": True, "running": False})

    # ─────────────────────────────────────────────────────────────────────
    # Phi-bridge — phone ↔ desktop intranet sync
    # ─────────────────────────────────────────────────────────────────────

    @app.route("/bridge")
    def bridge_page():
        bridge_path = os.path.join(STATIC_DIR, "bridge.html")
        if not os.path.exists(bridge_path):
            return ("<h1>Bridge UI missing</h1>", 200)
        resp = send_from_directory(STATIC_DIR, "bridge.html")
        # Force the phone to refetch the shell on every visit so a stale
        # service-worker cache can never pin an old version of the JS.
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp

    @app.route("/bridge-reset")
    def bridge_reset():
        """
        Nuclear reset for a phone stuck on a stale service-worker shell.
        Unregisters all SWs, clears all caches, then redirects to /bridge.
        """
        html = """<!doctype html><html><head><meta charset=utf-8>
<title>Aureon Bridge — Reset</title>
<meta name=viewport content="width=device-width, initial-scale=1">
<style>
  body{background:#0b0d16;color:#e6e8f2;font-family:system-ui,sans-serif;
       padding:40px 20px;text-align:center;}
  h1{background:linear-gradient(90deg,#ff9f43,#9b6bff);
     -webkit-background-clip:text;background-clip:text;color:transparent;}
  .log{font-family:monospace;font-size:12px;color:#7a81a5;
       background:#141726;padding:16px;border-radius:8px;
       text-align:left;max-width:480px;margin:20px auto;white-space:pre-wrap;}
</style></head><body>
<h1>Aureon Bridge · Reset</h1>
<p>Clearing stale service worker and caches…</p>
<div class=log id=log></div>
<script>
(async function(){
  const log=document.getElementById('log');
  const line=(s)=>{log.textContent+=s+'\\n';};
  try {
    if ('serviceWorker' in navigator) {
      const regs = await navigator.serviceWorker.getRegistrations();
      line('found '+regs.length+' service worker(s)');
      for (const r of regs) { await r.unregister(); line('unregistered '+r.scope); }
    }
    if (window.caches) {
      const keys = await caches.keys();
      line('found '+keys.length+' cache(s)');
      for (const k of keys) { await caches.delete(k); line('deleted '+k); }
    }
    try { localStorage.removeItem('aureon.log'); line('cleared local chat log'); } catch(e){}
    line('done — reloading the bridge');
    setTimeout(()=>{ window.location.href='/bridge?t='+Date.now(); }, 800);
  } catch (e) {
    line('error: '+e.message);
  }
})();
</script>
</body></html>"""
        from flask import Response
        return Response(html, mimetype="text/html", headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        })

    @app.route("/bridge-invite")
    def bridge_invite():
        """Desktop-side onboarding page: shows the LAN URL big + share button."""
        invite_path = os.path.join(STATIC_DIR, "bridge_invite.html")
        if not os.path.exists(invite_path):
            return ("<h1>Invite page missing</h1>", 200)
        return send_from_directory(STATIC_DIR, "bridge_invite.html")

    @app.route("/manifest.webmanifest")
    def bridge_manifest():
        manifest_path = os.path.join(STATIC_DIR, "manifest.webmanifest")
        if not os.path.exists(manifest_path):
            return jsonify({"ok": False, "error": "manifest missing"}), 404
        return send_from_directory(
            STATIC_DIR,
            "manifest.webmanifest",
            mimetype="application/manifest+json",
        )

    @app.route("/sw.js")
    def bridge_service_worker():
        """
        Served from the root so its scope covers /bridge.
        A service worker can only control pages at or below its own URL,
        which is why this route is here and not under /static/.
        """
        sw_path = os.path.join(STATIC_DIR, "sw.js")
        if not os.path.exists(sw_path):
            return ("// service worker missing", 404, {"Content-Type": "application/javascript"})
        return send_from_directory(
            STATIC_DIR,
            "sw.js",
            mimetype="application/javascript",
        )

    @app.route("/api/bridge/info")
    def api_bridge_info():
        try:
            return jsonify(bridge.info())
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/bridge/invite")
    def api_bridge_invite():
        """Return a loopback-only HOLD receipt without probing the network."""

        try:
            port = int(request.environ.get("SERVER_PORT", 5566))
        except (TypeError, ValueError):
            port = 5566
        if not 1 <= port <= 65535:
            port = 5566
        local_origin = f"http://127.0.0.1:{port}"
        return jsonify({
            "ok": True,
            "status": "HOLD",
            "reason_code": "production_magic_star_release_unavailable",
            "lan_ip": "",
            "phone_url": None,
            "desktop_url": f"{local_origin}/",
            "invite_url": f"{local_origin}/bridge-invite",
            "loopback_only": True,
        })

    @app.route("/api/bridge/state")
    def api_bridge_state():
        """Big snapshot that the phone substation can render."""
        try:
            status = loop.get_status()
        except Exception as e:
            status = {"error": str(e)}
        try:
            binfo = bridge.info()
        except Exception as e:
            binfo = {"error": str(e)}
        recent = []
        if loop.voice_engine is not None:
            try:
                recent = [u.to_dict() for u in loop.voice_engine.history[-5:]]
            except Exception:
                recent = []
        return jsonify({
            "ok": True,
            "server_time": time.time(),
            "loop": status,
            "bridge": binfo,
            "recent_utterances": recent,
        })

    @app.route("/api/bridge/peers")
    def api_bridge_peers():
        try:
            return jsonify({"ok": True, "peers": bridge.peers()})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/bridge/register", methods=["POST"])
    def api_bridge_register():
        data = request.get_json(silent=True) or {}
        try:
            peer = bridge.register_peer(
                label=str(data.get("label") or "peer"),
                kind=str(data.get("kind") or "phone"),
                user_agent=str(request.headers.get("User-Agent", ""))[:300],
                remote_addr=str(request.remote_addr or ""),
                peer_id=data.get("peer_id"),
            )
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500
        return jsonify({
            "ok": True,
            "peer": peer.to_dict(),
            "cadence": bridge.cadence(),
        })

    @app.route("/api/bridge/sync", methods=["POST"])
    def api_bridge_sync():
        data = request.get_json(silent=True) or {}
        peer_id = str(data.get("peer_id") or "").strip()
        if not peer_id:
            return jsonify({"ok": False, "error": "missing peer_id"}), 400
        try:
            result = bridge.exchange(
                peer_id,
                peer_state=data.get("state") or {},
                peer_fingerprint=str(data.get("fingerprint") or ""),
            )
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500
        return jsonify(result)

    @app.route("/api/bridge/drop", methods=["POST"])
    def api_bridge_drop():
        data = request.get_json(silent=True) or {}
        peer_id = str(data.get("peer_id") or "").strip()
        if not peer_id:
            return jsonify({"ok": False, "error": "missing peer_id"}), 400
        dropped = bridge.drop_peer(peer_id)
        return jsonify({"ok": True, "dropped": dropped})

    # ─────────────────────────────────────────────────────────────────────
    # Phi-bridge mesh — P2P card-level gossip
    # ─────────────────────────────────────────────────────────────────────
    #
    # Peers discovered over the LAN (PhiBridgeDiscovery) POST here to
    # exchange VaultContent cards. PhiBridgeMesh.handle_inbound consumes
    # their batch (deduped by harmonic_hash), and returns the cards we
    # have that they haven't listed in `our_hashes`. Eventually consistent
    # union — any two nodes converge by replaying each other's history.

    mesh = PhiBridgeMesh(vault=loop.vault, discovery=None)
    app.config["AUREON_PHI_BRIDGE_MESH"] = mesh
    app.config["AUREON_PHI_BRIDGE_DISCOVERY"] = None

    @app.route("/api/bridge/cards", methods=["POST"])
    def api_bridge_cards():
        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return jsonify({"ok": False, "error": "body must be a JSON object"}), 400
        try:
            reply = mesh.handle_inbound(data)
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500
        return jsonify(reply)

    @app.route("/api/bridge/mesh/info")
    def api_bridge_mesh_info():
        try:
            return jsonify({"ok": True, **mesh.info()})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    # ─────────────────────────────────────────────────────────────────────
    # Queen action bridge — tools, skills, arming, action log
    # ─────────────────────────────────────────────────────────────────────

    @app.route("/api/queen/status")
    def api_queen_status():
        try:
            br = get_queen_action_bridge()
            return jsonify({"ok": True, **br.status()})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/queen/tools")
    def api_queen_tools():
        try:
            br = get_queen_action_bridge()
            return jsonify({"ok": True, "tools": br.list_tools()})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/queen/skills")
    def api_queen_skills():
        try:
            br = get_queen_action_bridge()
            return jsonify({"ok": True, "skills": br.list_skills()})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/queen/actions")
    def api_queen_actions():
        try:
            br = get_queen_action_bridge()
            n = request.args.get("n", default=32, type=int)
            return jsonify({"ok": True, "actions": br.recent_actions(n)})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/queen/arm", methods=["POST"])
    def api_queen_arm():
        try:
            data = request.get_json(silent=True) or {}
            live = bool(data.get("live", False))
            br = get_queen_action_bridge()
            return jsonify({"ok": True, **br.arm(live=live)})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/queen/memory")
    def api_queen_memory():
        """Inspect conversation memory — per-peer turn counts + last seen."""
        try:
            mem = get_conversation_memory()
            peer_id = request.args.get("peer_id")
            if peer_id:
                turns = mem.recent(peer_id, n=request.args.get("n", default=20, type=int))
                return jsonify({
                    "ok": True,
                    "peer_id": peer_id,
                    "turns": [t.to_dict() for t in turns],
                })
            return jsonify({"ok": True, **mem.summary()})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/queen/memory/clear", methods=["POST"])
    def api_queen_memory_clear():
        """Wipe a peer's thread (or all threads)."""
        try:
            data = request.get_json(silent=True) or {}
            mem = get_conversation_memory()
            peer_id = data.get("peer_id")
            if peer_id:
                dropped = mem.clear(peer_id)
                return jsonify({"ok": True, "dropped": dropped, "peer_id": peer_id})
            mem.clear_all()
            return jsonify({"ok": True, "dropped_all": True})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/queen/execute", methods=["POST"])
    def api_queen_execute():
        """Direct-execute a tool by name. Dev/debug path — respects arm state."""
        try:
            data = request.get_json(silent=True) or {}
            tool = str(data.get("tool") or "").strip()
            params = data.get("params") or {}
            if not tool:
                return jsonify({"ok": False, "error": "missing tool"}), 400
            br = get_queen_action_bridge()
            # Route through handle_message via a synthetic LLM tool_call so
            # the same safety gates apply.
            class _Call:
                def __init__(self, n, a):
                    self.name = n
                    self.arguments = a
            class _Resp:
                def __init__(self, c):
                    self.tool_calls = c
            reply = br.handle_message(
                f"execute {tool}",
                llm_response=_Resp([_Call(tool, params)]),
            )
            return jsonify({"ok": True, "reply": reply.to_dict()})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    # ─────────────────────────────────────────────────────────────────────
    # Health
    # ─────────────────────────────────────────────────────────────────────

    @app.route("/api/health")
    def api_health():
        return jsonify({
            "ok": True,
            "service": "aureon_vault_ui",
            "loop_id": loop.loop_id,
            "cycles": loop._cycle,
            "voice_enabled": loop.voice_engine is not None,
            "timestamp": time.time(),
        })

    # ─────────────────────────────────────────────────────────────────────
    # Mesh — UDP discovery + φ²-cadenced card gossip
    # ─────────────────────────────────────────────────────────────────────

    _ = mesh_port
    _ = mesh_label
    _ = mesh_kind
    app.config["AUREON_PHI_BRIDGE_MESH_RUNTIME"] = {
        "status": "HOLD",
        "udp_discovery_started": False,
        "card_gossip_started": False,
        "reason_code": "production_magic_star_release_unavailable",
        "production_ready": False,
    }

    @app.route("/api/bridge/discovery/peers")
    def api_bridge_discovery_peers():
        return jsonify({
            "ok": True,
            "running": False,
            "status": "HOLD",
            "reason_code": "production_magic_star_release_unavailable",
            "peers": [],
        })

    return app


# ─────────────────────────────────────────────────────────────────────────────
# Runner
# ─────────────────────────────────────────────────────────────────────────────


def run_server(
    host: str = "127.0.0.1",
    port: int = 5566,
    loop: Optional[AureonSelfFeedbackLoop] = None,
    start_loop: bool = False,
    debug: bool = False,
    base_interval_s: float = 1.0,
) -> None:
    """Run the local HOLD-only server after an exact fail-closed preflight."""

    preflight = vault_ui_security_preflight(host=host, debug=debug)
    if preflight["status"] != "READY_LOCAL_HOLD":
        codes = ",".join(preflight["denial_codes"])
        raise RuntimeError(f"vault_ui_security_preflight_failed:{codes}")
    if start_loop:
        raise RuntimeError(
            "vault_ui_loop_start_hold:production_magic_star_release_unavailable"
        )
    if loop is not None:
        raise RuntimeError(
            "vault_ui_supplied_feedback_loop_forbidden:factory_owned_inert_loop_required"
        )
    app = create_app(loop=loop, base_interval_s=base_interval_s)
    logger.info("Aureon Vault UI listening on http://%s:%d/", host, port)
    app.run(host="127.0.0.1", port=port, debug=False, load_dotenv=False)
