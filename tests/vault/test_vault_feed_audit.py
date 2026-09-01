"""Read-only audit tests and fail-closed patch tests."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from aureon.vault.voice.vault_feed_audit import (
    VAULT_FEED_AUDIT_RELEASE_HOLD,
    VaultFeedAudit,
)


class _Trap:
    def __getattribute__(self, _name: str) -> Any:
        raise AssertionError("release-held vault patch touched an effect owner")


class _FlightReadStub:
    def topology(self):
        return {
            "topics": [
                {"topic": "goal.completed", "publications": 6},
                {"topic": "persona.collapse", "publications": 1},
            ]
        }


class _VaultReadStub:
    DEFAULT_SUBSCRIPTIONS = ["persona.*"]
    _contents = {
        "c1": SimpleNamespace(source_topic="persona.collapse"),
    }


def test_read_only_coverage_and_subscription_diff_remain_available() -> None:
    audit = VaultFeedAudit(_VaultReadStub(), _FlightReadStub())
    report = audit.coverage_report()
    assert report["high_severity_dead_branches"] == ["goal.completed"]
    assert report["covered_count"] == 1
    patch = audit.subscription_patch()
    assert patch["missing_topics"] == ["goal.completed"]
    assert patch["already_covered_topics"] == ["persona.collapse"]
    assert audit.last_report()["total_topics"] == 2


@pytest.mark.parametrize("rewire", [False, True])
def test_apply_patch_holds_before_diff_mutation_or_subscription(rewire: bool) -> None:
    audit = VaultFeedAudit(_Trap(), _Trap())
    with pytest.raises(RuntimeError, match="vault_feed_audit_hold"):
        audit.apply_patch(rewire=rewire)
    assert audit.last_report() == {}
    assert VAULT_FEED_AUDIT_RELEASE_HOLD.endswith(
        "production_magic_star_release_unavailable"
    )
