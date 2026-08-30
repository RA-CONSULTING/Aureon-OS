"""Tests for the leaderless bee-ball swarm defense.

On a detected breach the swarm fans out N independent defenders and confirms neutralization only on a
majority quorum. These tests confirm it flags a real threat, ignores a benign report, survives a
minority of compromised or silent defenders but is overwhelmed only by a majority, and has no single
authority (or leader) that can force or veto the outcome. No real subject, ever.
"""

from __future__ import annotations

import json

from aureon.bio import swarm_defense as sd

_FORBIDDEN = ("health", "aura", "emotion", "spirit", "diagnos", "disease", "personality")

_REAL = sd.ThreatReport(threat_id="t-real", kind="mutated_invariant",
                        description="a pinned invariant drifted", severity=2)
_BENIGN = sd.ThreatReport(threat_id="t-benign", kind="unknown", description="no drift", severity=0)


def test_real_threat_confirmed_all_honest():
    r = sd.mount_defense(_REAL)
    assert r.confirmed
    assert r.leaderless
    assert r.n_threat == r.n_defenders
    assert r.confidence >= 0.9
    assert r.quorum == r.n_defenders // 2 + 1
    assert r.tolerated_faults == r.quorum - 1


def test_benign_report_not_confirmed():
    r = sd.mount_defense(_BENIGN)
    assert not r.confirmed
    assert r.n_threat == 0


def test_survives_minority_of_compromised_defenders():
    r0 = sd.mount_defense(_REAL)
    tol = r0.tolerated_faults
    r = sd.mount_defense(_REAL, faulty_idx=tuple(range(tol)))  # a minority vote the wrong way
    assert r.confirmed
    assert r.n_threat == r.n_defenders - tol


def test_overwhelmed_only_by_a_majority():
    r0 = sd.mount_defense(_REAL)
    r = sd.mount_defense(_REAL, faulty_idx=tuple(range(r0.quorum)))  # a majority compromised
    assert not r.confirmed


def test_survives_minority_silent_but_fails_safe_when_too_many_silent():
    r0 = sd.mount_defense(_REAL)
    tol = r0.tolerated_faults
    survived = sd.mount_defense(_REAL, silent_idx=tuple(range(tol)))
    assert survived.confirmed
    assert survived.n_abstain == tol
    starved = sd.mount_defense(_REAL, silent_idx=tuple(range(r0.quorum)))
    assert not starved.confirmed  # silence counts against confirmation — fail-safe


def test_no_single_defender_flips_a_quorum_outcome():
    # With all honest, dropping any one defender to faulty still leaves a quorum → still confirmed.
    r = sd.mount_defense(_REAL, faulty_idx=(0,))
    assert r.confirmed
    # No single defender is an authority: its vote alone never decides while others hold quorum.


def test_module_is_leaderless_no_authority_surface():
    names = [n.lower() for n in dir(sd)]
    for banned in ("authority", "leader", "queen", "commander", "boss", "dictator"):
        assert not any(banned in n for n in names), f"unexpected {banned!r} surface"


def test_defend_from_guard_report_wires_intact_and_breach():
    class _Intact:
        intact = True
        findings: list = []
        n_findings = 0

    class _Breach:
        intact = False
        findings = [object(), object()]
        n_findings = 2

    assert sd.defend_from_guard_report(_Intact()) is None
    r = sd.defend_from_guard_report(_Breach())
    assert r is not None and r.confirmed and r.kind == "mutated_invariant"


def test_on_breach_handler_shape():
    assert sd.on_breach({"intact": True, "n_findings": 0}) is None
    r = sd.on_breach({"intact": False, "n_findings": 3})
    assert r is not None and r.confirmed


def test_compute_is_deterministic():
    assert sd.mount_defense(_REAL).to_dict() == sd.mount_defense(_REAL).to_dict()


def test_write_report_writes_md_and_json(tmp_path):
    result = sd.mount_defense(_REAL)
    out_md = tmp_path / "defense.md"
    out_json = tmp_path / "defense.json"
    rendered = sd.write_defense_report(result, out_md, out_json)

    assert out_md.exists() and out_md.stat().st_size > 0
    assert out_json.exists() and out_json.stat().st_size > 0
    assert rendered.out_path == str(out_md)

    md = out_md.read_text(encoding="utf-8")
    assert sd.SWARM_DEFENSE_BOUNDARY in md
    row_lines = [ln for ln in md.splitlines() if ln.startswith("| ") and "---" not in ln]
    assert len(row_lines) == result.n_defenders + 1  # + header row

    loaded = json.loads(out_json.read_text(encoding="utf-8"))
    assert loaded["confirmed"] == result.confirmed
    assert loaded["boundary"] == sd.SWARM_DEFENSE_BOUNDARY


def test_write_report_is_byte_identical_on_rewrite(tmp_path):
    result = sd.mount_defense(_REAL)
    a_md, a_json = tmp_path / "a.md", tmp_path / "a.json"
    b_md, b_json = tmp_path / "b.md", tmp_path / "b.json"
    sd.write_defense_report(result, a_md, a_json)
    sd.write_defense_report(result, b_md, b_json)
    assert a_md.read_bytes() == b_md.read_bytes()
    assert a_json.read_bytes() == b_json.read_bytes()


def test_boundary_present_and_no_subject_claims():
    low = sd.SWARM_DEFENSE_BOUNDARY.lower()
    for w in _FORBIDDEN:
        assert w not in low, f"boundary leaked {w!r}"


def test_module_has_no_person_reading_surface():
    names = [n.lower() for n in dir(sd)]
    for banned in ("face", "speaker", "voice", "pose", "emotion", "identity", "biometric"):
        assert not any(banned in n for n in names), f"unexpected {banned!r} surface"


def test_emit_publishes_to_bus():
    published = []

    class _Bus:
        def publish(self, thought):
            published.append(thought)

    result = sd.mount_defense(_REAL)
    payload = sd.emit_defense(result, bus=_Bus(), trace=False)
    assert payload["confirmed"] == result.confirmed
    assert len(published) == 1
    assert published[0].topic == sd.DEFENSE_RUN_TOPIC
    assert published[0].payload["leaderless"] is True
    assert published[0].payload["boundary"] == sd.SWARM_DEFENSE_BOUNDARY


def test_emit_tolerates_throwing_bus():
    class _BadBus:
        def publish(self, thought):
            raise RuntimeError("bus down")

    result = sd.mount_defense(_REAL)
    payload = sd.emit_defense(result, bus=_BadBus(), trace=False)  # must not raise
    assert payload["confirmed"] == result.confirmed
