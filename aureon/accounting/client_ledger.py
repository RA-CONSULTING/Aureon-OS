"""
The Client Ledger — the King's double-entry doctrine, generalized to any business.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The trading organism's ``KingLedger`` proved the doctrine on R&A Consulting's
own books: every financial event is two balanced entries or it does not exist.
This module carries that doctrine to ANY client — a UK SME nominal chart
(sales, purchases, VAT control, payroll, director's loan), client-keyed books,
and money as INTEGER PENNIES so a commercial ledger never drifts on a float.

Every posting is an HNC coordination step: the entry proves its own balance,
and the step records the canonical field's Γ when the field is live (``None``
when dark — a dark field is reported dark, never invented). The pipeline's
coordination coherence is the measured fraction of steps that balanced — a
real metric of the books, not a decoration.

Gary Leckey · Aureon Institute
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List

__all__ = ["UK_SME_CHART", "Posting", "CoordinationStep", "ClientLedger"]

#: UK SME nominal chart (Sage-style 4-digit ranges). Registry-as-data: a
#: posting may only touch a code that is HERE — an unknown code is refused,
#: never silently created.
UK_SME_CHART: Dict[str, str] = {
    # assets (1xxx debit-normal)
    "1000": "Bank current account",
    "1010": "Bank deposit account",
    "1100": "Trade debtors (accounts receivable)",
    "1200": "Crypto holdings at cost",
    "1300": "Prepayments",
    # liabilities (2xxx credit-normal)
    "2000": "Trade creditors (accounts payable)",
    "2100": "VAT control account",
    "2110": "VAT on sales (output tax)",
    "2120": "VAT on purchases (input tax)",
    "2200": "PAYE/NI control account",
    "2300": "Pension control account",
    "2400": "Director's loan account",
    "2500": "Corporation tax payable",
    # equity (3xxx credit-normal)
    "3000": "Share capital / opening capital",
    "3100": "Retained earnings",
    # revenue (4xxx credit-normal)
    "4000": "Sales",
    "4100": "Other operating income",
    "4200": "Interest received",
    # expenses (5xxx-7xxx debit-normal)
    "5000": "Cost of sales / purchases",
    "6000": "Gross wages",
    "6100": "Employer's NI",
    "6200": "Employer's pension",
    "7000": "Rent and rates",
    "7100": "Office and admin",
    "7200": "Travel and subsistence",
    "7300": "Bank charges and fees",
    "7400": "Professional fees",
    "7500": "Software and subscriptions",
    # the honest bucket — uncategorized money waits HERE for a human/agent
    # decision; it is never guessed into a P&L line
    "9999": "Suspense (awaiting categorization)",
}

_DEBIT_NORMAL_PREFIXES = ("1", "5", "6", "7", "9")


def _canonical_gamma() -> float | None:
    """Canonical field Γ when live; ``None`` when dark. Never raises,
    never substitutes a neutral number for a dark field."""
    try:
        from aureon.core.hnc_field import read_canonical_field

        f = read_canonical_field()
        g = getattr(f, "coherence_gamma", None)
        if getattr(f, "is_live", False) and g is not None:
            return float(g)
    except Exception:  # noqa: BLE001 — accounting must not crash on a dark field
        pass
    return None


@dataclass(frozen=True)
class Posting:
    """One side of a journal entry, in integer pennies."""

    code: str
    debit_pennies: int = 0
    credit_pennies: int = 0
    memo: str = ""


@dataclass(frozen=True)
class CoordinationStep:
    """One measured step of the accounting pipeline — the HNC's audit row."""

    step: str
    ok: bool
    detail: str
    gamma: float | None
    ts: float

    def to_dict(self) -> Dict[str, Any]:
        return {"step": self.step, "ok": self.ok, "detail": self.detail,
                "gamma": self.gamma, "ts": self.ts}


