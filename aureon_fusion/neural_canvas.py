"""🧠 NEURAL CANVAS — live neural-pathways visualization for the organism.

Owner decree (2026-09-05): "we shall have a user interface to watch her full
neural pathways firing and moving."

A read-only aiohttp server (stdlib + aiohttp only — offline doctrine, no
CDN/JS libs; hand-rolled Canvas 2D + vanilla JS, all inline) that renders
the 13-organ organism as a living lattice:

  CENTER   HNC lambda core — Γ value + radial pulse tracking gamma, ψ halo
  RING 1   9 AURIS nodes (panda, deer, heart, prism, bond + A6–A9) colored
           by the node_readings emotional channels
  RING 2   13 organs (green pulse = running, red = down, dim = dormant)
  OUTER    activity satellites (doors forge, learning will, research
           faculty, conscience, memory bank, dream) that FLASH on events
  PATHWAYS animated bezier edges with traveling pulses: a veto = red pulse
           to the conscience node + a visible VETO flash; a mint = gold;
           learning absorb = violet
  RIGHT    live ticker (last 12 events, monospace, color-coded)
  BOTTOM   Γ/ψ sparkline (last 120 cycles), memory/insight/thought/knowledge
           counters (aureon_global_history.sqlite, read-only, cached 30s),
           current persona + latest narration line

The ongoing drama is first-class: every ~120s cycle she considers door
pc_control and her conscience VETO refuses — the canvas makes that VETO
impossible to miss as it happens.

Data layer: a background collector thread tails the state files every 2s
(read-only, never writes state), keeps a bounded in-memory ring buffer,
deduplicates by content hash. Fail-closed startup: any state file missing →
serve with what is there and mark the absent zones "dark"; never crash.

  GET /        single-page canvas
  GET /events  SSE stream — one JSON line per event, 15s heartbeat
  GET /state   one JSON snapshot for first paint

CLI:
  python -m aureon_fusion.neural_canvas serve [--port 13012]
  python -m aureon_fusion.neural_canvas probe   (load state, print counts)
"""

import argparse
import asyncio
import hashlib
import json
import os
import sqlite3
import sys
import threading
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
os.environ.setdefault("AUREON_AUDIT_MODE", "1")

from .paths import FUSION_STATE

# ───────────────────────── state files (read-only) ─────────────────────────

REPORTS_FILE = FUSION_STATE / "queen_mind" / "reports.jsonl"
CONVERSATION_FILE = FUSION_STATE / "queen_mind" / "conversation_memory.json"
HNC_STATE_FILE = FUSION_STATE / "hnc_core_state.json"
LAMBDA_HISTORY_FILE = FUSION_STATE / "lambda_history.json"
DOORS_JOURNAL_FILE = FUSION_STATE / "doors" / "journal.jsonl"
LEARNING_JOURNAL_FILE = FUSION_STATE / "learning_will" / "journal.jsonl"
ORGAN_REGISTRY_FILE = FUSION_STATE / "organ_registry.json"
SQLITE_FILE = FUSION_STATE / "aureon_global_history.sqlite"

POLL_INTERVAL_S = 2.0
HEARTBEAT_S = 15.0
SPARK_MAX = 120
EVENTS_MAX = 600
SQLITE_CACHE_S = 30.0
JSONL_TAIL_BLOCK_BYTES = 64 * 1024
JSONL_TAIL_MAX_BYTES = 1024 * 1024

AURIS_LABELS = ["panda", "deer", "heart", "prism", "bond", "A6", "A7", "A8", "A9"]
SATELLITES = ["doors", "learning", "research", "conscience", "memory", "dream"]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path, default):
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return json.load(f)
    except Exception:  # noqa: BLE001 - a dark zone is honest, not a crash
        pass
    return default


