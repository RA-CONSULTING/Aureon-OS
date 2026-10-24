"""Organism circulation — one thought bus, every named seat publishing and listening.

The HTTP seat listens on 127.0.0.1:8799 (override with AUREON_ORGANISM_HTTP_PORT).
GET /healthz and GET /health report that seat. The fusion seat keeps
127.0.0.1:8765. A taken circulation port is a failed boot.
metacognition, queen reasoning, logic, neural, lighthouse, QGITA, mycelium,
baton relay, council, deterministic systems, algorithmic nodes, self-repair,
the HTTP seat, and self-code each subscribe to ``organism.circulation`` and
publish their own pulse. The HTTP seat's pulse reports ``listening`` false
when this process has not bound the socket. A self-model reading is published
on ``organism.self_model`` from the pulses just heard. No model is called.
Autonomy audit records on the circulation topic are
consumed by the metacognition and self-repair loops. After repeated failed
self-changes, metacognition raises a concern and lowers its confidence, and
self-repair deprioritises a target that keeps failing. Connectors switch on
at boot. Self-code records a proposal; it does not edit the repo and it
does not arm live trading.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from aureon.core.algorithmic_nodes import list_nodes
from aureon.core.aureon_thought_bus import Thought, get_thought_bus
from aureon.core.deterministic_systems import list_systems

_HOST = "127.0.0.1"
_DEFAULT_PORT = 8799
_CIRCULATION = "organism.circulation"
_RECEIPT = "organism.receipt"
_LOCK = threading.Lock()
_STATE: dict[str, Any] = {
    "started": False,
    "server": None,
    "thread": None,
    "http_thread": None,
    "stop": None,
    "port": None,
    "inbox": {},
    "loops": {},
    "error": None,
    "self_model_seen": {},
    "consume_count": {},
    "latency_samples": [],
    "audit_consumed": {"metacognition": [], "self_repair": []},
}

ORGANS: tuple[dict[str, str], ...] = (
    {"name": "metacognition", "role": "metacognition", "module": "aureon.core.metacognition_monitor"},
    {"name": "queen", "role": "reasoning", "module": "aureon.queen.queen_layer"},
    {"name": "logic", "role": "logic", "module": "aureon.core.deterministic_systems"},
    {"name": "neural", "role": "neural", "module": "aureon.utils.aureon_queen_unified_neural_chain"},
    {"name": "lighthouse", "role": "lighthouse", "module": "aureon.analytics.lighthouse_metrics"},
    {"name": "qgita", "role": "qgita", "module": "aureon.wisdom.aureon_qgita"},
    {"name": "mycelium", "role": "mycelium", "module": "aureon.core.aureon_mycelium"},
    {"name": "baton_relay", "role": "baton_relay", "module": "aureon.core.baton_relay_monitor"},
    {"name": "council", "role": "council", "module": "aureon.swarm.druidic_council"},
    {"name": "deterministic_systems", "role": "deterministic_systems", "module": "aureon.core.deterministic_systems"},
    {"name": "algorithmic_nodes", "role": "algorithmic_nodes", "module": "aureon.core.algorithmic_nodes"},
)

# Seats that already had a connector or a loop, and did not publish a circulation
# pulse. They stay out of ORGANS so existing organ lists keep their names.
BUS_SEATS: tuple[dict[str, str], ...] = (
    {"name": "self_repair", "role": "self_repair", "module": "aureon.core.organism_circulation"},
    {"name": "http_seat", "role": "http_seat", "module": "aureon.core.organism_circulation"},
    {"name": "self_code", "role": "self_code", "module": "aureon.core.organism_circulation"},
)
_SELF_MODEL = "organism.self_model"


def circulation_seats() -> tuple[dict[str, str], ...]:
    """Every seat that must publish and consume on the circulation bus."""

    return ORGANS + BUS_SEATS


def _http_listening() -> bool:
    """True only while this process is serving the circulation HTTP socket."""

    with _LOCK:
        server = _STATE.get("server")
        thread = _STATE.get("http_thread")
    return server is not None and thread is not None and thread.is_alive()

_DEFAULT_CONNECTORS = {
    "thought_bus": True,
    "http_seat": True,
    "self_repair": True,
    "metacognition": True,
    "queen": True,
    "logic": True,
    "neural": True,
    "lighthouse": True,
    "qgita": True,
    "mycelium": True,
    "baton_relay": True,
    "council": True,
    "deterministic_systems": True,
    "algorithmic_nodes": True,
    "self_code": True,
}

_SECRET_PATH_MARKERS = (".env", "secret", "credential", "id_rsa", "password")
_BATON_STAGES = ("intent", "plan", "execute", "confirm")
_SUBSCRIBED = False
_AUDIT_WIRED = False
_AUDIT_BUS: Any = None
_AUDIT_CAP = 50
_LATENCY_CAP = 5000
_FAILURE_REPEAT = 2
_CONFIDENCE_BASE = 1.0
_CONFIDENCE_FLOOR = 0.2
_CONFIDENCE_STEP = 0.25
_FAILED_SELF_CHANGE_EVENTS = frozenset(
    {
        "self_patch_kept",
        "write_refused",
        "repair_refused",
        "repair_reverted",
        "self_patch_merge_failed",
        "human_review_required",
    }
)
_FAILED_SELF_CHANGE_REASONS = frozenset(
    {
        "tests_failed",
        "write_refused",
        "retest_failed_change_reverted",
    }
)
_FAILURE_COUNTS: dict[str, int] = {}
_DEPRIORITISED: list[str] = []
_SEEN_FAILURE_IDS: set[str] = set()
_META: dict[str, Any] = {
    "truth_status": "loop_running",
    "loop": "running",
    "audit_concern": None,
    "audit_confidence": _CONFIDENCE_BASE,
}


def _state_dir() -> Path:
    raw = os.environ.get("AUREON_ORGANISM_STATE") or "state"
    path = Path(raw)
    path.mkdir(parents=True, exist_ok=True)
    return path


def connector_state() -> dict[str, bool]:
    path = _state_dir() / "organism_connectors.json"
    state = dict(_DEFAULT_CONNECTORS)
    if path.is_file():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                for key, value in loaded.items():
                    state[str(key)] = bool(value)
        except (OSError, json.JSONDecodeError):
            pass
    return state


def switch_connector(name: str, enabled: bool) -> dict[str, bool]:
    """Turn a connector or bus seat on or off and remember it."""
    state = connector_state()
    state[str(name)] = bool(enabled)
    path = _state_dir() / "organism_connectors.json"
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if connector_state_enabled("thought_bus"):
        try:
            get_thought_bus().publish(
                Thought(
                    source="organism",
                    topic="organism.connectors.switched",
                    payload={"name": name, "enabled": bool(enabled), "connectors": state},
                )
            )
        except Exception:
            pass
    return state


def connector_state_enabled(name: str) -> bool:
    return bool(connector_state().get(name, False))


def propose_self_code(path: str, reason: str) -> dict[str, Any]:
    """Record a self-code proposal. Never writes the target file or a secret."""
    target = str(path or "").strip()
    lowered = target.lower()
    if not target or any(marker in lowered for marker in _SECRET_PATH_MARKERS):
        return {"accepted": False, "reason": "credential_paths_are_refused"}
    if not connector_state_enabled("self_code"):
        return {"accepted": False, "reason": "self_code_connector_off"}
    record = {
        "ts": time.time(),
        "path": target,
        "reason": str(reason or "")[:500],
        "applied": False,
        "note": "proposal only; AUREON_SELF_CODE_APPLY is not consulted and no patch is written",
    }
    log = _state_dir() / "self_code_proposals.jsonl"
    with log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {"accepted": True, "applied": False, "record": record}


def _payload_for(organ: dict[str, str], tick: int) -> dict[str, Any]:
    name = organ["name"]
    payload: dict[str, Any] = {
        "kind": "pulse",
        "role": organ["role"],
        "module": organ["module"],
        "tick": tick,
        "loop": "running",
        "listening": True,
    }
    if name == "metacognition":
        payload.update(dict(_META))
        payload["loop"] = "running"
    elif name == "baton_relay":
        payload["stage"] = _BATON_STAGES[tick % len(_BATON_STAGES)]
        payload["stages"] = list(_BATON_STAGES)
    elif name == "council":
        payload["seats"] = ["seer", "sentinel", "weaver", "keeper"]
        payload["active_threshold"] = 0.80
    elif name == "logic" or name == "deterministic_systems":
        payload["systems"] = list_systems()
    elif name == "algorithmic_nodes":
        payload["nodes"] = list_nodes()
    elif name == "queen":
        payload["reasoning"] = "queen"
    elif name == "http_seat":
        bound = _http_listening()
        payload["listening"] = bound
        payload["http_seat_bound"] = bound
    elif name == "self_repair":
        with _LOCK:
            heard = list((_STATE.get("audit_consumed") or {}).get("self_repair") or [])
        payload["loop"] = "running"
        if heard:
            payload["last_audit_event"] = str(heard[-1].get("event") or "")
    elif name == "self_code":
        payload["applied"] = False
        payload["live_trading"] = False
    return payload


def _metacognition_reading() -> dict[str, Any]:
    if not connector_state_enabled("metacognition"):
        return {"truth_status": "connector_off"}
    try:
        from aureon.core.metacognition_monitor import get_metacognition_monitor

        assessment = get_metacognition_monitor().assess()
        return {
            "truth_status": assessment.truth_status,
            "self_coherence": assessment.self_coherence,
            "psi": assessment.psi,
        }
    except Exception as exc:  # noqa: BLE001 — the loop stays up when the field is quiet
        return {"truth_status": "no_data", "note": str(exc)[:180]}


def publish_faculty_reading(source: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Publish one faculty reading and its baton link. No model is called.

    Metacognition and self-questioning use this when Ollama is absent. The
    payload is the reading already in hand, or an explicit unavailable reason.
    """

    body = dict(payload)
    body["ollama"] = False
    body.setdefault("live_trading", False)
    bus = get_thought_bus()
    bus.publish(Thought(source=source, topic=f"organism.{source}", payload=body))
    link = bus.publish(
        Thought(
            source=source,
            topic="baton.link",
            payload={"module": source, "ollama": False, "live_trading": False},
        )
    )
    return {"published": True, "source": source, "id": getattr(link, "id", None)}


