"""
🎛️ AUREON OPERATOR — the switchboard.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"Many voices in. One grounded answer out."

A prompt enters. The operator patches it out across every AI line on the board
(ChatGPT, Grok, Gemini, … — see :mod:`aureon.operator.providers`), but first it
grounds the prompt in the Aureon repo so no line is answering from vendor memory
alone. The replies come back, the operator collapses them to one, runs that one
past the Queen's conscience (the 4th-pass veto), and only then speaks.

Five phases, each publishing a ``Thought`` on the bus under ``operator.phase.*``
with a shared ``trace_id`` — so a dashboard (or the phone) can watch the cascade
live, exactly like :class:`aureon.cognition.pipeline.CognitionPipeline`:

    [prompt] → ground → fan_out → consensus → veto → [answer]

This is the response-synthesis engine from the "Aureon Setup" overview: the
grounding + consensus + veto chain is what makes the guarantee — no logic drift,
no hallucination, fully grounded via the Aureon repository — falsifiable rather
than decorative.
"""

from __future__ import annotations

import logging
import re
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from threading import Lock
from typing import Any, Dict, Generator, List, Optional

try:  # optional wiring hook other modules self-register with
    from aureon.core.aureon_baton_link import link_system as _baton_link

    _baton_link(__name__)
except Exception:  # noqa: BLE001 — never fail import over a tracing hook
    pass

from aureon.inhouse_ai.llm_adapter import LLMAdapter, StreamChunk
from aureon.operator.cache import ResponseCache, cache_key
from aureon.operator.config import OperatorConfig
from aureon.operator.metrics import OperatorMetrics
from aureon.operator.providers import build_provider_set, describe_provider_set
from aureon.operator.schemas import (
    ConsensusReading,
    GroundingContext,
    OperatorResponse,
    ProviderAnswer,
)

logger = logging.getLogger("aureon.operator")


class _CircuitBreaker:
    """Per-line failure tracker. Trips a line after N consecutive failures."""

    def __init__(self, threshold: int, cooldown_s: float) -> None:
        self.threshold = threshold
        self.cooldown_s = cooldown_s
        self._fails: Dict[str, int] = {}
        self._open_until: Dict[str, float] = {}
        self._lock = Lock()

    def is_open(self, line: str) -> bool:
        with self._lock:
            until = self._open_until.get(line, 0.0)
            if until and until > time.time():
                return True
            if until:
                # cooldown elapsed — half-open: clear so the line gets one more try
                self._open_until.pop(line, None)
                self._fails[line] = 0
            return False

    def record(self, line: str, ok: bool) -> None:
        with self._lock:
            if ok:
                self._fails[line] = 0
                self._open_until.pop(line, None)
                return
            self._fails[line] = self._fails.get(line, 0) + 1
            if self._fails[line] >= self.threshold:
                self._open_until[line] = time.time() + self.cooldown_s

# ── Thought bus (fail-safe) ───────────────────────────────────────────────────
try:
    from aureon.core.aureon_thought_bus import Thought, get_thought_bus

    _HAS_THOUGHT_BUS = True
except Exception:  # noqa: BLE001
    get_thought_bus = None  # type: ignore[assignment]
    Thought = None  # type: ignore[assignment,misc]
    _HAS_THOUGHT_BUS = False


_PHASE_TOPICS = {
    "boot": "operator.phase.boot",
    "ground": "operator.phase.ground",
    "fan_out": "operator.phase.fan_out",
    "consensus": "operator.phase.consensus",
    "veto": "operator.phase.veto",
    "complete": "operator.complete",
}

_OPERATOR_PERSONA = (
    "You are Aureon, an operator routing a question through the Harmonic Nexus "
    "Core (HNC) trading system. Answer from the grounded Aureon repository context "
    "below. Be precise and falsifiable: cite the system or document a claim comes "
    "from, and say plainly when the context does not cover something. Do not invent "
    "trade executions, balances, filings, or credentials."
)