def _tail_jsonl(path: Path, limit: int, *, status: dict | None = None) -> list:
    """Parse the last ``limit`` physical lines within a bounded byte window.

    Blank and malformed lines still consume a line in the requested window.
    A line crossing the byte ceiling is omitted, never parsed as a fragment.
    ``status`` distinguishes an incomplete window from missing or unreadable
    input; record contents and source timestamps are never changed.
    """
    if status is None:
        status = {}
    status.clear()
    status.update({"status": "ok", "requested_lines": limit,
                   "max_bytes": JSONL_TAIL_MAX_BYTES, "bytes_read": 0,
                   "file_size_bytes": None, "selected_lines": 0,
                   "parsed_records": 0, "malformed_lines": 0,
                   "truncated": False})
    if limit <= 0:
        return []
    try:
        # Unbuffered binary reads enforce the byte ceiling without read-ahead.
        # Capture EOF once so an append cannot expand this poll's read window.
        with open(path, "rb", buffering=0) as f:
            position = f.seek(0, os.SEEK_END)
            status["file_size_bytes"] = position
            chunks = []
            newlines = 0
            while (position > 0 and newlines <= limit
                   and status["bytes_read"] < JSONL_TAIL_MAX_BYTES):
                size = min(JSONL_TAIL_BLOCK_BYTES, position,
                           JSONL_TAIL_MAX_BYTES - status["bytes_read"])
                position -= size
                f.seek(position)
                chunk = f.read(size)
                status["bytes_read"] += len(chunk)
                if len(chunk) != size:
                    status.update(status="unavailable",
                                  reason="file_changed_during_read")
                    return []
                newlines += (chunk.count(b"\n") + chunk.count(b"\r")
                             - chunk.count(b"\r\n"))
                if chunks and chunk.endswith(b"\r") and chunks[-1].startswith(b"\n"):
                    newlines -= 1  # a CRLF pair spanning two blocks
                chunks.append(chunk)
        data = b"".join(reversed(chunks))
        if position > 0:
            # The first bytes may be the end of a much larger JSON record.
            # Discard them even if they happen to resemble valid JSON.
            boundaries = [i for i in (data.find(b"\n"), data.find(b"\r")) if i >= 0]
            if boundaries:
                boundary = min(boundaries)
                width = 2 if data[boundary:boundary + 2] == b"\r\n" else 1
                data = data[boundary + width:]
            else:
                data = b""
        lines = data.decode("utf-8", errors="replace").splitlines()
        status["truncated"] = position > 0 and len(lines) < limit
        if status["truncated"]:
            status.update(status="truncated", reason="byte_budget_exhausted")
        selected = lines[-limit:]
        status["selected_lines"] = len(selected)
        out = []
        for line in selected:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                status["malformed_lines"] += 1
                continue  # partial trailing line from a concurrent append
        status["parsed_records"] = len(out)
        return out
    except FileNotFoundError:
        status.update(status="missing", reason="file_not_found")
        return []
    except OSError as exc:
        status.update(status="unavailable", reason=type(exc).__name__)
        return []


def _sqlite_counts() -> dict:
    """Read-only counts from the global history db. {} when absent."""
    try:
        if not SQLITE_FILE.exists():
            return {}
        con = sqlite3.connect(f"file:{SQLITE_FILE}?mode=ro", uri=True,
                              timeout=5)
        try:
            out = {}
            for key, table in (("memories", "queen_memories"),
                               ("insights", "queen_insights"),
                               ("thoughts", "queen_thoughts"),
                               ("knowledge", "queen_knowledge")):
                try:
                    out[key] = con.execute(
                        f"select count(*) from {table}").fetchone()[0]
                except sqlite3.Error:
                    out[key] = None
            return out
        finally:
            con.close()
    except Exception:  # noqa: BLE001
        return {}