def _on_circulation(thought: Thought) -> None:
    """Every other seat hears the pulse. Receipts stay in memory so the log is not a storm."""
    source = str(getattr(thought, "source", "") or "")
    topic = str(getattr(thought, "topic", "") or "")
    if topic != _CIRCULATION:
        return
    published_ts = float(getattr(thought, "ts", 0.0) or 0.0)
    received_ts = time.time()
    latency_s = received_ts - published_ts if published_ts > 0 else None
    for organ in circulation_seats():
        name = organ["name"]
        if source == name or not connector_state_enabled(name):
            continue
        with _LOCK:
            heard = _STATE["inbox"].setdefault(name, [])
            heard.append(
                {
                    "source": source,
                    "topic": topic,
                    "role": organ["role"],
                    "kind": "receipt",
                    "ts": received_ts,
                    "published_ts": published_ts,
                    "received_ts": received_ts,
                    "latency_s": latency_s,
                }
            )
            del heard[:-50]
            counts = _STATE.setdefault("consume_count", {})
            counts[name] = int(counts.get(name, 0)) + 1
            if latency_s is not None:
                samples = _STATE.setdefault("latency_samples", [])
                samples.append(latency_s)
                del samples[:-_LATENCY_CAP]


def _on_self_model(thought: Thought) -> None:
    """Remember the last pulse from each seat. No model is called."""

    if str(getattr(thought, "topic", "") or "") != _CIRCULATION:
        return
    payload = getattr(thought, "payload", None)
    if not isinstance(payload, dict) or payload.get("kind") != "pulse":
        return
    source = str(getattr(thought, "source", "") or "")
    kept = {
        "tick": payload.get("tick"),
        "loop": payload.get("loop"),
        "role": payload.get("role"),
        "error": payload.get("error"),
        "stage": payload.get("stage"),
        "listening": payload.get("listening"),
        "http_seat_bound": payload.get("http_seat_bound"),
    }
    with _LOCK:
        seen = _STATE.setdefault("self_model_seen", {})
        seen[source] = kept


