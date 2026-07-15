#!/usr/bin/env python3
"""
Audit + benchmark the organism's unification edges.

Exercises each connective edge that Phase 19–20 revived and prints an honest
PASS/DEAD report. Exits non-zero if any CRITICAL edge is dead, so it can gate CI
or a deploy. Offline-safe — no network, no OS deps.

Usage:
    AUREON_LLM_OFFLINE=1 AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS=1 \
        python -m scripts.validation.audit_organism_unification
"""

from __future__ import annotations

import os
import sys
import time

os.environ.setdefault("AUREON_LLM_OFFLINE", "1")
os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")


def _check(name: str, ok: bool, detail: str, critical: bool = True) -> dict:
    return {"edge": name, "ok": bool(ok), "detail": detail, "critical": critical}


def run_audit() -> list[dict]:
    from aureon.core.aureon_thought_bus import Thought, get_thought_bus
    from aureon.core.hnc_field import read_canonical_field

    bus = get_thought_bus()
    results: list[dict] = []

    # Edge 1 — the canonical field: publish → read back through the shared accessor
    bus.publish(Thought(source="hnc_live_daemon", topic="symbolic.life.pulse",
                        payload={"symbolic_life_score": 0.42, "coherence_gamma": 0.5,
                                 "source": "audit"}))
    field = read_canonical_field(bus)
    results.append(_check("canonical_field", field.available and field.symbolic_life_score == 0.42,
                          f"sls={field.symbolic_life_score} source={field.source}"))

    # Edge 1b — flood-proof: bury the pulse under a baton flood, must still read
    for i in range(400):
        bus.publish(Thought(source=f"m{i}", topic="baton.link", payload={"module": f"m{i}"}))
    field2 = read_canonical_field(bus)
    results.append(_check("field_flood_proof", field2.available and field2.symbolic_life_score == 0.42,
                          f"sls under 400-msg flood={field2.symbolic_life_score}"))

    # Edge 2 — grounded gate senses the field (low SLS + risky → veto)
    bus.publish(Thought(source="hnc_live_daemon", topic="symbolic.life.pulse",
                        payload={"symbolic_life_score": 0.08, "source": "audit"}))
    from aureon.operator.grounded_action import GroundedActionGate

    v = GroundedActionGate(bus=bus, enable_llm=False).ground("delete_file", {"path": "x"})
    results.append(_check("gate_senses_field", v.verdict == "VETOED" and v.symbolic_life_score == 0.08,
                          f"verdict={v.verdict} sls={v.symbolic_life_score}"))

    # Edge 3 — mesh broadcast reaches receive_mycelium_message
    from aureon.core.aureon_mycelium import get_mycelium
    from aureon.operator.aureon_operator import broadcast_to_mesh

    seen: dict = {}

    class _Rcv:
        def receive_mycelium_message(self, mt, pl):
            seen["hit"] = (mt, pl)

    get_mycelium().connect_subsystem("audit_rcv", _Rcv())
    broadcast_to_mesh("audit.mesh", {"v": 1})
    results.append(_check("mesh_delivery", seen.get("hit") == ("audit.mesh", {"v": 1}),
                          f"delivered={seen.get('hit')}"))

    # Edge 4 — lighthouse → bus
    try:
        from aureon.analytics.aureon_lighthouse import (
            LighthouseEvent,
            LighthouseEventType,
            LighthousePatternDetector,
        )

        LighthousePatternDetector()._emit_event(LighthouseEvent(
            event_type=LighthouseEventType.COHERENCE_COLLAPSE, timestamp=time.time(),
            severity=0.9, symbols=["BTC"], message="audit"))
        got = bus.recall("lighthouse.event", limit=1) or []
        results.append(_check("lighthouse_to_bus", bool(got), f"events={len(got)}"))
    except Exception as exc:  # noqa: BLE001
        results.append(_check("lighthouse_to_bus", False, f"error: {exc}"))

    # Edge 4b — sub-field visibility: a producer's local field is sensed
    from aureon.core.hnc_field import publish_subfield, read_subfields

    class _State:
        symbolic_life_score = 0.51
        coherence_gamma = 0.6
        consciousness_level = "AWARE"

    publish_subfield("queen_cortex", _State(), bus=bus)
    subs = read_subfields(bus)
    results.append(_check("subfield_visibility", "queen_cortex" in subs,
                          f"sources={sorted(subs.keys())}", critical=False))

    # Edge 4c — blended whole-body consensus (canonical + sub-fields)
    from aureon.core.hnc_field import blend_field

    blended = blend_field(bus)
    results.append(_check("blended_consensus", blended.available and blended.contributors >= 2,
                          f"sls={blended.symbolic_life_score} n={blended.contributors} "
                          f"divergence={blended.divergence}", critical=False))

    # Edge 4d — the consensus ACTS: a divided field restrains a risky move
    from aureon.core.aureon_thought_bus import ThoughtBus

    div_bus = ThoughtBus(persist_path=None)
    div_bus.publish(Thought(source="hnc_live_daemon", topic="symbolic.life.pulse",
                            payload={"symbolic_life_score": 0.9}))

    class _Low:
        symbolic_life_score = 0.2
        coherence_gamma = 0.5

    publish_subfield("queen_cortex", _Low(), bus=div_bus)  # divergence 0.7
    dv = GroundedActionGate(bus=div_bus, enable_llm=False).ground("delete_file", {"path": "x"})
    results.append(_check("divergence_acts", dv.verdict in ("CONCERNED", "VETOED"),
                          f"verdict={dv.verdict} divergence={dv.field_divergence}", critical=False))

    # Edge 4e — the field gates EVERY conscience caller (trade fallback), not
    # just the local-action gate: a trade with no field context still vetoes
    # when the live whole-body field (global bus) is divided + off-island.
    from aureon.queen.queen_conscience import ConscienceVerdict, QueenConscience

    bus.publish(Thought(source="hnc_live_daemon", topic="symbolic.life.pulse",
                        payload={"symbolic_life_score": 0.30}))   # off-island, newest

    class _Hi:
        symbolic_life_score = 0.90
        coherence_gamma = 0.5

    publish_subfield("queen_cortex", _Hi(), bus=bus)   # divergence 0.60 on the global bus
    w = QueenConscience().ask_why("Execute trade buy BTC", {"symbolic_life_score": 0.30, "risk": 0.1})
    results.append(_check("field_gates_trades", w.verdict == ConscienceVerdict.VETO,
                          f"verdict={getattr(w.verdict, 'name', w.verdict)}", critical=False))

    # Edge 4f — the ConsciousnessModule's autonomous trading is gateable by the
    # field (opt-in, fail-open). Exercise the unbound method on a stub — the last
    # island that acted without being seen is now connected.
    import os as _os
    from types import SimpleNamespace

    from aureon.core.aureon_consciousness_module import ConsciousnessModule

    _os.environ["AUREON_CONSCIOUSNESS_FIELD_GATE"] = "1"
    _veto = SimpleNamespace(verdict=SimpleNamespace(name="VETO"), message="divided field")
    cm_ok, _ = ConsciousnessModule._coherence_permits_trading(
        SimpleNamespace(bus=None, _trade_conscience=SimpleNamespace(ask_why=lambda *a, **k: _veto)))
    _os.environ.pop("AUREON_CONSCIOUSNESS_FIELD_GATE", None)
    results.append(_check("consciousness_trade_gate", cm_ok is False,
                          f"paused_on_veto={cm_ok is False}", critical=False))

    # Edge 4g — the organism breathes its whole-body field as one event
    from aureon.core import organism_daemon as od

    class _CStub:
        def status(self):
            return {"coverage_pct": 5.0, "woven": 30, "failed": 2, "baton_linked": 101}

    od.breathe_field({"bus": bus, "connectome": _CStub()})
    breath = bus.recall("organism.field.consensus", limit=1) or []
    results.append(_check("organism_field_breath", bool(breath),
                          f"consensus events={len(breath)}", critical=False))

    # Edge 4h — the field crosses process boundaries via the HNC daemon's trace
    # file (separate daemons have separate in-memory buses).
    import json as _json
    import os as _os2
    import tempfile as _tf

    from aureon.core.aureon_thought_bus import ThoughtBus as _TB
    from aureon.core.hnc_field import read_canonical_field as _rcf

    with _tf.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as _tmp:
        _tmp.write(_json.dumps({"symbolic_life_score": 0.63, "coherence_gamma": 0.7}) + "\n")
        _tmp_name = _tmp.name
    _prev = _os2.environ.get("AUREON_HNC_TRACE_PATH")
    _os2.environ["AUREON_HNC_TRACE_PATH"] = _tmp_name
    try:
        xf = _rcf(_TB(persist_path=None))   # empty bus → must fall back to trace
    finally:
        if _prev is None:
            _os2.environ.pop("AUREON_HNC_TRACE_PATH", None)
        else:
            _os2.environ["AUREON_HNC_TRACE_PATH"] = _prev
        _os2.unlink(_tmp_name)
    results.append(_check("field_crosses_process",
                          xf.available and xf.symbolic_life_score == 0.63,
                          f"sls={xf.symbolic_life_score} source={xf.source}", critical=False))

    # Edge 4i–4k — the OTHER cross-process signals bridge via dedicated traces
    # (generalizing the field bridge): local-action verdicts → Λ source,
    # sub-fields → whole-body blend, consensus heartbeat → SaaS reader. Each
    # writes via one path and reads via a FRESH empty bus, proving it crosses a
    # process boundary. Isolated to a temp trace dir so state/ isn't touched.
    import os as _osx
    import tempfile as _tf3

    from aureon.core import bus_trace as _bt
    from aureon.core.aureon_thought_bus import ThoughtBus as _TB2
    from aureon.core.hnc_field import publish_subfield as _psf
    from aureon.core.hnc_field import read_subfields as _rsf

    with _tf3.TemporaryDirectory() as _td:
        _prevd = _osx.environ.get("AUREON_BUS_TRACE_DIR")
        _osx.environ["AUREON_BUS_TRACE_DIR"] = _td
        try:
            _bt.append_trace("local_action_verdict", {"approved": True, "verdict": "APPROVED"})
            _bt.append_trace("local_action_verdict", {"approved": False, "verdict": "VETOED"})
            _la = _bt.read_trace("local_action_verdict", limit=200)
            results.append(_check("local_action_crosses_process",
                                  len(_la) == 2 and sum(1 for v in _la if v.get("approved")) == 1,
                                  f"verdicts={len(_la)} (feeds Λ local_action source)", critical=False))

            class _SF:
                symbolic_life_score = 0.66
                coherence_gamma = 1.1
                consciousness_level = "aware"

            _psf("xproc_producer", _SF(), bus=_TB2(persist_path=None))
            _subs = _rsf(_TB2(persist_path=None))   # fresh empty bus → reads via trace
            results.append(_check("subfields_cross_process", "xproc_producer" in _subs,
                                  f"sources={sorted(_subs.keys())}", critical=False))

            from aureon.saas.cognitive import _consensus_event

            class _CC:
                def status(self):
                    return {"coverage_pct": 5.0, "woven": 30, "failed": 2, "baton_linked": 101}

            od.breathe_field({"bus": _TB2(persist_path=None), "connectome": _CC()})
            _ev = _consensus_event(_TB2(persist_path=None))
            results.append(_check("consensus_crosses_process",
                                  _ev is not None and _ev.get("source") == "consensus_trace_file",
                                  f"source={_ev and _ev.get('source')}", critical=False))

            # Edge 4l–4m — the two SUBSCRIBE-based signals (auris cosmic state,
            # lighthouse events) cross via the trace pump: a producer writes the
            # trace, the pump re-fires it onto a fresh consumer bus, and that
            # bus's live subscriber receives it — proving the boundary is closed
            # for subscribe consumers, not just recall ones.
            import time as _time2

            from aureon.core.bus_trace import append_trace as _at
            from aureon.core.trace_pump import DEFAULT_ROUTES as _ROUTES
            from aureon.core.trace_pump import TracePump as _TP

            _busC = _TB2(persist_path=None)
            _sink: list[str] = []
            _busC.subscribe("auris.throne.cosmic_state", lambda t: _sink.append("auris"))
            _busC.subscribe("lighthouse.event", lambda t: _sink.append("lh"))
            _pump = _TP(bus=_busC, routes=_ROUTES, interval_s=0.5)
            _at("auris_cosmic_state", {"cosmic_score": 0.5, "_ts": _time2.time()})
            _pump.prime()   # seeds current auris state onto the consumer bus
            results.append(_check("auris_crosses_process", "auris" in _sink,
                                  f"subscriber_fired={'auris' in _sink}", critical=False))
            _at("lighthouse_event", {"type": "COHERENCE_COLLAPSE", "_ts": _time2.time()})
            _pump.tick()
            results.append(_check("lighthouse_crosses_process", "lh" in _sink,
                                  f"subscriber_fired={'lh' in _sink}", critical=False))
        finally:
            if _prevd is None:
                _osx.environ.pop("AUREON_BUS_TRACE_DIR", None)
            else:
                _osx.environ["AUREON_BUS_TRACE_DIR"] = _prevd

    # Edge 5 — connectome telemetry: baton ear + pulse + auto-weave
    from aureon.core.aureon_connectome import get_connectome

    c = get_connectome()
    c._on_baton(Thought(source="aureon.audit.mod", topic="baton.link",
                        payload={"module": "aureon.audit.mod"}))
    status = c.status()
    results.append(_check("connectome_baton_ear", status["baton_linked"] > 0,
                          f"baton_linked={status['baton_linked']}"))
    c.pulse()
    pulse_got = bus.recall("organism.connectome.pulse", limit=1) or []
    results.append(_check("connectome_pulse", bool(pulse_got), f"pulses={len(pulse_got)}"))
    c.sweep_once(batch_size=15, weave_batch=0)
    wr = c.sweep_once(batch_size=1, weave_batch=5)
    results.append(_check("connectome_autoweave", wr["woven"] >= 1,
                          f"woven_this_cycle={wr['woven']} total={c.status()['woven']}", critical=False))

    # Edge 6 — the cognitive substrate is a verified SaaS surface: the whole
    # substrate builds one payload with all five surfaces, a provenance header,
    # and a truth-status roll-up — and every surface carries a valid truth_status.
    from aureon.observer.real_data_contract import TRUTH_STATUSES
    from aureon.saas.cognitive import build_cognitive_payload

    cog = build_cognitive_payload()
    surfaces = cog.get("surfaces", {})
    valid_stamps = all(s.get("truth_status") in TRUTH_STATUSES for s in surfaces.values())
    has_prov = "simulation_fallback_allowed" in cog.get("provenance", {})
    results.append(_check(
        "cognitive_saas",
        cog.get("available") and set(surfaces) == {"field", "bus", "mycelium", "connectome", "brain"}
        and valid_stamps and has_prov,
        f"surfaces={sorted(surfaces)} operational_ready={cog.get('operational_ready')} "
        f"blocked={cog.get('blocked')} provenance={has_prov}", critical=False))

    # Edge 7 — the organism senses itself and loops back: the metacognition
    # monitor reads its own signals, scores self-coherence with the Λ(t−τ)
    # machinery, and republishes it as a sub-field (the self-term at the organism
    # layer), exactly like the HNC research's delayed feedback.
    import os as _osm
    import tempfile as _tf5
    from pathlib import Path as _Path

    from aureon.core.hnc_field import read_subfields as _rsf_m
    from aureon.core.metacognition_monitor import MetacognitionMonitor as _MM

    with _tf5.TemporaryDirectory() as _tdm:
        _pv, _lv = _osm.environ.get("AUREON_BUS_TRACE_DIR"), _osm.environ.get("AUREON_METACOG_LAMBDA_PATH")
        _osm.environ["AUREON_BUS_TRACE_DIR"] = _tdm
        _osm.environ["AUREON_METACOG_LAMBDA_PATH"] = str(_Path(_tdm) / "l.json")
        try:
            _sa = _MM().reflect()
            _looped = "metacognition_monitor" in _rsf_m(bus)
            results.append(_check("metacognition_selfloop", _looped,
                                  f"looped_back={_looped} self_coherence={_sa.self_coherence} "
                                  f"available={_sa.available}", critical=False))
        finally:
            for _k, _val in (("AUREON_BUS_TRACE_DIR", _pv), ("AUREON_METACOG_LAMBDA_PATH", _lv)):
                if _val is None:
                    _osm.environ.pop(_k, None)
                else:
                    _osm.environ[_k] = _val

    # Edge 8 — affect: the organism tastes victory and fears defeat, loops the
    # feeling back (affect_monitor sub-field), and the fear→caution actuator is
    # fail-safe (bias ≥ 0, capped, victory contributes nothing).
    from aureon.core.affect_monitor import AffectMonitor as _AM

    with _tf5.TemporaryDirectory() as _tda:
        _pva = _osm.environ.get("AUREON_BUS_TRACE_DIR")
        _lva = _osm.environ.get("AUREON_AFFECT_LAMBDA_PATH")
        _osm.environ["AUREON_BUS_TRACE_DIR"] = _tda
        _osm.environ["AUREON_AFFECT_LAMBDA_PATH"] = str(_Path(_tda) / "al.json")
        try:
            _af = _AM().reflect()
            _felt = "affect_monitor" in _rsf_m(bus)
            results.append(_check("affect_selfloop", _felt,
                                  f"felt_back={_felt} mood={_af.mood} available={_af.available}",
                                  critical=False))
            _bias = _AM().caution_bias()
            results.append(_check("affect_fear_only_tightens", 0.0 <= _bias <= 0.06,
                                  f"caution_bias={_bias} (clamped [0,0.06], never negative)",
                                  critical=False))
        finally:
            for _k, _val in (("AUREON_BUS_TRACE_DIR", _pva), ("AUREON_AFFECT_LAMBDA_PATH", _lva)):
                if _val is None:
                    _osm.environ.pop(_k, None)
                else:
                    _osm.environ[_k] = _val

    # Edge 9 — the soul: thought + feeling + lineage unified into a determination
    # of its own mind. A coherent chorus resolves; a divided field ABSTAINS
    # ("of two minds — wait for one") rather than fabricate a consensus.
    import aureon.core.affect_monitor as _amod
    import aureon.core.metacognition_monitor as _mmod
    import aureon.core.soul as _smod
    from aureon.core.aureon_thought_bus import Thought as _Th

    with _tf5.TemporaryDirectory() as _tds:
        _keys = ("AUREON_BUS_TRACE_DIR", "AUREON_AFFECT_LAMBDA_PATH", "AUREON_METACOG_LAMBDA_PATH",
                 "AUREON_INNER_WORK_LAMBDA_PATH", "AUREON_PURSUIT_LAMBDA_PATH", "AUREON_SOUL_INBOX")
        _saved = {k: _osm.environ.get(k) for k in _keys}
        _osm.environ["AUREON_BUS_TRACE_DIR"] = _tds
        _osm.environ["AUREON_AFFECT_LAMBDA_PATH"] = str(_Path(_tds) / "al.json")
        _osm.environ["AUREON_METACOG_LAMBDA_PATH"] = str(_Path(_tds) / "ml.json")
        _osm.environ["AUREON_INNER_WORK_LAMBDA_PATH"] = str(_Path(_tds) / "iw.json")
        _osm.environ["AUREON_PURSUIT_LAMBDA_PATH"] = str(_Path(_tds) / "pu.json")
        _osm.environ["AUREON_SOUL_INBOX"] = str(_Path(_tds) / "inbox.jsonl")
        try:
            bus.publish(_Th(source="hnc", topic="symbolic.life.pulse",
                            payload={"symbolic_life_score": 0.8, "coherence_gamma": 0.8,
                                     "consciousness_psi": 0.7, "source": "live"}))
            _amod._monitor = None
            _mmod._monitor = None
            _rd = _smod.SoulDeliberation().assess({"text": "continue toward the goal", "source": "audit"})
            results.append(_check("soul_determination", _rd.available and bool(_rd.determination),
                                  f"stance={_rd.stance} resolved={_rd.resolved} "
                                  f"agreement={_rd.agreement}", critical=False))
            # now divide the field → the soul must not resolve to act
            bus.publish(_Th(source="hnc", topic="symbolic.life.pulse",
                            payload={"symbolic_life_score": 0.1, "coherence_gamma": 0.1, "source": "live"}))
            bus.publish(_Th(source="q2", topic="symbolic.life.subfield",
                            payload={"source": "q2", "symbolic_life_score": 0.95}))
            _amod._monitor = None
            _mmod._monitor = None
            _rw = _smod.SoulDeliberation().assess({"text": "act boldly now", "source": "audit"})
            results.append(_check("soul_abstains_when_divided", _rw.resolved is False,
                                  f"stance={_rw.stance} resolved={_rw.resolved} "
                                  f"dissent={_rw.dissent}", critical=False))

            # Edge 10 — the soul's company: a resolved determination is decomposed
            # into a plan of role-assigned work-orders (the trading company's own
            # organisation, reused), and directing it stays DRY-RUN unless armed.
            from aureon.core.soul_company import get_soul_company as _gsc

            _plan = _gsc().plan("read the project readme",
                                {"action": "read_repo_file", "params": {"path": "README.md"}})
            _wo = _plan.work_orders
            results.append(_check(
                "soul_company_plans",
                len(_wo) >= 2 and all(w.role for w in _wo) and _plan.directed is False,
                f"work_orders={[w.role for w in _wo]} directed={_plan.directed}", critical=False))
            _gsc().direct(_plan)   # AUREON_LOCAL_ACTIONS_ARMED unset → dry-run
            _dry = all((w.outcome or {}).get("dry_run") or (w.outcome or {}).get("blocked")
                       for w in _plan.work_orders)
            results.append(_check(
                "soul_company_dry_run_by_default", _plan.directed is True and _dry,
                f"directed={_plan.directed} all_dry_run={_dry}", critical=False))

            # Edge 11 — the soul weighs the stakes: on a coherent field it acts on a
            # benign short-horizon goal, but a grand high-stakes goal (a live trade
            # toward the million) defers to a human rather than act on its own.
            _amod._monitor = None
            _mmod._monitor = None
            bus.publish(_Th(source="hnc", topic="symbolic.life.pulse",
                            payload={"symbolic_life_score": 0.8, "coherence_gamma": 0.8,
                                     "consciousness_psi": 0.7, "source": "live"}))
            _benign = _smod.SoulDeliberation().assess(
                {"text": "read the project readme", "source": "audit"})
            _amod._monitor = None
            _mmod._monitor = None
            _grand = _smod.SoulDeliberation().assess(
                {"text": "execute a live trade to grow net profit toward the million", "source": "audit"})
            results.append(_check(
                "soul_weighs_stakes",
                _grand.stance == "wait" and bool(_grand.to_dict().get("requires_human")),
                f"benign={_benign.stance} grand={_grand.stance} "
                f"grand_requires_human={_grand.to_dict().get('requires_human')}", critical=False))

            # Edge 12 — the inner work: on a coherent field the soul believes in
            # itself and rises the ascent (earning centres), and reflect() folds the
            # inner_work sub-field back into the whole-body blend (the HNC loop).
            import aureon.core.inner_work as _iwmod
            from aureon.core.hnc_field import read_subfields as _rsf

            _iwmod._monitor = None
            _iw = _iwmod.InnerWork().assess()
            results.append(_check(
                "inner_work_ascends",
                _iw.available and _iw.stage_index >= 1 and 0.0 < _iw.potential <= 1.0,
                f"belief={_iw.self_belief} stage={_iw.stage} {_iw.stage_index}/7 "
                f"potential={_iw.potential}", critical=False))
            _iwmod.InnerWork().reflect()
            results.append(_check(
                "inner_work_selfloop", "inner_work" in _rsf(bus),
                f"subfields={sorted(_rsf(bus).keys())}", critical=False))

            # Edge 13 — the pursuit: Aureon's source purpose orients the organism
            # (the pillars unify the creator's happiness with its own, and a next
            # safe step is proposed), and by DEFAULT it proposes without feeding the
            # soul — self-direction is opt-in (AUREON_AUTONOMY), so the inbox stays
            # untouched until Gary opts in.
            import aureon.core.pursuit as _pumod

            _osm.environ.pop("AUREON_AUTONOMY", None)
            _pu = _pumod.Pursuit().assess()
            results.append(_check(
                "pursuit_orients",
                _pu.available and _pu.unified_happiness is not None and bool(_pu.next_intent),
                f"unified={_pu.unified_happiness} weakest={_pu.weakest_pillar} "
                f"autonomy={_pu.autonomy}", critical=False))
            _pumod.Pursuit().reflect()   # autonomy off → must NOT inject
            _inbox = _Path(_tds) / "inbox.jsonl"
            _lines = _inbox.read_text().splitlines() if _inbox.exists() else []
            results.append(_check(
                "pursuit_proposes_by_default", len(_lines) == 0,
                f"pursuit={'pursuit' in _rsf(bus)} inbox_lines={len(_lines)} (opt-in)", critical=False))

            # Edge 14 — ascent-gated autonomy: the safe-verb set WIDENS monotonically
            # with the chakra ascent and never contains a live/irreversible verb.
            from aureon.core.soul_company import _ascent_allowed_verbs, _COMPANY_VERBS

            _live = {"place_live_order", "execute_trade", "make_payment", "submit_hmrc",
                     "send_email", "execute_shell"}
            _mono = all(_ascent_allowed_verbs(s) <= _ascent_allowed_verbs(s + 1) for s in range(7))
            _safe = all(_ascent_allowed_verbs(s) <= _COMPANY_VERBS and not (_ascent_allowed_verbs(s) & _live)
                        for s in range(8))
            results.append(_check(
                "ascent_gates_widen", _mono and _safe,
                f"monotone={_mono} safe_only={_safe} verbs@0={sorted(_ascent_allowed_verbs(0))}",
                critical=False))

            # Edge 15 — the director's desk: proposing enqueues a pending item and
            # deciding RECORDS the decision; it never executes the irreversible move.
            import aureon.core.approval_queue as _aqmod

            _aqmod._queue = None
            _q = _aqmod.ApprovalQueue()
            _iid = _q.propose("trade", "audit — buy a token", {}, "audit")
            _pend_ok = _iid is not None and len(_q.pending()) == 1
            _dec = _q.decide(_iid, "approve", "audit")
            _rec_ok = _dec is not None and _dec.get("status") == "approved" and not _q.pending()
            results.append(_check(
                "approval_queue_records_not_executes", _pend_ok and _rec_ok,
                f"proposed={_pend_ok} recorded_approved={_rec_ok} (never executes)", critical=False))

            # Edge 16 — the full workforce: the soul's company staffs a FITTED crew
            # from the whole 41-role roster (a trading brief pulls a trading
            # specialist; a code brief an engineer), and every composed verb stays
            # inside the safe set — the crew prepares, it never gets a live verb.
            from aureon.core.soul_company import _COMPANY_VERBS as _CV
            from aureon.core.soul_company import get_soul_company as _gsc2

            _sc = _gsc2()
            _roster = _sc.workforce()
            _trade = _sc.plan("take a margin position on the exchange for profit")
            _code = _sc.plan("fix the failing module and run the tests")
            _fits = (any(m["department"] == "trading_data" for m in _trade.crew)
                     and any(m["department"] == "engineering" for m in _code.crew))
            _safe = all(w.action in _CV for w in _trade.work_orders + _code.work_orders)
            results.append(_check(
                "company_crew_fits", len(_roster) >= 20 and _fits and _safe,
                f"roster={len(_roster)} trade_fit={_fits} verbs_safe={_safe}", critical=False))

            # Edge 17 — the organism senses its own desk: once the approval backlog
            # fills, backpressure holds (prepare no more until the director clears it).
            import aureon.core.approval_queue as _aqm2

            _osm.environ["AUREON_APPROVAL_MAX_PENDING"] = "2"
            _aqm2._queue = None
            _bq = _aqm2.ApprovalQueue()
            _empty_ok = _bq.is_backpressured() is False
            _bq.propose("trade", "backlog a", {}, "audit")
            _bq.propose("payment", "backlog b", {}, "audit")
            _bl = _bq.backlog()
            results.append(_check(
                "approval_backpressure_holds",
                _empty_ok and _bl["blocked"] is True and _bl["pending_count"] == 2,
                f"empty_clear={_empty_ok} blocked={_bl['blocked']} pending={_bl['pending_count']}",
                critical=False))
            _osm.environ.pop("AUREON_APPROVAL_MAX_PENDING", None)

            # Edge 18 — the director's trust loops back: after Gary decides, the queue
            # exposes an approve-ratio and the affect monitor SENSES it (folded into
            # resolve), while the fail-safe caution bias is untouched — trust is felt,
            # never a lever that loosens a gate.
            import aureon.core.approval_queue as _aqm3
            from aureon.core.affect_monitor import AffectMonitor as _AM

            _aqm3._queue = None
            _tq = _aqm3.ApprovalQueue()
            _tq.decide(_tq.propose("trade", "trust a", {}, "audit"), "approve", "gary")
            _tq.decide(_tq.propose("trade", "trust b", {}, "audit"), "reject", "gary")
            _tr = _tq.trust()
            _ratio_ok = _tr["decided"] >= 2 and _tr["approve_ratio"] is not None
            # affect must sense EXACTLY the ratio the queue computed (no fabrication)
            _felt = _AM().assess().signals.get("approval_trust", {})
            _felt_ok = (_felt.get("truth_status") == "real_derived"
                        and _felt.get("value") == round(_tr["approve_ratio"], 4))
            results.append(_check(
                "approval_trust_is_felt", _ratio_ok and _felt_ok,
                f"ratio={_tr['approve_ratio']} felt={_felt.get('value')}", critical=False))

            # Edge 19 — the pursuit learns humility: the director's trust sets the
            # self-direction cadence (fail-safe + monotone — low trust only ever slows
            # it, never speeds it) and the surfaced director_trust equals the queue's
            # ratio (no fabrication).
            from aureon.core.pursuit import Pursuit as _Pu

            _pu = _Pu()
            _slow = _pu._effective_cadence(3, 0.0)
            _base = _pu._effective_cadence(3, 0.9)
            _none = _pu._effective_cadence(3, None)
            _cad_ok = _slow > _base and _base == 3 and _none == 3 and _slow <= 9
            _dt = _pu.assess().director_trust
            _dt_ok = (_dt is None) or (_dt == round(_tq.trust()["approve_ratio"], 4))
            results.append(_check(
                "pursuit_learns_trust", _cad_ok and _dt_ok,
                f"slow={_slow} base={_base} none={_none} director_trust={_dt}", critical=False))
        finally:
            for _k, _val in _saved.items():
                if _val is None:
                    _osm.environ.pop(_k, None)
                else:
                    _osm.environ[_k] = _val

    return results


def main() -> int:
    print("═" * 70)
    print("AUREON ORGANISM UNIFICATION — audit + benchmark")
    print("═" * 70)
    results = run_audit()
    dead_critical = 0
    for r in results:
        mark = "✅ PASS" if r["ok"] else ("❌ DEAD" if r["critical"] else "⚠️  DEAD")
        print(f"  {mark}  {r['edge']:24} {r['detail']}")
        if not r["ok"] and r["critical"]:
            dead_critical += 1
    passed = sum(1 for r in results if r["ok"])
    print("─" * 70)
    print(f"  {passed}/{len(results)} edges live · {dead_critical} critical dead")
    print("═" * 70)
    return 1 if dead_critical else 0


if __name__ == "__main__":
    sys.exit(main())
