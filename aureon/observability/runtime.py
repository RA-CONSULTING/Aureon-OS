"""Fail-closed, local-only observability primitives.

This module deliberately has no exporter, network client, file sink, or provider
integration. It prepares bounded JSON records for an application-supplied
``logging.Logger`` and provides a dependency-free ASGI boundary that propagates
one validated request identifier. A collector is not implied by either API.
"""

from __future__ import annotations

import contextvars
import hashlib
import json
import logging
import re
import uuid
from collections.abc import Mapping, Sequence
from contextlib import contextmanager
from typing import Any, Awaitable, Callable, Iterator

_REDACTED = "[REDACTED]"
_TRUNCATED = "[TRUNCATED]"
_MAX_DEPTH = 6
_MAX_ITEMS = 64
_MAX_STRING = 2_048
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,63}$")
_CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_KEY_SEP_RE = re.compile(r"[^a-z0-9]+")
_BEARER_RE = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+\-/]+=*")
_BASIC_RE = re.compile(r"(?i)\bBasic\s+[A-Za-z0-9+/]+=*")
_URL_CREDENTIAL_RE = re.compile(r"(?i)(\b[a-z][a-z0-9+.-]*://)[^/@\s:]+:[^/@\s]+@")
_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)(\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|auth(?:orization)?|"
    r"client[_-]?secret|password|passwd|private[_-]?key|session|cookie)\b\s*[=:]\s*)"
    r"([^\s,;&]+)"
)
_PRIVATE_KEY_RE = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
    re.DOTALL,
)
_TOKEN_PREFIX_RE = re.compile(
    r"(?i)\b(?:sk-(?:proj-)?|gh[opusr]_|xox[baprs]-|AKIA|ASIA)[A-Za-z0-9_\-]{8,}"
)
_SENSITIVE_KEYS = {
    "api_key",
    "apikey",
    "access_key",
    "access_token",
    "auth",
    "authorization",
    "client_secret",
    "cookie",
    "credential",
    "credentials",
    "encryption_key",
    "jwt",
    "operator_key",
    "passwd",
    "password",
    "private_key",
    "refresh_token",
    "secret",
    "secret_key",
    "session",
    "session_id",
    "set_cookie",
    "signing_key",
    "token",
}

_correlation_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "aureon_correlation_id", default=""
)


def normalize_correlation_id(candidate: Any = None) -> str:
    """Return a safe request ID, preserving only a conservative valid input."""
    if isinstance(candidate, bytes):
        try:
            candidate = candidate.decode("ascii", "strict")
        except UnicodeDecodeError:
            candidate = None
    value = candidate.strip() if isinstance(candidate, str) else ""
    if _REQUEST_ID_RE.fullmatch(value):
        return value
    return uuid.uuid4().hex


def current_correlation_id() -> str:
    """Return the request ID in the current context, or an empty string."""
    return _correlation_id.get()


@contextmanager
def correlation_scope(candidate: Any = None) -> Iterator[str]:
    """Bind one validated request ID for the duration of a local operation."""
    correlation_id = normalize_correlation_id(candidate)
    token = _correlation_id.set(correlation_id)
    try:
        yield correlation_id
    finally:
        _correlation_id.reset(token)


def _safe_field_key(key: Any) -> str:
    if isinstance(key, str):
        return key
    if isinstance(key, bytes):
        return key.decode("utf-8", "replace")
    if key is None or isinstance(key, (bool, int, float)):
        return str(key)
    return f"<{type(key).__name__}>"


def _normalise_field_name(key: Any) -> str:
    value = _CAMEL_BOUNDARY_RE.sub("_", _safe_field_key(key)).lower()
    return _KEY_SEP_RE.sub("_", value).strip("_")


def _is_sensitive_key(key: Any) -> bool:
    name = _normalise_field_name(key)
    return (
        name in _SENSITIVE_KEYS
        or name.endswith("_token")
        or name.endswith("_password")
        or name.endswith("_secret")
        or name.endswith("_credential")
        or name.endswith("_private_key")
    )


def _redact_string(value: str) -> str:
    safe = _PRIVATE_KEY_RE.sub(_REDACTED, value)
    safe = _URL_CREDENTIAL_RE.sub(r"\1[REDACTED]@", safe)
    safe = _BEARER_RE.sub(f"Bearer {_REDACTED}", safe)
    safe = _BASIC_RE.sub(f"Basic {_REDACTED}", safe)
    safe = _SECRET_ASSIGNMENT_RE.sub(rf"\1{_REDACTED}", safe)
    safe = _TOKEN_PREFIX_RE.sub(_REDACTED, safe)
    if len(safe) > _MAX_STRING:
        safe = f"{safe[:_MAX_STRING]}{_TRUNCATED}"
    return safe


