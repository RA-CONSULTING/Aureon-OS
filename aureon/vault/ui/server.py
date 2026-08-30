"""
AureonVaultUI — Flask Server for Communicating with the Vault
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

A small Flask HTTP server that exposes the self-feedback vault and its
voice layer as a REST API plus a single-file web UI. Lets the user:

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

Phi-bridge (phone ↔ desktop intranet sync):
  GET  /api/bridge/info        — bridge state, peers, cadence, desktop view
  GET  /api/bridge/peers       — coupled peers only
  POST /api/bridge/register    — register / refresh a peer
  POST /api/bridge/sync        — peer pushes state, gets desktop view back
  POST /api/bridge/drop        — explicit peer disconnect

Phi-bridge mesh (P2P card-level gossip between desktops on the LAN):
  POST /api/bridge/cards           — peers exchange VaultContent cards here
  GET  /api/bridge/mesh/info       — mesh stats (cycles, cards in/out, peers)
  GET  /api/bridge/discovery/peers — peers discovered via UDP LAN broadcast

The discovery + gossip loop start at app boot.

Usage:
    from aureon.vault.ui import create_app, run_server
    run_server(host="127.0.0.1", port=5566)

Or programmatically:
    from aureon.vault import AureonSelfFeedbackLoop
    from aureon.vault.ui import create_app
    loop = AureonSelfFeedbackLoop()
    app = create_app(loop=loop)
    app.run(port=5566)
"""

from __future__ import annotations

import logging
import os
import threading
import time
import uuid
from typing import Any, Dict, Optional

try:
    from flask import Flask, jsonify, request, send_from_directory
    _FLASK_AVAILABLE = True
except Exception:  # pragma: no cover
    Flask = None  # type: ignore[assignment,misc]
    jsonify = None  # type: ignore[assignment]
    request = None  # type: ignore[assignment]
    send_from_directory = None  # type: ignore[assignment]
    _FLASK_AVAILABLE = False

from aureon.harmonic.auris_voice_filter import get_auris_voice_filter
from aureon.harmonic.phi_bridge import get_phi_bridge
from aureon.harmonic.phi_bridge_discovery import (
    DEFAULT_PORT as _DISCOVERY_PORT,
    PhiBridgeDiscovery,
)
from aureon.harmonic.phi_bridge_mesh import get_phi_bridge_mesh
from aureon.harmonic.phi_swarm_router import get_phi_swarm_router
from aureon.queen.conversation_memory import get_conversation_memory
from aureon.queen.meaning_resolver import get_meaning_resolver
from aureon.queen.queen_action_bridge import get_queen_action_bridge
from aureon.vault.self_feedback_loop import AureonSelfFeedbackLoop
from aureon.ollama_config import is_ollama_cloud_url

logger = logging.getLogger("aureon.vault.ui")

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


# ─────────────────────────────────────────────────────────────────────────────
# Error helper
# ─────────────────────────────────────────────────────────────────────────────


def _check_flask() -> None:
    if not _FLASK_AVAILABLE:
        raise RuntimeError(
            "Flask is not installed. Run `pip install flask` to enable the vault UI."
        )


# ─────────────────────────────────────────────────────────────────────────────
# App factory
# ─────────────────────────────────────────────────────────────────────────────


