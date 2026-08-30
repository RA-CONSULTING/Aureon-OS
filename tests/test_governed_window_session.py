from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from aureon.autonomous.aureon_governed_desktop_gateway import WindowInfo
from aureon.operator.governed_window_session import (
    GatewayWindowBinding,
    GovernedWindowSession,
    SignedWindowSessionPolicy,
    WindowCandidate,
    WindowSessionError,
    WindowSessionPolicy,
    sign_window_session_policy,
    verify_window_session_policy,
)

SECRET = b"window-session-test-secret-is-at-least-32-bytes"
ORIGIN = "sealed-course-suite"


class FakeClock:
    def __init__(self) -> None:
        self.current = datetime(2026, 8, 16, 12, 0, tzinfo=UTC)

    def now(self) -> datetime:
        return self.current

    def advance(self, seconds: float) -> None:
        self.current += timedelta(seconds=seconds)


class FakeWindowEnumerator:
    def __init__(self, windows: list[WindowCandidate]) -> None:
        self.windows = windows
        self.calls = 0

    def enumerate_windows(self) -> list[WindowCandidate]:
        self.calls += 1
        return list(self.windows)


class FakeProcessInspector:
    def __init__(self, parents: dict[int, int | None]) -> None:
        self.parents = dict(parents)
        self.calls: list[tuple[int, int]] = []
        self.fail = False

    def is_same_process_or_descendant(
        self,
        process_id: int,
        *,
        ancestor_process_id: int,
    ) -> bool:
        self.calls.append((process_id, ancestor_process_id))
        if self.fail:
            raise RuntimeError("injected inspector failure")
        seen: set[int] = set()
        current: int | None = process_id
        while current is not None and current not in seen:
            if current == ancestor_process_id:
                return True
            seen.add(current)
            current = self.parents.get(current)
        return False


class FakeExactWindowGateway:
    def __init__(self) -> None:
        self.active: GatewayWindowBinding | None = None
        self.replace_calls: list[tuple[str | None, WindowInfo]] = []
        self.release_calls: list[str] = []
        self.counter = 0
        self.return_wrong_window = False

    def replace_target_window_binding(
        self,
        *,
        previous_binding_id: str | None,
        window: WindowInfo,
    ) -> GatewayWindowBinding:
        active_id = self.active.binding_id if self.active is not None else None
        if previous_binding_id != active_id:
            raise RuntimeError("atomic replacement compare-and-swap failed")
        self.replace_calls.append((previous_binding_id, window))
        self.counter += 1
        receipt_window = replace(window, left=window.left + 1) if self.return_wrong_window else window
        self.active = GatewayWindowBinding(f"binding-{self.counter}", receipt_window)
        return self.active

    def release_target_window_binding(self, binding_id: str) -> None:
        self.release_calls.append(binding_id)
        if self.active is not None and self.active.binding_id == binding_id:
            self.active = None


def browser_window(
    *,
    handle: int = 10,
    title: str = "Course - Home",
    process_id: int = 100,
    left: int = 20,
) -> WindowInfo:
    return WindowInfo(
        handle=handle,
        title=title,
        process_id=process_id,
        left=left,
        top=30,
        width=900,
        height=700,
    )


def candidate(window: WindowInfo, origin: str = ORIGIN) -> WindowCandidate:
    return WindowCandidate(window=window, origin_label=origin)


def signed_policy(
    clock: FakeClock,
    initial: WindowInfo,
    *,
    max_handoffs: int = 4,
    ttl_seconds: float = 600,
    title_regex: str = r"Course(?: - .+)?",
) -> SignedWindowSessionPolicy:
    policy = WindowSessionPolicy(
        session_id="session-20260816-a",
        nonce="unique-window-policy-nonce",
        initial_window=initial,
        root_process_id=initial.process_id,
        allowed_title_regex=title_regex,
        origin_label=ORIGIN,
        issued_at=clock.now(),
        expires_at=clock.now() + timedelta(seconds=ttl_seconds),
        max_handoffs=max_handoffs,
    )
    return sign_window_session_policy(policy, SECRET)


def make_session(
    *,
    clock: FakeClock | None = None,
    initial: WindowInfo | None = None,
    windows: list[WindowCandidate] | None = None,
    parents: dict[int, int | None] | None = None,
    envelope: SignedWindowSessionPolicy | None = None,
) -> tuple[
    GovernedWindowSession,
    FakeExactWindowGateway,
    FakeWindowEnumerator,
    FakeProcessInspector,
    FakeClock,
]:
    fake_clock = clock or FakeClock()
    initial_window = initial or browser_window()
    enumerator = FakeWindowEnumerator(windows or [candidate(initial_window)])
    inspector = FakeProcessInspector(parents or {initial_window.process_id: None})
    gateway = FakeExactWindowGateway()
    session = GovernedWindowSession(
        gateway=gateway,
        window_enumerator=enumerator,
        process_inspector=inspector,
        signed_policy=envelope or signed_policy(fake_clock, initial_window),
        signing_secret=SECRET,
        utc_now=fake_clock.now,
    )
    return session, gateway, enumerator, inspector, fake_clock


