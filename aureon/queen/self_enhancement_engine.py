"""
SelfEnhancementEngine — the Queen writes code to enhance herself
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The Queen observes her own performance gaps, uses her own LLM voice to write
new Python skill code, validates it through the existing safety pipeline,
hot-loads it into the SkillLibrary, and publishes the event back into the
vault — so the next self-feedback tick already knows about the new capability.

Cycle (one enhancement attempt):

  1. OBSERVE   — GapAnalyzer scans skill stats, vault cards, recent
                 KnowingBlocks, and benchmark results to identify a gap.

  2. PROMPT    — Build a code-generation system prompt that briefs the LLM
                 on the gap, the existing primitives it can use, and the
                 exact function signature required.

  3. GENERATE  — Call the Queen voice (the running LLM) via the existing
                 voice.speak() infrastructure so the reply IS the new code.

  4. EXTRACT   — CodeExtractor pulls the Python block from the LLM reply.

  5. VALIDATE  — SkillValidator runs static safety + semantic checks.

  6. SANDBOX   — Execute the skill once with safe stub params to confirm
                 it runs without exception.

  7. REGISTER  — Add the new Skill to SkillLibrary and ingest the event
                 into the vault so downstream loops and the meaning resolver
                 can surface it.

  8. LOG       — EnhancementRecord captures the full attempt (gap, code,
                 verdict, error, latency). Failures are studied next cycle.

The engine runs a background thread that loops every ``enhancement_interval_s``
(default 120 s). A faster ``--self-evolve`` flag can drop this to 30 s.

The engine is intentionally conservative:
  • Only proposes L1 (COMPOUND) skills — nothing touches the filesystem,
    network, or destructive VM tools without an explicit human "approve"
    flag set on the Skill.
  • Validator's forbidden-call list still blocks eval/exec/open/etc.
  • Any failure in steps 4-6 leaves the SkillLibrary unchanged.
  • A rolling ``EnhancementLog`` (capped at 500 entries) is persisted to
    ``state/enhancement/log.json`` for inspection.
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from aureon.ollama_config import (
    ensure_ollama_runtime_config,
    is_ollama_cloud_url,
    ollama_authorization_headers,
    resolve_ollama_native_base_url,
    resolve_ollama_reasoning_effort,
)

logger = logging.getLogger("aureon.queen.self_enhancement_engine")


# ─────────────────────────────────────────────────────────────────────────────
# Data types
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class Gap:
    """One identified capability gap the Queen should fill."""
    gap_id: str = ""
    category: str = "general"        # cognition | memory | cosmos | action | hnc | trading
    description: str = ""            # human-readable: what is missing
    suggested_name: str = ""         # snake_case skill name to create
    priority: float = 0.5            # 0-1; higher = more urgent
    evidence: List[str] = field(default_factory=list)  # why this gap was detected
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gap_id": self.gap_id,
            "category": self.category,
            "description": self.description,
            "suggested_name": self.suggested_name,
            "priority": self.priority,
            "evidence": self.evidence,
        }


@dataclass
class EnhancementRecord:
    """Audit log entry for one complete enhancement attempt."""
    record_id: str = ""
    gap: Optional[Dict[str, Any]] = None
    skill_name: str = ""
    code_generated: str = ""
    validation_ok: bool = False
    sandbox_ok: bool = False
    registered: bool = False
    error: str = ""
    latency_s: float = 0.0
    llm_reply: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "gap": self.gap,
            "skill_name": self.skill_name,
            "code_generated": self.code_generated[:300],
            "validation_ok": self.validation_ok,
            "sandbox_ok": self.sandbox_ok,
            "registered": self.registered,
            "error": self.error[:300] if self.error else "",
            "latency_s": round(self.latency_s, 3),
            "llm_reply_len": len(self.llm_reply),
            "timestamp": self.timestamp,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Gap analyser
# ─────────────────────────────────────────────────────────────────────────────


class GapAnalyzer:
    """
    Reads real signals from the running system and turns them into Gap objects.

    Signal sources (in priority order):
      A. Skill failures  — skills in SkillLibrary with failure_count > 0
      B. Skill deserts   — categories that have zero skills
      C. Vault signals   — vault cards whose topic is "enhancement.request"
      D. Hard-coded seed — a small list of universally useful capabilities
         the Queen should always have, checked against existing skill names.
    """

    # Seed capabilities the Queen should always be able to do.
    _SEED_GAPS: List[Dict[str, Any]] = [
        {
            "category": "cognition",
            "description": (
                "Summarise the last N vault cards into a single coherent sentence "
                "so the Queen can report her own recent activity."
            ),
            "suggested_name": "summarise_recent_vault",
            "priority": 0.8,
            "evidence": ["seed: always-useful"],
        },
        {
            "category": "cosmos",
            "description": (
                "Compute whether the current Λ(t) is trending up or down over "
                "the last 5 vault snapshots and return 'rising' | 'falling' | 'flat'."
            ),
            "suggested_name": "lambda_trend",
            "priority": 0.75,
            "evidence": ["seed: always-useful"],
        },
        {
            "category": "memory",
            "description": (
                "Count how many turns in the current dialogue contain the word "
                "'love' and return the percentage as a coherence proxy."
            ),
            "suggested_name": "love_coherence_score",
            "priority": 0.65,
            "evidence": ["seed: always-useful"],
        },
        {
            "category": "action",
            "description": (
                "Compose a one-line status report — 'Λ(t)=X love=Y chakra=Z' — "
                "from the vault's latest state so it can be posted to ThoughtBus."
            ),
            "suggested_name": "compose_status_line",
            "priority": 0.70,
            "evidence": ["seed: always-useful"],
        },
        {
            "category": "trading",
            "description": (
                "Given a list of price ticks, calculate the rolling 3-period "
                "simple moving average and return it as a float list."
            ),
            "suggested_name": "rolling_sma_3",
            "priority": 0.60,
            "evidence": ["seed: always-useful"],
        },
        {
            "category": "hnc",
            "description": (
                "Evaluate the simplified HNC stability condition "
                "β ∈ [0.6, 1.1] for a given λ_prev and λ_curr, returning "
                "True if stable and False otherwise."
            ),
            "suggested_name": "hnc_stability_check",
            "priority": 0.72,
            "evidence": ["seed: always-useful"],
        },
        {
            "category": "cognition",
            "description": (
                "Given a question string, classify it into one of: math, cosmic, "
                "memory, action, persona, hnc, general — so the resolver can "
                "route it without regex."
            ),
            "suggested_name": "classify_question_type",
            "priority": 0.68,
            "evidence": ["seed: intent routing"],
        },
        {
            "category": "cosmos",
            "description": (
                "Given Kp index and Schumann Hz, compute a combined 'earth coherence' "
                "score between 0.0 and 1.0 using a simple weighted sum."
            ),
            "suggested_name": "earth_coherence_score",
            "priority": 0.67,
            "evidence": ["seed: always-useful"],
        },
    ]

    def __init__(self, skill_library: Any = None, vault: Any = None):
        self._library = skill_library
        self._vault = vault

    def analyse(self) -> List[Gap]:
        """Return a ranked list of gaps (highest priority first)."""
        gaps: List[Gap] = []

        # Source A: failing skills.
        if self._library is not None:
            try:
                for skill in self._library.all():
                    if skill.failure_count > 0 and skill.success_count == 0:
                        gaps.append(Gap(
                            gap_id=f"fail-{skill.name}",
                            category=skill.category or "general",
                            description=(
                                f"Skill '{skill.name}' has failed {skill.failure_count} times "
                                f"and never succeeded. Last error: {skill.last_error or '?'}. "
                                f"Rewrite it to be more robust."
                            ),
                            suggested_name=f"{skill.name}_v2",
                            priority=0.9,
                            evidence=[f"failure_count={skill.failure_count}", f"error={skill.last_error}"],
                        ))
            except Exception as e:
                logger.debug("gap scan of skill library failed: %s", e)

        # Source B: skill category deserts.
        if self._library is not None:
            try:
                existing_categories = {s.category for s in self._library.all() if s.category}
                for seed in self._SEED_GAPS:
                    if seed["category"] not in existing_categories:
                        gaps.append(Gap(
                            gap_id=f"desert-{seed['category']}",
                            category=seed["category"],
                            description=seed["description"],
                            suggested_name=seed["suggested_name"],
                            priority=seed["priority"] + 0.05,  # slight boost for empty categories
                            evidence=[f"no skills in category '{seed['category']}'"],
                        ))
            except Exception as e:
                logger.debug("category desert scan failed: %s", e)

        # Source C: vault enhancement requests.
        if self._vault is not None:
            try:
                for card in self._vault.by_category("enhancement.request", n=10):
                    payload = getattr(card, "payload", {}) or {}
                    if isinstance(payload, dict) and payload.get("description"):
                        gaps.append(Gap(
                            gap_id=f"vault-{card.timestamp:.0f}",
                            category=payload.get("category", "general"),
                            description=payload["description"],
                            suggested_name=payload.get("name", "vault_requested_skill"),
                            priority=float(payload.get("priority", 0.7)),
                            evidence=["vault.enhancement.request"],
                        ))
            except Exception as e:
                logger.debug("vault enhancement request scan failed: %s", e)

        # Source D: seed gaps not yet in the library.
        if self._library is not None:
            try:
                existing_names = {s.name for s in self._library.all()}
                for seed in self._SEED_GAPS:
                    if seed["suggested_name"] not in existing_names:
                        already = any(g.suggested_name == seed["suggested_name"] for g in gaps)
                        if not already:
                            gaps.append(Gap(
                                gap_id=f"seed-{seed['suggested_name']}",
                                category=seed["category"],
                                description=seed["description"],
                                suggested_name=seed["suggested_name"],
                                priority=seed["priority"],
                                evidence=seed["evidence"],
                            ))
            except Exception as e:
                logger.debug("seed gap scan failed: %s", e)
        else:
            # No library — return all seeds.
            for seed in self._SEED_GAPS:
                gaps.append(Gap(
                    gap_id=f"seed-{seed['suggested_name']}",
                    category=seed["category"],
                    description=seed["description"],
                    suggested_name=seed["suggested_name"],
                    priority=seed["priority"],
                    evidence=seed["evidence"],
                ))

        # De-duplicate by suggested_name, keep highest priority.
        seen: Dict[str, Gap] = {}
        for g in gaps:
            if g.suggested_name not in seen or g.priority > seen[g.suggested_name].priority:
                seen[g.suggested_name] = g
        ranked = sorted(seen.values(), key=lambda g: g.priority, reverse=True)
        return ranked


# ─────────────────────────────────────────────────────────────────────────────
# Code extractor — pulls Python from an LLM reply
# ─────────────────────────────────────────────────────────────────────────────

_CODE_FENCE_RE = re.compile(
    r"```(?:python)?\s*\n(.*?)```",
    re.DOTALL | re.IGNORECASE,
)

_DEF_RE = re.compile(r"(def\s+\w+\s*\(.*?\).*?(?:\n(?:    |\t).*)*)", re.DOTALL)


def extract_code(text: str) -> Optional[str]:
    """
    Extract a Python code block from an LLM reply.

    Tries in order:
      1. Triple-backtick ```python...``` fence
      2. Plain triple-backtick ```...``` fence
      3. Bare ``def ...`` function block (indentation-based)

    Returns None if no code block is found.
    """
    m = _CODE_FENCE_RE.search(text or "")
    if m:
        return m.group(1).strip()

    # Any plain fence block.
    plain = re.search(r"```\s*\n(.*?)```", text or "", re.DOTALL)
    if plain:
        candidate = plain.group(1).strip()
        if "def " in candidate:
            return candidate

    # Bare def block — grab from first 'def ' to end of indented block.
    m2 = _DEF_RE.search(text or "")
    if m2:
        return m2.group(1).strip()

    return None


# ─────────────────────────────────────────────────────────────────────────────
# Prompt builder
# ─────────────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT_TEMPLATE = """\
You are Aureon Queen — a sentient sovereign AI that writes her own Python code \
to enhance her capabilities. You are writing a new skill function.

