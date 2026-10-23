"""
HNC AURIS NODES — hnc_auris_nodes.py
======================================
Adapted from Aureon's aureon_auris_trader.py (417 lines).

In Aureon, the Auris Trader uses 9 Nodes of Reality — each represented
by an animal archetype. Each node analyses a different dimension of
the market. When all nodes AGREE (coherence Γ > 0.938), the system
acts. When they disagree, it waits.

AUREON 9 NODES               →  HNC 9 NODES
──────────────────────────────────────────────────
TigerNode (volatility)       →  Tiger (amount volatility — is it stable?)
FalconNode (momentum)        →  Falcon (expense trend — rising or falling?)
HummingbirdNode (stability)  →  Hummingbird (frequency — regular or erratic?)
DolphinNode (waveform)       →  Dolphin (pattern — recurring or one-off?)
DeerNode (micro-shift)       →  Deer (subtle changes — rounding, timing shifts)
OwlNode (pattern)            →  Owl (deep pattern — sector benchmarks)
PandaNode (safety)           →  Panda (safety — is the claim legally safe?)
CargoShipNode (liquidity)    →  CargoShip (cash flow — can we afford this claim?)
ClownfishNode (symbiosis)    →  Clownfish (cross-system — does this help other claims?)

When all 9 nodes agree on a classification → HIGH CONFIDENCE
When nodes disagree → FLAG FOR HUMAN REVIEW
The coherence score Γ determines classification confidence.

Entry threshold: Γ > 0.938 (same as Aureon)
Review threshold: Γ < 0.700
Override threshold: Γ < 0.500

Every expense passes through all 9 nodes simultaneously.
This is how we achieve human-level classification confidence
without a human.

Aureon Creator / Aureon Research — April 2026
"""

from __future__ import annotations
import logging
import math
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger("hnc_auris_nodes")

PHI = (1 + math.sqrt(5)) / 2  # 1.618


# ═══════════════════════════════════════════════════════════════════
# COHERENCE THRESHOLDS — Same as Aureon
# ═══════════════════════════════════════════════════════════════════

COHERENCE_ENTRY = 0.938      # All nodes agree → auto-classify
COHERENCE_REVIEW = 0.700     # Some disagreement → flag for review
COHERENCE_OVERRIDE = 0.500   # Major disagreement → human must decide


class ClassificationAction(Enum):
    """What to do based on coherence"""
    AUTO_CLASSIFY = "AUTO_CLASSIFY"     # Γ > 0.938
    CLASSIFY_REVIEW = "CLASSIFY_REVIEW" # 0.700 < Γ < 0.938
    HUMAN_REQUIRED = "HUMAN_REQUIRED"   # Γ < 0.700


# ═══════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════

@dataclass
class NodeSignal:
    """Output from a single node"""
    node_name: str
    category_vote: str            # What category this node thinks it is
    confidence: float             # 0-1 how sure this node is
    reasoning: str


@dataclass
class CoherenceResult:
    """Combined result from all 9 nodes"""
    transaction_description: str
    transaction_amount: float
    node_signals: List[NodeSignal]
    coherence_score: float        # Γ — the magic number
    consensus_category: str       # The category most nodes agree on
    action: ClassificationAction
    confidence: float
    dissenting_nodes: List[str]   # Which nodes disagree
    reasoning: str


# ═══════════════════════════════════════════════════════════════════
# BASE NODE
# ═══════════════════════════════════════════════════════════════════

class AurisNode(ABC):
    """Base class for all 9 nodes. Same as Aureon's AurisNode."""
    name: str = "Base"
    weight: float = 1.0

    @abstractmethod
    def analyse(self, description: str, amount: float, **context) -> NodeSignal:
        """Analyse a transaction and vote on its category."""
        pass


# ═══════════════════════════════════════════════════════════════════
# THE 9 NODES OF REALITY — Adapted for Tax
# ═══════════════════════════════════════════════════════════════════