def _audit_payload(thought: Thought) -> dict[str, Any] | None:
    source = str(getattr(thought, "source", "") or "")
    payload = getattr(thought, "payload", None)
    if not isinstance(payload, dict):
        return None
    if payload.get("kind") != "autonomy_audit" and source != "autonomy_audit":
        return None
    return payload


def _safe_target(payload: dict[str, Any]) -> str:
    """A repo path the loops may rank. Credential paths are dropped."""

    raw = payload.get("path") or payload.get("target") or payload.get("target_path") or ""
    text = str(raw).replace("\\", "/").strip()
    if not text:
        return ""
    lowered = text.lower()
    if any(marker in lowered for marker in _SECRET_PATH_MARKERS):
        return ""
    return text


def _failed_self_change(payload: dict[str, Any]) -> bool:
    event = str(payload.get("event") or "")
    reason = str(payload.get("reason") or "")
    return event in _FAILED_SELF_CHANGE_EVENTS or reason in _FAILED_SELF_CHANGE_REASONS


def _reset_audit_effects() -> None:
    _FAILURE_COUNTS.clear()
    _DEPRIORITISED.clear()
    _SEEN_FAILURE_IDS.clear()
    _META["audit_concern"] = None
    _META["audit_confidence"] = _CONFIDENCE_BASE