def redact_observability_value(value: Any, *, _depth: int = 0) -> Any:
    """Recursively redact secrets and bound values before serialization.

    Unknown objects are represented only by their type. Their ``repr`` or
    ``str`` methods are never called because those frequently expose provider
    payloads, credentials, or exception messages.
    """
    if _depth >= _MAX_DEPTH:
        return _TRUNCATED
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, bytes):
        return _redact_string(value.decode("utf-8", "replace"))
    if isinstance(value, str):
        return _redact_string(value)
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for index, (raw_key, raw_value) in enumerate(value.items()):
            if index >= _MAX_ITEMS:
                out[_TRUNCATED] = len(value) - _MAX_ITEMS
                break
            key = _redact_string(_safe_field_key(raw_key))[:128]
            out[key] = (
                _REDACTED
                if _is_sensitive_key(raw_key)
                else redact_observability_value(raw_value, _depth=_depth + 1)
            )
        return out
    if isinstance(value, Sequence):
        items = [
            redact_observability_value(item, _depth=_depth + 1)
            for item in value[:_MAX_ITEMS]
        ]
        if len(value) > _MAX_ITEMS:
            items.append(_TRUNCATED)
        return items
    return f"<{type(value).__name__}>"


def safe_observability_event(
    event: str,
    *,
    correlation_id: Any = None,
    fields: Mapping[str, Any] | None = None,
    exception: BaseException | None = None,
) -> dict[str, Any]:
    """Build a bounded event that never includes exception text or traceback."""
    requested_id = correlation_id if correlation_id is not None else current_correlation_id()
    record: dict[str, Any] = {
        "schema": "aureon.observability.v1",
        "event": _redact_string(str(event or "event"))[:128],
        "correlation_id": normalize_correlation_id(requested_id),
    }
    safe_fields = redact_observability_value(dict(fields or {}))
    if isinstance(safe_fields, dict):
        for key, value in safe_fields.items():
            if key not in {"schema", "event", "correlation_id"}:
                record[key] = value
    if exception is not None:
        record["exception_type"] = type(exception).__name__[:128]
        record["exception_fingerprint"] = _exception_fingerprint(exception)
    return record


def _exception_fingerprint(exception: BaseException) -> str:
    """Hash bounded code metadata, never exception text, locals, or full paths."""
    parts: list[str] = []
    current: BaseException | None = exception
    seen: set[int] = set()
    while current is not None and id(current) not in seen and len(seen) < 4:
        seen.add(id(current))
        current_type = type(current)
        parts.append(f"{current_type.__module__}.{current_type.__qualname__}")
        traceback = current.__traceback__
        frame_count = 0
        while traceback is not None and frame_count < 12:
            code = traceback.tb_frame.f_code
            basename = re.split(r"[/\\]", code.co_filename)[-1]
            module = traceback.tb_frame.f_globals.get("__name__", "")
            safe_module = module if isinstance(module, str) else f"<{type(module).__name__}>"
            parts.append(f"{safe_module}:{basename}:{code.co_name}:{traceback.tb_lineno}")
            traceback = traceback.tb_next
            frame_count += 1
        if current.__cause__ is not None:
            current = current.__cause__
        elif not current.__suppress_context__:
            current = current.__context__
        else:
            current = None
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]


def emit_local_event(
    logger: logging.Logger,
    level: int,
    event: str,
    *,
    correlation_id: Any = None,
    fields: Mapping[str, Any] | None = None,
    exception: BaseException | None = None,
) -> dict[str, Any]:
    """Emit one sanitized JSON line through a caller-owned local logger.

    Logging is deliberately best-effort: an unavailable or broken handler must
    never alter application control flow. The returned record is useful for
    deterministic local tests and in-process inspection.
    """
    try:
        record = safe_observability_event(
            event,
            correlation_id=correlation_id,
            fields=fields,
            exception=exception,
        )
    except Exception:  # noqa: BLE001 - fail closed to a content-free event
        record = {
            "schema": "aureon.observability.v1",
            "event": "observability_redaction_failure",
            "correlation_id": normalize_correlation_id(correlation_id),
        }
    try:
        logger.log(level, json.dumps(record, ensure_ascii=True, separators=(",", ":")))
    except Exception:  # noqa: BLE001 - observability cannot take down the runtime
        pass
    return record