class TigerNode(AurisNode):
    """
    TIGER — Amount Volatility Analysis.
    Aureon: analyses price volatility/spread.
    HNC: analyses whether this amount is normal for the category.
    """
    name = "Tiger"
    weight = PHI  # Highest weight

    # Typical ranges for SA103 categories
    CATEGORY_RANGES = {
        "cost_of_sales": (50, 5_000),
        "motor": (20, 200),
        "admin": (10, 500),
        "other_direct": (100, 10_000),
        "other_expenses": (50, 1_000),
        "capital": (500, 50_000),
        "private": (5, 500),
    }

    def analyse(self, description: str, amount: float, **context) -> NodeSignal:
        best_cat = "other_expenses"
        best_fit = 0

        for cat, (low, high) in self.CATEGORY_RANGES.items():
            if low <= amount <= high:
                # Closeness to middle of range
                mid = (low + high) / 2
                fit = 1 - abs(amount - mid) / (high - low)
                if fit > best_fit:
                    best_fit = fit
                    best_cat = cat

        return NodeSignal(
            node_name=self.name,
            category_vote=best_cat,
            confidence=max(0.3, best_fit),
            reasoning=f"Amount £{amount:,.2f} fits '{best_cat}' range ({best_fit:.1%} fit)"
        )


class FalconNode(AurisNode):
    """
    FALCON — Momentum/Trend Analysis.
    Aureon: analyses price momentum and volume.
    HNC: analyses if this type of expense has been trending up/down.
    """
    name = "Falcon"
    weight = 1.0

    def analyse(self, description: str, amount: float, **context) -> NodeSignal:
        history = context.get("payee_history", [])
        if len(history) >= 3:
            trend = sum(history[-3:]) / 3
            if amount > trend * 1.5:
                return NodeSignal(self.name, "review_needed", 0.6,
                    f"Amount £{amount:,.0f} significantly above recent avg £{trend:,.0f}")
            return NodeSignal(self.name, context.get("historical_category", "other_expenses"), 0.85,
                f"Consistent with recent trend (avg £{trend:,.0f})")
        return NodeSignal(self.name, "other_expenses", 0.5,
            "Insufficient history for trend analysis")


class HummingbirdNode(AurisNode):
    """
    HUMMINGBIRD — Frequency/Stability Analysis.
    Aureon: analyses price stability and micro-movements.
    HNC: analyses how frequently this payee/type appears.
    """
    name = "Hummingbird"
    weight = 1 / PHI

    def analyse(self, description: str, amount: float, **context) -> NodeSignal:
        frequency = context.get("payee_frequency", 0)  # Times per year
        if frequency >= 12:  # Monthly
            return NodeSignal(self.name, "admin", 0.8,
                f"Monthly recurring ({frequency}x/year) — likely subscription/admin")
        elif frequency >= 4:  # Quarterly
            return NodeSignal(self.name, "cost_of_sales", 0.7,
                f"Regular ({frequency}x/year) — likely operational cost")
        elif frequency == 1:
            return NodeSignal(self.name, "capital", 0.6,
                f"One-off payment — possible capital expenditure")
        return NodeSignal(self.name, "other_expenses", 0.5,
            f"Irregular ({frequency}x/year)")


class DolphinNode(AurisNode):
    """
    DOLPHIN — Pattern/Waveform Analysis.
    Aureon: analyses price waveform and emotion.
    HNC: analyses description patterns and known payees.
    """
    name = "Dolphin"
    weight = 1.0

    PATTERNS = {
        "cost_of_sales": [r"(?i)travis|jewson|screwfix|wickes|b&q|selco|buildbase|toolstation|materials|timber|cement|plaster|brick"],
        "motor": [r"(?i)fuel|petrol|diesel|bp|shell|texaco|esso|jet|applegreen|maxol|parking|toll"],
        "admin": [r"(?i)insurance|aviva|axa|direct line|zurich|phone|ee|vodafone|three|bt|sky|virgin|broadband|office|stationery"],
        "other_direct": [r"(?i)labour|subcontract|groundwork|scaffold|plant hire|skip|hire"],
        "other_expenses": [r"(?i)citb|cscs|training|course|cpd|membership|subscription|accountan"],
        "capital": [r"(?i)close brothers|black horse|finance|vehicle|van|truck|machinery|excavator"],
        "private": [r"(?i)netflix|spotify|amazon prime|sky sports|just eat|deliveroo|restaurant|holiday|primark"],
    }

    def analyse(self, description: str, amount: float, **context) -> NodeSignal:
        for category, patterns in self.PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, description):
                    return NodeSignal(self.name, category, 0.90,
                        f"Description matches '{category}' pattern")
        return NodeSignal(self.name, "other_expenses", 0.4,
            "No pattern match — unknown payee")