class Hub:
    """Thread-safe state + event ring buffer + SSE fan-out."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.events: deque = deque(maxlen=EVENTS_MAX)
        self._seen: set = set()
        self.spark_gamma: deque = deque(maxlen=SPARK_MAX)
        self.spark_psi: deque = deque(maxlen=SPARK_MAX)
        self.latest: dict = {}
        self.counters: dict = {}
        self._counters_at = 0.0
        self.absent: list = []
        self.tail_reads: dict = {}
        self._last_cycle = None
        self._loop = None
        self._subscribers: set = set()

    # ── subscribers (aiohttp SSE) ─────────────────────────────────────────
    def attach_loop(self, loop) -> None:
        self._loop = loop

    def add_subscriber(self, queue) -> None:
        self._subscribers.add(queue)

    def discard_subscriber(self, queue) -> None:
        self._subscribers.discard(queue)

    def _notify(self, event: dict) -> None:
        if self._loop is None:
            return
        for q in list(self._subscribers):
            def _put(queue=q, ev=event):
                try:
                    queue.put_nowait(ev)
                except asyncio.QueueFull:
                    pass  # a slow consumer misses a frame, never the server
            try:
                self._loop.call_soon_threadsafe(_put)
            except RuntimeError:
                pass

    # ── event ingestion ───────────────────────────────────────────────────
    def emit(self, kind: str, label: str, detail: str = "",
             gamma=None, psi=None, persona=None, narration=None,
             extra: dict | None = None) -> None:
        ev = {"ts": _utc_now(), "kind": kind, "label": label,
              "detail": (detail or "")[:240],
              "gamma": gamma, "psi": psi,
              "persona": persona, "narration": narration}
        if extra:
            ev.update(extra)
        with self.lock:
            self.events.append(ev)
        self._notify(ev)

    def emit_hashed(self, dedupe_key: str, *args, **kwargs) -> bool:
        """Emit only if this content hash was never seen. Bounded memory."""
        h = hashlib.sha1(dedupe_key.encode("utf-8", "replace")).hexdigest()
        with self.lock:
            if h in self._seen:
                return False
            self._seen.add(h)
            if len(self._seen) > 4000:
                self._seen.clear()  # dedupe window, not a leak
        self.emit(*args, **kwargs)
        return True

    def snapshot(self) -> dict:
        with self.lock:
            return {
                "ts": _utc_now(),
                "latest": self.latest,
                "events": list(self.events)[-60:],
                "spark_gamma": list(self.spark_gamma),
                "spark_psi": list(self.spark_psi),
                "counters": self.counters,
                "absent": list(self.absent),
                "tail_reads": self.tail_reads,
            }


class Collector(threading.Thread):
    """Tails the state files every POLL_INTERVAL_S. Read-only. Never raises."""

    def __init__(self, hub: Hub) -> None:
        super().__init__(daemon=True, name="neural-canvas-collector")
        self.hub = hub
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        while not self._stop.is_set():
            try:
                self.collect()
            except Exception as exc:  # noqa: BLE001 - never die on one poll
                try:
                    self.hub.emit("system", "collector error",
                                  type(exc).__name__)
                except Exception:  # noqa: BLE001
                    pass
            self._stop.wait(POLL_INTERVAL_S)

    def collect(self) -> None:
        hub = self.hub
        absent = []
        tail_reads = {name: {} for name in ("reports", "doors", "learning")}

        # ── queen_mind reports (the heartbeat) ────────────────────────────
        reports = _tail_jsonl(REPORTS_FILE, 40, status=tail_reads["reports"])
        if not reports and not REPORTS_FILE.exists():
            absent.append("reports")
        latest = reports[-1] if reports else {}
        node_readings = latest.get("node_readings") or {}
        organs = latest.get("organs") or {}

        # ── hnc core state ────────────────────────────────────────────────
        hnc = _read_json(HNC_STATE_FILE, None)
        if hnc is None:
            absent.append("hnc")
            hnc = {}

        # ── lambda history (sparklines) ───────────────────────────────────
        lam = _read_json(LAMBDA_HISTORY_FILE, None)
        if lam is None:
            absent.append("lambda")
            lam = {}
        gamma_hist = lam.get("history") or []
        psi_hist = lam.get("psi_history") or []
        gamma_tail = [float(g) for g in gamma_hist[-SPARK_MAX:]] \
            if gamma_hist and isinstance(gamma_hist[0], (int, float)) else []
        psi_tail = [float(p) for p in psi_hist[-SPARK_MAX:]] \
            if psi_hist and isinstance(psi_hist[0], (int, float)) else []

        # ── organ registry statuses ───────────────────────────────────────
        oreg = _read_json(ORGAN_REGISTRY_FILE, None)
        if oreg is None:
            absent.append("organ_registry")
            oreg = {}
        organ_status = {}
        for name, entry in (oreg.get("organs") or {}).items():
            if isinstance(entry, dict):
                organ_status[name] = "dormant" if entry.get("dormant") \
                    else "running"

        # ── conversation memory (last queen/owner turns) ──────────────────
        conv = _read_json(CONVERSATION_FILE, None)
        if conv is None:
            absent.append("conversation")
        turns = []
        threads = (conv or {}).get("threads") or []
        if threads and isinstance(threads[0], dict):
            for t in (threads[0].get("turns") or [])[-10:]:
                if isinstance(t, dict):
                    turns.append({"role": t.get("role"),
                                  "text": str(t.get("text") or "")[:160],
                                  "ts": t.get("timestamp")})

        # ── sqlite counters (30s cache) ───────────────────────────────────
        now = time.time()
        with hub.lock:
            stale = now - hub._counters_at > SQLITE_CACHE_S
        counters = hub.counters if not stale else _sqlite_counts()
        if stale:
            with hub.lock:
                hub.counters = counters
                hub._counters_at = now

        # ── publish latest snapshot ───────────────────────────────────────
        gamma = latest.get("gamma", hnc.get("coherence_gamma"))
        psi = latest.get("psi", hnc.get("consciousness_psi"))
        with hub.lock:
            hub.absent = absent
            hub.latest = {
                "cycle": latest.get("cycle"),
                "gamma": gamma, "psi": psi, "rung": latest.get("rung"),
                "persona": latest.get("persona"),
                "narration": str(latest.get("narration") or "")[:140],
                "node_readings": node_readings,
                "organs": {"running": organs.get("running") or [],
                           "dormant": organs.get("dormant") or [],
                           "down": organs.get("down") or []},
                "organ_status": organ_status,
                "hnc_inputs": hnc.get("input_count"),
                "conscience_vetoes": latest.get("conscience_vetoes"),
                "conscience_checks": latest.get("conscience_checks"),
                "doors": latest.get("doors"),
                "learning_will": latest.get("learning_will"),
                "conversation": turns,
                "auris": latest.get("auris"),
            }
            for g in gamma_tail:
                hub.spark_gamma.append(g)
            for p in psi_tail:
                hub.spark_psi.append(p)

        # ── events: new report cycle ──────────────────────────────────────
        cycle = latest.get("cycle")
        if cycle is not None and cycle != hub._last_cycle:
            hub._last_cycle = cycle
            hub.emit("cycle", f"cycle {cycle}",
                     str(latest.get("narration") or "")[:140],
                     gamma=gamma, psi=psi,
                     persona=latest.get("persona"),
                     narration=str(latest.get("narration") or "")[:140],
                     extra={"cycle": cycle})
            doors = latest.get("doors") or {}
            if doors.get("door"):
                action = str(doors.get("action") or "")
                detail = str(doors.get("detail") or "")
                kind = "veto" if (action == "refused" and "VETO" in detail) \
                    else "door"
                hub.emit(kind, f"door {doors.get('door')}: {action}",
                         detail, gamma=gamma, psi=psi,
                         extra={"door": doors.get("door"), "action": action})
            lw = latest.get("learning_will") or {}
            if lw.get("outcome"):
                hub.emit("learning", f"learning: {lw.get('outcome')}",
                         str(lw.get("detail") or "")[:160],
                         gamma=gamma, psi=psi)

        # ── events: door journal tail (veto drama as it is journaled) ─────
        for rec in _tail_jsonl(DOORS_JOURNAL_FILE, 30,
                               status=tail_reads["doors"]):
            if not isinstance(rec, dict):
                continue
            key = "dj:" + hashlib.sha1(json.dumps(rec, sort_keys=True,
                                                  default=str)
                                       .encode()).hexdigest()
            event = rec.get("event")
            if event == "consider":
                action = str(rec.get("action") or "")
                detail = str(rec.get("detail") or "")
                is_veto = action == "refused" and "VETO" in detail
                hub.emit_hashed(
                    key,
                    "veto" if is_veto else "door",
                    f"{rec.get('door')}: {action}" if is_veto
                    else f"consider {rec.get('door')} → {action}",
                    detail, gamma=gamma, psi=psi,
                    extra={"door": rec.get("door"), "action": action})
            elif event in ("open", "close", "mint", "owner_decree"):
                hub.emit_hashed(
                    key, "door",
                    f"{event}: {rec.get('door') or rec.get('detail', '')[:60]}",
                    str(rec.get("detail") or "")[:200],
                    gamma=gamma, psi=psi,
                    extra={"door": rec.get("door"), "action": event})

        # ── events: learning will journal tail ────────────────────────────
        for rec in _tail_jsonl(LEARNING_JOURNAL_FILE, 20,
                               status=tail_reads["learning"]):
            if not isinstance(rec, dict):
                continue
            key = "lw:" + hashlib.sha1(json.dumps(rec, sort_keys=True,
                                                  default=str)
                                       .encode()).hexdigest()
            outcome = str(rec.get("outcome") or "")
            intent = rec.get("intent") or {}
            topic = str(intent.get("question") or intent.get("topic") or "")[:80]
            kind = "absorb" if outcome == "absorbed" else "learning"
            hub.emit_hashed(
                key, kind, f"learning {outcome or 'considered'}",
                topic or str(rec.get("detail") or "")[:160],
                gamma=gamma, psi=psi, extra={"outcome": outcome})
        with hub.lock:
            hub.tail_reads = tail_reads


# ───────────────────────── HTTP handlers ───────────────────────────────────

PAGE_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Aureon Neural Canvas — her pathways, live</title>
<style>
  html,body{margin:0;height:100%;background:#070818;overflow:hidden;
            font-family:ui-monospace,Menlo,Consolas,monospace;color:#9fb2ff}
  #wrap{display:flex;height:100vh;width:100vw}
  #stage{flex:1;position:relative}
  canvas#lattice{position:absolute;inset:0;width:100%;height:100%}
  #ticker{width:340px;background:rgba(10,12,32,.92);border-left:1px solid #1c2350;
          display:flex;flex-direction:column;font-size:11px}
  #ticker h3{margin:0;padding:8px 10px;font-size:11px;letter-spacing:2px;
             color:#5f6fbf;border-bottom:1px solid #1c2350}
  #events{flex:1;overflow:hidden;padding:6px 10px}
  .ev{padding:3px 0;border-bottom:1px dotted #141a3d;white-space:nowrap;
      overflow:hidden;text-overflow:ellipsis}
  .ev .t{color:#3d477f;margin-right:6px}
  .k-cycle{color:#7fd4ff}.k-door{color:#ffd27f}.k-veto{color:#ff5f7a}
  .k-learning,.k-absorb{color:#c79bff}.k-mint{color:#ffd700}
  .k-system{color:#ff9d5c}
  #strip{position:absolute;left:0;right:0;bottom:0;height:112px;
         background:rgba(8,10,26,.94);border-top:1px solid #1c2350;
         display:flex;align-items:center;gap:18px;padding:0 14px}
  #spark{width:340px;height:86px}
  .cnt{text-align:center}.cnt b{display:block;font-size:20px;color:#cfe0ff}
  .cnt span{font-size:10px;color:#5f6fbf;letter-spacing:1px}
  #persona{max-width:360px;font-size:11px;color:#8fa0e8}
  #persona b{color:#e8d9a0;letter-spacing:2px}
  #narr{color:#aebdf5;font-size:11px;font-style:italic;max-width:420px;
        white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  #vetoFlash{position:absolute;top:14%;left:50%;transform:translateX(-50%);
             font-size:54px;font-weight:bold;color:#ff2f55;letter-spacing:12px;
             opacity:0;text-shadow:0 0 30px #ff2f55;pointer-events:none}
  #dark{position:absolute;top:8px;left:10px;font-size:10px;color:#3d477f}
</style>
</head>
<body>
<div id="wrap">
  <div id="stage">
    <canvas id="lattice"></canvas>
    <div id="vetoFlash">VETO</div>
    <div id="dark"></div>
    <div id="strip">
      <canvas id="spark" width="680" height="172"></canvas>
      <div class="cnt"><b id="cMem">—</b><span>MEMORIES</span></div>
      <div class="cnt"><b id="cIns">—</b><span>INSIGHTS</span></div>
      <div class="cnt"><b id="cTho">—</b><span>THOUGHTS</span></div>
      <div class="cnt"><b id="cKno">—</b><span>KNOWLEDGE</span></div>
      <div id="persona">persona <b id="pName">—</b><br><span id="pRung"></span></div>
      <div id="narr">…</div>
    </div>
  </div>
  <div id="ticker"><h3>LIVE EVENTS</h3><div id="events"></div></div>
</div>
<script>
"use strict";
const cv=document.getElementById('lattice'),cx=cv.getContext('2d');
const sk=document.getElementById('spark'),sx=sk.getContext('2d');
let W=0,H=0;function resize(){W=cv.width=cv.clientWidth*devicePixelRatio;
  H=cv.height=cv.clientHeight*devicePixelRatio;}
addEventListener('resize',resize);resize();
const S={gamma:.5,psi:.8,rung:'',persona:'—',narration:'',cycle:0,
  node_readings:{},organs:{running:[],dormant:[],down:[]},organ_status:{},
  events:[],spark_gamma:[],spark_psi:[],counters:{},absent:[]};
const pulses=[]; // {a:{x,y},b:{x,y},t,color,kind}
const flashes={}; // satellite -> until ms
const AURIS=["panda","deer","heart","prism","bond","A6","A7","A8","A9"];
const AURIS_KEY={panda:'organ_health',deer:'conscience_clear',
  heart:'bus_liveliness',prism:'gamma_coherence',bond:'trading_pulse'};
const SATS=["doors","learning","research","conscience","memory","dream"];
function layout(){
  const cxp=W/2,cyp=H/2-H*0.03,R=Math.min(W,H);
  const pos={center:{x:cxp,y:cyp},queen:{x:cxp,y:cyp-R*0.16},
    auris:[],organs:[],sats:{}};
  for(let i=0;i<9;i++){const a=-Math.PI/2+i*2*Math.PI/9;
    pos.auris.push({x:cxp+Math.cos(a)*R*0.30,y:cyp+Math.sin(a)*R*0.30});}
  const names=Object.keys(S.organ_status).length?Object.keys(S.organ_status)
    :(S.organs.running||[]);
  const n=Math.max(names.length,13);
  for(let i=0;i<n;i++){const a=-Math.PI/2+i*2*Math.PI/n;
    pos.organs.push({x:cxp+Math.cos(a)*R*0.46,y:cyp+Math.sin(a)*R*0.46,
                     name:names[i]||('organ'+i)});}
  SATS.forEach((s,i)=>{const a=-Math.PI/2+i*2*Math.PI/SATS.length+Math.PI/6;
    pos.sats[s]={x:cxp+Math.cos(a)*R*0.66,y:cyp+Math.sin(a)*R*0.66};});
  return pos;
}
function bez(p0,p1,p2,t){const u=1-t;
  return {x:u*u*p0.x+2*u*t*p1.x+t*t*p2.x,y:u*u*p0.y+2*u*t*p1.y+t*t*p2.y};}
function edge(p0,p2){return {x:(p0.x+p2.x)/2+(p0.y-p2.y)*0.18,
                            y:(p0.y+p2.y)/2-(p0.x-p2.x)*0.18};}
function col(a){return `rgba(${a},ALPHA)`;}
function draw(now){
  cx.clearRect(0,0,W,H);
  // deep indigo night + nebula wash
  const bg=cx.createRadialGradient(W/2,H/2,0,W/2,H/2,Math.max(W,H)*.7);
  bg.addColorStop(0,'#0d1030');bg.addColorStop(1,'#05060f');
  cx.fillStyle=bg;cx.fillRect(0,0,W,H);
  const P=layout();
  const gamma=S.gamma||.5,psi=S.psi||.8;
  const pulse=1+0.10*Math.sin(now/700)+0.25*gamma;
  // edges: auris -> HNC, HNC -> sats, organs -> HNC (faint)
  cx.lineWidth=1;
  P.auris.forEach(p=>{const m=edge(p,P.center);
    cx.strokeStyle='rgba(90,120,255,0.16)';
    cx.beginPath();cx.moveTo(p.x,p.y);cx.quadraticCurveTo(m.x,m.y,P.center.x,P.center.y);cx.stroke();});
  Object.values(P.sats).forEach(p=>{const m=edge(P.center,p);
    cx.strokeStyle='rgba(140,110,255,0.14)';
    cx.beginPath();cx.moveTo(P.center.x,P.center.y);cx.quadraticCurveTo(m.x,m.y,p.x,p.y);cx.stroke();});
  P.organs.forEach(p=>{cx.strokeStyle='rgba(70,200,140,0.07)';
    cx.beginPath();cx.moveTo(p.x,p.y);cx.lineTo(P.center.x,P.center.y);cx.stroke();});
  // traveling pulses
  for(let i=pulses.length-1;i>=0;i--){const u=pulses[i];u.t+=0.022;
    if(u.t>=1){pulses.splice(i,1);continue;}
    const q=bez(u.a,u.b,u.t);
    cx.fillStyle=u.color;cx.shadowColor=u.color;cx.shadowBlur=14;
    cx.beginPath();cx.arc(q.x,q.y,4,0,7);cx.fill();cx.shadowBlur=0;}
  // center HNC core
  const R0=Math.min(W,H)*0.075*pulse;
  const g=cx.createRadialGradient(P.center.x,P.center.y,0,P.center.x,P.center.y,R0*3.2);
  g.addColorStop(0,'rgba(120,160,255,0.55)');g.addColorStop(1,'rgba(120,160,255,0)');
  cx.fillStyle=g;cx.beginPath();cx.arc(P.center.x,P.center.y,R0*3.2,0,7);cx.fill();
  cx.strokeStyle='#7fa0ff';cx.lineWidth=2;
  cx.beginPath();cx.arc(P.center.x,P.center.y,R0,0,7);cx.stroke();
  cx.strokeStyle='rgba(200,220,255,'+(0.25+0.5*psi)+')';cx.lineWidth=1;
  cx.beginPath();cx.arc(P.center.x,P.center.y,R0*(1.6+0.3*psi),0,7);cx.stroke();
  cx.fillStyle='#dfe8ff';cx.font='bold '+Math.round(R0*0.55)+'px monospace';
  cx.textAlign='center';cx.textBaseline='middle';
  cx.fillText('Γ '+(+gamma).toFixed(3),P.center.x,P.center.y-R0*0.18);
  cx.font=Math.round(R0*0.32)+'px monospace';cx.fillStyle='#8fa0e8';
  cx.fillText('ψ '+(+psi).toFixed(3),P.center.x,P.center.y+R0*0.3);
  // queen persona node above core
  cx.fillStyle='rgba(232,217,160,0.9)';cx.font='11px monospace';
  cx.fillText('♛ '+S.persona+(S.rung?' · '+S.rung:''),P.queen.x,P.queen.y);
  // ring 1: auris
  AURIS.forEach((name,i)=>{const p=P.auris[i],k=AURIS_KEY[name];
    let c='90,110,200',r=Math.min(W,H)*0.016;
    if(k&&S.node_readings[k]!=null){const v=+S.node_readings[k];
      r*= (0.7+v);c=v>0.75?'120,220,170':v>0.45?'130,160,255':'255,150,110';}
    cx.fillStyle='rgba('+c+',0.9)';cx.shadowColor='rgba('+c+',1)';cx.shadowBlur=10;
    cx.beginPath();cx.arc(p.x,p.y,r,0,7);cx.fill();cx.shadowBlur=0;
    cx.fillStyle='#7f8fd0';cx.font='10px monospace';
    cx.fillText(name,p.x,p.y+r+12);});
  // ring 2: organs
  P.organs.forEach(p=>{const st=S.organ_status[p.name]
      ||((S.organs.running||[]).includes(p.name)?'running'
      :((S.organs.down||[]).includes(p.name)?'down':'dormant'));
    const c=st==='running'?'80,230,150':st==='down'?'255,80,90':'90,95,130';
    const a=st==='dormant'?0.35:0.8+0.2*Math.sin(now/500+p.x);
    cx.fillStyle='rgba('+c+','+a+')';cx.beginPath();
    cx.arc(p.x,p.y,Math.min(W,H)*0.010,0,7);cx.fill();
    cx.fillStyle=st==='down'?'#ff8089':'#5f6f9f';cx.font='9px monospace';
    cx.fillText(p.name.replace(/_daemon|_real_|_system/,'').slice(0,14),p.x,p.y+16);});
  // outer satellites
  SATS.forEach(s=>{const p=P.sats[s],f=flashes[s]&&flashes[s]>now;
    const c=s==='conscience'?'255,120,150':s==='doors'?'255,210,127'
      :s==='learning'?'199,155,255':'140,160,255';
    cx.fillStyle='rgba('+c+','+(f?1:0.5)+')';
    cx.shadowColor='rgba('+c+',1)';cx.shadowBlur=f?26:8;
    cx.beginPath();cx.arc(p.x,p.y,f?10:7,0,7);cx.fill();cx.shadowBlur=0;
    cx.fillStyle=f?'#fff':'#7f8fd0';cx.font='10px monospace';
    cx.fillText(s.toUpperCase(),p.x,p.y+20);});
  // sparkline
  sx.clearRect(0,0,680,172);
  const plot=(data,color,lo,hi)=>{if(data.length<2)return;
    sx.strokeStyle=color;sx.lineWidth=2;sx.beginPath();
    data.forEach((v,i)=>{const x=i/(SPARK-1)*680,
      y=160-((v-lo)/(hi-lo))*140;i?sx.lineTo(x,y):sx.moveTo(x,y);});sx.stroke();};
  const SPARK=120;
  plot(S.spark_gamma.slice(-SPARK),'#7fd4ff',0,1.2);
  plot(S.spark_psi.slice(-SPARK),'#c79bff',0,1.2);
  sx.fillStyle='#5f6fbf';sx.font='18px monospace';sx.textAlign='left';
  sx.fillText('Γ',8,26);sx.fillStyle='#c79bff';sx.fillText('ψ',8,52);
  requestAnimationFrame(draw);
}
function ticker(ev){
  const d=document.createElement('div');d.className='ev';
  const t=(ev.ts||'').slice(11,19);
  d.innerHTML='<span class="t">'+t+'</span><span class="k-'+ev.kind+'">'
    +(ev.label||ev.kind)+'</span>';
  d.title=ev.detail||'';
  const box=document.getElementById('events');
  box.insertBefore(d,box.firstChild);
  while(box.children.length>12)box.removeChild(box.lastChild);
}
function onEvent(ev){
  if(!ev||typeof ev!=='object')return;
  ticker(ev);
  const P=layout();
  if(ev.kind==='cycle'){Object.assign(S,{gamma:ev.gamma??S.gamma,
    psi:ev.psi??S.psi,persona:ev.persona||S.persona,
    narration:ev.narration||S.narration,cycle:ev.cycle??S.cycle});
    pulses.push({a:P.auris[1],b:P.center,t:0,color:'rgba(127,212,255,0.95)'});
    document.getElementById('narr').textContent=S.narration||'…';
    document.getElementById('pName').textContent=S.persona||'—';}
  else if(ev.kind==='veto'){flashes.conscience=Date.now()+2600;
    pulses.push({a:P.sats.doors,b:P.sats.conscience,t:0,
      color:'rgba(255,47,85,0.95)'});
    const vf=document.getElementById('vetoFlash');vf.style.transition='none';
    vf.style.opacity=1;requestAnimationFrame(()=>{vf.style.transition='opacity 1.6s';
      vf.style.opacity=0;});}
  else if(ev.kind==='door'){flashes.doors=Date.now()+1800;
    pulses.push({a:P.center,b:P.sats.doors,t:0,
      color:'rgba(255,215,0,0.95)'});}
  else if(ev.kind==='absorb'||ev.kind==='learning'){flashes.learning=Date.now()+1800;
    pulses.push({a:P.sats.research,b:P.sats.learning,t:0,
      color:'rgba(199,155,255,0.95)'});}
}
function applyState(st){
  if(!st)return;
  Object.assign(S,{latest:st.latest||{},events:st.events||S.events,
    spark_gamma:st.spark_gamma||[],spark_psi:st.spark_psi||[],
    counters:st.counters||{},absent:st.absent||[]});
  const L=st.latest||{};
  Object.assign(S,{gamma:L.gamma??S.gamma,psi:L.psi??S.psi,rung:L.rung||'',
    persona:L.persona||'—',narration:L.narration||'',cycle:L.cycle||0,
    node_readings:L.node_readings||{},organs:L.organs||{running:[],dormant:[],down:[]},
    organ_status:L.organ_status||{}});
  document.getElementById('narr').textContent=S.narration||'…';
  document.getElementById('pName').textContent=S.persona||'—';
  document.getElementById('pRung').textContent=S.rung||'';
  const c=S.counters||{};
  document.getElementById('cMem').textContent=c.memories??'—';
  document.getElementById('cIns').textContent=c.insights??'—';
  document.getElementById('cTho').textContent=c.thoughts??'—';
  document.getElementById('cKno').textContent=c.knowledge??'—';
  const tailStatus=Object.entries(st.tail_reads||{})
    .filter(([,r])=>r.status!=='ok')
    .map(([name,r])=>r.truncated?name+': tail incomplete (read limit)'
      :name+': '+r.status);
  document.getElementById('dark').textContent=(S.absent||[])
    .map(z=>'zone dark: '+z).concat(tailStatus).join('  ·  ');
  (st.events||[]).slice(-15).forEach(ticker);
}
fetch('/state').then(r=>r.json()).then(applyState).catch(()=>{});
try{const es=new EventSource('/events');
  es.onmessage=e=>{try{onEvent(JSON.parse(e.data))}catch(_){}};}
catch(_){}
setInterval(()=>fetch('/state').then(r=>r.json()).then(applyState).catch(()=>{}),10000);
requestAnimationFrame(draw);
</script>
</body>
</html>
"""