def install_flask_request_correlation(
    app: Any,
    *,
    logger: logging.Logger | None = None,
) -> None:
    """Install local correlation hooks on a Flask app without an exporter.

    Flask is imported lazily so the core primitive remains dependency-free for
    ASGI and non-web runtimes. The request context owns and always resets the
    correlation ``ContextVar`` during teardown.
    """
    from flask import g, request

    event_logger = logger or logging.getLogger("aureon.observability.flask")

    def _aureon_log_exception(exc_info: tuple[Any, BaseException, Any]) -> None:
        # Flask's default implementation writes the raw message and traceback.
        # Replace only that logging hook; the framework still performs its
        # normal error dispatch and generic response handling.
        exception = exc_info[1]
        emit_local_event(
            event_logger,
            logging.ERROR,
            "flask_unhandled_exception",
            correlation_id=current_correlation_id(),
            fields={"method": request.method, "path": request.path},
            exception=exception,
        )

    app.log_exception = _aureon_log_exception

    @app.before_request
    def _aureon_bind_request_id() -> None:
        scope = correlation_scope(request.headers.get("X-Request-ID"))
        correlation_id = scope.__enter__()
        g._aureon_observability_scope = scope
        g.correlation_id = correlation_id

    @app.after_request
    def _aureon_propagate_request_id(response: Any) -> Any:
        correlation_id = getattr(g, "correlation_id", "") or current_correlation_id()
        if correlation_id:
            response.headers["X-Request-ID"] = correlation_id
        return response

    @app.teardown_request
    def _aureon_reset_request_id(_exception: BaseException | None) -> None:
        scope = getattr(g, "_aureon_observability_scope", None)
        if scope is None:
            return
        g._aureon_observability_scope = None
        try:
            scope.__exit__(None, None, None)
        except Exception:  # noqa: BLE001 - never alter Flask teardown
            pass


ASGIApp = Callable[
    [dict[str, Any], Callable[[], Awaitable[dict[str, Any]]], Callable[[dict[str, Any]], Awaitable[None]]],
    Awaitable[None],
]


class ASGIObservabilityMiddleware:
    """Validate/propagate ``X-Request-ID`` and sanitize uncaught failures."""

    def __init__(self, app: ASGIApp, *, logger: logging.Logger | None = None) -> None:
        self.app = app
        self.logger = logger or logging.getLogger("aureon.observability.asgi")

    async def __call__(self, scope: dict[str, Any], receive: Callable, send: Callable) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        supplied_id: bytes | None = None
        for raw_name, raw_value in scope.get("headers", []):
            if bytes(raw_name).lower() == b"x-request-id":
                supplied_id = bytes(raw_value)
                break

        response_started = False
        with correlation_scope(supplied_id) as correlation_id:
            async def send_with_id(message: dict[str, Any]) -> None:
                nonlocal response_started
                if message.get("type") == "http.response.start":
                    response_started = True
                    headers = [
                        (bytes(name), bytes(value))
                        for name, value in message.get("headers", [])
                        if bytes(name).lower() != b"x-request-id"
                    ]
                    headers.append((b"x-request-id", correlation_id.encode("ascii")))
                    message = {**message, "headers": headers}
                await send(message)

            try:
                await self.app(scope, receive, send_with_id)
            except Exception as exc:  # noqa: BLE001 - application boundary
                emit_local_event(
                    self.logger,
                    logging.ERROR,
                    "asgi_unhandled_exception",
                    correlation_id=correlation_id,
                    fields={
                        "method": scope.get("method", ""),
                        "path": scope.get("path", ""),
                    },
                    exception=exc,
                )
                if response_started:
                    # The status and headers are already immutable. Close the
                    # partial body locally and do not re-raise the application
                    # exception into an outer server logger that may print its
                    # raw message or traceback.
                    try:
                        await send(
                            {
                                "type": "http.response.body",
                                "body": b"",
                                "more_body": False,
                            }
                        )
                    except Exception:  # noqa: BLE001 - transport is already closing
                        pass
                    return
                body = json.dumps(
                    {
                        "error": {
                            "code": 500,
                            "message": "internal server error",
                            "request_id": correlation_id,
                        }
                    },
                    separators=(",", ":"),
                ).encode("utf-8")
                await send(
                    {
                        "type": "http.response.start",
                        "status": 500,
                        "headers": [
                            (b"content-type", b"application/json"),
                            (b"cache-control", b"no-store"),
                            (b"content-length", str(len(body)).encode("ascii")),
                            (b"x-request-id", correlation_id.encode("ascii")),
                        ],
                    }
                )
                await send({"type": "http.response.body", "body": body})


__all__ = [
    "ASGIObservabilityMiddleware",
    "correlation_scope",
    "current_correlation_id",
    "emit_local_event",
    "install_flask_request_correlation",
    "normalize_correlation_id",
    "redact_observability_value",
    "safe_observability_event",
]
