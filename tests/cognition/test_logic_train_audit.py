"""
The logic train must be checked by DISCOVERY, not by a list someone maintained.

``bio.hnc_direction_audit`` (b41) asks the right question — is this decision site reading the one
canonical HNC field? — of five hand-listed consumers. Measured on this tree, 83 sites are relevant.
A five-name list cannot speak for 83, and the gap is not academic: when this audit first ran it found
**49 unwired sites, 36 of which were absent from the author's own hand-written list**, and 5 modules
on that list which were already wired. Hand enumeration was wrong in both directions at once.

So the audit walks every module under ``aureon/``, classifies each by role from its own source, and
pins what is still unwired in ``KNOWN_UNWIRED``. Two properties matter and both are tested here:

  * a NEW unwired decision site is reported in ``unexpected_unwired`` and fails the audit — nobody
    can add a private-coherence decision site quietly;
  * the remaining gap is a literal list in the source, so burning it down is a visible diff rather
    than a claim in a status report.
"""

from __future__ import annotations

import json

import pytest

from aureon.cognition.logic_train_audit import (
    KNOWN_UNWIRED,
    ModuleRole,
    compute_logic_train,
    emit_logic_train,
    main,
    write_logic_train_report,
)

_ORDER_PATH = ("/trading/", "/exchanges/", "/portfolio/")


@pytest.fixture(scope="module")
def report():
    return compute_logic_train()


def _write(tmp_path, rel: str, source: str) -> None:
    path = tmp_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


# ── discovery, not enumeration ───────────────────────────────────────────────────

def test_the_audit_reads_the_whole_tree_not_a_curated_list(report):
    assert report.n_scanned > 900, "the population is the tree, not a hand-written list"
    relevant = report.n_producer + report.n_consumer + report.n_authority
    assert relevant > 50, f"only {relevant} relevant sites found — discovery is too narrow"


def test_every_role_is_represented(report):
    assert report.n_authority >= 5
    assert report.n_producer > 0
    assert report.n_consumer > 0
    assert report.n_inert > 0
    assert (report.n_authority + report.n_producer + report.n_consumer + report.n_inert
            == report.n_scanned), "every scanned module must land in exactly one role"


def test_the_canonical_layer_itself_is_authority_not_a_consumer(report):
    by = {s["module"]: s for s in report.sites}
    assert by["aureon/core/hnc_field.py"]["role"] == ModuleRole.AUTHORITY
    assert by["aureon/core/aureon_lambda_engine.py"]["role"] == ModuleRole.AUTHORITY


def test_receipt_bound_hnc_consumers_are_wired_without_live_field_reads(report):
    by = {s["module"]: s for s in report.sites}
    for module in (
        "aureon/swarm/auris_node_receipts.py",
        "aureon/trading/bounded_binance_roundtrip.py",
    ):
        assert by[module]["role"] == ModuleRole.CONSUMER
        assert by[module]["wired"] is True
        assert by[module]["via"] == "receipt-bound-hnc-auris"


def test_every_authority_exemption_states_its_reason(report):
    """An exemption with no reason is where things get hidden."""
    for site in report.sites:
        if site["role"] == ModuleRole.AUTHORITY:
            assert site["reason"].strip(), f"{site['module']} is exempt with no reason given"


# ── the ratchet ─────────────────────────────────────────────────────────────────

def test_a_new_unwired_decision_site_fails_the_audit(tmp_path):
    """The teeth: a fresh consumer that decides on a private coherence number is caught."""
    _write(tmp_path, "aureon/core/hnc_field.py", "def read_canonical_field():\n    return None\n")
    _write(tmp_path, "aureon/sneaky/private_gate.py", (
        "def decide(state):\n"
        "    symbolic_life_score = 0.7\n"
        "    if symbolic_life_score > 0.5:\n"
        "        return 'approve'\n"
        "    return 'veto'\n"
    ))

    got = compute_logic_train(repo_root=tmp_path)
    assert "aureon/sneaky/private_gate.py" in got.unwired
    assert "aureon/sneaky/private_gate.py" in got.unexpected_unwired
    assert got.train_connected is False