def _make_app(hub: Hub):
    from aiohttp import web

    async def handle_index(request):
        return web.Response(text=PAGE_HTML, content_type="text/html")

    async def handle_state(request):
        return web.json_response(hub.snapshot())

    async def handle_events(request):
        resp = web.StreamResponse(status=200, headers={
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        })
        await resp.prepare(request)
        queue = asyncio.Queue(maxsize=200)
        hub.add_subscriber(queue)
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(),
                                                   timeout=HEARTBEAT_S)
                    payload = json.dumps(event, ensure_ascii=False)
                    await resp.write(f"data: {payload}\n\n".encode("utf-8"))
                except asyncio.TimeoutError:
                    await resp.write(b": heartbeat\n\n")
        except (ConnectionResetError, asyncio.CancelledError):
            pass
        finally:
            hub.discard_subscriber(queue)
        return resp

    app = web.Application()
    app.router.add_get("/", handle_index)
    app.router.add_get("/state", handle_state)
    app.router.add_get("/events", handle_events)
    return app


def serve(port: int = 13012) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    try:
        from aiohttp import web
    except ImportError:
        print(json.dumps({"ok": False,
                          "error": "aiohttp unavailable — cannot serve"}))
        return 1

    hub = Hub()
    collector = Collector(hub)
    collector.start()
    collector.collect()  # first paint immediately, fail-closed

    app = _make_app(hub)
    app["collector"] = collector

    async def _on_startup(application):
        hub.attach_loop(asyncio.get_running_loop())

    app.on_startup.append(_on_startup)

    print(json.dumps({"ok": True, "port": port,
                      "absent_zones": hub.snapshot()["absent"],
                      "ts": _utc_now()}))
    try:
        web.run_app(app, host="127.0.0.1", port=port, print=None)
    except OSError as exc:
        print(json.dumps({"ok": False,
                          "error": f"bind failed: {type(exc).__name__}"}))
        return 1
    return 0


