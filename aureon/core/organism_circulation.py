"""Organism circulation — one thought bus, every named seat publishing and listening.

The HTTP seat listens on 127.0.0.1:8765 (override with AUREON_ORGANISM_HTTP_PORT).
metacognition, queen reasoning, logic, neural, lighthouse, QGITA, mycelium,
baton relay, and council each subscribe to ``organism.circulation`` and
publish their own pulse. Connectors switch on at boot. Self-code records a
proposal; it does not edit the repo and it does not arm live trading.
"""

from __future__ import annotations

import json
import os
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
_DEFAULT_PORT = 8765
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

_DEFAULT_CONNECTORS = {
    "thought_bus": True,
    "http_seat": True,
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
_META: dict[str, Any] = {"truth_status": "loop_running", "loop": "running"}


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


def _on_circulation(thought: Thought) -> None:
    """Every other seat hears the pulse. Receipts stay in memory so the log is not a storm."""
    source = str(getattr(thought, "source", "") or "")
    topic = str(getattr(thought, "topic", "") or "")
    if topic != _CIRCULATION:
        return
    for organ in ORGANS:
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
                    "ts": time.time(),
                }
            )
            del heard[:-50]


def _metacognition_loop(stop: threading.Event) -> None:
    while not stop.is_set():
        reading = _metacognition_reading()
        reading["loop"] = "running"
        with _LOCK:
            _META.update(reading)
        stop.wait(5.0)


def _loop(stop: threading.Event) -> None:
    bus = get_thought_bus()
    tick = 0
    while not stop.is_set():
        connectors = connector_state()
        if connectors.get("thought_bus", True):
            for organ in ORGANS:
                if not connectors.get(organ["name"], True):
                    continue
                bus.publish(
                    Thought(
                        source=organ["name"],
                        topic=_CIRCULATION,
                        payload=_payload_for(organ, tick),
                    )
                )
            with _LOCK:
                _STATE["loops"] = {
                    organ["name"]: "running" for organ in ORGANS if connectors.get(organ["name"], True)
                }
        tick += 1
        stop.wait(1.0)


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
        if parsed.path in ("/health", "/"):
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
        if _STATE.get("started") and _STATE.get("thread") and _STATE["thread"].is_alive():
            return circulation_status()
        _STATE["inbox"] = {}
        _STATE["error"] = None
        stop = threading.Event()
        _STATE["stop"] = stop

    for name in _DEFAULT_CONNECTORS:
        switch_connector(name, True)

    global _SUBSCRIBED
    bus = get_thought_bus()
    if not _SUBSCRIBED:
        bus.subscribe(_CIRCULATION, _on_circulation)
        _SUBSCRIBED = True

    chosen = port
    if chosen is None:
        chosen = int(os.environ.get("AUREON_ORGANISM_HTTP_PORT", str(_DEFAULT_PORT)))
    server: ThreadingHTTPServer | None = None
    http_thread: threading.Thread | None = None
    try:
        server = ThreadingHTTPServer((_HOST, chosen), _Handler)
        http_thread = threading.Thread(target=server.serve_forever, name="organism-http", daemon=True)
        http_thread.start()
        bound = int(server.server_address[1])
    except OSError as exc:
        bound = None
        with _LOCK:
            _STATE["error"] = f"thought bus port unavailable: {exc}"

    meta = threading.Thread(target=_metacognition_loop, args=(stop,), name="metacognition-loop", daemon=True)
    meta.start()
    thread = threading.Thread(target=_loop, args=(stop,), name="organism-circulation", daemon=True)
    thread.start()
    with _LOCK:
        _STATE.update(
            started=True,
            server=server,
            thread=thread,
            http_thread=http_thread,
            port=bound,
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