def test_start_binds_full_signed_window_identity_and_authorizes_readback() -> None:
    initial = browser_window()
    session, gateway, _enumerator, inspector, _clock = make_session(initial=initial)

    binding = session.start()

    assert gateway.active is not None
    assert gateway.active.window == initial
    assert binding.window == initial
    assert binding.generation == 0
    assert binding.handoff_count == 0
    assert len(binding.policy_sha256) == 64
    assert len(binding.window_sha256) == 64
    assert session.authorize_active_binding() == binding
    assert inspector.calls == [(100, 100), (100, 100)]
    audit = binding.audit_dict()
    assert "Course - Home" not in str(audit)
    assert ORIGIN not in str(audit)


def test_same_handle_title_change_requires_then_permits_exact_handoff() -> None:
    initial = browser_window()
    session, gateway, enumerator, _inspector, _clock = make_session(initial=initial)
    first = session.start()
    changed = replace(initial, title="Course - Lesson 2")
    enumerator.windows = [candidate(changed)]

    with pytest.raises(WindowSessionError, match="active_window_identity_changed_handoff_required"):
        session.authorize_active_binding()

    second = session.handoff(
        expected_active_binding_id=first.binding_id,
        expected_active_window_sha256=first.window_sha256,
        target_handle=initial.handle,
    )

    assert second.window == changed
    assert second.generation == 1
    assert second.handoff_count == 1
    assert gateway.active is not None
    assert gateway.active.binding_id == second.binding_id
    assert len(gateway.replace_calls) == 2


def test_child_process_popup_is_allowed_but_unrelated_pid_is_rejected() -> None:
    initial = browser_window()
    session, gateway, enumerator, _inspector, _clock = make_session(
        initial=initial,
        parents={100: None, 120: 100, 999: None},
    )
    first = session.start()
    popup = browser_window(handle=20, title="Course - Quiz Popup", process_id=120)
    enumerator.windows = [candidate(initial), candidate(popup)]

    second = session.handoff(
        expected_active_binding_id=first.binding_id,
        expected_active_window_sha256=first.window_sha256,
        target_handle=popup.handle,
    )
    assert second.window == popup

    unrelated = browser_window(handle=30, title="Course - Lookalike", process_id=999)
    enumerator.windows = [candidate(popup), candidate(unrelated)]
    with pytest.raises(WindowSessionError, match="window_process_lineage_not_allowed"):
        session.handoff(
            expected_active_binding_id=second.binding_id,
            expected_active_window_sha256=second.window_sha256,
            target_handle=unrelated.handle,
        )
    assert gateway.active is not None
    assert gateway.active.binding_id == second.binding_id


@pytest.mark.parametrize(
    ("changed", "error"),
    [
        (WindowCandidate(browser_window(title="Bank Login"), ORIGIN), "window_title_not_allowed"),
        (
            WindowCandidate(browser_window(title="Course - Lesson"), "different-origin"),
            "window_origin_label_not_allowed",
        ),
    ],
)
def test_title_and_origin_policy_mismatch_fail_closed(
    changed: WindowCandidate,
    error: str,
) -> None:
    initial = browser_window()
    session, gateway, enumerator, _inspector, _clock = make_session(initial=initial)
    first = session.start()
    enumerator.windows = [changed]

    with pytest.raises(WindowSessionError, match=error):
        session.handoff(
            expected_active_binding_id=first.binding_id,
            expected_active_window_sha256=first.window_sha256,
            target_handle=changed.window.handle,
        )
    assert gateway.active is not None
    assert gateway.active.binding_id == first.binding_id


def test_implicit_handoff_rejects_multiple_eligible_candidates() -> None:
    initial = browser_window()
    session, gateway, enumerator, _inspector, _clock = make_session(
        initial=initial,
        parents={100: None, 101: 100, 102: 100},
    )
    first = session.start()
    enumerator.windows = [
        candidate(initial),
        candidate(browser_window(handle=21, title="Course - Popup A", process_id=101)),
        candidate(browser_window(handle=22, title="Course - Popup B", process_id=102)),
    ]

    with pytest.raises(WindowSessionError, match="target_window_ambiguous"):
        session.handoff(
            expected_active_binding_id=first.binding_id,
            expected_active_window_sha256=first.window_sha256,
        )
    assert gateway.active is not None
    assert gateway.active.binding_id == first.binding_id