def _apply_failed_self_change(thought: Thought, payload: dict[str, Any]) -> None:
    """Count one failed self-change and let both loops act on the repeat.

    Subscribers see the same thought. The thought id keeps the count at one.
    A second failure of the same path deprioritises it. Two failures in total,
    on one path or across paths, raise the metacognition concern and lower
    confidence. Credential paths never enter the ranking.
    """

    if not _failed_self_change(payload):
        return
    target = _safe_target(payload)
    if not target:
        return
    identity = str(getattr(thought, "id", "") or "") or str(id(thought))
    with _LOCK:
        if identity in _SEEN_FAILURE_IDS:
            return
        _SEEN_FAILURE_IDS.add(identity)
        count = _FAILURE_COUNTS.get(target, 0) + 1
        _FAILURE_COUNTS[target] = count
        if count >= _FAILURE_REPEAT and target not in _DEPRIORITISED:
            _DEPRIORITISED.append(target)
        total = sum(_FAILURE_COUNTS.values())
        if total >= _FAILURE_REPEAT:
            _META["audit_concern"] = f"repeated failed self-change on {target}"
            dropped = _CONFIDENCE_STEP * (total - 1)
            _META["audit_confidence"] = max(_CONFIDENCE_FLOOR, round(_CONFIDENCE_BASE - dropped, 4))


def _audit_record(thought: Thought) -> dict[str, Any] | None:
    payload = _audit_payload(thought)
    if payload is None:
        return None
    record = {
        "event": str(payload.get("event") or ""),
        "ts": payload.get("ts"),
        "loop": "",
    }
    target = _safe_target(payload)
    if target:
        record["path"] = target
    reason = str(payload.get("reason") or "")
    if reason and not any(marker in reason.lower() for marker in _SECRET_PATH_MARKERS):
        record["reason"] = reason
    return record


def _remember_audit(loop: str, thought: Thought) -> None:
    payload = _audit_payload(thought)
    if payload is None:
        return
    _apply_failed_self_change(thought, payload)
    record = _audit_record(thought)
    if record is None:
        return
    record["loop"] = loop
    with _LOCK:
        box = _STATE.setdefault("audit_consumed", {})
        heard = box.setdefault(loop, [])
        heard.append(record)
        del heard[:-_AUDIT_CAP]


def _on_audit_metacognition(thought: Thought) -> None:
    _remember_audit("metacognition", thought)


