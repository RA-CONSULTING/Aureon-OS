"""
🔌 Aureon Operator — the Mount (OpenAI-compatible front door).
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

*"That which is below is like that which is above."* — the Emerald Tablet.

The **mount** is the formal way any flagship model plugs into Aureon: it speaks
the one protocol every model client already knows — ``POST /v1/chat/completions``
— so an external model mounts by pointing its ``base_url`` at Aureon and changing
nothing else. But the request is **never a raw passthrough**. It runs *through*
Aureon as the **host mind**: grounded in the whole repository, vetted by the
Queen's conscience, and only the grounded, vetted answer falls out the far side.
A request that crosses a hard authority boundary comes back ``content_filter``-ed
and **nothing executes** — the mount returns *text and a verdict only*.

This module is pure translation (no Flask, no I/O): it maps an OpenAI chat body
into the ``(prompt, context, engine)`` the existing engines already take, and
maps their ``CognitionResult`` / ``OperatorResponse`` ``.to_dict()`` back into an
OpenAI ``chat.completion`` — with Aureon's provenance (grounding, veto, the
ordered stages that ran) attached in an additive ``aureon`` field. The engines
themselves (``AureonCognition.reason`` / ``AureonOperator.respond``) are unchanged;
they already ground and veto.

The ``model`` field selects which Aureon engine grounds the request:
  • ``aureon-cognition``  — a single grounded agentic mind (repo-wide grounding
    + tools + conscience veto). The honest default; runs offline.
  • ``aureon-switchboard`` — many models → ground → fan-out → consensus → veto.
"""

from __future__ import annotations

from typing import Any, Dict, Iterator, List

# ── The mount's model catalogue (what GET /v1/models advertises) ───────────────
_DEFAULT_MODEL = "aureon-cognition"

MOUNT_MODELS: List[Dict[str, Any]] = [
    {
        "id": "aureon-cognition",
        "object": "model",
        "owned_by": "aureon",
        "engine": "cognition",
        "description": (
            "Single grounded agentic mind: repo-wide grounding + tools + conscience "
            "veto. The honest default; runs offline with no keys."
        ),
    },
    {
        "id": "aureon-switchboard",
        "object": "model",
        "owned_by": "aureon",
        "engine": "switchboard",
        "description": (
            "Many models → ground → fan-out → consensus → conscience veto. "
            "One grounded answer collapsed from every reachable line."
        ),
    },
]

# The ordered pipeline each engine declares. Reported honestly per-request in
# ``_stages_for`` — a boundary refusal short-circuits to just the veto.
_COGNITION_STAGES = ["ground", "agentic_cognition", "connectome_hnc_context", "conscience_veto"]
_SWITCHBOARD_STAGES = ["ground", "fan_out", "consensus", "conscience_veto"]

# The additive provenance keys every mounted response carries — the part of the
# contract an external model relies on. Single source of truth for the manifest,
# the benchmark's validation, and the docs.
AUREON_ENVELOPE_KEYS = (
    "engine", "trace_id", "grounded", "grounding",
    "conscience_verdict", "conscience_message", "blocked", "stages", "host_mind",
)

# Bump when the wire contract changes in a way an integrator must notice.
MOUNT_API_VERSION = "1"


class MountError(ValueError):
    """A malformed mount request (bad body / missing messages). Maps to HTTP 400."""


# ── Request: OpenAI chat body → (prompt, context, engine) ──────────────────────

def resolve_engine(model: str | None) -> str:
    """Map a requested ``model`` id to an Aureon engine name.

    Everything that is not explicitly the switchboard runs the single grounded
    mind — so an unknown or vendor model id (``gpt-4o``, ``claude-3``, …) still
    goes *through* Aureon rather than being rejected. That is the whole point:
    the host mind grounds every mounted request.
    """
    m = (model or "").strip().lower()
    if m == "aureon-switchboard" or m.endswith("switchboard"):
        return "switchboard"
    return "cognition"