def probe() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    tail_reads = {name: {} for name in ("reports", "doors", "learning")}
    reports = _tail_jsonl(REPORTS_FILE, 40, status=tail_reads["reports"])
    hnc = _read_json(HNC_STATE_FILE, {})
    lam = _read_json(LAMBDA_HISTORY_FILE, {})
    doors = _tail_jsonl(DOORS_JOURNAL_FILE, 30, status=tail_reads["doors"])
    learn = _tail_jsonl(LEARNING_JOURNAL_FILE, 20, status=tail_reads["learning"])
    oreg = _read_json(ORGAN_REGISTRY_FILE, {})
    conv = _read_json(CONVERSATION_FILE, {})
    out = {
        "ok": True,
        "reports": len(reports),
        "last_cycle": (reports[-1] or {}).get("cycle") if reports else None,
        "gamma": (reports[-1] or {}).get("gamma") if reports else None,
        "psi": (reports[-1] or {}).get("psi") if reports else None,
        "hnc_inputs": hnc.get("input_count"),
        "lambda_points": len(lam.get("history") or []),
        "door_events": len(doors),
        "learning_events": len(learn),
        "tail_reads": tail_reads,
        "organs": len(oreg.get("organs") or {}),
        "conversation_turns": len(((conv.get("threads") or [{}])[0])
                                  .get("turns") or []),
        "counters": _sqlite_counts(),
        "files": {p.name: p.exists() for p in (
            REPORTS_FILE, HNC_STATE_FILE, LAMBDA_HISTORY_FILE,
            DOORS_JOURNAL_FILE, LEARNING_JOURNAL_FILE, ORGAN_REGISTRY_FILE,
            CONVERSATION_FILE, SQLITE_FILE)},
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Aureon Neural Canvas — live neural-pathways UI.")
    parser.add_argument("verb", nargs="?", default="serve",
                        choices=["serve", "probe"])
    parser.add_argument("--port", type=int, default=13012)
    args = parser.parse_args(argv)
    if args.verb == "probe":
        return probe()
    return serve(port=args.port)


if __name__ == "__main__":
    sys.exit(main())