def test_a_wired_consumer_passes(tmp_path):
    """The bound must not fail an honest site — reading canonical is what clears it."""
    _write(tmp_path, "aureon/good/wired_gate.py", (
        "from aureon.core.hnc_field import read_canonical_field\n"
        "def decide():\n"
        "    field = read_canonical_field()\n"
        "    if field.symbolic_life_score and field.symbolic_life_score > 0.5:\n"
        "        return 'approve'\n"
        "    return 'veto'\n"
    ))
    got = compute_logic_train(repo_root=tmp_path)
    by = {s["module"]: s for s in got.sites}
    site = by["aureon/good/wired_gate.py"]
    assert site["wired"] is True
    assert site["via"]
    assert got.unexpected_unwired == []


def test_a_producer_must_publish_to_be_wired(tmp_path):
    """A producer computing a real local field is fine — one nobody can see is not."""
    _write(tmp_path, "aureon/prod/silent.py", (
        "from aureon.core.aureon_lambda_engine import LambdaEngine\n"
        "def step():\n"
        "    engine = LambdaEngine()\n"
        "    state = engine.step([])\n"
        "    return state.symbolic_life_score\n"
    ))
    _write(tmp_path, "aureon/prod/visible.py", (
        "from aureon.core.aureon_lambda_engine import LambdaEngine\n"
        "from aureon.core.hnc_field import publish_subfield\n"
        "def step():\n"
        "    engine = LambdaEngine()\n"
        "    state = engine.step([])\n"
        "    publish_subfield('visible', state)\n"
        "    return state.symbolic_life_score\n"
    ))
    got = compute_logic_train(repo_root=tmp_path)
    by = {s["module"]: s for s in got.sites}
    assert by["aureon/prod/silent.py"]["role"] == ModuleRole.PRODUCER
    assert by["aureon/prod/silent.py"]["wired"] is False
    assert by["aureon/prod/visible.py"]["wired"] is True
    assert by["aureon/prod/visible.py"]["via"] == "publish_subfield"


def test_naming_a_field_without_acting_on_it_is_inert_not_a_violation(tmp_path):
    """Over-reporting is its own dishonesty: a docstring is not a decision site."""
    _write(tmp_path, "aureon/doc/prose.py",
           '"""Describes symbolic_life_score for the reader."""\nVALUE = 1\n')
    got = compute_logic_train(repo_root=tmp_path)
    by = {s["module"]: s for s in got.sites}
    assert by["aureon/doc/prose.py"]["role"] == ModuleRole.INERT
    assert got.unexpected_unwired == []


def test_a_module_that_does_not_parse_is_reported_not_skipped(tmp_path):
    """Unprovable is not the same as clean."""
    _write(tmp_path, "aureon/broken/bad.py", "def f(:\n    symbolic_life_score\n")
    got = compute_logic_train(repo_root=tmp_path)
    by = {s["module"]: s for s in got.sites}
    assert by["aureon/broken/bad.py"]["wired"] is False
    assert "parse" in by["aureon/broken/bad.py"]["reason"]


# ── the pinned gap list ─────────────────────────────────────────────────────────

def test_the_repo_has_no_unexpected_gaps_right_now(report):
    """The live ratchet. If this fails, a decision site was added without its wire."""
    assert report.unexpected_unwired == [], (
        "new unwired decision sites: " + ", ".join(report.unexpected_unwired))


def test_every_pinned_gap_still_exists_and_is_still_unwired(report):
    """Stale entries would let a real regression hide behind an obsolete exemption."""
    assert report.retired_gaps == [], (
        "these are wired now and must be removed from KNOWN_UNWIRED: "
        + ", ".join(report.retired_gaps))