# Hard authority boundaries (mirrors PUBLIC_BOUNDARIES in the dynamic prompt
# filter). These are deterministic, prompt-level refusals: the operator will not
# emit an answer that helps cross them, regardless of the soft conscience verdict.
_HARD_BOUNDARY_PATTERNS = (
    r"\b(disable|bypass|ignore|override|turn off|switch off|remove)\b[^.]{0,40}\b(safety|gate|gates|guard|guardrail|risk limit|risk-limit|limits|conscience|governance|veto)\b",
    r"\b(execute|place|open|run|make|do)\b[^.]{0,40}\b(live|real|all[- ]?in|leveraged)\b[^.]{0,20}\btrade\b",
    r"\b(move|withdraw|send|transfer|wire|pay out|payout)\b[^.]{0,40}\b(payment|funds|money|balance|account)\b",
    r"\b(reveal|expose|print|show|leak)\b[^.]{0,30}\b(api[_ -]?key|secret|password|credential|private key)\b",
    r"\b(submit|file|lodge)\b[^.]{0,30}\b(official|regulatory|tax|legal)\b[^.]{0,20}\b(filing|return|document)\b",
)


def _hard_boundary_violation(prompt: str) -> Optional[str]:
    low = str(prompt or "").lower()
    for pat in _HARD_BOUNDARY_PATTERNS:
        if re.search(pat, low):
            return pat
    return None


_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "is", "are", "for", "on",
    "with", "as", "by", "it", "this", "that", "be", "at", "from", "how", "does",
    "do", "what", "aureon",
}