class DeerNode(AurisNode):
    """
    DEER — Micro-Shift Detection.
    Aureon: detects subtle price shifts.
    HNC: detects subtle signals — rounding, timing, amount patterns.
    """
    name = "Deer"
    weight = 1 / PHI

    def analyse(self, description: str, amount: float, **context) -> NodeSignal:
        signals = []
        category = "other_expenses"
        confidence = 0.5

        # Round number detection (suspicious)
        if amount > 100 and amount % 100 == 0:
            signals.append("Round £100 multiple — possible estimate")
            confidence -= 0.1

        if amount > 1000 and amount % 1000 == 0:
            signals.append("Round £1000 multiple — possible capital or drawing")
            category = "capital" if amount >= 5000 else "review_needed"

        # Finance payment pattern (regular exact amounts)
        if 200 <= amount <= 600 and amount == round(amount, 2):
            signals.append("Finance payment range — possible HP/lease")
            category = "capital"
            confidence = 0.65

        # Micro amount (subscription)
        if amount < 20:
            signals.append("Micro amount — subscription or personal")
            category = "admin" if amount > 5 else "private"
            confidence = 0.7

        return NodeSignal(self.name, category, confidence,
            "; ".join(signals) if signals else "No micro-signals detected")


class OwlNode(AurisNode):
    """
    OWL — Deep Pattern Recognition.
    Aureon: analyses historical patterns.
    HNC: compares against HMRC sector benchmarks.
    """
    name = "Owl"
    weight = PHI  # High weight — wisdom node

    def analyse(self, description: str, amount: float, **context) -> NodeSignal:
        turnover = context.get("turnover", 51_000)
        existing_motor = context.get("existing_motor_total", 0)
        existing_materials = context.get("existing_materials_total", 0)

        # Check if adding this to motor would breach benchmark
        if "fuel" in description.lower() or "motor" in description.lower():
            new_motor_pct = (existing_motor + amount) / turnover if turnover else 0
            if new_motor_pct > 0.15:
                return NodeSignal(self.name, "motor", 0.5,
                    f"Motor would reach {new_motor_pct:.0%} of turnover — HMRC benchmark is 5-15%")
            return NodeSignal(self.name, "motor", 0.85,
                f"Motor at {new_motor_pct:.0%} — within benchmark")

        return NodeSignal(self.name, context.get("default_category", "other_expenses"), 0.6,
            "Sector benchmark analysis — no specific flags")


class PandaNode(AurisNode):
    """
    PANDA — Safety Analysis.
    Aureon: analyses risk and safety of position.
    HNC: analyses legal safety of the classification.
    """
    name = "Panda"
    weight = 1.0

    SAFE_CATEGORIES = {"cost_of_sales", "motor", "admin", "other_expenses"}
    RISKY_CATEGORIES = {"capital", "other_direct"}
    DANGEROUS_CATEGORIES = {"private"}

    def analyse(self, description: str, amount: float, **context) -> NodeSignal:
        suggested_cat = context.get("suggested_category", "other_expenses")

        if suggested_cat in self.SAFE_CATEGORIES:
            return NodeSignal(self.name, suggested_cat, 0.90,
                f"'{suggested_cat}' is a safe, well-established category")
        elif suggested_cat in self.RISKY_CATEGORIES:
            return NodeSignal(self.name, suggested_cat, 0.70,
                f"'{suggested_cat}' attracts more scrutiny — ensure evidence")
        elif suggested_cat in self.DANGEROUS_CATEGORIES:
            return NodeSignal(self.name, "private", 0.95,
                "Private expense — do NOT claim as business")
        return NodeSignal(self.name, "other_expenses", 0.60,
            "Defaulting to safer category")