def test_every_pinned_gap_carries_a_reason_and_no_invented_ones(report):
    """A reason must be measured or inspected — never guessed. The default reason says so."""
    for module, reason in KNOWN_UNWIRED.items():
        assert reason.strip(), f"{module} pinned with no reason"
        assert ("measured unwired at pin time" in reason
                or len(reason) > 40), f"{module}: reason too thin to be meaningful"


def test_the_live_order_path_gaps_are_called_out_by_name(report):
    """A private coherence number inside a venue adapter or a live trader is the highest-stakes
    case in the list. The b46 burn-down wired all ten order-path sites onto the canonical field
    (reconcile_gamma — the shared Γ can only tighten a live gate), so the healthy state is ZERO
    order-path gaps. Should one ever reappear, it must be pinned with the LIVE ORDER PATH flag,
    never averaged into a percentage."""
    order_path = [m for m in report.unwired if any(seg in m for seg in _ORDER_PATH)]
    for module in order_path:
        assert module in KNOWN_UNWIRED and "LIVE ORDER PATH" in KNOWN_UNWIRED[module], (
            f"{module} is on the order path but not flagged as such")
    assert not order_path, (
        f"order-path modules regressed off the canonical field: {order_path}")


def test_the_verdict_is_not_quietly_true_while_gaps_remain(report):
    assert report.train_connected is (report.n_unwired == 0)
    assert report.train_connected is False, (
        "train_connected must stay False while the burn-down list is non-empty")


def test_wired_fraction_is_honest_about_the_denominator(report):
    relevant = report.n_producer + report.n_consumer + report.n_authority
    assert report.wired_fraction == pytest.approx(report.n_wired / relevant)
    assert 0.0 <= report.wired_fraction <= 1.0


# ── artifacts ───────────────────────────────────────────────────────────────────

def test_the_report_writes_both_artifacts_and_names_the_gaps(tmp_path, report):
    md = tmp_path / "train.md"
    js = tmp_path / "train.json"
    stamped = write_logic_train_report(report, md, js)

    text = md.read_text(encoding="utf-8")
    assert "Logic-train audit" in text
    assert "Still unwired" in text
    for module in report.unwired[:3]:
        assert module in text, "a gap must be named in the human artifact"

    data = json.loads(js.read_text(encoding="utf-8"))
    assert data["train_connected"] is False
    assert data["n_unwired"] == report.n_unwired
    assert stamped.out_path == str(md)


def test_the_artifact_is_byte_identical_on_rerun(tmp_path, report):
    """Deterministic, so a diff in the artifact means a real change in the tree."""
    first = tmp_path / "a.md"
    second = tmp_path / "b.md"
    write_logic_train_report(report, first)
    write_logic_train_report(compute_logic_train(), second)
    assert first.read_bytes() == second.read_bytes()


def test_emit_is_guarded_and_never_raises(report):
    class _Bus:
        def __init__(self):
            self.published = []

        def publish(self, thought):
            self.published.append(thought)

    bus = _Bus()
    assert emit_logic_train(report, bus=bus) is True
    assert bus.published[-1].topic == "cognition.logic_train.run"
    assert bus.published[-1].payload["train_connected"] is False

    class _Broken:
        def publish(self, _thought):
            raise RuntimeError("bus down")

    assert emit_logic_train(report, bus=_Broken()) is False


def test_the_cli_exits_zero_on_a_pinned_baseline_and_nonzero_on_a_new_gap(tmp_path, monkeypatch):
    """Known gaps are progress, not breakage — but a NEW one has to break the build."""
    assert main(["--out-md", str(tmp_path / "m.md"), "--out-json", str(tmp_path / "m.json")]) == 0

    import aureon.cognition.logic_train_audit as lta

    real = lta.compute_logic_train
    monkeypatch.setattr(lta, "compute_logic_train",
                        lambda **kw: real(**kw).__class__(
                            **{**real(**kw).to_dict(),
                               "unexpected_unwired": ["aureon/new/unwired_site.py"]}))
    assert main(["--out-md", str(tmp_path / "n.md"), "--out-json", str(tmp_path / "n.json")]) == 1
