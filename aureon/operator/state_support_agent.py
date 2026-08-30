"""Source-traceable eligibility and sequencing for business-support routes.

The agent evaluates declared facts against a dated rule snapshot. It does not
apply, submit, accept terms, or treat its result as an agency decision.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any, Callable, Iterable, Mapping


class RouteDecision(StrEnum):
    AVAILABLE_NOW = "AVAILABLE_NOW"
    PROVIDER_DECISION_REQUIRED = "PROVIDER_DECISION_REQUIRED"
    NEEDS_EVIDENCE = "NEEDS_EVIDENCE"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"
    CLOSED = "CLOSED"
    NOT_YET_OPEN = "NOT_YET_OPEN"


@dataclass(frozen=True)
class RuleResult:
    field: str
    label: str
    kind: str
    outcome: str
    declared_value: Any
    expected: Any
    evidence: str


@dataclass(frozen=True)
class RouteResult:
    route_id: str
    name: str
    decision: str
    readiness_score: float
    deadline: str | None
    source_url: str
    source_checked_at: str
    rule_results: tuple[RuleResult, ...]
    missing_evidence: tuple[str, ...]
    failed_eligibility: tuple[str, ...]
    next_actions: tuple[str, ...]
    alternative_path: str | None
    provider_is_final_authority: bool
    submission_allowed: bool = False

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["rule_results"] = [asdict(item) for item in self.rule_results]
        return value


def canonical_digest(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def parse_datetime(value: str) -> datetime:
    text = str(value).strip().replace("Z", "+00:00")
    return datetime.fromisoformat(text)


def lookup(profile: Mapping[str, Any], field: str) -> tuple[bool, Any]:
    current: Any = profile
    for part in field.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return False, None
        current = current[part]
    return True, current


def compare(operator: str, actual: Any, expected: Any) -> bool:
    if operator == "eq":
        return actual == expected
    if operator == "in":
        return actual in expected
    if operator == "not_in":
        return actual not in expected
    if operator == "lt":
        return float(actual) < float(expected)
    if operator == "lte":
        return float(actual) <= float(expected)
    if operator == "gte":
        return float(actual) >= float(expected)
    if operator == "between":
        return float(expected[0]) <= float(actual) <= float(expected[1])
    if operator == "truthy":
        return actual is True
    raise ValueError(f"Unsupported rule operator: {operator}")


class StateSupportEligibilityAgent:
    """Evaluate support routes without mutating any provider or company state."""

    def __init__(
        self,
        routes: Iterable[Mapping[str, Any]],
        *,
        grounder: Callable[[str, dict[str, Any]], Mapping[str, Any]] | None = None,
    ) -> None:
        self.routes = tuple(dict(route) for route in routes)
        self.grounder = grounder

    def _ground(self, profile_id: str) -> Mapping[str, Any] | None:
        if self.grounder is None:
            return None
        verdict = self.grounder(
            "evaluate_state_support_eligibility",
            {"profile_id": profile_id, "route_count": len(self.routes)},
        )
        if not bool(verdict.get("approved")):
            raise RuntimeError("Aureon grounding vetoed the read-only evaluation")
        return verdict

    def evaluate_route(
        self,
        profile: Mapping[str, Any],
        route: Mapping[str, Any],
        *,
        as_of: datetime,
    ) -> RouteResult:
        opens = route.get("opens")
        deadline = route.get("deadline")
        decision: RouteDecision | None = None
        if opens and as_of < parse_datetime(str(opens)):
            decision = RouteDecision.NOT_YET_OPEN
        if deadline and as_of > parse_datetime(str(deadline)):
            decision = RouteDecision.CLOSED

        results: list[RuleResult] = []
        failed_eligibility: list[str] = []
        missing_evidence: list[str] = []
        passed = 0
        for rule in route.get("rules", []):
            field = str(rule["field"])
            present, actual = lookup(profile, field)
            kind = str(rule.get("kind", "eligibility"))
            evidence = str(rule.get("evidence", field))
            if not present or actual is None:
                outcome = "MISSING"
                missing_evidence.append(evidence)
            else:
                matched = compare(str(rule["operator"]), actual, rule.get("expected"))
                outcome = "PASS" if matched else "FAIL"
                if matched:
                    passed += 1
                elif kind == "eligibility":
                    failed_eligibility.append(str(rule["label"]))
                else:
                    missing_evidence.append(evidence)
            results.append(
                RuleResult(
                    field=field,
                    label=str(rule["label"]),
                    kind=kind,
                    outcome=outcome,
                    declared_value=actual if present else None,
                    expected=rule.get("expected"),
                    evidence=evidence,
                )
            )

        if decision is None:
            if failed_eligibility:
                decision = RouteDecision.NOT_ELIGIBLE
            elif missing_evidence:
                decision = RouteDecision.NEEDS_EVIDENCE
            elif route.get("provider_decision_required", True):
                decision = RouteDecision.PROVIDER_DECISION_REQUIRED
            else:
                decision = RouteDecision.AVAILABLE_NOW

        total = len(results)
        readiness = round(passed / total, 3) if total else 1.0
        actions = list(route.get("next_actions", []))
        if decision == RouteDecision.NEEDS_EVIDENCE:
            actions.insert(0, "Resolve the listed evidence gaps before provider contact.")
        elif decision == RouteDecision.NOT_ELIGIBLE:
            actions.insert(0, "Do not submit through the direct-applicant route.")
        elif decision in {RouteDecision.CLOSED, RouteDecision.NOT_YET_OPEN}:
            actions.insert(0, "Preserve the route for monitoring; do not submit now.")
        elif decision == RouteDecision.PROVIDER_DECISION_REQUIRED:
            actions.insert(0, "Present the evidence to the provider for its decision.")

        return RouteResult(
            route_id=str(route["id"]),
            name=str(route["name"]),
            decision=decision.value,
            readiness_score=readiness,
            deadline=str(deadline) if deadline else None,
            source_url=str(route["source"]["url"]),
            source_checked_at=str(route["source"]["checked_at"]),
            rule_results=tuple(results),
            missing_evidence=tuple(dict.fromkeys(missing_evidence)),
            failed_eligibility=tuple(dict.fromkeys(failed_eligibility)),
            next_actions=tuple(actions),
            alternative_path=route.get("alternative_path"),
            provider_is_final_authority=True,
        )

    def evaluate_portfolio(
        self,
        profile: Mapping[str, Any],
        *,
        as_of: datetime,
        source_snapshot: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        profile_id = str(profile.get("profile_id") or "UNIDENTIFIED_PROFILE")
        grounding = self._ground(profile_id)
        results = [
            self.evaluate_route(profile, route, as_of=as_of)
            for route in self.routes
        ]
        priority = {
            RouteDecision.AVAILABLE_NOW.value: 0,
            RouteDecision.PROVIDER_DECISION_REQUIRED.value: 1,
            RouteDecision.NEEDS_EVIDENCE.value: 2,
            RouteDecision.NOT_YET_OPEN.value: 3,
            RouteDecision.NOT_ELIGIBLE.value: 4,
            RouteDecision.CLOSED.value: 5,
        }
        ordered = sorted(
            results,
            key=lambda item: (
                priority[item.decision],
                item.deadline or "9999-12-31T23:59:59+00:00",
                item.route_id,
            ),
        )
        receipt = {
            "schema_version": "aureon.state-support-evaluation.v1",
            "profile_id": profile_id,
            "evaluated_at": as_of.isoformat(),
            "profile_digest": canonical_digest(profile),
            "source_snapshot_digest": canonical_digest(source_snapshot or self.routes),
            "grounding": dict(grounding) if grounding is not None else None,
            "route_results": [item.to_dict() for item in ordered],
            "sequenced_route_ids": [item.route_id for item in ordered],
            "controls": {
                "provider_is_final_authority": True,
                "submission_authority": False,
                "human_approval_required_before_external_action": True,
                "rules_are_dated_guidance_not_legal_or_funding_advice": True,
            },
            "external_actions": {
                "emails_sent": 0,
                "forms_submitted": 0,
                "portal_mutations": 0,
                "applications_submitted": 0,
            },
        }
        receipt["receipt_digest"] = canonical_digest(receipt)
        return receipt


__all__ = [
    "RouteDecision",
    "RouteResult",
    "RuleResult",
    "StateSupportEligibilityAgent",
    "canonical_digest",
]
