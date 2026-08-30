from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

import aureon.operator.synthetic_assessment_grant as grant_module
from aureon.operator.synthetic_assessment_grant import (
    LOOPBACK_HOST,
    SCHEMA_VERSION,
    SYNTHETIC_MODE,
    SYNTHETIC_PERSONA_ID,
    AssessmentActionContext,
    AssessmentSessionContext,
    GrantContextError,
    GrantFormatError,
    GrantReplayError,
    GrantSignatureError,
    SyntheticAssessmentGrant,
    SyntheticAssessmentReplayGuard,
    activate_synthetic_assessment_grant,
    build_asset_manifest,
    canonical_asset_root,
)

SECRET = b"runtime-only-synthetic-grant-key-material-v1"
OTHER_SECRET = b"different-runtime-key-material-for-negative-test"
ISSUED = datetime(2026, 8, 16, 12, 0, 0, tzinfo=UTC)
EXPIRES = ISSUED + timedelta(hours=2)
SERVER_PID = 41_001
BROWSER_PID = 41_002
PORT = 38_417
RUN_ID = "run-local-synthetic-suite-0001"
NONCE = "nonce-0123456789abcdef0123456789abcdef"
BINDING_ID = "window-binding-local-synthetic-0001"


def _suite(tmp_path: Path) -> Path:
    root = tmp_path / "synthetic-suite"
    (root / "assets").mkdir(parents=True)
    (root / "index.html").write_text("<h1>Local synthetic suite</h1>\n", encoding="utf-8")
    (root / "assets" / "app.js").write_text("window.synthetic = true;\n", encoding="utf-8")
    (root / "assets" / "empty.bin").write_bytes(b"")
    return root


def _grant(root: Path, **overrides: object) -> SyntheticAssessmentGrant:
    values: dict[str, object] = {
        "secret": SECRET,
        "asset_root": root,
        "run_id": RUN_ID,
        "nonce": NONCE,
        "loopback_port": PORT,
        "server_pid": SERVER_PID,
        "browser_pid": BROWSER_PID,
        "expected_window_binding_id": BINDING_ID,
        "issued_at": ISSUED,
        "expires_at": EXPIRES,
        "allowed_actions": ("type_text", "left_click"),
        "max_actions": 4,
    }
    values.update(overrides)
    return SyntheticAssessmentGrant.issue(**values)  # type: ignore[arg-type]


def _session_context(root: Path, **overrides: object) -> AssessmentSessionContext:
    values: dict[str, object] = {
        "asset_root": root,
        "origin": f"http://{LOOPBACK_HOST}:{PORT}",
        "server_pid": SERVER_PID,
        "browser_pid": BROWSER_PID,
        "window_binding_id": BINDING_ID,
        "run_id": RUN_ID,
        "nonce": NONCE,
        "now": ISSUED + timedelta(minutes=1),
    }
    values.update(overrides)
    return AssessmentSessionContext(**values)  # type: ignore[arg-type]


def _action_context(
    root: Path,
    *,
    action: str,
    sequence: int,
    observation: bytes,
    **overrides: object,
) -> AssessmentActionContext:
    values = dict(_session_context(root).__dict__)
    values.update(
        {
            "action": action,
            "action_sequence": sequence,
            "observation_sha256": hashlib.sha256(observation).hexdigest(),
        }
    )
    values.update(overrides)
    return AssessmentActionContext(**values)  # type: ignore[arg-type]


def _canonical(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _resign(envelope: dict[str, object]) -> str:
    payload = envelope["grant"]
    envelope["hmac_sha256"] = hmac.new(
        SECRET,
        _canonical(payload).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return _canonical(envelope)


def test_issue_round_trip_is_canonical_exact_and_contains_no_runtime_secret(tmp_path: Path) -> None:
    root = _suite(tmp_path)
    grant = _grant(root)
    encoded = grant.to_json()
    decoded = json.loads(encoded)

    assert encoded == _canonical(decoded)
    assert decoded["grant"]["schema_version"] == SCHEMA_VERSION
    assert decoded["grant"]["persona_id"] == SYNTHETIC_PERSONA_ID
    assert decoded["grant"]["synthetic"] is True
    assert decoded["grant"]["mode"] == SYNTHETIC_MODE
    assert decoded["grant"]["origin"] == {
        "scheme": "http",
        "host": "127.0.0.1",
        "port": PORT,
    }
    assert SECRET.decode("ascii") not in encoded
    assert SECRET.decode("ascii") not in repr(grant)
    assert SyntheticAssessmentGrant.from_json(encoded).to_json() == encoded
    grant.verify_signature(SECRET)


def test_manifest_binds_every_file_with_sorted_paths_sizes_and_root_digest(tmp_path: Path) -> None:
    root = _suite(tmp_path)
    manifest = build_asset_manifest(root)

    assert [entry.path for entry in manifest.files] == [
        "assets/app.js",
        "assets/empty.bin",
        "index.html",
    ]
    assert [entry.size_bytes for entry in manifest.files] == [
        (root / "assets" / "app.js").stat().st_size,
        0,
        (root / "index.html").stat().st_size,
    ]
    assert all(entry.sha256 == entry.sha256.lower() for entry in manifest.files)
    assert len(manifest.root_sha256) == 64
    assert canonical_asset_root(root) == _grant(root).asset_root


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("schema_version", "wrong-schema", "schema_version"),
        ("persona_id", "john-brown", "persona_id"),
        ("synthetic", False, "synthetic"),
        ("mode", "production", "mode"),
    ],
)
def test_identity_and_synthetic_mode_are_exact_even_with_a_valid_hmac(
    tmp_path: Path,
    field: str,
    value: object,
    message: str,
) -> None:
    envelope = json.loads(_grant(_suite(tmp_path)).to_json())
    envelope["grant"][field] = value

    with pytest.raises(GrantFormatError, match=message):
        SyntheticAssessmentGrant.from_json(_resign(envelope))