def _on_audit_self_repair(thought: Thought) -> None:
    _remember_audit("self_repair", thought)


def consumed_audits(loop: str) -> list[dict[str, Any]]:
    """Audit events this loop has taken from the circulation bus."""

    with _LOCK:
        box = _STATE.get("audit_consumed") or {}
        return [dict(item) for item in box.get(loop, [])]


def metacognition_audit_state() -> dict[str, Any]:
    """Concern and confidence the metacognition loop has drawn from audits."""

    with _LOCK:
        return {
            "audit_concern": _META.get("audit_concern"),
            "audit_confidence": _META.get("audit_confidence", _CONFIDENCE_BASE),
            "failed_self_changes": sum(_FAILURE_COUNTS.values()),
        }


def deprioritised_targets() -> list[str]:
    """Paths self-repair has moved behind the rest after repeated failure."""

    with _LOCK:
        return list(_DEPRIORITISED)


def repair_priority(paths: list[str]) -> list[str]:
    """Keep the caller's order, with repeatedly failing targets last."""

    demoted = set(deprioritised_targets())
    return sorted(paths, key=lambda path: (path in demoted, paths.index(path)))


def ensure_audit_subscribers() -> None:
    """Subscribe the audit loops on the bus that ``get_thought_bus()`` returns now.

    A later test or importer can replace the process bus. Subscriptions do not
    move with it, so a publish on the new bus would be stored and never consumed.
    The previous bus object is held until this comparison. A freed bus can be
    allocated again at the same id, and that new object would look already wired.
    """

    global _SUBSCRIBED, _AUDIT_WIRED, _AUDIT_BUS
    bus = get_thought_bus()
    if _AUDIT_WIRED and _SUBSCRIBED and _AUDIT_BUS is bus:
        return
    if _AUDIT_BUS is not bus:
        _SUBSCRIBED = False
        _AUDIT_WIRED = False
    if not _SUBSCRIBED:
        bus.subscribe(_CIRCULATION, _on_circulation)
        bus.subscribe(_CIRCULATION, _on_self_model)
        _SUBSCRIBED = True
    if not _AUDIT_WIRED:
        bus.subscribe(_CIRCULATION, _on_audit_metacognition)
        bus.subscribe(_CIRCULATION, _on_audit_self_repair)
        _AUDIT_WIRED = True
    _AUDIT_BUS = bus


def _metacognition_loop(stop: threading.Event) -> None:
    while not stop.is_set():
        reading = _metacognition_reading()
        reading["loop"] = "running"
        reading["ollama"] = False
        reading.setdefault("reason", "no model is called")
        with _LOCK:
            heard = list((_STATE.get("audit_consumed") or {}).get("metacognition") or [])
            if heard:
                reading["last_audit_event"] = heard[-1].get("event")
            concern = _META.get("audit_concern")
            confidence = _META.get("audit_confidence", _CONFIDENCE_BASE)
            _META.update(reading)
            _META["audit_concern"] = concern
            _META["audit_confidence"] = confidence
        try:
            publish_faculty_reading("metacognition", reading)
        except Exception:
            pass
        stop.wait(5.0)


def _self_repair_loop(stop: threading.Event) -> None:
    """Keep the self-repair seat awake and name the last audit it consumed."""

    while not stop.is_set():
        with _LOCK:
            heard = list((_STATE.get("audit_consumed") or {}).get("self_repair") or [])
            loops = dict(_STATE.get("loops") or {})
            loops["self_repair"] = "running"
            if heard:
                loops["self_repair_last_audit"] = str(heard[-1].get("event") or "")
            if _DEPRIORITISED:
                loops["self_repair_deprioritised"] = list(_DEPRIORITISED)
            _STATE["loops"] = loops
        stop.wait(5.0)