def _extract_text(content: Any) -> str:
    """Pull the text out of an OpenAI message ``content`` — a plain string or the
    content-part list (``[{"type": "text", "text": …}]``) that vision-capable
    clients send. Non-text parts (images/audio) are ignored honestly."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        out: List[str] = []
        for part in content:
            if isinstance(part, str):
                out.append(part)
            elif isinstance(part, dict):
                text = part.get("text")
                if isinstance(text, str) and text:
                    out.append(text)
        return " ".join(out).strip()
    return str(content).strip()


def parse_chat_request(body: Any) -> Dict[str, Any]:
    """Translate an OpenAI ``chat.completions`` body into Aureon's inputs.

    ``system`` turns become grounding *context*; the **last** ``user`` turn is the
    *prompt*; any earlier user/assistant turns are folded into the context as
    prior conversation. Returns ``{prompt, context, engine, model, stream,
    session_id}``. Raises :class:`MountError` on a body Aureon can't run.
    """
    if not isinstance(body, dict):
        raise MountError("request body must be a JSON object")
    messages = body.get("messages")
    if not isinstance(messages, list) or not messages:
        raise MountError("'messages' must be a non-empty array")

    user_indices = [
        i for i, m in enumerate(messages)
        if isinstance(m, dict) and str(m.get("role", "")).strip() == "user"
    ]
    last_user_idx = user_indices[-1] if user_indices else None

    system_parts: List[str] = []
    convo_parts: List[str] = []
    prompt = ""
    for i, m in enumerate(messages):
        if not isinstance(m, dict):
            continue
        role = str(m.get("role", "")).strip() or "user"
        text = _extract_text(m.get("content"))
        if not text:
            continue
        if i == last_user_idx:
            prompt = text
        elif role == "system":
            system_parts.append(text)
        else:
            convo_parts.append(f"{role}: {text}")

    if not prompt:
        raise MountError("no user message with text content found in 'messages'")

    context_blocks: List[str] = list(system_parts)
    if convo_parts:
        context_blocks.append("Prior conversation:\n" + "\n".join(convo_parts))
    context = "\n\n".join(b for b in context_blocks if b).strip()

    model = str(body.get("model") or _DEFAULT_MODEL)
    # OpenAI's stable per-caller handle is ``user``; accept our ``session_id`` too.
    raw_session = body.get("session_id") or body.get("user")
    session_id = str(raw_session) if raw_session else None

    return {
        "prompt": prompt,
        "context": context,
        "engine": resolve_engine(model),
        "model": model,
        "stream": bool(body.get("stream", False)),
        "session_id": session_id,
    }


def build_engine_prompt(parsed: Dict[str, Any]) -> str:
    """Fold the context ahead of the prompt into the single string the engines
    take. Context rides *through* the same grounding + boundary check as the
    prompt — conservative by construction."""
    context = str(parsed.get("context") or "").strip()
    prompt = str(parsed.get("prompt") or "").strip()
    if context:
        return f"{context}\n\n{prompt}".strip()
    return prompt


# ── Response: engine result dict → OpenAI chat.completion ──────────────────────

def _approx_tokens(text: str) -> int:
    """A deterministic, tokenizer-free *approximation* (~4 chars/token). The mount
    does not run a vendor tokenizer, so ``usage`` is explicitly approximate — never
    a fabricated exact count."""
    return max(0, (len(text or "") + 3) // 4)


def _usage(prompt: str, completion: str) -> Dict[str, int]:
    p = _approx_tokens(prompt)
    c = _approx_tokens(completion)
    return {"prompt_tokens": p, "completion_tokens": c, "total_tokens": p + c}


def _grounded(result: Dict[str, Any], engine: str) -> bool:
    if engine == "cognition":
        return bool(result.get("grounded"))
    grounding = result.get("grounding") or {}
    return bool(grounding.get("source_count"))


def _stages_for(engine: str, result: Dict[str, Any]) -> List[str]:
    """The ordered pipeline that actually ran for this request — honest, not a
    fixed label. A hard-boundary refusal happens before grounding, so only the
    conscience veto ran."""
    grounding = result.get("grounding") or {}
    has_ground = bool(grounding)
    if engine == "switchboard":
        if not has_ground and not result.get("answers"):
            return ["conscience_veto"]
        stages = []
        if has_ground:
            stages.append("ground")
        if result.get("answers"):
            stages.append("fan_out")
        if result.get("consensus"):
            stages.append("consensus")
        stages.append("conscience_veto")
        return stages
    # cognition: a boundary refusal returns with no grounding, no tools, 0 turns.
    if not has_ground and not result.get("tool_calls") and not result.get("turns"):
        return ["conscience_veto"]
    return list(_COGNITION_STAGES)


def _aureon_envelope(result: Dict[str, Any], engine: str) -> Dict[str, Any]:
    """The additive provenance the mount attaches to every response: which engine
    ran, the grounding, the conscience verdict, and the ordered stages."""
    return {
        "engine": engine,
        "trace_id": result.get("trace_id"),
        "grounded": _grounded(result, engine),
        "grounding": result.get("grounding") or {},
        "conscience_verdict": result.get("conscience_verdict"),
        "conscience_message": result.get("conscience_message", ""),
        "blocked": bool(result.get("blocked")),
        "stages": _stages_for(engine, result),
        "elapsed_ms": result.get("elapsed_ms"),
        "host_mind": "aureon",
    }


def to_chat_completion(
    result: Dict[str, Any], *, model: str, engine: str, created: int
) -> Dict[str, Any]:
    """Map an engine ``.to_dict()`` into an OpenAI ``chat.completion`` object.

    A vetoed/blocked answer becomes ``finish_reason: "content_filter"`` carrying
    the honest blocked message — the same shape a vendor uses when its own safety
    layer refuses, so an external client handles it without special-casing.
    """
    text = str(result.get("text", ""))
    blocked = bool(result.get("blocked"))
    trace_id = str(result.get("trace_id") or "unknown")
    finish_reason = "content_filter" if blocked else "stop"
    return {
        "id": f"chatcmpl-{trace_id}",
        "object": "chat.completion",
        "created": int(created),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": finish_reason,
            }
        ],
        "usage": _usage(str(result.get("prompt", "")), text),
        "aureon": _aureon_envelope(result, engine),
    }


def _word_pieces(text: str) -> Iterator[str]:
    """Yield the answer as delta pieces, preserving spacing (same post-hoc
    streaming the existing SSE routes use)."""
    if not text:
        return
    parts = text.split(" ")
    for idx, word in enumerate(parts):
        yield word if idx == len(parts) - 1 else word + " "


def iter_chat_chunks(
    result: Dict[str, Any], *, model: str, engine: str, created: int
) -> Iterator[Dict[str, Any]]:
    """Yield OpenAI ``chat.completion.chunk`` objects for a streamed response: a
    role delta, the content word-by-word, then a final chunk carrying the
    ``finish_reason`` and the ``aureon`` provenance envelope."""
    trace_id = str(result.get("trace_id") or "unknown")
    base = {
        "id": f"chatcmpl-{trace_id}",
        "object": "chat.completion.chunk",
        "created": int(created),
        "model": model,
    }
    yield {**base, "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}]}
    for piece in _word_pieces(str(result.get("text", ""))):
        yield {**base, "choices": [{"index": 0, "delta": {"content": piece}, "finish_reason": None}]}
    finish_reason = "content_filter" if result.get("blocked") else "stop"
    yield {
        **base,
        "choices": [{"index": 0, "delta": {}, "finish_reason": finish_reason}],
        "aureon": _aureon_envelope(result, engine),
    }


def openai_error(message: str, *, code: str = "invalid_request_error", type_: str = "invalid_request_error") -> Dict[str, Any]:
    """The OpenAI error envelope, so a flagship client's error handling just works."""
    return {"error": {"message": message, "type": type_, "code": code}}