def create_app(
    loop: Optional[AureonSelfFeedbackLoop] = None,
    base_interval_s: float = 1.0,
    enable_voice: bool = True,
    *,
    mesh_discovery: Optional[PhiBridgeDiscovery] = None,
    mesh_port: Optional[int] = None,
    mesh_label: str = "aureon",
    mesh_kind: str = "desktop",
) -> "Flask":
    """
    Create a Flask app bound to a SelfFeedbackLoop.

    If no loop is provided, a fresh one is constructed.

    Mesh wiring:
      PhiBridgeDiscovery (UDP LAN broadcast) and the card-level gossip
      loop start at app boot. Pass ``mesh_discovery`` to inject a pre-
      built discovery (tests use this with a stub transport instead of
      binding real sockets). ``mesh_port`` is the HTTP port this app is
      reachable on — announced so peers know where to POST.
    """
    _check_flask()

    if loop is None:
        loop = AureonSelfFeedbackLoop(
            base_interval_s=base_interval_s,
            enable_voice=enable_voice,
        )

    app = Flask(
        "aureon_vault_ui",
        static_folder=STATIC_DIR,
        static_url_path="/static",
    )

    # Expose the loop on the app config so tests can reach it
    app.config["AUREON_LOOP"] = loop

    # PhiBridge — process-wide singleton, attached to this loop's vault.
    # The voices read it through the same vault that the bridge writes to.
    bridge = get_phi_bridge(vault=loop.vault)
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

    # ─────────────────────────────────────────────────────────────────
    # LLM pre-warm + pin-in-RAM daemon.
    # Ollama unloads idle models after 5 min by default; on a 3.7 GiB
    # box the reload + prompt processing blows a phone fetch. We send
    # a tiny ping now and every 3 minutes to keep qwen2.5:0.5b hot in
    # RAM so phone messages land on a warm model every time.
    # ─────────────────────────────────────────────────────────────────
    def _llm_warm_ping(why: str) -> None:
        """
        Pin the local LLM in RAM.

        Ollama's OpenAI-compatible /v1 shim ignores keep_alive, so we hit
        its NATIVE /api/generate endpoint which does accept it. Each ping
        extends the model's TTL by 30 minutes, so a 3-minute warmer loop
        plus the boot ping means the model is effectively pinned for as
        long as the server runs.
        """
        if loop.voice_engine is None:
            return
        try:
            any_voice = next(iter(loop.voice_engine.voices.values()))
            adapter = any_voice.adapter
            if adapter is None:
                return
            bridge = getattr(adapter, "bridge", None)
            base_url = getattr(adapter, "base_url", "") or getattr(bridge, "base_url", "")
            model = getattr(adapter, "model", "") or getattr(bridge, "chat_model", "")
            if not base_url or not model:
                return
            # Derive the native endpoint from the /v1 base_url.
            #   http://localhost:11434/v1  →  http://localhost:11434/api/generate
            native = base_url.rstrip("/")
            if native.endswith("/v1"):
                native = native[:-3]
            native = native + "/api/generate"
            if is_ollama_cloud_url(native):
                # Hosted models need no local RAM keepalive. Avoid recurring
                # cloud inference solely for local warm-state management.
                return
            import requests as _requests
            headers_fn = getattr(adapter, "_headers", None)
            headers = headers_fn() if callable(headers_fn) else dict(
                getattr(bridge, "_authorization_headers", {}) or {}
            )
            t0 = time.time()
            _requests.post(
                native,
                json={
                    "model": model,
                    "prompt": "ping",
                    "stream": False,
                    "keep_alive": "30m",
                    "options": {"num_predict": 1},
                },
                headers=headers,
                timeout=60,
            )
            dt = (time.time() - t0) * 1000.0
            logger.info("LLM warm ping (%s) via %s: %.0f ms", why, native, dt)
        except Exception as e:
            logger.debug("LLM warm ping failed (%s): %s", why, e)

    # Pre-warm once at app creation, then every 3 minutes in the background.
    threading.Thread(target=_llm_warm_ping, args=("boot",), daemon=True).start()

    def _warm_loop():
        while True:
            time.sleep(180)
            _llm_warm_ping("keepalive")

    threading.Thread(target=_warm_loop, daemon=True).start()

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
            return jsonify({"ok": False, "error": "voice engine disabled"}), 400
        return jsonify({
            "ok": True,
            "voices": list(loop.voice_engine.voices.keys()),
        })

    @app.route("/api/utterances")
    def api_utterances():
        if loop.voice_engine is None:
            return jsonify({"ok": True, "utterances": []})
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
        """
        Tell the caller what URL the phone should open.
        We pick the LAN-facing IPv4 of this host using the standard
        "connect to a public address" trick — no packet is actually sent.
        """
        import socket

        lan_ip = ""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.connect(("8.8.8.8", 80))
            lan_ip = sock.getsockname()[0]
        except Exception:
            try:
                lan_ip = socket.gethostbyname(socket.gethostname())
            except Exception:
                lan_ip = ""
        finally:
            try:
                sock.close()
            except Exception:
                pass

        host = request.host  # includes port
        scheme = request.scheme
        # Rewrite 127.0.0.1 / localhost to the LAN IP for the phone URL.
        phone_host = host
        if lan_ip and ("127.0.0.1" in host or "localhost" in host or "0.0.0.0" in host):
            port = host.split(":", 1)[1] if ":" in host else "5566"
            phone_host = f"{lan_ip}:{port}"
        phone_url = f"{scheme}://{phone_host}/bridge"
        return jsonify({
            "ok": True,
            "lan_ip": lan_ip,
            "phone_url": phone_url,
            "desktop_url": f"{scheme}://{phone_host}/",
            "invite_url": f"{scheme}://{phone_host}/bridge-invite",
            "hostname": socket.gethostname(),
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

    mesh = get_phi_bridge_mesh(vault=loop.vault)
    app.config["AUREON_PHI_BRIDGE_MESH"] = mesh

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

    http_port = int(mesh_port or os.environ.get("AUREON_UI_PORT") or 8000)
    discovery = mesh_discovery
    if discovery is None:
        discovery = PhiBridgeDiscovery(
            host="",  # auto-detect the LAN IP
            port=http_port,
            label=str(mesh_label),
            kind=str(mesh_kind),
            fingerprint_fn=lambda: str(loop.vault.fingerprint()) if hasattr(loop.vault, "fingerprint") else "",
        )

    mesh.discovery = discovery
    app.config["AUREON_PHI_BRIDGE_DISCOVERY"] = discovery

    try:
        discovery.start()
    except Exception as e:
        logger.warning("phi-bridge discovery failed to start: %s", e)
    try:
        mesh.start()
    except Exception as e:
        logger.warning("phi-bridge mesh failed to start: %s", e)

    # Stop the background threads cleanly on interpreter shutdown.
    import atexit as _atexit
    def _shutdown_mesh():
        try:
            discovery.stop()
        except Exception:
            pass
        try:
            mesh.stop()
        except Exception:
            pass
    _atexit.register(_shutdown_mesh)

    @app.route("/api/bridge/discovery/peers")
    def api_bridge_discovery_peers():
        disc = app.config.get("AUREON_PHI_BRIDGE_DISCOVERY")
        if disc is None:
            return jsonify({
                "ok": True, "running": False,
                "peers": [],
            })
        try:
            return jsonify({
                "ok": True,
                "running": True,
                "self_peer_id": disc.peer_id,
                "host": disc.host,
                "port": disc.port,
                "announce_count": disc.announce_count,
                "recv_count": disc.recv_count,
                "peers": disc.known_peers_dict(),
            })
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

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
) -> None:
    """Blocking server run. Use `start_loop=True` to also spawn the loop."""
    app = create_app(loop=loop)
    if start_loop:
        cfg_loop = app.config["AUREON_LOOP"]
        cfg_loop.start()
    logger.info("Aureon Vault UI listening on http://%s:%d/", host, port)
    app.run(host=host, port=port, debug=debug, use_reloader=False, threaded=True)