def _self_model_pulse(tick: int) -> dict[str, Any]:
    """A reading of seats just heard. Internal state only; no model is called."""

    with _LOCK:
        seen = dict(_STATE.get("self_model_seen") or {})
        error = _STATE.get("error")
        inbox_counts = {name: len(items) for name, items in (_STATE.get("inbox") or {}).items()}
    seats = []
    for seat in circulation_seats():
        name = seat["name"]
        last = seen.get(name) if isinstance(seen.get(name), dict) else {}
        seats.append(
            {
                "name": name,
                "role": seat["role"],
                "module": seat["module"],
                "last_tick": None if last is None else last.get("tick"),
                "loop": None if last is None else last.get("loop"),
                "error": None if last is None else last.get("error"),
                "inbox": inbox_counts.get(name, 0),
            }
        )
    return {
        "kind": "self_model",
        "tick": tick,
        "ollama": False,
        "external_llm": False,
        "live_trading": False,
        "http_seat_bound": _http_listening(),
        "process_error": bool(error),
        "seats": seats,
    }


def _publish_tick(tick: int) -> None:
    """Publish one circulation pulse for every connector that is switched on."""
    bus = get_thought_bus()
    connectors = connector_state()
    if not connectors.get("thought_bus", True):
        return
    running: dict[str, str] = {}
    for organ in circulation_seats():
        if not connectors.get(organ["name"], True):
            continue
        bus.publish(
            Thought(
                source=organ["name"],
                topic=_CIRCULATION,
                payload=_payload_for(organ, tick),
            )
        )
        running[organ["name"]] = "running"
    bus.publish(
        Thought(
            source="self_model",
            topic=_SELF_MODEL,
            payload=_self_model_pulse(tick),
        )
    )
    with _LOCK:
        previous = _STATE.get("loops") or {}
        if previous.get("self_repair"):
            running["self_repair"] = previous["self_repair"]
        if previous.get("self_repair_last_audit"):
            running["self_repair_last_audit"] = previous["self_repair_last_audit"]
        if previous.get("self_repair_deprioritised"):
            running["self_repair_deprioritised"] = list(previous["self_repair_deprioritised"])
        _STATE["loops"] = running


def _loop(stop: threading.Event) -> None:
    tick = 0
    while not stop.is_set():
        _publish_tick(tick)
        tick += 1
        stop.wait(1.0)


class _ReuseServer(ThreadingHTTPServer):
    allow_reuse_address = True


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def _json(self, code: int, body: dict[str, Any]) -> None:
        raw = json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or "0")
        if length <= 0 or length > 65536:
            return {}
        try:
            data = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path in ("/healthz", "/health", "/"):
            with _LOCK:
                port = _STATE.get("port")
                loops = dict(_STATE.get("loops") or {})
                error = _STATE.get("error")
            recent = get_thought_bus().recall(limit=40)
            sources = sorted({str(item.get("source") or "") for item in recent if item.get("source")})
            self._json(
                200,
                {
                    "ok": True,
                    "listening": True,
                    "host": _HOST,
                    "port": port,
                    "loops": loops,
                    "connectors": connector_state(),
                    "sources": sources,
                    "error": error,
                },
            )
            return
        if parsed.path == "/organs":
            self._json(200, {"organs": list(ORGANS), "nodes": list_nodes(), "systems": list_systems()})
            return
        if parsed.path == "/connectors":
            self._json(200, {"connectors": connector_state()})
            return
        if parsed.path == "/thoughts":
            limit = 40
            query = parse_qs(parsed.query)
            if "limit" in query:
                try:
                    limit = max(1, min(200, int(query["limit"][0])))
                except ValueError:
                    limit = 40
            self._json(200, {"thoughts": get_thought_bus().recall(limit=limit)})
            return
        self._json(404, {"ok": False})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        body = self._read_json()
        if parsed.path == "/connectors":
            name = str(body.get("name") or "")
            if not name:
                self._json(400, {"ok": False, "reason": "name_required"})
                return
            state = switch_connector(name, bool(body.get("enabled", True)))
            self._json(200, {"ok": True, "connectors": state})
            return
        if parsed.path == "/publish":
            source = str(body.get("source") or "http_seat")
            topic = str(body.get("topic") or _CIRCULATION)
            payload = body.get("payload") if isinstance(body.get("payload"), dict) else {"value": body.get("payload")}
            thought = get_thought_bus().publish(Thought(source=source, topic=topic, payload=payload))
            self._json(200, {"ok": True, "id": thought.id})
            return
        if parsed.path == "/self-code":
            result = propose_self_code(str(body.get("path") or ""), str(body.get("reason") or ""))
            self._json(200 if result.get("accepted") else 400, result)
            return
        self._json(404, {"ok": False})