def test_expiry_releases_active_binding_and_closes_session() -> None:
    clock = FakeClock()
    initial = browser_window()
    envelope = signed_policy(clock, initial, ttl_seconds=10)
    session, gateway, _enumerator, _inspector, _clock = make_session(
        clock=clock,
        initial=initial,
        envelope=envelope,
    )
    binding = session.start()
    clock.advance(10)

    with pytest.raises(WindowSessionError, match="policy_expired"):
        session.authorize_active_binding()

    assert session.closed is True
    assert session.active_binding is None
    assert gateway.active is None
    assert gateway.release_calls == [binding.binding_id]


def test_policy_hash_signature_and_initial_ambiguity_fail_before_binding() -> None:
    clock = FakeClock()
    initial = browser_window()
    envelope = signed_policy(clock, initial)
    tampered = replace(envelope, policy_sha256="0" * 64)

    with pytest.raises(WindowSessionError, match="policy_hash_mismatch"):
        verify_window_session_policy(tampered, SECRET, now=clock.now())
    bad_signature = replace(envelope, signature_sha256="f" * 64)
    with pytest.raises(WindowSessionError, match="policy_signature_invalid"):
        verify_window_session_policy(bad_signature, SECRET, now=clock.now())

    duplicate_session, gateway, _enumerator, _inspector, _clock = make_session(
        clock=clock,
        initial=initial,
        windows=[candidate(initial), candidate(initial)],
        envelope=envelope,
    )
    with pytest.raises(WindowSessionError, match="initial_window_ambiguous"):
        duplicate_session.start()
    assert gateway.active is None


def test_handoff_compare_and_swap_and_limit_are_enforced() -> None:
    clock = FakeClock()
    initial = browser_window()
    envelope = signed_policy(clock, initial, max_handoffs=1)
    session, gateway, enumerator, _inspector, _clock = make_session(
        clock=clock,
        initial=initial,
        envelope=envelope,
    )
    first = session.start()
    lesson = replace(initial, title="Course - Lesson 1")
    enumerator.windows = [candidate(lesson)]

    with pytest.raises(WindowSessionError, match="active_binding_compare_and_swap_failed"):
        session.handoff(
            expected_active_binding_id="stale-binding",
            expected_active_window_sha256=first.window_sha256,
            target_handle=initial.handle,
        )
    second = session.handoff(
        expected_active_binding_id=first.binding_id,
        expected_active_window_sha256=first.window_sha256,
        target_handle=initial.handle,
    )

    enumerator.windows = [candidate(replace(lesson, title="Course - Lesson 2"))]
    with pytest.raises(WindowSessionError, match="maximum_window_handoffs_reached"):
        session.handoff(
            expected_active_binding_id=second.binding_id,
            expected_active_window_sha256=second.window_sha256,
            target_handle=initial.handle,
        )
    assert gateway.active is not None
    assert gateway.active.binding_id == second.binding_id


def test_inspector_failure_and_bad_gateway_receipt_poison_fail_closed() -> None:
    initial = browser_window()
    session, gateway, enumerator, inspector, _clock = make_session(initial=initial)
    first = session.start()
    changed = replace(initial, title="Course - Lesson 3")
    enumerator.windows = [candidate(changed)]
    inspector.fail = True
    with pytest.raises(WindowSessionError, match="process_lineage_inspection_failed"):
        session.handoff(
            expected_active_binding_id=first.binding_id,
            expected_active_window_sha256=first.window_sha256,
            target_handle=initial.handle,
        )
    assert gateway.active is not None
    inspector.fail = False
    gateway.return_wrong_window = True

    with pytest.raises(WindowSessionError, match="gateway_window_binding_identity_mismatch"):
        session.handoff(
            expected_active_binding_id=first.binding_id,
            expected_active_window_sha256=first.window_sha256,
            target_handle=initial.handle,
        )
    assert session.closed is True
    assert session.active_binding is None
    assert gateway.active is None


def test_close_is_idempotent_and_unknown_handle_never_rebinds() -> None:
    initial = browser_window()
    session, gateway, _enumerator, _inspector, _clock = make_session(initial=initial)
    first = session.start()

    with pytest.raises(WindowSessionError, match="target_window_handle_not_found"):
        session.handoff(
            expected_active_binding_id=first.binding_id,
            expected_active_window_sha256=first.window_sha256,
            target_handle=987_654,
        )
    assert len(gateway.replace_calls) == 1

    session.close()
    session.close()
    assert gateway.active is None
    assert gateway.release_calls == [first.binding_id]
    with pytest.raises(WindowSessionError, match="window_session_closed"):
        session.authorize_active_binding()