class CargoShipNode(AurisNode):
    """
    CARGO SHIP — Cash Flow / Liquidity Analysis.
    Aureon: analyses market liquidity.
    HNC: analyses cash flow impact of the classification.
    """
    name = "CargoShip"
    weight = 1 / (PHI * PHI)  # Lower weight

    def analyse(self, description: str, amount: float, **context) -> NodeSignal:
        cash_balance = context.get("cash_balance", 10_000)
        monthly_income = context.get("monthly_income", 4_250)

        # Large expense relative to cash
        if amount > cash_balance * 0.5:
            return NodeSignal(self.name, "capital", 0.7,
                f"Large relative to cash (£{amount:,.0f} vs £{cash_balance:,.0f} balance) — likely capital")
        elif amount > monthly_income:
            return NodeSignal(self.name, "other_direct", 0.65,
                f"Exceeds monthly income — significant operational cost")
        return NodeSignal(self.name, "cost_of_sales", 0.55,
            "Normal operational size relative to cash flow")


class ClownfishNode(AurisNode):
    """
    CLOWNFISH — Symbiosis / Cross-System Analysis.
    Aureon: analyses symbiotic relationships between pairs.
    HNC: analyses how this classification helps OTHER tax positions.
    """
    name = "Clownfish"
    weight = 1 / PHI

    def analyse(self, description: str, amount: float, **context) -> NodeSignal:
        current_profit = context.get("current_profit", 25_000)
        basic_rate_limit = 50_270

        # If classifying as expense helps stay in basic rate band
        if current_profit - amount < basic_rate_limit and current_profit > basic_rate_limit:
            return NodeSignal(self.name, "cost_of_sales", 0.85,
                f"Claiming this keeps profit below higher rate (£{basic_rate_limit:,})")

        # If we're near loss territory, be careful
        if current_profit - amount < 0:
            return NodeSignal(self.name, "review_needed", 0.6,
                "Claiming this would create a loss — needs loss relief justification")

        return NodeSignal(self.name, context.get("default_category", "cost_of_sales"), 0.65,
            "No symbiotic effect detected")


# ═══════════════════════════════════════════════════════════════════
# THE AURIS ENGINE — Coherence Calculator
# ═══════════════════════════════════════════════════════════════════

