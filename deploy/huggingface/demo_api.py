"""Bounded, loopback-only HTTP API for the public Aureon/HNC demo.

The service has no authentication or trading authority.  A public reverse proxy
should expose only the explicit routes below; the default listener is not a
public interface.  Prompts and completions are never logged by this module.
"""

from __future__ import annotations

import argparse
import http.client
import ipaddress
import json
import math
import os
import re
import threading
import time
from collections import OrderedDict
from collections.abc import Callable, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8792
PROVIDER_MODE = "aureon_own_model"
MODEL = "aureon-7b-v65k"
MODEL_BASE_URL = "http://127.0.0.1:11435/v1"
MODEL_READY_URL = "http://127.0.0.1:11435/readyz"
OPERATOR_READY_URL = "http://127.0.0.1:8790/readyz"
WEIGHT_SHA256 = "48487f800623474ab99371d71b369694cae64f8ebc4ef038019c7e60da3d45bb"
MAX_BODY_BYTES = 16 * 1024
MAX_PROMPT_CHARS = 4096
MAX_READY_BYTES = 64 * 1024
BRAIN_RECORD = "huggingface/hnc-field/replay/brain.json"
ORGANISM_RECORD = "huggingface/organism-replay/replay/organism.json"
PUBLIC_COMMIT = "ac9fa3151b63bd4143dc1aa434ec79b382406b7e"

PUBLIC_ENV = {
    "AUREON_PUBLIC_READ_ONLY": "1",
    "AUREON_LIVE_TRADING": "0",
    "AUREON_FUSION_ARM_LIVE": "",
    "AUREON_DISABLE_REAL_ORDERS": "1",
    "AUREON_DISABLE_EXCHANGE_MUTATIONS": "1",
    "AUREON_ORDER_INTENT_PUBLISH": "0",
    "AUREON_AUTONOMY_MODE": "guarded",
    "AUREON_DEPLOYMENT_HOLD": "1",
    "AUREON_OPERATOR_ALLOW_LIVE": "",
    "AUREON_LOCAL_ACTIONS_ARMED": "0",
    "AUREON_UNIFIED_ORDER_EXECUTOR": "0",
    "AUREON_DRY_RUN": "1",
    "DRY_RUN": "1",
    "AUREON_CODE_AUTO_APPROVE": "0",
    "AUREON_SOUL_ACT": "0",
    "AUREON_BILLING_CHARGE_ENABLED": "0",
    "AUREON_SOVEREIGN_MODE": "0",
    "AUREON_ACCEPT_LIVE_RISK": "0",
    "AUREON_ENABLE_AUTONOMOUS_CONTROL": "0",
    "AUREON_EXTERNAL_LLM_FALLBACK": "none",
    "AUREON_MODEL_REPOSITORY": "GaryLeckey/aureon-7b",
    "AUREON_MODEL_EXPECTED_SHA256": WEIGHT_SHA256,
    "AUREON_OWN_LLM_BASE_URL": MODEL_BASE_URL,
    "AUREON_OWN_LLM_MODEL": MODEL,
}
SENSITIVE_ENV = (
    "KRAKEN_API_KEY", "KRAKEN_API_SECRET", "KRAKEN_PRIVATE_KEY", "KRAKEN_SECRET",
    "BINANCE_API_KEY", "BINANCE_API_SECRET", "BINANCE_SECRET_KEY", "BINANCE_KEY", "BINANCE_SECRET",
    "ALPACA_API_KEY", "ALPACA_SECRET_KEY", "ALPACA_API_SECRET", "ALPACA_KEY", "ALPACA_SECRET",
    "APCA_API_KEY_ID", "APCA_API_SECRET_KEY",
    "CAPITAL_API_KEY", "CAPITAL_IDENTIFIER", "CAPITAL_PASSWORD", "CAPITAL_EMAIL", "CAPITAL_USER",
    "CAPITAL_API_PASSWORD", "CAPITAL_API_SECRET",
    "COINBASE_API_KEY", "COINBASE_API_SECRET", "COINAPI_API_KEY", "COINAPI_KEY",
    "COINGECKO_API_KEY", "FRED_API_KEY", "FMP_API_KEY", "NASA_API_KEY",
    "FIRMS_MAP_KEY", "NOAA_API_KEY", "USGS_API_KEY", "ETHERSCAN_API_KEY",
    "ALCHEMY_API_KEY", "COVALENT_API_KEY", "GLASSNODE_API_KEY",
    "UNUSUAL_WHALES_API_KEY", "WORLD_NEWS_API_KEY", "OPENAI_API_KEY",
    "XAI_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY",
    "DEEPSEEK_API_KEY", "MISTRAL_API_KEY", "GROQ_API_KEY",
    "OPENROUTER_API_KEY", "PERPLEXITY_API_KEY", "OLLAMA_API_KEY",
    "AUREON_OLLAMA_API_KEY", "AUREON_LLM_API_KEY", "AUREON_OWN_LLM_API_KEY",
    "QUICKBOOKS_CLIENT_ID", "QUICKBOOKS_CLIENT_SECRET", "QUICKBOOKS_AUTH_CODE",
    "QUICKBOOKS_RETURNED_STATE", "QUICKBOOKS_EXPECTED_STATE", "QUICKBOOKS_REALM_ID",
    "QUICKBOOKS_CLIENT_CREDENTIAL_VAULT", "QUICKBOOKS_TOKEN_VAULT",
    "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "MASTER_ENCRYPTION_KEY", "AUREON_MASTER_ENCRYPTION_KEY",
    "AUREON_ACCOUNTING_APPROVAL_HMAC_KEY", "AUREON_INGEST_TOKEN", "INGEST_TOKEN",
    "AUREON_HNC_PACKET_MASTER_KEY", "AUREON_HNC_PACKET_LEGACY_MASTER_KEY",
    "AUREON_SUPABASE_JWT_SECRET", "SUPABASE_SERVICE_ROLE_KEY",
    "HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "AUREON_OPERATOR_API_KEY",
    "AUREON_FUSION_API_TOKEN",
)

