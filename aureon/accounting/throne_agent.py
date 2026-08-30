"""
Dr. Auris Throne takes the agent seat — the categorization judge.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

``categorize.recategorize_suspense`` exposes a ``decide`` callable — this
module fills that seat with a real agent: Dr. Auris Throne speaking through
the in-house Ollama adapter (``aureon.inhouse_ai.llm_adapter``), the same
sovereign local-model path the rest of the organism uses. No new wheel.

The doctrine holds at every layer:

* **The chart is the law**: the agent is shown the client's nominal chart and
  may answer ONLY with a code from it (or UNDECIDED). Whatever comes back is
  validated here first, and the ledger validates it again on post — a
  hallucinated code is refused twice, never booked once.
* **A dark model is reported dark**: no Ollama server (or offline/audit mode)
  means ``decide`` returns ``None`` — the pound stays in suspense and the
  named blocker says exactly why. The agent's silence is never converted
  into a guess.
* **Every consultation is measured**: ``consultations`` records what was
  asked, what came back, and whether it was usable — the same honesty the
  ledger's coordination steps give the books.

Gary Leckey · Aureon Institute
"""

from __future__ import annotations

import re
from typing import Any

from aureon.accounting.client_ledger import UK_SME_CHART

__all__ = ["ThroneCategorizer", "THRONE_SYSTEM_PROMPT"]

THRONE_SYSTEM_PROMPT = (
    "You are Dr. Auris Throne, the categorization judge of the King's Court "
    "accounting body. You are shown one bank-statement line and the client's "
    "nominal chart. Answer with EXACTLY one nominal code from the chart, or "
    "the single word UNDECIDED if the description does not clearly name one. "
    "Never invent a code. Never explain. One token of judgement only."
)

#: answers that mean "I cannot honestly name this" — mapped to None (suspense)
_UNDECIDED_WORDS = {"undecided", "unknown", "none", "n/a", "9999"}


class ThroneCategorizer:
    """The agent seat for ``recategorize_suspense(decide=...)``.

    ``adapter`` is anything with ``health_check() -> bool`` and
    ``prompt(messages, system=..., max_tokens=..., temperature=...) ->
    LLMResponse`` — by default the in-house ``AureonLocalAdapter`` (Ollama).
    Tests inject a stub; production plugs the live local model in unchanged.
    """

    def __init__(self, chart: dict[str, str] | None = None, adapter: Any = None):
        self.chart = dict(chart or UK_SME_CHART)
        if adapter is None:
            from aureon.integrations.ollama import OllamaModelSwitchboard

            adapter, _selection = OllamaModelSwitchboard().compatible_adapter_for("fast")
        self.adapter = adapter
        self.consultations: list[dict[str, Any]] = []
        self.blockers: list[str] = []

    # ── the seat itself ───────────────────────────────────────────────────
    def decide(self, description: str, signed_pennies: int) -> str | None:
        """Name one chart code for a suspense line, or ``None`` (undecided)."""
        if not self._model_live():
            return None
        raw = self._ask(description, signed_pennies)
        code = self._parse_code(raw)
        self.consultations.append({
            "description": str(description),
            "signed_pennies": int(signed_pennies),
            "raw_answer": raw,
            "code": code,
            "usable": code is not None,
        })
        return code

    def status(self) -> dict[str, Any]:
        """Measured record of the seat: live or dark, and every consultation."""
        live = self._model_live(record=False)
        return {
            "agent": "dr_auris_throne",
            "backend": type(self.adapter).__name__,
            "model_live": live,
            "consultations": list(self.consultations),
            "blockers": list(self.blockers),
            "note": ("a dark model returns None (undecided) — the pound stays in "
                     "suspense with a named blocker, never a guessed code"),
        }

    # ── internals ─────────────────────────────────────────────────────────
    def _model_live(self, record: bool = True) -> bool:
        try:
            live = bool(self.adapter.health_check())
        except Exception as exc:  # noqa: BLE001 — a crashing backend is a dark backend
            live = False
            if record:
                self.blockers.append(f"agent backend raised on health check: {exc}")
            return False
        if not live and record:
            blocker = ("no local model reachable (Ollama server dark or "
                       "offline/audit mode) — agent seat empty, suspense stays honest")
            if blocker not in self.blockers:
                self.blockers.append(blocker)
        return live

    def _ask(self, description: str, signed_pennies: int) -> str:
        chart_lines = "\n".join(f"{code} — {name}" for code, name in sorted(self.chart.items())
                                if code != "9999")
        direction = "money IN (income-shaped)" if signed_pennies > 0 else "money OUT (cost-shaped)"
        pounds = abs(int(signed_pennies))
        prompt = (
            f"Nominal chart:\n{chart_lines}\n\n"
            f"Bank line: \"{description}\" — {direction}, "
            f"£{pounds // 100:,}.{pounds % 100:02d}\n\n"
            "Your one-token judgement (a code above, or UNDECIDED):"
        )
        try:
            resp = self.adapter.prompt(
                [{"role": "user", "content": prompt}],
                system=THRONE_SYSTEM_PROMPT,
                max_tokens=8,
                temperature=0.0,
            )
            if getattr(resp, "stop_reason", "") == "error":
                self.blockers.append(f"model call errored: {resp.text[:120]}")
                return ""
            return str(getattr(resp, "text", "") or "")
        except Exception as exc:  # noqa: BLE001 — an erring agent is an undecided agent
            self.blockers.append(f"model call raised: {exc}")
            return ""

    def _parse_code(self, raw: str) -> str | None:
        text = str(raw or "").strip()
        if not text or text.lower().split()[0].strip(".,") in _UNDECIDED_WORDS:
            return None
        match = re.search(r"\b(\d{4})\b", text)
        if not match:
            return None
        code = match.group(1)
        # the chart is the law — and 9999 is a destination the agent may not name
        if code not in self.chart or code == "9999":
            return None
        return code