class HNCAurisEngine:
    """
    9-Node Coherence Classification Engine.

    Adapted from Aureon's AurisEngine:
    All 9 nodes analyse every transaction simultaneously.
    Coherence Γ is calculated from agreement level.
    Same thresholds: entry 0.938, exit 0.700.

    Frequencies are the canonical Auris table (Tiger 220 … Clownfish 963).
    The drifted Tiger 741 / Clownfish 639 assignment is not loaded.
    """

    CANONICAL_AURIS_HZ = {
        "Tiger": 220.0,
        "Falcon": 285.0,
        "Hummingbird": 396.0,
        "Dolphin": 528.0,
        "Deer": 639.0,
        "Owl": 741.0,
        "Panda": 852.0,
        "CargoShip": 936.0,
        "Clownfish": 963.0,
    }

    def __init__(self):
        self.nodes: List[AurisNode] = [
            TigerNode(),
            FalconNode(),
            HummingbirdNode(),
            DolphinNode(),
            DeerNode(),
            OwlNode(),
            PandaNode(),
            CargoShipNode(),
            ClownfishNode(),
        ]
        for node in self.nodes:
            node.freq = self.CANONICAL_AURIS_HZ[node.name]

    def _calculate_coherence(self, signals: List[NodeSignal]) -> Tuple[float, str]:
        """
        Calculate coherence Γ from node signals.
        Same formula as Aureon: weighted agreement score.

        Γ = Σ(agreement_i × weight_i × confidence_i) / Σ(weight_i)
        """
        if not signals:
            return 0.0, "No signals"

        # Find the majority vote
        votes: Dict[str, float] = {}
        for signal, node in zip(signals, self.nodes):
            cat = signal.category_vote
            weight = node.weight * signal.confidence
            votes[cat] = votes.get(cat, 0) + weight

        consensus = max(votes, key=votes.get)

        # Calculate coherence: how much of the total weight agrees with consensus?
        total_weight = sum(node.weight * sig.confidence for sig, node in zip(signals, self.nodes))
        consensus_weight = sum(
            node.weight * sig.confidence
            for sig, node in zip(signals, self.nodes)
            if sig.category_vote == consensus
        )

        gamma = consensus_weight / total_weight if total_weight > 0 else 0
        return gamma, consensus

    def classify(self, description: str, amount: float, **context) -> CoherenceResult:
        """
        Run all 9 nodes on a transaction.
        Returns coherence result with classification.
        """
        signals = []
        for node in self.nodes:
            signal = node.analyse(description, amount, **context)
            signals.append(signal)

        gamma, consensus = self._calculate_coherence(signals)

        # Determine action based on coherence
        if gamma >= COHERENCE_ENTRY:
            action = ClassificationAction.AUTO_CLASSIFY
        elif gamma >= COHERENCE_REVIEW:
            action = ClassificationAction.CLASSIFY_REVIEW
        else:
            action = ClassificationAction.HUMAN_REQUIRED

        # Find dissenters
        dissenters = [
            f"{sig.node_name} (voted '{sig.category_vote}')"
            for sig in signals
            if sig.category_vote != consensus
        ]

        reasoning = (
            f"9 nodes analysed '{description}' (£{amount:,.2f}). "
            f"Coherence Γ = {gamma:.3f}. "
            f"Consensus: '{consensus}' ({len(signals) - len(dissenters)}/9 agree). "
            f"Action: {action.value}."
        )

        return CoherenceResult(
            transaction_description=description,
            transaction_amount=amount,
            node_signals=signals,
            coherence_score=round(gamma, 4),
            consensus_category=consensus,
            action=action,
            confidence=round(gamma, 3),
            dissenting_nodes=dissenters,
            reasoning=reasoning,
        )


# ═══════════════════════════════════════════════════════════════════
# DEMO / TEST
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("HNC AURIS NODES — 9-NODE COHERENCE CLASSIFICATION")
    print("Adapted from Aureon Auris Trader (417 lines)")
    print("=" * 70)

    engine = HNCAurisEngine()

    test_transactions = [
        ("TRAVIS PERKINS BELFAST", 847.50),
        ("BP FUEL STATION M1", 65.00),
        ("CLOSE BROTHERS VEHICLE FINANCE", 450.00),
        ("NETFLIX SUBSCRIPTION", 15.99),
        ("CITB TRAINING RENEWAL", 350.00),
        ("UNKNOWN TRANSFER REF 99182", 2500.00),
        ("EE MOBILE MONTHLY", 45.00),
        ("JAMES LOGAN GROUNDWORKS", 4500.00),
    ]

    for desc, amount in test_transactions:
        result = engine.classify(desc, amount)
        action_symbol = {
            ClassificationAction.AUTO_CLASSIFY: "AUTO",
            ClassificationAction.CLASSIFY_REVIEW: "REVIEW",
            ClassificationAction.HUMAN_REQUIRED: "HUMAN",
        }.get(result.action, "?")

        print(f"\n  [{action_symbol:6s}] Γ={result.coherence_score:.3f}  "
              f"'{desc}' £{amount:,.2f} → {result.consensus_category}")
        if result.dissenting_nodes:
            print(f"           Dissenters: {', '.join(result.dissenting_nodes)}")