_ROUTES = {
    "/healthz": {"GET", "HEAD"},
    "/readyz": {"GET", "HEAD"},
    "/api/demo/generate": {"POST"},
    "/api/demo/status": {"GET", "HEAD"},
    "/api/hnc/status": {"GET", "HEAD"},
    "/api/hnc/replay": {"GET", "HEAD"},
    "/api/hnc/organism-replay": {"GET", "HEAD"},
    "/hnc": {"GET", "HEAD"},
    "/hnc/": {"GET", "HEAD"},
}


@dataclass(frozen=True)
class Response:
    """One complete, non-streaming HTTP response."""

    status: int
    payload: dict[str, Any] | str
    content_type: str = "application/json; charset=utf-8"
    headers: Mapping[str, str] = field(default_factory=dict)


def _json_response(
    status: int,
    payload: dict[str, Any],
    headers: Mapping[str, str] | None = None,
) -> Response:
    return Response(status, payload, headers=headers or {})


def _error(status: int, code: str, message: str) -> Response:
    return _json_response(status, {"ok": False, "error": {"code": code, "message": message}})


def _finite_setting(env: Mapping[str, str], name: str, default: float, low: float, high: float) -> float:
    try:
        value = float(env.get(name, str(default)))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{name} must be between {low} and {high}")
    return value


def _int_setting(env: Mapping[str, str], name: str, default: int, low: int, high: int) -> int:
    raw = env.get(name, str(default))
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if str(raw).strip() != str(value) or not low <= value <= high:
        raise ValueError(f"{name} must be an integer between {low} and {high}")
    return value


def public_posture(env: Mapping[str, str]) -> dict[str, Any]:
    """Return only pass/fail checks for the required public environment."""

    checks = {name: env.get(name, "") == expected for name, expected in PUBLIC_ENV.items()}
    checks["credentials_absent"] = all(not env.get(name) for name in SENSITIVE_ENV)
    return {"ok": all(checks.values()), "checks": checks}