def test_hmac_uses_constant_time_comparison_and_wrong_key_fails_before_replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _suite(tmp_path)
    grant = _grant(root)
    calls: list[tuple[str, str]] = []
    original = hmac.compare_digest

    def observed(left: str, right: str) -> bool:
        calls.append((left, right))
        return original(left, right)

    monkeypatch.setattr(grant_module.hmac, "compare_digest", observed)
    with pytest.raises(GrantSignatureError):
        activate_synthetic_assessment_grant(
            grant,
            secret=OTHER_SECRET,
            context=_session_context(root),
            replay_guard=SyntheticAssessmentReplayGuard(tmp_path / "replay"),
        )

    assert len(calls) == 1
    assert all(len(value) == 64 for value in calls[0])
    assert list((tmp_path / "replay").iterdir()) == []


def test_grant_lifetime_is_positive_at_most_24_hours_and_enforced(tmp_path: Path) -> None:
    root = _suite(tmp_path)
    with pytest.raises(GrantFormatError, match="24 hours"):
        _grant(root, expires_at=ISSUED + timedelta(hours=24, seconds=1))
    with pytest.raises(GrantFormatError, match="24 hours"):
        _grant(root, expires_at=ISSUED)

    grant = _grant(root)
    replay = SyntheticAssessmentReplayGuard(tmp_path / "replay")
    with pytest.raises(GrantContextError, match="not yet valid"):
        activate_synthetic_assessment_grant(
            grant,
            secret=SECRET,
            context=_session_context(root, now=ISSUED - timedelta(seconds=1)),
            replay_guard=replay,
        )
    with pytest.raises(GrantContextError, match="expired"):
        activate_synthetic_assessment_grant(
            grant,
            secret=SECRET,
            context=_session_context(root, now=EXPIRES),
            replay_guard=replay,
        )
    assert list(replay.directory.iterdir()) == []


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("origin", "http://localhost:38417", "origin"),
        ("origin", "http://127.0.0.1:38418", "origin"),
        ("server_pid", SERVER_PID + 1, "server_pid"),
        ("browser_pid", BROWSER_PID + 1, "browser_pid"),
        ("window_binding_id", "different-window-binding", "window binding"),
        ("run_id", "different-run", "run_id"),
        ("nonce", "different-nonce-0123456789abcdef", "nonce"),
    ],
)
def test_activation_rejects_every_mismatched_live_context_without_consuming_nonce(
    tmp_path: Path,
    field: str,
    value: object,
    message: str,
) -> None:
    root = _suite(tmp_path)
    grant = _grant(root)
    replay = SyntheticAssessmentReplayGuard(tmp_path / "replay")

    with pytest.raises(GrantContextError, match=message):
        activate_synthetic_assessment_grant(
            grant,
            secret=SECRET,
            context=_session_context(root, **{field: value}),
            replay_guard=replay,
        )
    assert list(replay.directory.iterdir()) == []