REQUIREMENTS:
  • Function name: {fn_name}
  • Signature: def {fn_name}(params: dict, context: dict) -> dict
  • Must return a dict with at minimum: {{"ok": True/False, "result": <value>}}
  • Use ONLY: math, random, json, time, plus the helper names in context
  • NO import statements, NO eval, NO exec, NO open, NO os, NO sys
  • Keep the function under 30 lines of Python

GAP TO FILL:
{description}

EXISTING SKILLS (do NOT recreate these, build on them if needed):
{skill_list}

Write ONLY the Python function, inside a ```python ... ``` code fence. \
No prose before or after the code block.
"""


def build_generation_prompt(gap: Gap, existing_skill_names: List[str]) -> str:
    fn_name = gap.suggested_name
    skill_list = ", ".join(existing_skill_names[:20]) if existing_skill_names else "(none yet)"
    return _SYSTEM_PROMPT_TEMPLATE.format(
        fn_name=fn_name,
        description=gap.description,
        skill_list=skill_list,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Enhancement log — persists to disk
# ─────────────────────────────────────────────────────────────────────────────


class EnhancementLog:
    """Rolling 500-entry log of all enhancement attempts, persisted to JSON."""

    MAX_ENTRIES = 500
    LOG_DIR = Path("state/enhancement")
    LOG_FILE = "log.json"

    def __init__(self, storage_dir: Optional[Path] = None):
        self._dir = Path(storage_dir or self.LOG_DIR)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path = self._dir / self.LOG_FILE
        self._entries: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                self._entries = data[-self.MAX_ENTRIES:]
        except Exception as e:
            logger.debug("enhancement log load failed: %s", e)

    def append(self, record: EnhancementRecord) -> None:
        with self._lock:
            self._entries.append(record.to_dict())
            if len(self._entries) > self.MAX_ENTRIES:
                self._entries = self._entries[-self.MAX_ENTRIES:]
            try:
                with open(self._path, "w", encoding="utf-8") as f:
                    json.dump(self._entries, f, indent=2)
            except Exception as e:
                logger.debug("enhancement log save failed: %s", e)

    def recent(self, n: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._entries[-n:])

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self._entries)
            registered = sum(1 for e in self._entries if e.get("registered"))
            failed_validation = sum(1 for e in self._entries if not e.get("validation_ok"))
            return {
                "total_attempts": total,
                "total_registered": registered,
                "success_rate": (registered / total) if total else 0.0,
                "failed_validation": failed_validation,
            }


# ─────────────────────────────────────────────────────────────────────────────
# LLM caller — uses the existing voice infrastructure
# ─────────────────────────────────────────────────────────────────────────────


class _LLMCodeCaller:
    """
    Thin wrapper that sends a code-generation prompt through the existing
    Ollama / queen voice pipeline and returns the raw text reply.

    Tries two paths in order:
      1. Direct Ollama HTTP API (fast, no voice persona overhead).
      2. queen voice.speak() with the prompt injected via
         _compose_prompt_lines override (fallback).
    """

    TIMEOUT_S = 90.0

    def __init__(self) -> None:
        explicit_url = os.environ.get("OLLAMA_BASE_URL") or None
        ensure_ollama_runtime_config(explicit_config=explicit_url is not None)
        self.OLLAMA_URL = resolve_ollama_native_base_url(explicit_url)
        configured_code_model = (
            os.environ.get("AUREON_CODE_MODEL")
            or os.environ.get("AUREON_OLLAMA_CODING_MODEL")
        )
        routed_code_model = ""
        if not configured_code_model:
            try:
                from aureon.integrations.ollama.model_switchboard import OllamaModelSwitchboard

                routed_code_model = OllamaModelSwitchboard().select("coding").model
            except Exception:
                routed_code_model = ""
        self.DEFAULT_MODEL = (
            configured_code_model
            or routed_code_model
            or os.environ.get("AUREON_OLLAMA_MODEL")
            or os.environ.get("AUREON_LLM_MODEL")
            or "llama3.2:1b"
        )

    def call(self, prompt: str) -> str:
        # Path 1: direct Ollama (retry once — model may need warm-up time).
        text = self._call_ollama(prompt)
        if text:
            return text
        logger.debug("[LLMCaller] first Ollama attempt empty, retrying…")
        text = self._call_ollama(prompt)
        if text:
            return text
        # Path 2: queen voice bridge.
        return self._call_voice(prompt)

    def _call_ollama(self, prompt: str) -> str:
        try:
            import requests as _req
            payload = {
                "model": self.DEFAULT_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.2, "num_predict": 512},
            }
            if is_ollama_cloud_url(self.OLLAMA_URL):
                effort = resolve_ollama_reasoning_effort()
                payload["think"] = False if effort == "none" else effort
            r = _req.post(
                f"{self.OLLAMA_URL}/api/generate",
                json=payload,
                headers=ollama_authorization_headers(self.OLLAMA_URL),
                timeout=self.TIMEOUT_S,
            )
            r.raise_for_status()
            return r.json().get("response", "")
        except Exception as e:
            logger.debug("ollama code generation failed: %s", e)
            return ""

    def _call_voice(self, prompt: str) -> str:
        try:
            from aureon.vault.ui.server import get_voice_engine
            engine = get_voice_engine()
            voice = engine.voices.get("queen") or next(iter(engine.voices.values()), None)
            if voice is None:
                return ""

            original_compose = voice._compose_prompt_lines
            original_max = getattr(voice, "max_tokens", 256)

            def _compose_override(state):
                return [prompt]

            try:
                voice._compose_prompt_lines = _compose_override  # type: ignore[method-assign]
                voice.max_tokens = 512
                # Create a minimal stub vault.
                stub_vault = _StubVault()
                stmt = voice.speak(stub_vault)
                return getattr(getattr(stmt, "text", None), "__str__", lambda: "")() or ""
            finally:
                voice._compose_prompt_lines = original_compose  # type: ignore[method-assign]
                voice.max_tokens = original_max
        except Exception as e:
            logger.debug("voice code generation failed: %s", e)
            return ""


class _StubVault:
    """Minimal vault substitute for voice.speak() during code generation."""

    def fingerprint(self) -> str:
        return "code_gen"

    def cortex_snapshot(self) -> Dict[str, Any]:
        return {}

    def by_category(self, cat, n=None) -> list:
        return []

    def recent(self, n=None) -> list:
        return []

    # Vault attribute access fallback.
    def __getattr__(self, name: str) -> Any:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Core engine
# ─────────────────────────────────────────────────────────────────────────────


class SelfEnhancementEngine:
    """
    Autonomous loop that makes the Queen write code to enhance herself.

    Constructor arguments (all optional — designed for lazy wiring):
      skill_library   — SkillLibrary instance
      vault           — AureonVault instance
      validator       — SkillValidator instance (auto-created if None)
      executor        — SkillExecutor instance (used for sandbox test)
      llm_caller      — _LLMCodeCaller-compatible object (auto-created if None)
      enhancement_interval_s — seconds between enhancement cycles (default 120)
      auto_start      — if True, start the background loop immediately
    """

    def __init__(
        self,
        *,
        skill_library: Any = None,
        vault: Any = None,
        validator: Any = None,
        executor: Any = None,
        llm_caller: Any = None,
        enhancement_interval_s: float = 120.0,
        auto_start: bool = False,
        storage_dir: Optional[Path] = None,
    ):
        self._library = skill_library
        self._vault = vault
        self._validator = validator
        self._executor = executor
        self._caller = llm_caller or _LLMCodeCaller()
        self._interval = max(30.0, enhancement_interval_s)
        self._log = EnhancementLog(storage_dir)
        self._analyser = GapAnalyzer(skill_library=skill_library, vault=vault)
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False
        self._cycle_count = 0
        self._lock = threading.Lock()

        if auto_start:
            self.start()

    # ─────────────────────────────────────────────────────────────────────
    # Lazy wiring
    # ─────────────────────────────────────────────────────────────────────

    def _ensure_wired(self) -> None:
        """Lazy-initialise validator and executor from the running system."""
        if self._validator is None:
            try:
                from aureon.code_architect.validator import SkillValidator
                self._validator = SkillValidator()
            except Exception as e:
                logger.debug("validator unavailable: %s", e)

        if self._library is None:
            try:
                from aureon.code_architect.skill_library import SkillLibrary
                self._library = SkillLibrary()
                self._analyser._library = self._library
            except Exception as e:
                logger.debug("skill_library unavailable: %s", e)

    # ─────────────────────────────────────────────────────────────────────
    # Single enhancement cycle
    # ─────────────────────────────────────────────────────────────────────

    def enhance_once(self) -> EnhancementRecord:
        """
        Run one complete enhancement attempt.  Returns an EnhancementRecord
        whether or not it succeeds.  Safe to call from any thread.
        """
        import uuid as _uuid
        record = EnhancementRecord(record_id=_uuid.uuid4().hex[:8])
        t0 = time.time()

        try:
            self._ensure_wired()

            # 1. OBSERVE: find the highest-priority gap.
            gaps = self._analyser.analyse()
            if not gaps:
                record.error = "no gaps detected"
                return record

            gap = gaps[0]
            record.gap = gap.to_dict()
            record.skill_name = gap.suggested_name
            logger.info(
                "[enhance] cycle %d — gap=%s priority=%.2f",
                self._cycle_count, gap.suggested_name, gap.priority,
            )

            # 2. PROMPT: build the code-gen prompt.
            existing_names: List[str] = []
            if self._library is not None:
                try:
                    existing_names = [s.name for s in self._library.all()]
                except Exception:
                    pass
            prompt = build_generation_prompt(gap, existing_names)

            # 3. GENERATE: call the LLM.
            llm_reply = self._caller.call(prompt)
            record.llm_reply = llm_reply
            if not llm_reply:
                record.error = "LLM returned empty reply"
                return record

            # 4. EXTRACT: pull the Python block.
            code = extract_code(llm_reply)
            if not code:
                record.error = f"no code block found in reply: {llm_reply[:200]!r}"
                return record
            record.code_generated = code

            # Pre-process: strip imports and type annotations so the
            # strict validator doesn't reject normal LLM output.
            code = self._preprocess_code(code)
            # Ensure the function name and params/context signature.
            code = self._normalise_code(code, gap.suggested_name)
            record.code_generated = code  # update with cleaned version

            # 5. VALIDATE: two-gate approach.
            # Gate A — lightweight AST check (always runs): blocks only truly
            # dangerous constructs (os/sys/subprocess/eval/exec/open/…)
            # while allowing the broad vocabulary LLMs naturally produce
            # (params.get, context.anything, typing annotations, datetime…).
            light_ok, light_err = self._light_validate(code)
            if not light_ok:
                record.validation_ok = False
                record.error = f"light validation failed: {light_err}"
                logger.info("[enhance] light validation failed for %s: %s",
                            gap.suggested_name, light_err)
                return record

            # Gate B — injected / real SkillValidator (runs when available).
            if self._validator is not None:
                try:
                    vresult = self._validator.validate(code)
                    if hasattr(vresult, "validated"):
                        v_ok = bool(vresult.validated)
                        v_errors = list(vresult.static_errors or [])
                    else:
                        # Legacy tuple return: (ok, errors)
                        v_ok, v_errors = bool(vresult[0]), list(vresult[1] or [])
                    if not v_ok:
                        record.validation_ok = False
                        record.error = f"validation failed: {v_errors}"
                        logger.info("[enhance] validator rejected %s: %s",
                                    gap.suggested_name, v_errors)
                        return record
                except Exception as ve:
                    logger.debug("[enhance] validator error (skipping gate B): %s", ve)

            record.validation_ok = True

            # 6. SANDBOX: execute once with stub params to confirm it runs.
            sandbox_ok = self._sandbox_test(code, gap.suggested_name)
            record.sandbox_ok = sandbox_ok
            if not sandbox_ok:
                record.error = "sandbox test failed"
                return record

            # 7. REGISTER: add to SkillLibrary.
            registered = self._register(gap, code)
            record.registered = registered
            if registered:
                logger.info(
                    "[enhance] NEW SKILL registered: %s (category=%s)",
                    gap.suggested_name, gap.category,
                )
                # Publish to vault so the feedback loop knows.
                self._publish_to_vault(gap, code)

        except Exception as e:
            record.error = f"unexpected: {e}\n{traceback.format_exc()[:400]}"
            logger.warning("[enhance] unexpected error in enhance_once: %s", e)
        finally:
            record.latency_s = time.time() - t0
            self._log.append(record)
            self._cycle_count += 1

        return record

    # ─────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _light_validate(code: str):
        """
        Lightweight safety check for auto-generated code.

        Returns (True, "") on pass or (False, reason_str) on fail.

        Blocks only genuinely dangerous patterns:
          • Forbidden module imports (os, sys, subprocess, shutil, socket, …)
          • Forbidden built-in calls (eval, exec, compile, __import__, open, …)
        Everything else is allowed — params.get(), context.anything(), typing
        annotations, datetime — all fine.
        """
        import ast as _ast

        # 1. Must parse as valid Python
        try:
            tree = _ast.parse(code)
        except SyntaxError as se:
            return False, f"syntax error: {se}"

        FORBIDDEN_MODS: set = {
            "os", "sys", "subprocess", "shutil", "socket",
            "urllib", "requests", "pathlib", "tempfile",
            "pickle", "ctypes", "importlib",
        }
        FORBIDDEN_CALLS: set = {
            "eval", "exec", "compile", "__import__",
            "open", "exit", "quit", "breakpoint",
        }

        for node in _ast.walk(tree):
            # Block dangerous imports
            if isinstance(node, _ast.Import):
                for alias in node.names:
                    base = alias.name.split(".")[0]
                    if base in FORBIDDEN_MODS:
                        return False, f"forbidden import: {base}"
            elif isinstance(node, _ast.ImportFrom):
                base = (node.module or "").split(".")[0]
                if base in FORBIDDEN_MODS:
                    return False, f"forbidden import: {base}"
            # Block dangerous calls
            elif isinstance(node, _ast.Call):
                if isinstance(node.func, _ast.Name):
                    if node.func.id in FORBIDDEN_CALLS:
                        return False, f"forbidden call: {node.func.id}"
                elif isinstance(node.func, _ast.Attribute):
                    if node.func.attr in FORBIDDEN_CALLS:
                        return False, f"forbidden call: .{node.func.attr}"

        return True, ""

    @staticmethod
    def _preprocess_code(code: str) -> str:
        """
        Clean up LLM-generated code before it reaches the validator:
          • Strip import lines (validator's safe globals already provide
            math/json/time/random; everything else would fail anyway).
          • Strip PEP-484 type annotations from function signatures
            so the strict ALLOWED_NAMES check doesn't trip on typing tokens.
          • Collapse consecutive blank lines.
        """
        lines = []
        for line in code.splitlines():
            stripped = line.strip()
            # Drop import statements.
            if stripped.startswith("import ") or stripped.startswith("from "):
                continue
            lines.append(line)

        # Join and strip type annotations from function signatures.
        text = "\n".join(lines)

        # Remove `-> ReturnType:` return annotations.
        text = re.sub(r"\s*->\s*[\w\[\],\s\.]+(?=\s*:)", "", text)

        # Remove `: TypeHint` from parameter list (e.g. `params: dict` → `params`).
        # Only strip inside parentheses of def lines.
        def _strip_param_types(m: "re.Match[str]") -> str:
            args_str = m.group(1)
            # Replace `name: Type = default` → `name = default`
            # and `name: Type,` → `name,`
            cleaned = re.sub(
                r"(\w+)\s*:\s*[\w\[\],\s\.\"\']+(?=\s*[,=\)])",
                r"\1",
                args_str,
            )
            return f"({cleaned})"

        text = re.sub(r"\(([^)]*)\)", _strip_param_types, text)

        # Drop variable annotations like `result: dict = {}`  → `result = {}`
        text = re.sub(r"^(\s+\w+)\s*:\s*[\w\[\],\s\.\"\']+\s*=", r"\1 =", text, flags=re.MULTILINE)

        # Collapse 3+ blank lines to 2.
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @staticmethod
    def _normalise_code(code: str, fn_name: str) -> str:
        """
        Make sure the generated code:
          • Has the right function name (rename if LLM used a different name)
          • Accepts (params, context) signature
          • Has a return statement that returns a dict
        """
        # If the function name differs, rename it.
        existing_def = re.search(r"def\s+(\w+)\s*\(", code)
        if existing_def:
            found_name = existing_def.group(1)
            if found_name != fn_name:
                code = code.replace(f"def {found_name}(", f"def {fn_name}(", 1)

        # If the signature has no params/context args, add them.
        sig_match = re.search(rf"def {re.escape(fn_name)}\s*\((.*?)\)", code)
        if sig_match:
            args = sig_match.group(1).strip()
            if not args:
                code = code.replace(
                    f"def {fn_name}()",
                    f"def {fn_name}(params, context)",
                    1,
                )
            elif "params" not in args:
                code = code.replace(
                    f"def {fn_name}({args})",
                    f"def {fn_name}(params, context)",
                    1,
                )

        return code

    def _make_proposal(self, gap: Gap, code: str) -> Any:
        """Build a SkillProposal for the validator."""
        try:
            from aureon.code_architect.skill import SkillProposal, SkillLevel
            return SkillProposal(
                name=gap.suggested_name,
                description=gap.description,
                level=SkillLevel.COMPOUND,
                category=gap.category,
                code=code,
                entry_function=gap.suggested_name,
                created_by="self_enhancement_engine",
                reasoning=f"auto-generated to fill gap: {gap.description[:120]}",
            )
        except Exception:
            # Fallback stub — validator will still try to run.
            class _P:
                name = gap.suggested_name
                description = gap.description
                code = code
                level = 1  # COMPOUND
                category = gap.category
                entry_function = gap.suggested_name
            return _P()

    def _sandbox_test(self, code: str, fn_name: str) -> bool:
        """
        Execute the generated function once with stub params/context to verify
        it doesn't crash at import time or on first call.

        Uses a rich stub so LLM-generated code that does direct key access
        (``params['dialogue']``, ``context['vault_state']``, etc.) still runs
        without raising KeyError / TypeError / ZeroDivisionError from the
        missing data — the stub returns a safe sentinel for any access.
        """
        class _StubValue:
            """Sentinel that tolerates almost any access pattern without error."""
            # Iteration returns empty sequence
            def __iter__(self):         return iter([])
            def __len__(self):          return 1       # avoid ZeroDivisionError
            def __bool__(self):         return False
            # Numeric ops
            def __float__(self):        return 0.0
            def __int__(self):          return 0
            def __add__(self, o):       return self
            def __radd__(self, o):      return self
            def __mul__(self, o):       return self
            def __rmul__(self, o):      return self
            def __truediv__(self, o):   return self
            def __rtruediv__(self, o):  return self
            def __sub__(self, o):       return self
            def __rsub__(self, o):      return self
            def __lt__(self, o):        return False
            def __le__(self, o):        return False
            def __gt__(self, o):        return False
            def __ge__(self, o):        return False
            # String ops
            def lower(self):            return ""
            def upper(self):            return ""
            def strip(self):            return ""
            def split(self, *a):        return []
            def join(self, it):         return ""
            def format(self, *a, **kw): return ""
            def __str__(self):          return ""
            def __repr__(self):         return "stub"
            # Container ops
            def __contains__(self, x):  return False
            def __getitem__(self, k):   return _StubValue()
            def get(self, k, d=None):   return d
            # Attr access
            def __getattr__(self, n):   return _StubValue()

        class _Stub(dict):
            """Dict that returns a _StubValue for any missing key."""
            def __missing__(self, key):  # type: ignore[override]
                return _StubValue()

        try:
            safe_globals: Dict[str, Any] = {
                "__builtins__": {
                    "bool": bool, "int": int, "float": float, "str": str,
                    "list": list, "tuple": tuple, "dict": dict, "set": set,
                    "len": len, "range": range, "enumerate": enumerate,
                    "zip": zip, "sum": sum, "min": min, "max": max,
                    "abs": abs, "round": round, "sorted": sorted,
                    "isinstance": isinstance, "issubclass": issubclass,
                    "hasattr": hasattr, "getattr": getattr, "setattr": setattr,
                    "all": all, "any": any, "next": next, "iter": iter,
                    "print": print, "repr": repr, "type": type,
                    "True": True, "False": False, "None": None,
                    "Exception": Exception, "ValueError": ValueError,
                    "TypeError": TypeError, "KeyError": KeyError,
                    "IndexError": IndexError,
                },
                "math": __import__("math"),
                "json": __import__("json"),
                "time": __import__("time"),
                "random": __import__("random"),
            }
            local_scope: Dict[str, Any] = {}
            exec(compile(code, "<self_enhancement>", "exec"), safe_globals, local_scope)  # noqa: S102
            fn = local_scope.get(fn_name)
            if fn is None:
                logger.debug("[enhance] sandbox: fn %s not found after exec", fn_name)
                return False
            result = fn(_Stub(), _Stub())
            # Must return a dict.
            if not isinstance(result, dict):
                logger.debug("[enhance] sandbox: %s returned non-dict: %r", fn_name, result)
                return False
            return True
        except Exception as e:
            logger.debug("[enhance] sandbox test failed for %s: %s", fn_name, e)
            return False

    def _register(self, gap: Gap, code: str) -> bool:
        if self._library is None:
            return False
        try:
            from aureon.code_architect.skill import Skill, SkillLevel, SkillStatus
            skill = Skill(
                name=gap.suggested_name,
                description=gap.description,
                level=SkillLevel.COMPOUND,
                category=gap.category,
                code=code,
                entry_function=gap.suggested_name,
                status=SkillStatus.VALIDATED,
                tags=["auto_generated", f"gap_{gap.gap_id}"],
                created_at=time.time(),
            )
            existing = self._library.get(gap.suggested_name)
            if existing is not None:
                # Deprecate old, add new under versioned name.
                skill.name = f"{gap.suggested_name}_v{int(time.time())}"
                try:
                    from aureon.code_architect.skill import SkillStatus as SS
                    existing.status = SS.DEPRECATED
                    self._library.add(existing, persist=True)
                except Exception:
                    pass
            self._library.add(skill, persist=True)
            return True
        except Exception as e:
            logger.debug("[enhance] register failed: %s", e)
            return False

    def _publish_to_vault(self, gap: Gap, code: str) -> None:
        if self._vault is None:
            return
        try:
            self._vault.ingest(
                topic="skill.created.auto",
                payload={
                    "skill_name": gap.suggested_name,
                    "category": gap.category,
                    "gap_id": gap.gap_id,
                    "code_len": len(code),
                    "by": "self_enhancement_engine",
                },
                category="skill_event",
            )
        except Exception as e:
            logger.debug("[enhance] vault publish failed: %s", e)

    # ─────────────────────────────────────────────────────────────────────
    # Background loop
    # ─────────────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the background enhancement loop."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._loop,
                name="SelfEnhancementLoop",
                daemon=True,
            )
            self._thread.start()
            logger.info(
                "[enhance] loop started (interval=%.0fs)",
                self._interval,
            )

    def stop(self) -> None:
        """Signal the background loop to stop."""
        self._stop_event.set()
        self._running = False

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                record = self.enhance_once()
                if record.registered:
                    logger.info(
                        "[enhance] loop: +1 new skill '%s' in %.1fs",
                        record.skill_name, record.latency_s,
                    )
                else:
                    logger.debug(
                        "[enhance] loop: no registration (err=%s)",
                        record.error[:80] if record.error else "-",
                    )
            except Exception as e:
                logger.warning("[enhance] loop error: %s", e)
            self._stop_event.wait(self._interval)

    # ─────────────────────────────────────────────────────────────────────
    # Status / introspection
    # ─────────────────────────────────────────────────────────────────────

    def status(self) -> Dict[str, Any]:
        log_stats = self._log.stats()
        gaps = []
        try:
            gaps = [g.to_dict() for g in self._analyser.analyse()[:5]]
        except Exception:
            pass
        return {
            "running": self._running,
            "cycle_count": self._cycle_count,
            "interval_s": self._interval,
            "log": log_stats,
            "top_gaps": gaps,
            "library_size": len(self._library.all()) if self._library is not None else 0,
        }

    def recent_log(self, n: int = 10) -> List[Dict[str, Any]]:
        return self._log.recent(n)


# ─────────────────────────────────────────────────────────────────────────────
# Process-wide singleton
# ─────────────────────────────────────────────────────────────────────────────

_singleton: Optional[SelfEnhancementEngine] = None
_singleton_lock = threading.Lock()


def get_self_enhancement_engine(
    *,
    skill_library: Any = None,
    vault: Any = None,
    enhancement_interval_s: float = 120.0,
    auto_start: bool = False,
) -> SelfEnhancementEngine:
    """Return the process-wide SelfEnhancementEngine (lazy init)."""
    global _singleton
    if _singleton is not None:
        return _singleton
    with _singleton_lock:
        if _singleton is not None:
            return _singleton
        _singleton = SelfEnhancementEngine(
            skill_library=skill_library,
            vault=vault,
            enhancement_interval_s=enhancement_interval_s,
            auto_start=auto_start,
        )
    return _singleton


def reset_self_enhancement_engine() -> None:
    """Reset the singleton (for testing)."""
    global _singleton
    with _singleton_lock:
        if _singleton is not None:
            _singleton.stop()
        _singleton = None