def probe_ready(url: str, timeout: float) -> dict[str, Any]:
    """Fetch one bounded loopback readiness document without following redirects."""

    try:
        parsed = urlsplit(url)
        address = ipaddress.ip_address(str(parsed.hostname or ""))
        if (
            parsed.scheme != "http"
            or not address.is_loopback
            or parsed.port is None
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("loopback readiness URL required")
        connection = http.client.HTTPConnection(address.compressed, parsed.port, timeout=timeout)
        try:
            connection.request("GET", parsed.path or "/readyz", headers={"Accept": "application/json"})
            upstream = connection.getresponse()
            raw = upstream.read(MAX_READY_BYTES + 1)
            result: dict[str, Any] = {"http_status": upstream.status, "payload": None, "error": None}
            if upstream.status != 200:
                result["error"] = "http_status"
                return result
            if len(raw) > MAX_READY_BYTES:
                result["error"] = "response_too_large"
                return result
            try:
                payload = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                result["error"] = "invalid_json"
                return result
            if not isinstance(payload, dict):
                result["error"] = "invalid_payload"
                return result
            result["payload"] = payload
            return result
        finally:
            connection.close()
    except Exception as exc:  # Network and parser failures are data, not tracebacks.
        return {"http_status": None, "payload": None, "error": type(exc).__name__}


class TokenBucket:
    """Thread-safe process-local token buckets with an injectable clock."""

    def __init__(
        self,
        rate_per_minute: float = 6.0,
        burst: int = 2,
        *,
        clock: Callable[[], float] = time.monotonic,
        max_clients: int = 4096,
    ) -> None:
        if not math.isfinite(rate_per_minute) or rate_per_minute <= 0 or burst < 1 or max_clients < 1:
            raise ValueError("invalid token bucket configuration")
        self.rate_per_second = rate_per_minute / 60.0
        self.burst = burst
        self.clock = clock
        self.max_clients = max_clients
        self._clients: OrderedDict[str, tuple[float, float]] = OrderedDict()
        self._lock = threading.Lock()

    def allow(self, client: str) -> tuple[bool, int]:
        now = float(self.clock())
        if not math.isfinite(now):
            now = 0.0
        with self._lock:
            tokens, updated = self._clients.get(client, (float(self.burst), now))
            elapsed = max(0.0, now - updated)
            tokens = min(float(self.burst), tokens + elapsed * self.rate_per_second)
            self._clients.pop(client, None)
            self._clients[client] = (tokens, now)
            while len(self._clients) > self.max_clients:
                self._clients.popitem(last=False)
            if tokens >= 1.0:
                self._clients[client] = (tokens - 1.0, now)
                return True, 0
            retry_after = max(1, math.ceil((1.0 - tokens) / self.rate_per_second))
            return False, retry_after


class GenerationTimeout(RuntimeError):
    pass


class GenerationBusy(RuntimeError):
    pass


class AdapterGateway:
    """Run the real own-model adapter with bounded concurrency and waiting."""

    def __init__(self, adapter_factory: Callable[[], Any], timeout: float, max_workers: int = 1) -> None:
        self.adapter_factory = adapter_factory
        self.timeout = timeout
        self._slots = threading.BoundedSemaphore(max_workers)

    def prompt(self, prompt: str, max_tokens: int) -> Any:
        if not self._slots.acquire(blocking=False):
            raise GenerationBusy("generation capacity is bounded")
        finished = threading.Event()
        result: dict[str, Any] = {}

        def call() -> None:
            try:
                adapter = self.adapter_factory()
                result["response"] = adapter.prompt(
                    [{"role": "user", "content": prompt}],
                    tools=None,
                    max_tokens=max_tokens,
                    temperature=0.0,
                )
            except Exception as exc:  # The HTTP boundary intentionally hides adapter details.
                result["exception"] = exc
            finally:
                finished.set()
                self._slots.release()

        threading.Thread(target=call, name="aureon-demo-generate", daemon=True).start()
        if not finished.wait(self.timeout):
            raise GenerationTimeout("own-model generation exceeded its deadline")
        if "exception" in result:
            raise RuntimeError("own-model adapter failed") from result["exception"]
        return result["response"]


def _default_adapter_factory() -> Any:
    from aureon.inhouse_ai.llm_adapter import _aureon_own_adapter

    return _aureon_own_adapter()


def _normalized(value: Any) -> Any:
    """Apply the same JSON number normalization used by the existing HNC app."""

    return json.loads(json.dumps(value, allow_nan=False))


def _without_private_paths(value: Any) -> Any:
    """Remove local path and credential-shaped fields from an HNC status tree."""

    if isinstance(value, dict):
        cleaned = {}
        for raw_key, item in value.items():
            key = str(raw_key)
            lowered = key.lower()
            if (
                lowered == "path"
                or lowered.endswith("_path")
                or lowered.endswith("_paths")
                or lowered == "memory_db"
                or any(part in lowered for part in ("secret", "password", "credential", "api_key", "token"))
            ):
                continue
            cleaned[key] = _without_private_paths(item)
        return cleaned
    if isinstance(value, (list, tuple)):
        return [_without_private_paths(item) for item in value]
    return value


@contextmanager
def _preserve_hnc_import_env():
    names = ("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "AUREON_AUDIT_MODE", "AUREON_HNC_PERSIST_EVERY")
    missing = object()
    previous = {name: os.environ.get(name, missing) for name in names}
    try:
        yield
    finally:
        for name, value in previous.items():
            if value is missing:
                os.environ.pop(name, None)
            else:
                os.environ[name] = str(value)


def _default_hnc_status() -> dict[str, Any]:
    """Read organ and canonical state independently; absence is not success."""

    with _preserve_hnc_import_env():
        from aureon_fusion import hnc_core

    try:
        organ = _without_private_paths(hnc_core.status())
        organ["available"] = True
    except Exception as exc:
        organ = {"available": False, "error": type(exc).__name__}
    try:
        running, reason = hnc_core.organ_running()
        running_body = {"available": True, "running": bool(running), "reason": str(reason)}
    except Exception as exc:
        running_body = {"available": False, "running": False, "error": type(exc).__name__}
    try:
        from aureon.core.hnc_field import read_canonical_field

        canonical = _without_private_paths(read_canonical_field().to_dict())
    except Exception as exc:
        canonical = {"available": False, "error": type(exc).__name__}
    return {"organ": organ, "organ_running": running_body, "canonical_field": canonical}


class DemoApplication:
    """Framework-free application, separated from its HTTP transport for tests."""

    def __init__(
        self,
        *,
        env: Mapping[str, str] | None = None,
        repo_root: Path | None = None,
        adapter_factory: Callable[[], Any] | None = None,
        readiness_probe: Callable[[str, float], dict[str, Any]] = probe_ready,
        hnc_status_provider: Callable[[], dict[str, Any]] = _default_hnc_status,
        field_factory: Callable[..., Any] | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.env = os.environ if env is None else env
        self.repo_root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[2]
        self.brain_path = self.repo_root / BRAIN_RECORD
        self.organism_path = self.repo_root / ORGANISM_RECORD
        self.readiness_probe = readiness_probe
        self.hnc_status_provider = hnc_status_provider
        self.field_factory = field_factory
        self.ready_timeout = _finite_setting(env=self.env, name="AUREON_DEMO_READY_TIMEOUT_S", default=0.5, low=0.05, high=2.0)
        generate_timeout = _finite_setting(
            self.env, "AUREON_DEMO_GENERATE_TIMEOUT_S", 120.0, 0.1, 120.0
        )
        self.gateway = AdapterGateway(adapter_factory or _default_adapter_factory, generate_timeout)
        rate = _finite_setting(self.env, "AUREON_DEMO_RATE_PER_MINUTE", 6.0, 0.1, 600.0)
        burst = _int_setting(self.env, "AUREON_DEMO_RATE_BURST", 2, 1, 64)
        self.rate_limit = TokenBucket(rate, burst, clock=clock)

    def health(self) -> Response:
        return _json_response(
            200,
            {"ok": True, "live_trading": False, "orders_placed": 0, "provider_mode": PROVIDER_MODE},
        )

    def _ready_probe(self, url: str) -> dict[str, Any]:
        try:
            result = self.readiness_probe(url, self.ready_timeout)
            if not isinstance(result, dict):
                raise TypeError("readiness probe must return an object")
            return result
        except Exception as exc:
            return {"http_status": None, "payload": None, "error": type(exc).__name__}

    def readiness(self) -> Response:
        posture = public_posture(self.env)
        operator_result = self._ready_probe(OPERATOR_READY_URL)
        model_result = self._ready_probe(MODEL_READY_URL)
        operator_payload = operator_result.get("payload")
        model_payload = model_result.get("payload")
        operator_payload = operator_payload if isinstance(operator_payload, dict) else {}
        model_payload = model_payload if isinstance(model_payload, dict) else {}
        operator_ready = operator_payload.get("ready") is True
        expected_revision = str(self.env.get("AUREON_MODEL_REVISION", ""))
        startup = model_payload.get("startup_generation")
        startup = startup if isinstance(startup, dict) else {}
        startup_tokens = startup.get("generated_tokens")
        model_checks = {
            "ready": model_payload.get("ready") is True,
            "provider_mode": model_payload.get("provider_mode") == PROVIDER_MODE,
            "model": model_payload.get("model") == MODEL,
            "immutable_revision": (
                re.fullmatch(r"[0-9a-f]{40}", expected_revision) is not None
                and model_payload.get("model_revision") == expected_revision
            ),
            "weight_sha256": model_payload.get("weight_sha256") == WEIGHT_SHA256,
            "weight_size_bytes": model_payload.get("weight_size_bytes") == 13_990_806_664,
            "parameters": model_payload.get("params") == 6_995_383_808,
            "vocabulary": model_payload.get("vocab_size") == 65_536,
            "eos": model_payload.get("eos_id") == 1,
            "cuda": model_payload.get("device") == "cuda",
            "startup_generation_verified": model_payload.get("startup_generation_verified") is True,
            "startup_generation_tokens": (
                isinstance(startup_tokens, int)
                and not isinstance(startup_tokens, bool)
                and 1 <= startup_tokens <= 16
            ),
        }
        operator_ok = (
            operator_result.get("error") is None
            and operator_result.get("http_status") == 200
            and operator_ready
        )
        model_ok = (
            model_result.get("error") is None
            and model_result.get("http_status") == 200
            and all(model_checks.values())
        )
        ready = posture["ok"] and operator_ok and model_ok
        body = {
            "ok": ready,
            "ready": ready,
            "live_trading": False,
            "orders_placed": 0,
            "provider_mode": PROVIDER_MODE,
            "model": MODEL,
            "checks": {
                "public_posture": posture,
                "operator": {
                    "ok": operator_ok,
                    "ready": operator_ready,
                    "http_status": operator_result.get("http_status"),
                    "error": operator_result.get("error"),
                },
                "model": {
                    "ok": model_ok,
                    "http_status": model_result.get("http_status"),
                    "error": model_result.get("error"),
                    "checks": model_checks,
                },
            },
        }
        return _json_response(200 if ready else 503, body)

    def demo_status(self) -> Response:
        return _json_response(
            200,
            {
                "ok": True,
                "provider_mode": PROVIDER_MODE,
                "model": MODEL,
                "route": {
                    "base_url": MODEL_BASE_URL,
                    "generate": MODEL_BASE_URL + "/chat/completions",
                    "readyz": MODEL_READY_URL,
                },
                "weight_sha256": WEIGHT_SHA256,
                "external_providers": False,
                "tools": False,
                "streaming": False,
                "live_trading": False,
                "orders_placed": False,
                "public_posture": public_posture(self.env),
            },
        )

    @staticmethod
    def _parse_generate(raw: bytes, content_type: str) -> tuple[str, int]:
        media_type = content_type.split(";", 1)[0].strip().lower()
        if media_type != "application/json":
            raise ValueError("content_type")
        if len(raw) > MAX_BODY_BYTES:
            raise OverflowError("body_too_large")
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("invalid_json") from exc
        if not isinstance(payload, dict) or set(payload) - {"prompt", "max_tokens"}:
            raise ValueError("json_object")
        prompt = payload.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > MAX_PROMPT_CHARS:
            raise ValueError("prompt")
        max_tokens = payload.get("max_tokens", 32)
        if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or not 1 <= max_tokens <= 64:
            raise ValueError("max_tokens")
        return prompt, max_tokens

    @staticmethod
    def _completion(response: Any) -> dict[str, Any]:
        if getattr(response, "stop_reason", "error") == "error":
            raise RuntimeError("adapter_error")
        raw = getattr(response, "raw", None)
        if not isinstance(raw, dict):
            raise RuntimeError("identity_mismatch")
        choices = raw.get("choices")
        choice = choices[0] if isinstance(choices, list) and len(choices) == 1 else None
        message = choice.get("message") if isinstance(choice, dict) else None
        text = message.get("content") if isinstance(message, dict) else None
        gears = raw.get("hnc_gears")
        if (
            getattr(response, "model", None) != MODEL
            or raw.get("provider_mode") != PROVIDER_MODE
            or raw.get("model") != MODEL
            or not isinstance(text, str)
            or not isinstance(gears, dict)
        ):
            raise RuntimeError("identity_mismatch")
        usage = raw.get("usage", getattr(response, "usage", {}))
        if not isinstance(usage, dict):
            raise RuntimeError("identity_mismatch")
        # Verify the selected fields before any of them reaches a JSON encoder.
        _normalized({"usage": usage, "hnc_gears": gears, "stop_reason": response.stop_reason})
        return {
            "provider_mode": PROVIDER_MODE,
            "model": MODEL,
            "text": text,
            "stop_reason": response.stop_reason,
            "usage": usage,
            "hnc_gears": gears,
            "live_trading": False,
            "orders_placed": False,
        }

    def generate(self, raw: bytes, *, content_type: str, client: str) -> Response:
        allowed, retry_after = self.rate_limit.allow(client)
        if not allowed:
            return _json_response(
                429,
                {"ok": False, "error": {"code": "rate_limited", "message": "Try again later."}, "retry_after": retry_after},
                {"Retry-After": str(retry_after)},
            )
        try:
            prompt, max_tokens = self._parse_generate(raw, content_type)
        except OverflowError:
            return _error(413, "body_too_large", "JSON body must be at most 16 KiB.")
        except ValueError as exc:
            code = str(exc)
            if code == "content_type":
                return _error(415, "content_type", "Content-Type must be application/json.")
            messages = {
                "invalid_json": "Body must be valid UTF-8 JSON.",
                "json_object": "Body must be an object containing only prompt and max_tokens.",
                "prompt": "prompt must be a nonempty string of at most 4096 characters.",
                "max_tokens": "max_tokens must be an integer from 1 through 64.",
            }
            return _error(400, code, messages.get(code, "Invalid generation request."))
        try:
            response = self.gateway.prompt(prompt, max_tokens)
            return _json_response(200, self._completion(response))
        except GenerationTimeout:
            return _error(503, "generation_timeout", "Aureon's own model exceeded the generation deadline.")
        except GenerationBusy:
            return _error(503, "generation_busy", "Aureon's own model is at its bounded concurrency limit.")
        except RuntimeError as exc:
            if str(exc) == "identity_mismatch":
                return _error(503, "identity_mismatch", "The own-model response identity or shape was invalid.")
            return _error(503, "own_model_unavailable", "Aureon's own model is unavailable; no fallback was used.")
        except (TypeError, ValueError):
            return _error(503, "invalid_model_response", "The own-model response contained invalid public data.")

    def hnc_status(self) -> Response:
        try:
            status = self.hnc_status_provider()
            if not isinstance(status, dict):
                raise TypeError("HNC status must be an object")
            status = _without_private_paths(status)
            _normalized(status)
        except Exception as exc:
            status = {
                "organ": {"available": False, "error": type(exc).__name__},
                "organ_running": {"available": False, "running": False},
                "canonical_field": {"available": False},
            }
        return _json_response(
            200,
            {**status, "live_trading": False, "orders_placed": False, "provider_mode": PROVIDER_MODE},
        )

    @staticmethod
    def _measure_field(factory: Callable[..., Any], steps: int, multiverse: bool) -> dict[str, Any]:
        instance = factory() if multiverse else factory(enable_multiverse=False)
        series = [float(instance.step()) for _ in range(steps)]
        return {
            "enable_multiverse": bool(instance.enable_multiverse),
            "coherence": float(instance.coherence),
            "lambda_last": series[-1],
            "series": series,
            "state": instance.state.value,
            "state_name": instance.state.name,
        }

    @staticmethod
    def _replay_path(fresh: dict[str, Any], committed: Any, multiverse: bool) -> dict[str, Any]:
        committed = committed if isinstance(committed, dict) else {}
        checks: dict[str, bool] = {}
        for name in ("series", "coherence", "lambda_last", "state"):
            try:
                checks[name] = _normalized(fresh[name]) == committed.get(name)
            except (TypeError, ValueError):
                checks[name] = False
        checks["enable_multiverse"] = fresh["enable_multiverse"] is multiverse
        return {**fresh, "match": all(checks.values()), "checks": checks}

    def hnc_replay(self) -> Response:
        record_source = {"label": "cited", "path": BRAIN_RECORD, "commit": PUBLIC_COMMIT}
        try:
            loaded = json.loads(self.brain_path.read_text(encoding="utf-8"))
            if not isinstance(loaded, dict) or not isinstance(loaded.get("hnc"), dict):
                raise ValueError("committed HNC record is missing")
            hnc = loaded["hnc"]
            steps = hnc.get("steps")
            if isinstance(steps, bool) or not isinstance(steps, int) or not 1 <= steps <= 10000:
                raise ValueError("committed HNC steps are invalid")
        except FileNotFoundError:
            return _json_response(
                200,
                {"ok": False, "available": False, "status": "missing", "match": False, "record": record_source},
            )
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            return _json_response(
                200,
                {
                    "ok": False,
                    "available": False,
                    "status": "invalid",
                    "match": False,
                    "record": record_source,
                    "error": type(exc).__name__,
                },
            )
        if self.field_factory is None:
            from aureon.harmonic.aureon_harmonic_reality import HarmonicRealityField

            factory = HarmonicRealityField
        else:
            factory = self.field_factory
        reruns: dict[str, Any] = {}
        for name, enabled in (("multiverse_off", False), ("multiverse_on", True)):
            try:
                fresh = self._measure_field(factory, steps, enabled)
                committed = hnc.get("multiverse_extension") if enabled else hnc
                reruns[name] = self._replay_path(fresh, committed, enabled)
            except Exception as exc:
                reruns[name] = {"available": False, "match": False, "error": type(exc).__name__}
        matched = all(item.get("match") is True for item in reruns.values())
        return _json_response(
            200,
            {
                "ok": matched,
                "available": True,
                "status": "match" if matched else "mismatch",
                "match": matched,
                "steps": steps,
                "record": {**record_source, "hnc": hnc},
                "rerun": {
                    "label": "inferred",
                    "source": "aureon.harmonic.aureon_harmonic_reality.HarmonicRealityField.step",
                    **reruns,
                },
                "live_trading": False,
                "orders_placed": False,
            },
        )

    def organism_replay(self) -> Response:
        source = {"label": "cited", "path": ORGANISM_RECORD, "commit": PUBLIC_COMMIT}
        try:
            record = json.loads(self.organism_path.read_text(encoding="utf-8"))
            if not isinstance(record, dict):
                raise ValueError("organism record must be an object")
            _normalized(record)
        except FileNotFoundError:
            return _json_response(
                200, {"ok": False, "available": False, "status": "missing", "record": source}
            )
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            return _json_response(
                200,
                {
                    "ok": False,
                    "available": False,
                    "status": "invalid",
                    "record": source,
                    "error": type(exc).__name__,
                },
            )
        fault = record.get("self_model", {})
        fault = fault.get("fault") if isinstance(fault, dict) else None
        return _json_response(
            200,
            {
                "ok": True,
                "available": True,
                "status": "cited",
                "record": {**source, "data": record},
                "recorded_circulation": {
                    "label": "recorded circulation replay; not newly sampled telemetry",
                    "data": record.get("connectivity"),
                },
                "synthetic_fault_block": {
                    "label": "seeded synthetic fault block; not live or recorded seat telemetry",
                    "seed": 20261024,
                    "data": fault,
                },
                "live_trading": False,
                "orders_placed": False,
            },
        )

    def evidence_html(self) -> Response:
        return Response(200, _EVIDENCE_HTML, "text/html; charset=utf-8")


# Static markup only: replay and generation JSON is assigned with textContent.
_EVIDENCE_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Aureon HNC public evidence</title>
<style>
:root{color-scheme:light dark;font-family:system-ui,sans-serif;line-height:1.5}
body{max-width:72rem;margin:auto;padding:1rem}section{margin:1rem 0;padding:1rem;border:1px solid #888}
pre{white-space:pre-wrap;overflow-wrap:anywhere}label{display:block;margin:.5rem 0}
textarea{width:100%;min-height:7rem}button,input{font:inherit}button{padding:.45rem .8rem}
.notice{font-weight:700}.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0)}
</style>
</head>
<body>
<main>
<h1>Aureon HNC public evidence</h1>
<p class="notice">Live trading is off. No orders are placed. Only Aureon's own model is used.</p>
<button id="refresh" type="button">Refresh public evidence</button>
<p id="loading" role="status" aria-live="polite"></p>
<section aria-labelledby="posture-heading"><h2 id="posture-heading">Demo posture</h2><pre id="posture">Not loaded.</pre></section>
<section aria-labelledby="field-heading"><h2 id="field-heading">HNC field status</h2><pre id="field">Not loaded.</pre></section>
<section aria-labelledby="replay-heading"><h2 id="replay-heading">Committed brain replay and inferred rerun</h2><pre id="replay">Not loaded.</pre></section>
<section aria-labelledby="organism-heading"><h2 id="organism-heading">Committed organism replay</h2><p>Circulation and the seed 20261024 synthetic fault block are labelled separately in the JSON.</p><pre id="organism">Not loaded.</pre></section>
<section aria-labelledby="generate-heading"><h2 id="generate-heading">Bounded own-model demo</h2>
<form id="generate-form">
<label for="prompt">Prompt</label><textarea id="prompt" maxlength="4096" required></textarea>
<label for="tokens">Maximum tokens (1–64)</label><input id="tokens" type="number" min="1" max="64" value="32" required>
<button type="submit">Generate without tools or streaming</button>
</form><p id="generation-status" role="status" aria-live="polite"></p><pre id="generation"></pre>
</section>
</main>
<script>
'use strict';
const show = (id, value) => { document.getElementById(id).textContent = JSON.stringify(value, null, 2); };
async function getJSON(path) {
  const response = await fetch(path, {headers: {'Accept': 'application/json'}, cache: 'no-store'});
  const body = await response.json();
  if (!response.ok) throw new Error('Request failed with status ' + response.status);
  return body;
}
async function refresh() {
  document.getElementById('loading').textContent = 'Loading same-origin public evidence…';
  const endpoints = [
    ['posture', '/api/demo/status'], ['field', '/api/hnc/status'],
    ['replay', '/api/hnc/replay'], ['organism', '/api/hnc/organism-replay']
  ];
  const results = await Promise.allSettled(endpoints.map((item) => getJSON(item[1])));
  results.forEach((result, index) => show(endpoints[index][0], result.status === 'fulfilled' ? result.value : {error: result.reason.message}));
  document.getElementById('loading').textContent = 'Evidence refresh complete.';
}
document.getElementById('refresh').addEventListener('click', refresh);
document.getElementById('generate-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  document.getElementById('generation-status').textContent = 'Generating…';
  try {
    const response = await fetch('/api/demo/generate', {method: 'POST', cache: 'no-store', headers: {'Content-Type': 'application/json', 'Accept': 'application/json'}, body: JSON.stringify({prompt: document.getElementById('prompt').value, max_tokens: Number(document.getElementById('tokens').value)})});
    const body = await response.json();
    show('generation', body);
    document.getElementById('generation-status').textContent = response.ok ? 'Generation complete.' : 'Generation unavailable; see the response.';
  } catch (error) {
    show('generation', {error: error.message});
    document.getElementById('generation-status').textContent = 'Generation request failed.';
  }
});
refresh();
</script>
</body>
</html>
"""


class DemoHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], application: DemoApplication) -> None:
        self.application = application
        super().__init__(address, DemoHandler)


class DemoHandler(BaseHTTPRequestHandler):
    """Explicit route dispatcher. Request logging is disabled by design."""

    protocol_version = "HTTP/1.1"
    server_version = "AureonDemo/1.0"

    def setup(self) -> None:
        super().setup()
        self.connection.settimeout(10.0)

    def log_message(self, fmt: str, *args: Any) -> None:
        del fmt, args

    def _client(self) -> str:
        client = str(self.client_address[0])
        try:
            if not ipaddress.ip_address(client).is_loopback:
                return client
            forwarded = self.headers.get("X-Forwarded-For", "").split(",", 1)[0].strip()
            return str(ipaddress.ip_address(forwarded)) if forwarded else client
        except ValueError:
            return client

    def _send(self, response: Response) -> None:
        if response.content_type.startswith("application/json"):
            try:
                raw = json.dumps(
                    response.payload,
                    ensure_ascii=False,
                    allow_nan=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            except (TypeError, ValueError):
                response = _error(503, "invalid_public_data", "Public data was not finite JSON.")
                raw = json.dumps(response.payload, allow_nan=False, sort_keys=True).encode("utf-8")
        else:
            raw = str(response.payload).encode("utf-8")
        self.send_response(response.status)
        self.send_header("Content-Type", response.content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
            "connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'",
        )
        for name, value in response.headers.items():
            self.send_header(name, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(raw)

    def _body(self) -> bytes | Response:
        if self.headers.get("Transfer-Encoding"):
            self.close_connection = True
            return _error(400, "transfer_encoding", "A bounded Content-Length body is required.")
        raw_length = self.headers.get("Content-Length")
        if raw_length is None:
            return _error(411, "content_length", "Content-Length is required.")
        try:
            length = int(raw_length)
        except ValueError:
            self.close_connection = True
            return _error(400, "content_length", "Content-Length must be a nonnegative integer.")
        if length < 0:
            self.close_connection = True
            return _error(400, "content_length", "Content-Length must be a nonnegative integer.")
        if length > MAX_BODY_BYTES:
            self.close_connection = True
            return _error(413, "body_too_large", "JSON body must be at most 16 KiB.")
        raw = self.rfile.read(length)
        if len(raw) != length:
            self.close_connection = True
            return _error(400, "incomplete_body", "The request body was incomplete.")
        return raw

    def _dispatch(self, method: str) -> None:
        path = urlsplit(self.path).path
        allowed = _ROUTES.get(path)
        if allowed is None:
            self._send(_error(404, "not_found", "Route not found."))
            return
        if method not in allowed:
            if method == "POST":
                self.close_connection = True
            self._send(
                _json_response(
                    405,
                    {"ok": False, "error": {"code": "method_not_allowed", "message": "Method not allowed."}},
                    {"Allow": ", ".join(sorted(allowed))},
                )
            )
            return
        app = self.server.application
        if path == "/healthz":
            response = app.health()
        elif path == "/readyz":
            response = app.readiness()
        elif path == "/api/demo/status":
            response = app.demo_status()
        elif path == "/api/hnc/status":
            response = app.hnc_status()
        elif path == "/api/hnc/replay":
            response = app.hnc_replay()
        elif path == "/api/hnc/organism-replay":
            response = app.organism_replay()
        elif path in ("/hnc", "/hnc/"):
            response = app.evidence_html()
        else:
            body = self._body()
            response = body if isinstance(body, Response) else app.generate(
                body,
                content_type=self.headers.get("Content-Type", ""),
                client=self._client(),
            )
        self._send(response)

    def do_GET(self) -> None:  # noqa: N802
        self._dispatch("GET")

    def do_POST(self) -> None:  # noqa: N802
        self._dispatch("POST")

    def do_HEAD(self) -> None:  # noqa: N802
        self._dispatch("HEAD")

    def do_PUT(self) -> None:  # noqa: N802
        self._dispatch("PUT")

    def do_DELETE(self) -> None:  # noqa: N802
        self._dispatch("DELETE")

    def do_PATCH(self) -> None:  # noqa: N802
        self._dispatch("PATCH")

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._dispatch("OPTIONS")

    def do_TRACE(self) -> None:  # noqa: N802
        self._dispatch("TRACE")

    def do_CONNECT(self) -> None:  # noqa: N802
        self._dispatch("CONNECT")


def create_server(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    *,
    application: DemoApplication | None = None,
) -> DemoHTTPServer:
    """Create, but do not start, the bounded stdlib HTTP server."""

    address = ipaddress.ip_address(host)
    if not address.is_loopback:
        raise ValueError("The demo service binds only to a literal loopback address")
    return DemoHTTPServer((host, port), application or DemoApplication())


def serve(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    server = create_server(host, port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    serve(args.host, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