def integration_manifest() -> Dict[str, Any]:
    """The self-describing integration map an AGI system reads to plug in.

    A single machine-readable contract — endpoint, engines, request/response shape,
    the provenance keys, the boundary behaviour, and how to mount — served live at
    ``GET /v1/integration`` and validated by the mount integration benchmark. This
    is the map: *point your base_url here and every request is grounded and vetted
    through Aureon as the host mind.*
    """
    return {
        "service": "aureon-mount",
        "version": MOUNT_API_VERSION,
        "summary": (
            "Point your OpenAI-compatible base_url at Aureon; every request runs "
            "through Aureon as the host mind — grounded in the repo, vetted by the "
            "conscience — and only the grounded, vetted answer comes back."
        ),
        "endpoint": "POST /v1/chat/completions",
        "models_endpoint": "GET /v1/models",
        "manifest_endpoint": "GET /v1/integration",
        "engines": [
            {"id": m["id"], "engine": m["engine"], "description": m["description"]}
            for m in MOUNT_MODELS
        ],
        "default_model": _DEFAULT_MODEL,
        "request_shape": "OpenAI chat.completions {model, messages, stream}",
        "response_object": ["chat.completion", "chat.completion.chunk"],
        "provenance_field": "aureon",
        "provenance_keys": list(AUREON_ENVELOPE_KEYS),
        "boundary_behavior": (
            "crossing a hard authority boundary (live trading, payment, safety-gate "
            "bypass, credential, filing) → finish_reason=content_filter; text + a "
            "verdict only; nothing executes"
        ),
        "human_in_the_loop": True,
        "auth": "Authorization: Bearer <AUREON_OPERATOR_API_KEY> (required only when the key is set)",
        "mount_by": "point base_url at <host>/v1 — no other change",
        "mcp": {
            "endpoint": "POST /mcp",
            "transport": "streamable-http (JSON-RPC 2.0) + stdio",
            "stdio_command": "aureon-mcp",
            "tools": ["aureon_reason", "aureon_switchboard", "aureon_integration"],
        },
    }


__all__ = [
    "MOUNT_MODELS",
    "MOUNT_API_VERSION",
    "AUREON_ENVELOPE_KEYS",
    "MountError",
    "resolve_engine",
    "parse_chat_request",
    "build_engine_prompt",
    "to_chat_completion",
    "iter_chat_chunks",
    "openai_error",
    "integration_manifest",
]