class AureonOperator:
    """The switchboard: fan-out → ground → collapse → veto, traced on the bus."""

    def __init__(
        self,
        providers: Optional[Dict[str, LLMAdapter]] = None,
        *,
        bus: Any = None,
        conscience: Any = None,
        config: Optional[OperatorConfig] = None,
        cache: Optional[ResponseCache] = None,
        source: str = "aureon.operator",
    ) -> None:
        self.config = config or OperatorConfig.from_env()
        self.providers = providers if providers is not None else build_provider_set()
        if bus is not None:
            self.bus = bus
        elif _HAS_THOUGHT_BUS and get_thought_bus is not None:
            self.bus = get_thought_bus()
        else:
            self.bus = None
        self.source = source
        self._conscience = conscience
        self._conscience_loaded = conscience is not None
        self._breaker = _CircuitBreaker(self.config.breaker_threshold, self.config.breaker_cooldown_s)
        if cache is not None:
            self.cache = cache
        elif self.config.cache_enabled:
            self.cache = ResponseCache(self.config.cache_ttl_s, self.config.cache_max_entries)
        else:
            self.cache = None
        self._metrics: Optional[OperatorMetrics] = None

    # ------------------------------------------------------------------
    # Public entrypoints
    # ------------------------------------------------------------------

    def respond(self, prompt: str, session_id: Optional[str] = None) -> OperatorResponse:
        """Run a prompt through all five phases. Returns the grounded answer."""
        started = time.time()
        resp = OperatorResponse(
            trace_id=uuid.uuid4().hex,
            prompt=prompt,
            submitted_at=started,
            session_id=session_id,
        )
        self._metrics = OperatorMetrics(
            enabled=self.config.metrics_enabled,
            structured_logs=self.config.structured_logs,
            trace_id=resp.trace_id,
        )
        self._publish(
            resp,
            "boot",
            {"prompt": prompt, "session_id": session_id, "providers": describe_provider_set(self.providers)},
        )

        with self._metrics.phase("ground"):
            system_prompt = self._ground(prompt, resp)

        # Cache is keyed by the FULL determinants of an answer: prompt + grounding
        # signature + the exact model set. Grounding is cheap/local so we always
        # run it, then short-circuit fan-out + consensus + veto on a hit.
        cached = self._cache_get(resp)
        if cached is not None:
            resp.elapsed_ms = (time.time() - started) * 1000.0
            self._metrics.cache("hit")
            self._metrics.request("cache_hit", resp.elapsed_ms)
            self._publish(resp, "complete", resp.to_dict())
            return resp
        if self.cache is not None:
            self._metrics.cache("miss")

        with self._metrics.phase("fan_out"):
            self._fan_out(prompt, system_prompt, resp)
        with self._metrics.phase("consensus"):
            self._consensus(resp)
        with self._metrics.phase("veto"):
            self._veto(prompt, resp)

        resp.elapsed_ms = (time.time() - started) * 1000.0
        self._cache_set(resp)
        self._metrics.request("blocked" if resp.blocked else "ok", resp.elapsed_ms)
        self._publish(resp, "complete", resp.to_dict())
        return resp

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    def _cache_signature(self, resp: OperatorResponse) -> Optional[str]:
        if self.cache is None:
            return None
        grounding_sig = ",".join(sorted(s.get("path", "") for s in (resp.grounding.sources if resp.grounding else [])))
        model_set = ",".join(sorted(self.providers.keys()))
        return cache_key(resp.prompt, grounding_sig, model_set)

    def _cache_get(self, resp: OperatorResponse) -> Optional[OperatorResponse]:
        sig = self._cache_signature(resp)
        if not sig:
            return None
        payload = self.cache.get(sig)
        if payload is None:
            return None
        # Re-hydrate the cached answer onto THIS response (fresh trace_id preserved).
        resp.text = payload.get("text", "")
        resp.answers = [ProviderAnswer(**a) for a in payload.get("answers", [])]
        resp.consensus = ConsensusReading(**payload["consensus"]) if payload.get("consensus") else None
        resp.conscience_verdict = payload.get("conscience_verdict", "APPROVED")
        resp.conscience_message = payload.get("conscience_message", "")
        resp.blocked = payload.get("blocked", False)
        resp.errors.append({"phase": "cache", "note": "served from cache"})
        return resp

    def _cache_set(self, resp: OperatorResponse) -> None:
        sig = self._cache_signature(resp)
        if not sig or resp.blocked:  # don't cache vetoed answers
            return
        self.cache.set(
            sig,
            {
                "text": resp.text,
                "answers": [a.to_dict() for a in resp.answers],
                "consensus": resp.consensus.to_dict() if resp.consensus else None,
                "conscience_verdict": resp.conscience_verdict,
                "conscience_message": resp.conscience_message,
                "blocked": resp.blocked,
            },
        )

    def stream(self, prompt: str, session_id: Optional[str] = None) -> Generator[StreamChunk, None, None]:
        """LLMAdapter-style stream of the final grounded answer (word chunks)."""
        for event in self.stream_events(prompt, session_id=session_id):
            if event.get("type") == "token":
                yield StreamChunk(text=event.get("text", ""))
            elif event.get("type") == "complete":
                yield StreamChunk(done=True, stop_reason="end_turn")

    def stream_events(
        self, prompt: str, session_id: Optional[str] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Rich event stream for the phone/SSE surface. Yields dict events:
          {"type": "phase", "phase": ..., "detail": {...}}   as each phase resolves
          {"type": "token", "text": ...}                     final answer, word by word
          {"type": "complete", "response": {...}}            the full OperatorResponse
        """
        resp = self.respond(prompt, session_id=session_id)
        # Replay the resolved phases as events (order preserved by insertion).
        for phase in ("ground", "fan_out", "consensus", "veto"):
            yield {"type": "phase", "phase": phase, "detail": self._phase_summary(phase, resp)}
        for word in (resp.text or "").split(" "):
            yield {"type": "token", "text": word + " "}
        yield {"type": "complete", "response": resp.to_dict()}

    # ------------------------------------------------------------------
    # Phase 1 — Ground (repo-anchored system prompt)
    # ------------------------------------------------------------------

    def _ground(self, prompt: str, resp: OperatorResponse) -> str:
        sources: List[Dict[str, str]] = []
        lane = task_family = ""
        filter_block = ""
        messages = [{"role": "user", "content": prompt}]
        try:
            from aureon.autonomous.aureon_dynamic_prompt_filter import (
                build_dynamic_prompt_filter,
                render_filter_prompt_block,
            )

            report = build_dynamic_prompt_filter(messages, system=_OPERATOR_PERSONA, publish=False)
            lane = str(report.get("lane") or "")
            task_family = str(report.get("task_family") or "")
            for packet in report.get("source_packets") or []:
                if isinstance(packet, dict):
                    sources.append(
                        {
                            "title": str(packet.get("title") or "Source packet"),
                            "path": str(packet.get("source_path") or ""),
                        }
                    )
            filter_block = render_filter_prompt_block(report)
        except Exception as exc:  # noqa: BLE001 — grounding degrades, never crashes
            logger.debug("dynamic prompt filter unavailable: %s", exc)
            sources = self._fallback_sources(prompt)

        system_prompt = "\n\n".join(part for part in (_OPERATOR_PERSONA, filter_block) if part.strip())
        resp.grounding = GroundingContext(
            sources=sources,
            lane=lane,
            task_family=task_family,
            system_prompt_chars=len(system_prompt),
        )
        self._publish(resp, "ground", resp.grounding.to_dict())
        return system_prompt

    @staticmethod
    def _fallback_sources(prompt: str) -> List[Dict[str, str]]:
        try:
            from aureon.autonomous.aureon_dynamic_prompt_filter import select_source_packets

            return [
                {"title": p.title, "path": p.source_path}
                for p in select_source_packets(prompt, limit=4)
            ]
        except Exception:  # noqa: BLE001
            return []

    # ------------------------------------------------------------------
    # Phase 2 — Fan out (patch the prompt to every line)
    # ------------------------------------------------------------------

    def _fan_out(self, prompt: str, system_prompt: str, resp: OperatorResponse) -> None:
        messages = [{"role": "user", "content": prompt}]
        lines = list(self.providers.items())

        if self.config.parallel and len(lines) > 1:
            workers = min(self.config.max_workers, len(lines))
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {
                    pool.submit(self._call_line, name, adapter, messages, system_prompt): name
                    for name, adapter in lines
                }
                # gather in submission order for deterministic output
                results = {name: None for name, _ in lines}
                for fut, name in futures.items():
                    try:
                        results[name] = fut.result(timeout=self.config.request_timeout_s + 5)
                    except Exception as exc:  # noqa: BLE001
                        results[name] = self._error_answer(name, self.providers[name], 0.0, f"fan_out_error: {exc}")
                for name, _ in lines:
                    resp.answers.append(results[name])
        else:
            for name, adapter in lines:
                resp.answers.append(self._call_line(name, adapter, messages, system_prompt))

        for a in resp.answers:
            self._metrics_provider_call(a)
            if not a.ok:
                resp.errors.append({"phase": "fan_out", "provider": a.provider, "error": a.error})

        self._publish(
            resp,
            "fan_out",
            {
                "n_providers": len(self.providers),
                "n_ok": sum(1 for a in resp.answers if a.ok),
                "parallel": bool(self.config.parallel and len(lines) > 1),
                "answers": [a.to_dict() for a in resp.answers],
            },
        )

    def _call_line(self, name, adapter, messages, system_prompt) -> ProviderAnswer:
        """One switchboard line, with circuit-breaker + retry + hard timeout."""
        if self._breaker.is_open(name):
            return self._error_answer(name, adapter, 0.0, "circuit_open")

        t0 = time.time()
        last_err = "empty response"
        attempts = max(1, self.config.max_retries + 1)
        for attempt in range(attempts):
            try:
                out = self._call_with_timeout(adapter, messages, system_prompt)
                text = (out.text or "").strip()
                ok = out.stop_reason != "error" and bool(text)
                if ok:
                    self._breaker.record(name, True)
                    return ProviderAnswer(
                        provider=name,
                        model=str(out.model or getattr(adapter, "model", "") or ""),
                        text=text,
                        ok=True,
                        latency_ms=(time.time() - t0) * 1000.0,
                    )
                last_err = text or "empty response"
            except FutureTimeout:
                last_err = f"timeout>{self.config.request_timeout_s}s"
            except Exception as exc:  # noqa: BLE001
                last_err = str(exc)
            if attempt < attempts - 1:
                time.sleep(self.config.retry_backoff_s * (2 ** attempt))

        self._breaker.record(name, False)
        return self._error_answer(name, adapter, (time.time() - t0) * 1000.0, last_err)

    def _call_with_timeout(self, adapter, messages, system_prompt):
        """Enforce a hard wall-clock timeout around any adapter, even blocking ones."""
        with ThreadPoolExecutor(max_workers=1) as pool:
            fut = pool.submit(
                adapter.prompt,
                messages,
                system=system_prompt,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
            )
            return fut.result(timeout=self.config.request_timeout_s)

    @staticmethod
    def _error_answer(name, adapter, latency_ms, err) -> ProviderAnswer:
        return ProviderAnswer(
            provider=name,
            model=str(getattr(adapter, "model", "") or ""),
            text="",
            ok=False,
            latency_ms=latency_ms,
            error=str(err),
        )

    def _metrics_provider_call(self, a: ProviderAnswer) -> None:
        if self._metrics is not None:
            self._metrics.provider_call(a.provider, a.ok, a.latency_ms)

    # ------------------------------------------------------------------
    # Phase 3 — Consensus collapse (agreement → one answer)
    # ------------------------------------------------------------------

    def _consensus(self, resp: OperatorResponse) -> None:
        good = [a for a in resp.answers if a.ok and a.text.strip()]
        if not good:
            # No line answered — surface the failure honestly rather than inventing.
            resp.text = (
                "No AI line produced a usable answer. "
                "Check provider keys and connectivity, or run offline for a grounded stub."
            )
            resp.consensus = ConsensusReading(n_answers=0, agreement=0.0, winner="", synthesized=False)
            self._emit_consensus(resp)
            return

        if len(good) == 1:
            winner = good[0]
            resp.text = winner.text
            resp.consensus = ConsensusReading(
                n_answers=1, agreement=1.0, winner=winner.provider, synthesized=False
            )
            self._emit_consensus(resp)
            return

        # Medoid collapse: the answer most similar to all the others wins.
        # Agreement = mean pairwise Jaccard token overlap (a coherence proxy).
        token_sets = {a.provider: self._tokens(a.text) for a in good}
        best_provider = ""
        best_score = -1.0
        pairwise: List[float] = []
        for a in good:
            sims = []
            for b in good:
                if a.provider == b.provider:
                    continue
                sim = self._jaccard(token_sets[a.provider], token_sets[b.provider])
                sims.append(sim)
                pairwise.append(sim)
            mean_sim = sum(sims) / len(sims) if sims else 0.0
            # Tie-break toward the more substantive answer.
            score = mean_sim + min(len(a.text), 1200) / 1e6
            if score > best_score:
                best_score = score
                best_provider = a.provider

        agreement = sum(pairwise) / len(pairwise) if pairwise else 0.0
        winner = next(a for a in good if a.provider == best_provider)
        resp.text = winner.text
        resp.consensus = ConsensusReading(
            n_answers=len(good),
            agreement=agreement,
            winner=winner.provider,
            runner_ups=[a.provider for a in good if a.provider != winner.provider],
            synthesized=True,
        )
        self._publish(resp, "consensus", resp.consensus.to_dict())

    def _emit_consensus(self, resp: OperatorResponse) -> None:
        if self._metrics is not None and resp.consensus is not None:
            self._metrics.consensus(resp.consensus.agreement, resp.consensus.winner, resp.consensus.n_answers)
        self._publish(resp, "consensus", resp.consensus.to_dict())

    @staticmethod
    def _tokens(text: str) -> set:
        words = re.findall(r"[a-z0-9]+", str(text).lower())
        return {w for w in words if w not in _STOPWORDS and len(w) > 2}

    @staticmethod
    def _jaccard(a: set, b: set) -> float:
        if not a or not b:
            return 0.0
        inter = len(a & b)
        union = len(a | b)
        return inter / union if union else 0.0

    # ------------------------------------------------------------------
    # Phase 4 — Veto (the Queen's 4th-pass conscience)
    # ------------------------------------------------------------------

    def _veto(self, prompt: str, resp: OperatorResponse) -> None:
        if not self.config.veto_enabled:
            resp.conscience_verdict = "SKIPPED"
            self._publish(resp, "veto", {"verdict": "SKIPPED", "available": False})
            return

        # ── Hard authority boundary: deterministic refusal, no soft override ──
        boundary = _hard_boundary_violation(prompt)
        if boundary is not None:
            resp.blocked = True
            resp.conscience_verdict = "VETO"
            resp.conscience_message = (
                "This request crosses a hard Aureon authority boundary "
                "(live trading, payment movement, safety-gate bypass, credential reveal, "
                "or official filing). The operator will not assist with it."
            )
            resp.text = f"🦗 Blocked at the Aureon authority boundary.\nReason: {resp.conscience_message}"
            if self._metrics is not None:
                self._metrics.veto("VETO", True)
            self._publish(
                resp, "veto",
                {"verdict": "VETO", "blocked": True, "boundary": True, "message": resp.conscience_message},
            )
            return

        conscience = self._get_conscience()
        if conscience is None:
            resp.conscience_verdict = "APPROVED"
            if self._metrics is not None:
                self._metrics.veto("APPROVED", False)
            self._publish(resp, "veto", {"verdict": "APPROVED", "available": False})
            return

        action = f"answer operator question: {prompt[:160]}"
        context = {
            "answer_preview": resp.text[:400],
            "n_providers": len(resp.answers),
            "agreement": resp.consensus.agreement if resp.consensus else 0.0,
            "sources": [s.get("path", "") for s in (resp.grounding.sources if resp.grounding else [])],
        }
        try:
            whisper = conscience.ask_why(action, context)
            verdict = getattr(whisper.verdict, "name", str(whisper.verdict))
            resp.conscience_verdict = verdict
            resp.conscience_message = str(getattr(whisper, "message", "") or "")
            if verdict == "VETO":
                resp.blocked = True
                resp.text = (
                    "🦗 The Queen's conscience vetoed this answer.\n"
                    f"Reason: {resp.conscience_message}"
                )
        except Exception as exc:  # noqa: BLE001 — conscience failure is non-fatal
            logger.debug("conscience unavailable: %s", exc)
            resp.conscience_verdict = "APPROVED"
            resp.errors.append({"phase": "veto", "error": str(exc)})
        if self._metrics is not None:
            self._metrics.veto(resp.conscience_verdict, resp.blocked)
        self._publish(
            resp,
            "veto",
            {"verdict": resp.conscience_verdict, "blocked": resp.blocked, "message": resp.conscience_message},
        )

    def _get_conscience(self):
        if self._conscience_loaded:
            return self._conscience
        self._conscience_loaded = True
        try:
            from aureon.queen.queen_conscience import QueenConscience

            self._conscience = QueenConscience()
        except Exception as exc:  # noqa: BLE001
            logger.debug("QueenConscience unavailable: %s", exc)
            self._conscience = None
        return self._conscience

    # ------------------------------------------------------------------
    # Transport
    # ------------------------------------------------------------------

    def _phase_summary(self, phase: str, resp: OperatorResponse) -> Dict[str, Any]:
        if phase == "ground":
            return resp.grounding.to_dict() if resp.grounding else {}
        if phase == "fan_out":
            return {"n_ok": sum(1 for a in resp.answers if a.ok), "n_total": len(resp.answers)}
        if phase == "consensus":
            return resp.consensus.to_dict() if resp.consensus else {}
        if phase == "veto":
            return {"verdict": resp.conscience_verdict, "blocked": resp.blocked}
        return {}

    def _publish(self, resp: OperatorResponse, phase_key: str, payload: Dict[str, Any]) -> None:
        topic = _PHASE_TOPICS[phase_key]
        if self.bus is None or Thought is None:
            resp.phase_thought_ids[phase_key] = ""
            return
        try:
            thought = Thought(
                source=self.source,
                topic=topic,
                trace_id=resp.trace_id,
                parent_id=self._last_thought_id(resp),
                payload=dict(payload),
                meta={"phase": phase_key},
            )
            published = self.bus.publish(thought)
            resp.phase_thought_ids[phase_key] = getattr(published, "id", "") or ""
        except Exception as exc:  # noqa: BLE001
            logger.debug("failed to publish %s: %s", topic, exc)
            resp.phase_thought_ids[phase_key] = ""

    @staticmethod
    def _last_thought_id(resp: OperatorResponse) -> Optional[str]:
        for key in reversed(list(resp.phase_thought_ids.keys())):
            if resp.phase_thought_ids[key]:
                return resp.phase_thought_ids[key]
        return None


def run_operator(prompt: str, bus: Any = None, session_id: Optional[str] = None) -> OperatorResponse:
    """Convenience one-shot: build the switchboard and answer one prompt."""
    return AureonOperator(bus=bus).respond(prompt, session_id=session_id)


__all__ = ["AureonOperator", "run_operator"]