def test_exact_asset_root_and_complete_tree_are_rechecked(tmp_path: Path) -> None:
    root = _suite(tmp_path)
    grant = _grant(root)
    replay = SyntheticAssessmentReplayGuard(tmp_path / "replay")

    clone = tmp_path / "identical-suite-at-wrong-root"
    (clone / "assets").mkdir(parents=True)
    for entry in grant.asset_manifest.files:
        target = clone / Path(entry.path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((root / Path(entry.path)).read_bytes())
    with pytest.raises(GrantContextError, match="asset_root"):
        activate_synthetic_assessment_grant(
            grant,
            secret=SECRET,
            context=_session_context(clone),
            replay_guard=replay,
        )

    added = root / "unexpected.txt"
    added.write_text("undeclared", encoding="utf-8")
    with pytest.raises(GrantContextError, match="whole-suite"):
        activate_synthetic_assessment_grant(
            grant,
            secret=SECRET,
            context=_session_context(root),
            replay_guard=replay,
        )
    added.unlink()
    activate_synthetic_assessment_grant(
        grant,
        secret=SECRET,
        context=_session_context(root),
        replay_guard=replay,
    )


def test_activation_is_cross_instance_one_time_but_session_allows_many_actions(tmp_path: Path) -> None:
    root = _suite(tmp_path)
    grant = _grant(root, max_actions=3)
    replay_path = tmp_path / "replay"
    session = activate_synthetic_assessment_grant(
        grant,
        secret=SECRET,
        context=_session_context(root),
        replay_guard=SyntheticAssessmentReplayGuard(replay_path),
    )

    first = session.authorize_action(
        _action_context(root, action="type_text", sequence=1, observation=b"before answer")
    )
    second = session.authorize_action(
        _action_context(root, action="left_click", sequence=2, observation=b"before submit")
    )
    third = session.authorize_action(
        _action_context(root, action="left_click", sequence=3, observation=b"before confirm")
    )

    assert [first.action_sequence, second.action_sequence, third.action_sequence] == [1, 2, 3]
    assert len({first.receipt_sha256, second.receipt_sha256, third.receipt_sha256}) == 3
    assert session.next_action_sequence == 4
    with pytest.raises(GrantContextError, match="limit"):
        session.authorize_action(
            _action_context(root, action="left_click", sequence=4, observation=b"too many")
        )
    with pytest.raises(GrantReplayError, match="already been activated"):
        activate_synthetic_assessment_grant(
            SyntheticAssessmentGrant.from_json(grant.to_json()),
            secret=SECRET,
            context=_session_context(root),
            replay_guard=SyntheticAssessmentReplayGuard(replay_path),
        )

    marker_text = next(replay_path.iterdir()).read_text(encoding="utf-8")
    assert SECRET.decode("ascii") not in marker_text
    assert NONCE not in marker_text


def test_each_action_revalidates_context_scope_sequence_and_observation(tmp_path: Path) -> None:
    root = _suite(tmp_path)
    session = activate_synthetic_assessment_grant(
        _grant(root),
        secret=SECRET,
        context=_session_context(root),
        replay_guard=SyntheticAssessmentReplayGuard(tmp_path / "replay"),
    )

    with pytest.raises(GrantContextError, match="allowed scope"):
        session.authorize_action(_action_context(root, action="press_key", sequence=1, observation=b"before"))
    with pytest.raises(GrantContextError, match="next unused"):
        session.authorize_action(_action_context(root, action="type_text", sequence=2, observation=b"before"))
    with pytest.raises(GrantContextError, match="observation_sha256"):
        session.authorize_action(
            _action_context(
                root,
                action="type_text",
                sequence=1,
                observation=b"before",
                observation_sha256="A" * 64,
            )
        )
    with pytest.raises(GrantContextError, match="window binding"):
        session.authorize_action(
            _action_context(
                root,
                action="type_text",
                sequence=1,
                observation=b"before",
                window_binding_id="changed-window-binding",
            )
        )

    changed = root / "index.html"
    original = changed.read_bytes()
    changed.write_bytes(original + b"changed")
    with pytest.raises(GrantContextError, match="whole-suite"):
        session.authorize_action(_action_context(root, action="type_text", sequence=1, observation=b"before"))
    changed.write_bytes(original)

    authorized = session.authorize_action(
        _action_context(root, action="type_text", sequence=1, observation=b"before")
    )
    with pytest.raises(GrantContextError, match="next unused"):
        session.authorize_action(_action_context(root, action="type_text", sequence=1, observation=b"before"))
    assert authorized.context_sha256 != authorized.receipt_sha256


def test_scope_and_runtime_key_are_fail_closed(tmp_path: Path) -> None:
    root = _suite(tmp_path)
    with pytest.raises(GrantFormatError, match="allowed_actions"):
        _grant(root, allowed_actions=("hotkey",))
    with pytest.raises(ValueError, match="at least 32 bytes"):
        _grant(root, secret=b"too-short")
    with pytest.raises(TypeError, match="runtime-only bytes"):
        _grant(root, secret="never-accept-text-secret")


def test_parser_rejects_extra_duplicate_and_noncanonical_manifest_fields(tmp_path: Path) -> None:
    envelope = json.loads(_grant(_suite(tmp_path)).to_json())
    envelope["grant"]["unexpected_authority"] = True
    with pytest.raises(GrantFormatError, match="keys mismatch"):
        SyntheticAssessmentGrant.from_json(_resign(envelope))

    duplicate = '{"grant":{},"grant":{},"hmac_sha256":"' + ("0" * 64) + '"}'
    with pytest.raises(GrantFormatError, match="duplicate JSON key"):
        SyntheticAssessmentGrant.from_json(duplicate)

    envelope = json.loads(_grant(_suite(tmp_path / "second")).to_json())
    envelope["grant"]["asset_manifest"]["files"][0]["sha256"] = "A" * 64
    with pytest.raises(GrantFormatError, match="lowercase SHA-256"):
        SyntheticAssessmentGrant.from_json(_resign(envelope))


def test_non_string_identity_fields_are_not_coerced(tmp_path: Path) -> None:
    envelope = json.loads(_grant(_suite(tmp_path)).to_json())
    envelope["grant"]["run_id"] = 12345

    with pytest.raises(GrantFormatError, match="run_id"):
        SyntheticAssessmentGrant.from_json(_resign(envelope))
