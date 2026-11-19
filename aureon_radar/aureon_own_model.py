"""Aureon-own structured analysis for Phi Radar; no external model fallback."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any

from aureon.inhouse_ai.llm_adapter import _aureon_own_adapter

logger = logging.getLogger("aureon.radar.own_model")


class AureonOwnModelInterface:
    """Call only Aureon's pinned model and cache successful JSON analyses."""

    def __init__(self, *, adapter: Any = None, cache_dir: Path | None = None) -> None:
        self.adapter = adapter if adapter is not None else _aureon_own_adapter()
        self.model = self.adapter.model
        self.cache_dir = cache_dir or Path(__file__).resolve().parent / "aureon_llm_cache"

    @staticmethod
    def _cache_key(prompt: str) -> str:
        return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]

    def _get_cached(self, key: str) -> dict[str, Any] | None:
        cache_file = self.cache_dir / f"{key}.json"
        try:
            if time.time() - cache_file.stat().st_mtime >= 300:
                return None
            payload = json.loads(cache_file.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else None
        except (OSError, ValueError, TypeError):
            return None

    def _save_cache(self, key: str, data: dict[str, Any]) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        target = self.cache_dir / f"{key}.json"
        temporary = target.with_suffix(".tmp")
        temporary.write_text(json.dumps(data), encoding="utf-8")
        temporary.replace(target)

    def analyze_market_data(
        self,
        data: dict[str, Any],
        prompt_type: str = "signal_extraction",
    ) -> dict[str, Any]:
        """Return advisory structured analysis without authorizing any trade."""

        prompt = self._build_prompt(data, prompt_type)
        cache_key = self._cache_key(prompt)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        try:
            response = self.adapter.prompt(
                [{"role": "user", "content": prompt}],
                system=(
                    "You are Aureon's advisory market-data analyst. Return only the "
                    "requested JSON. Never claim that analysis authorizes or executes a trade."
                ),
                max_tokens=512,
                temperature=0,
            )
            if response.stop_reason == "error" or not str(response.text or "").strip():
                return {
                    "error": "aureon_own_model_unavailable",
                    "fallback": False,
                    "trade_allowed": False,
                }
            try:
                analysis = json.loads(response.text)
                if not isinstance(analysis, dict):
                    raise ValueError("aureon_analysis_must_be_an_object")
            except (json.JSONDecodeError, ValueError):
                analysis = {"raw": response.text, "parsed": False}
            analysis.setdefault("trade_allowed", False)
            self._save_cache(cache_key, analysis)
            return analysis
        except Exception as exc:
            logger.warning("Aureon own-model analysis failed: %s", type(exc).__name__)
            return {
                "error": "aureon_own_model_unavailable",
                "fallback": False,
                "trade_allowed": False,
            }

    @staticmethod
    def _build_prompt(data: dict[str, Any], prompt_type: str) -> str:
        if prompt_type == "signal_extraction":
            return f"""Analyze this market data and extract advisory signals.
Return ONLY valid JSON with this structure:
{{
    "direction": "LONG|SHORT|NEUTRAL",
    "confidence": 0.0-1.0,
    "target_price": float,
    "stop_loss": float,
    "reasoning": "brief explanation"
}}

Market Data: {json.dumps(data)}
"""
        if prompt_type == "volatility_scan":
            return f"""Scan this data for volatility anomalies.
Return ONLY valid JSON:
{{
    "volatility_score": 0.0-1.0,
    "anomaly_detected": true|false,
    "direction_bias": "LONG|SHORT|NEUTRAL",
    "urgency": "LOW|MEDIUM|HIGH"
}}

Data: {json.dumps(data)}
"""
        return f"Analyze: {json.dumps(data)}"
