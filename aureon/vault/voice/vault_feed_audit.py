"""
VaultFeedAudit — is the vault receiving from every subsystem?
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

HNC log 17/04/2026: *"ensure the entire vault is feeding itself via the
HNC Harmonic bridge and the thought bus."*

The Plan agent surfaced the concrete gap: AureonVault.DEFAULT_SUBSCRIPTIONS
at stage 6 start was a **13-topic list** that did not include the entire
persona chain. `persona.collapse`, `goal.*`, `queen.conscience.verdict`,
`symbolic.life.pulse`, `life.event`, `conversation.*` — none of it was
reaching the vault. Stage 6.2 widens that list and adds this audit so we
can spot the next gap the moment it opens.

Wiring:

    BusFlightCheck.topology()           (what is publishing)
              │
              ▼
    VaultFeedAudit                      (compares to what landed on the vault)
              │
              ▼
    coverage_report()                   per-topic {publications, vault_cards,
                                         covered, severity}
    subscription_patch()                diff against DEFAULT_SUBSCRIPTIONS —
                                         the exact topics the vault needs to
                                         subscribe to but doesn't
    apply_patch()                       widen the vault's subscription list
                                         and, if ``rewire=True``, re-wire
                                         the bus so live publications flow

Gary Leckey · Aureon Institute — April 2026
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("aureon.vault.voice.vault_feed_audit")

VAULT_FEED_AUDIT_RELEASE_HOLD = (
    "vault_feed_audit_hold:production_magic_star_release_unavailable"
)


# ─────────────────────────────────────────────────────────────────────────────
# Audit
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class _TopicCoverage:
    topic: str
    publications: int = 0
    vault_cards: int = 0
    covered: bool = False
    severity: str = "low"   # low | medium | high


class VaultFeedAudit:
    """Compare bus traffic against vault ingest per source_topic."""

    def __init__(
        self,
        vault: Any,
        flight_check: Any,
        *,
        severity_high_threshold: int = 5,
        severity_medium_threshold: int = 1,
    ):
        self.vault = vault
        self.flight_check = flight_check
        self.severity_high_threshold = int(severity_high_threshold)
        self.severity_medium_threshold = int(severity_medium_threshold)
        self._lock = threading.RLock()
        self._last_report: Dict[str, Any] = {}

    # ─── coverage ────────────────────────────────────────────────────────

    def coverage_report(self) -> Dict[str, Any]:
        """Full coverage report. Topics with publications but zero vault
        cards are classified by severity (high if publications >= 5,
        medium if >= 1, low otherwise)."""
        topology = {}
        try:
            topology = self.flight_check.topology()
        except Exception as e:
            logger.debug("VaultFeedAudit: flight_check.topology failed: %s", e)
            topology = {"topics": []}

        # Build vault source_topic → count map once.
        vault_counts = self._vault_counts_by_topic()

        rows: List[_TopicCoverage] = []
        for record in topology.get("topics", []):
            topic = record.get("topic", "")
            pubs = int(record.get("publications", 0) or 0)
            vcards = vault_counts.get(topic, 0)
            covered = vcards > 0
            severity = self._classify_severity(pubs, vcards)
            rows.append(_TopicCoverage(
                topic=topic, publications=pubs, vault_cards=vcards,
                covered=covered, severity=severity,
            ))

        rows.sort(key=lambda r: (-r.publications, r.topic))

        total_topics = len(rows)
        covered_count = sum(1 for r in rows if r.covered)
        high_severity = [r.topic for r in rows if r.severity == "high"]
        medium_severity = [r.topic for r in rows if r.severity == "medium"]

        coverage_pct = (covered_count / total_topics) if total_topics else 1.0

        report = {
            "ts": time.time(),
            "total_topics": total_topics,
            "covered_count": covered_count,
            "coverage_pct": round(coverage_pct, 4),
            "high_severity_dead_branches": high_severity,
            "medium_severity_dead_branches": medium_severity,
            "topics": [
                {
                    "topic": r.topic,
                    "publications": r.publications,
                    "vault_cards": r.vault_cards,
                    "covered": r.covered,
                    "severity": r.severity,
                }
                for r in rows
            ],
        }
        with self._lock:
            self._last_report = report
        return report

    def _classify_severity(self, pubs: int, vcards: int) -> str:
        if vcards > 0:
            return "low"        # covered
        if pubs >= self.severity_high_threshold:
            return "high"       # lots of traffic, none stored
        if pubs >= self.severity_medium_threshold:
            return "medium"
        return "low"

    def _vault_counts_by_topic(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        contents = getattr(self.vault, "_contents", None)
        if not contents:
            return counts
        for card in contents.values():
            topic = getattr(card, "source_topic", "") or ""
            if not topic:
                continue
            counts[topic] = counts.get(topic, 0) + 1
        return counts

    # ─── subscription patch ──────────────────────────────────────────────

    def subscription_patch(self) -> Dict[str, Any]:
        """Return the diff: topics that are being published, aren't in
        DEFAULT_SUBSCRIPTIONS, and aren't covered by any existing
        subscription pattern (prefix-`*` included).

        The patch is a list of new topic strings the vault should
        subscribe to. Shape suitable for feeding directly into
        apply_patch()."""
        current_patterns = set(self._current_subscription_patterns())
        topology = {}
        try:
            topology = self.flight_check.topology()
        except Exception as e:
            logger.debug("VaultFeedAudit: flight_check.topology failed: %s", e)
            topology = {"topics": []}

        missing: List[str] = []
        already_matched: List[str] = []
        for record in topology.get("topics", []):
            topic = record.get("topic", "")
            pubs = int(record.get("publications", 0) or 0)
            if pubs == 0:
                continue
            if self._topic_matched_by_any(topic, current_patterns):
                already_matched.append(topic)
                continue
            missing.append(topic)

        return {
            "ts": time.time(),
            "current_subscriptions": sorted(current_patterns),
            "missing_topics": sorted(set(missing)),
            "already_covered_topics": sorted(set(already_matched)),
            "total_missing": len(set(missing)),
        }

    def _current_subscription_patterns(self) -> List[str]:
        patterns = getattr(self.vault, "DEFAULT_SUBSCRIPTIONS", None) or []
        return list(patterns)

    @staticmethod
    def _topic_matched_by_any(topic: str, patterns) -> bool:
        """Mirror ThoughtBus's matching semantics."""
        for p in patterns:
            if p == "*":
                return True
            if p.endswith(".*") and topic.startswith(p[:-1]):
                return True
            if p == topic:
                return True
        return False

    def apply_patch(self, *, rewire: bool = False) -> Dict[str, Any]:
        """Widen the vault's DEFAULT_SUBSCRIPTIONS with the missing
        topics. If ``rewire=True`` and the vault has a thought bus
        attached, also subscribe the vault's handler to the new topics
        live."""
        raise RuntimeError(VAULT_FEED_AUDIT_RELEASE_HOLD)
        patch = self.subscription_patch()
        new_topics = patch.get("missing_topics", [])
        if not new_topics:
            return {"ok": True, "added": [], "rewired": [], "patch": patch}

        existing = list(getattr(self.vault, "DEFAULT_SUBSCRIPTIONS", []) or [])
        added: List[str] = []
        for t in new_topics:
            if t not in existing:
                existing.append(t)
                added.append(t)

        # Write back. DEFAULT_SUBSCRIPTIONS is class-level; we mutate
        # the instance's copy to avoid polluting other vault instances.
        self.vault.DEFAULT_SUBSCRIPTIONS = existing

        rewired: List[str] = []
        if rewire:
            bus = getattr(self.vault, "_thought_bus", None)
            handler = getattr(self.vault, "_on_thought", None)
            if bus is not None and callable(handler):
                for t in added:
                    try:
                        bus.subscribe(t, handler)
                        rewired.append(t)
                    except Exception as e:
                        logger.debug("VaultFeedAudit: rewire %s failed: %s", t, e)

        return {"ok": True, "added": added, "rewired": rewired, "patch": patch}

    # ─── introspection ───────────────────────────────────────────────────

    def last_report(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._last_report)


__all__ = ["VAULT_FEED_AUDIT_RELEASE_HOLD", "VaultFeedAudit"]