def circulation_status() -> dict[str, Any]:
    with _LOCK:
        return {
            "started": bool(_STATE.get("started")),
            "port": _STATE.get("port"),
            "loops": dict(_STATE.get("loops") or {}),
            "error": _STATE.get("error"),
            "url": None if not _STATE.get("port") else f"http://{_HOST}:{_STATE['port']}/health",
        }


def start_organism_circulation(port: int | None = None) -> dict[str, Any]:
    """Start the listener, the organ loops, and the default connectors."""
    with _LOCK:
        already = bool(_STATE.get("started") and _STATE.get("thread") and _STATE["thread"].is_alive())
        if not already:
            _STATE["inbox"] = {}
            _STATE["self_model_seen"] = {}
            _STATE["consume_count"] = {}
            _STATE["latency_samples"] = []
            _STATE["audit_consumed"] = {"metacognition": [], "self_repair": []}
            _reset_audit_effects()
            _STATE["error"] = None
            stop = threading.Event()
            _STATE["stop"] = stop
    ensure_audit_subscribers()
    if already:
        return circulation_status()

    for name in _DEFAULT_CONNECTORS:
        switch_connector(name, True)

    chosen = port
    if chosen is None:
        chosen = int(os.environ.get("AUREON_ORGANISM_HTTP_PORT", str(_DEFAULT_PORT)))
    server: ThreadingHTTPServer | None = None
    http_thread: threading.Thread | None = None
    try:
        server = _ReuseServer((_HOST, chosen), _Handler)
        http_thread = threading.Thread(target=server.serve_forever, name="organism-http", daemon=True)
        http_thread.start()
        bound = int(server.server_address[1])
    except OSError as exc:
        detail = exc.strerror or str(exc)
        message = (
            f"organism circulation failed to bind {_HOST}:{chosen} ({detail}); "
            "the fusion seat keeps 8765"
        )
        print(message, file=sys.stderr, flush=True)
        with _LOCK:
            _STATE["error"] = message
            _STATE["started"] = False
            _STATE["port"] = None
            _STATE["server"] = None
        return circulation_status()

    _publish_tick(0)
    meta = threading.Thread(target=_metacognition_loop, args=(stop,), name="metacognition-loop", daemon=True)
    meta.start()
    repair = threading.Thread(target=_self_repair_loop, args=(stop,), name="self-repair-loop", daemon=True)
    repair.start()
    thread = threading.Thread(target=_loop, args=(stop,), name="organism-circulation", daemon=True)
    thread.start()
    with _LOCK:
        _STATE.update(
            started=True,
            server=server,
            thread=thread,
            http_thread=http_thread,
            port=bound,
            error=None,
        )
    return circulation_status()


def stop_organism_circulation() -> None:
    with _LOCK:
        stop = _STATE.get("stop")
        server = _STATE.get("server")
        thread = _STATE.get("thread")
        _STATE["started"] = False
    if stop is not None:
        stop.set()
    if server is not None:
        server.shutdown()
        server.server_close()
    if thread is not None:
        thread.join(timeout=2.0)
    with _LOCK:
        _STATE["server"] = None
        _STATE["thread"] = None
        _STATE["http_thread"] = None


def main() -> int:
    """Bind the circulation seat and stay up. Exit 1 when the port is taken."""
    status = start_organism_circulation()
    if not status.get("started") or status.get("port") is None:
        if not status.get("error"):
            print(
                "organism circulation failed to bind 127.0.0.1:8799; the fusion seat keeps 8765",
                file=sys.stderr,
                flush=True,
            )
        return 1
    print(f"organism circulation listening on {status['url']}", flush=True)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        stop_organism_circulation()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