class ClientLedger:
    """Double-entry books for ONE client, on the UK SME chart.

    ``post()`` refuses an unbalanced entry or an unknown nominal code — the
    refusal is itself a recorded coordination step, so the books' coherence
    metric reflects what was attempted, not just what succeeded.
    """

    def __init__(self, client_id: str, chart: Dict[str, str] | None = None):
        if not client_id or not str(client_id).strip():
            raise ValueError("a client ledger needs a real client_id")
        self.client_id = str(client_id).strip()
        self.chart = dict(chart or UK_SME_CHART)
        self.entries: List[Dict[str, Any]] = []
        self.coordination: List[CoordinationStep] = []

    # ── the one write path ────────────────────────────────────────────────
    def post(self, description: str, postings: List[Posting],
             reference: str = "", when: float | None = None) -> str | None:
        """Post a balanced journal entry. Returns the entry id, or ``None``
        when refused (the refusal is recorded, never silent)."""
        ts = float(when) if when is not None else time.time()
        debits = sum(int(p.debit_pennies) for p in postings)
        credits = sum(int(p.credit_pennies) for p in postings)

        unknown = [p.code for p in postings if p.code not in self.chart]
        if unknown:
            self._step("post", False,
                       f"refused: unknown nominal code(s) {unknown} — the chart "
                       f"is a registry, codes join by name", ts)
            return None
        if debits != credits:
            self._step("post", False,
                       f"refused: unbalanced entry (debits {debits}p != credits "
                       f"{credits}p) — '{description}'", ts)
            return None
        if debits == 0:
            self._step("post", False, f"refused: zero-value entry '{description}'", ts)
            return None

        entry_id = uuid.uuid4().hex[:12]
        self.entries.append({
            "id": entry_id, "ts": ts, "description": str(description),
            "reference": str(reference),
            "lines": [{"code": p.code, "name": self.chart[p.code],
                       "debit_pennies": int(p.debit_pennies),
                       "credit_pennies": int(p.credit_pennies),
                       "memo": p.memo} for p in postings],
        })
        self._step("post", True,
                   f"balanced {debits}p entry '{description}' ({len(postings)} lines)", ts)
        return entry_id

    # ── reads ─────────────────────────────────────────────────────────────
    def balance_pennies(self, code: str) -> int:
        """Signed balance of one nominal code (positive in its normal sense)."""
        debit = sum(ln["debit_pennies"] for e in self.entries for ln in e["lines"]
                    if ln["code"] == code)
        credit = sum(ln["credit_pennies"] for e in self.entries for ln in e["lines"]
                     if ln["code"] == code)
        if code[:1] in _DEBIT_NORMAL_PREFIXES:
            return debit - credit
        return credit - debit

    def trial_balance(self) -> Dict[str, Any]:
        """The classic proof: every code's balance, and debits == credits
        across the whole book (guaranteed by construction, verified anyway)."""
        rows = []
        total_debit = total_credit = 0
        for code in sorted(self.chart):
            debit = sum(ln["debit_pennies"] for e in self.entries
                        for ln in e["lines"] if ln["code"] == code)
            credit = sum(ln["credit_pennies"] for e in self.entries
                         for ln in e["lines"] if ln["code"] == code)
            if debit or credit:
                rows.append({"code": code, "name": self.chart[code],
                             "debit_pennies": debit, "credit_pennies": credit})
                total_debit += debit
                total_credit += credit
        balanced = total_debit == total_credit
        self._step("trial_balance", balanced,
                   f"{len(rows)} active codes, debits {total_debit}p vs "
                   f"credits {total_credit}p", time.time())
        return {"client_id": self.client_id, "rows": rows,
                "total_debit_pennies": total_debit,
                "total_credit_pennies": total_credit, "balanced": balanced}

    def suspense_pennies(self) -> int:
        """What still awaits an honest categorization decision."""
        return self.balance_pennies("9999")

    # ── the HNC coordination metric ───────────────────────────────────────
    def coordination_report(self) -> Dict[str, Any]:
        """Measured pipeline coherence: the fraction of coordination steps
        that succeeded, each step carrying the canonical Γ it saw (or None)."""
        steps = [s.to_dict() for s in self.coordination]
        ok = sum(1 for s in self.coordination if s.ok)
        return {
            "client_id": self.client_id,
            "steps": steps,
            "steps_total": len(steps),
            "steps_ok": ok,
            "coordination_coherence": round(ok / len(steps), 6) if steps else None,
            "boundary": ("Measured record of every accounting coordination attempt for this "
                         "client — balance proofs, refusals, and the canonical HNC Γ each step "
                         "saw (None when the field was dark). It is bookkeeping evidence, not "
                         "a claim about any person."),
        }

    def _step(self, step: str, ok: bool, detail: str, ts: float) -> None:
        self.coordination.append(
            CoordinationStep(step=step, ok=ok, detail=detail,
                             gamma=_canonical_gamma(), ts=ts))
