from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDITOR_PATH = ROOT / "scripts" / "validation" / "audit_os_protection_boundaries.py"
SPEC = importlib.util.spec_from_file_location("os_protection_boundary_census", AUDITOR_PATH)
assert SPEC is not None and SPEC.loader is not None
AUDITOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUDITOR
SPEC.loader.exec_module(AUDITOR)


def _write(root: Path, relative: str, source: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def _findings(root: Path) -> list[dict[str, Any]]:
    return AUDITOR.audit(root)["findings"]


def test_comments_strings_and_imports_alone_cannot_earn_protection(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "hostile.py",
        '''
from aureon.plumber.os_protection import AdmittedHNC, LocalOSProtectionBoundary
import subprocess

FAKE_PROOF = "boundary.admit_external(data); boundary.protect_for_magic_star(handle)"

def unsafe(user_value):
    # LocalOSProtectionBoundary admit_external AdmittedHNC protect_for_magic_star
    return subprocess.run(["echo", user_value])
''',
    )

    findings = _findings(tmp_path)

    assert len(findings) == 1
    assert findings[0]["category"] == "subprocess-shell"
    assert findings[0]["classification"] == AUDITOR.BLOCKER
    assert findings[0]["evidence"] == ()


def test_custody_handoff_does_not_authorize_a_following_sink(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "protected.py",
        '''
from aureon.plumber.os_protection import AdmittedHNC, LocalOSProtectionBoundary
import subprocess

def protected(payload):
    boundary = LocalOSProtectionBoundary(
        boundary_id="fixture",
        master_key_provider=lambda: b"fixture-key-material-that-is-long-enough",
    )
    outcome = boundary.admit_external(
        payload,
        source_id="fixture",
        ingress_kind="test",
        purpose="fixture",
    )
    if isinstance(outcome, AdmittedHNC):
        boundary.protect_for_magic_star(
            outcome.handle,
            custody=object(),
            release_context_sha256="0" * 64,
        )
        return subprocess.run(["echo", "protected"])
    return None
''',
    )

    findings = _findings(tmp_path)

    assert len(findings) == 1
    assert findings[0]["classification"] == AUDITOR.BLOCKER
    assert findings[0]["evidence"] == ()


def test_negative_guard_and_custody_handoff_still_do_not_release_sink(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "negative_guard.py",
        '''
from aureon.plumber.os_protection import AdmittedHNC, LocalOSProtectionBoundary
import subprocess

def protected(payload):
    boundary = LocalOSProtectionBoundary(
        boundary_id="fixture",
        master_key_provider=lambda: b"fixture-key-material-that-is-long-enough",
    )
    outcome = boundary.admit_external(
        payload,
        source_id="fixture",
        ingress_kind="test",
        purpose="fixture",
    )
    if not isinstance(outcome, AdmittedHNC):
        raise RuntimeError("HOLD")
    boundary.protect_for_magic_star(
        outcome.handle,
        custody=object(),
        release_context_sha256="0" * 64,
    )
    return subprocess.run(["echo", "protected"])
''',
    )

    findings = _findings(tmp_path)

    assert len(findings) == 1
    assert findings[0]["classification"] == AUDITOR.BLOCKER


def test_registered_capability_selected_by_release_boundary_is_local_dev_only(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        "registered_release.py",
        '''
from aureon.plumber.os_protection import AdmittedHNC, LocalOSProtectionBoundary
from aureon.plumber.release_boundary_v02 import LocalDevelopmentReleaseBoundaryV02
from aureon.plumber.star_custody_v02 import (
    LocalDevelopmentStarCustodyV02,
    RegisteredCapabilityV02,
)
from flask import Flask
import subprocess

app = Flask(__name__)

def shell_capability(payload):
    return {"status": subprocess.run(["echo", "registered"]).returncode}

CAPABILITY = RegisteredCapabilityV02(
    capability_id="shell:test",
    measurement_sha256="1" * 64,
    policy_measurement_sha256="2" * 64,
    result_schema={"status": "bool"},
    handler=shell_capability,
)
POLICY = object()
CUSTODY = LocalDevelopmentStarCustodyV02(
    allow_insecure_same_process=True,
    source_authority=source_authority,
    source_private_key=source_private_key,
    state_store=state_store,
    authorization_trust=authorization_trust,
    capabilities={"shell:test": CAPABILITY},
)
RELEASE = LocalDevelopmentReleaseBoundaryV02(
    allow_insecure_same_process=True,
    state_store=state_store,
    epas_store=epas_store,
    custody=CUSTODY,
    recipient_verifier=recipient_verifier,
    star_trust=star_trust,
    release_evidence_trust=release_evidence_trust,
    authorization_trust=authorization_trust,
    receipt_authority=receipt_authority,
    receipt_private_key=receipt_private_key,
    capability_policies={"shell:test": POLICY},
    live_binding_probe=live_binding_probe,
    continuity_state_probe=continuity_state_probe,
    evidence_expectations_probe=evidence_expectations_probe,
)

@app.post("/command")
def route(payload):
    boundary = LocalOSProtectionBoundary(
        boundary_id="fixture",
        master_key_provider=lambda: b"fixture-key-material-that-is-long-enough",
    )
    outcome = boundary.admit_external(
        payload,
        source_id="fixture",
        ingress_kind="test",
        purpose="fixture",
    )
    if isinstance(outcome, AdmittedHNC):
        packet = boundary.protect_for_magic_star(
            outcome.handle,
            custody=CUSTODY,
            release_context_sha256="0" * 64,
        )
        return RELEASE.release(
            packet,
            session_id="fixture",
            challenge=challenge,
            recipient_proof=recipient_proof,
            temporal_commitment="3" * 64,
            observer_commitment="4" * 64,
            expected_channel_binding_sha256="5" * 64,
            expected_live_binding_sha256="6" * 64,
            expected_runtime_measurement_sha256="7" * 64,
            star=star,
            release_evidence=release_evidence,
            authorization_chain=authorization_chain,
            capability_id="shell:test",
        )
    return None
''',
    )

    census = AUDITOR.audit(tmp_path)

    assert census["blocker_count"] == 0
    assert census["protected_count"] == 2
    assert {
        (item["category"], item["classification"])
        for item in census["findings"]
    } == {
        ("http-server-ingress", AUDITOR.LOCAL_DEVELOPMENT_PROTECTED),
        ("subprocess-shell", AUDITOR.LOCAL_DEVELOPMENT_PROTECTED),
    }
    assert census["certified_full_os_protection"] is False
    assert census["certification_limitations"] == [
        "local-os-protection-boundary-production-ready-false",
        "magic-star-custody-production-ready-false",
        "release-boundary-production-ready-false",
    ]


def _strict_registered_release_source(
    *,
    admitted_raw: str = "payload",
    handler_argument: str = '["echo", "registered"]',
    handler_signature: str = "payload",
    module_prelude: str = "",
    module_after_capability: str = "",
    module_after_custody: str = "",
    module_after_release: str = "",
    boundary_constructor: str | None = None,
    boundary_after_constructor: str = "",
    outcome_after_admission: str = "",
    packet_after_handoff: str = "",
    custody_insecure: str = "True",
    release_insecure: str = "True",
) -> str:
    boundary = boundary_constructor or '''LocalOSProtectionBoundary(
        boundary_id="fixture",
        master_key_provider=lambda: b"fixture-key-material-that-is-long-enough",
    )'''
    return f'''
from aureon.plumber.os_protection import AdmittedHNC, LocalOSProtectionBoundary
from aureon.plumber.release_boundary_v02 import LocalDevelopmentReleaseBoundaryV02
from aureon.plumber.star_custody_v02 import (
    LocalDevelopmentStarCustodyV02,
    RegisteredCapabilityV02,
)
from flask import Flask
import subprocess

{module_prelude}
app = Flask(__name__)

def shell_capability({handler_signature}):
    return {{"status": subprocess.run({handler_argument}).returncode}}

CAPABILITY = RegisteredCapabilityV02(
    capability_id="shell:test",
    measurement_sha256="1" * 64,
    policy_measurement_sha256="2" * 64,
    result_schema={{"status": "bool"}},
    handler=shell_capability,
)
{module_after_capability}
POLICY = object()
CUSTODY = LocalDevelopmentStarCustodyV02(
    allow_insecure_same_process={custody_insecure},
    source_authority=source_authority,
    source_private_key=source_private_key,
    state_store=state_store,
    authorization_trust=authorization_trust,
    capabilities={{"shell:test": CAPABILITY}},
)
{module_after_custody}
RELEASE = LocalDevelopmentReleaseBoundaryV02(
    allow_insecure_same_process={release_insecure},
    state_store=state_store,
    epas_store=epas_store,
    custody=CUSTODY,
    recipient_verifier=recipient_verifier,
    star_trust=star_trust,
    release_evidence_trust=release_evidence_trust,
    authorization_trust=authorization_trust,
    receipt_authority=receipt_authority,
    receipt_private_key=receipt_private_key,
    capability_policies={{"shell:test": POLICY}},
    live_binding_probe=live_binding_probe,
    continuity_state_probe=continuity_state_probe,
    evidence_expectations_probe=evidence_expectations_probe,
)
{module_after_release}

@app.post("/command")
def route(payload):
    boundary = {boundary}
    {boundary_after_constructor}
    outcome = boundary.admit_external(
        {admitted_raw},
        source_id="fixture",
        ingress_kind="test",
        purpose="fixture",
    )
    {outcome_after_admission}
    if isinstance(outcome, AdmittedHNC):
        packet = boundary.protect_for_magic_star(
            outcome.handle,
            custody=CUSTODY,
            release_context_sha256="0" * 64,
        )
        {packet_after_handoff}
        return RELEASE.release(
            packet,
            session_id="fixture",
            challenge=challenge,
            recipient_proof=recipient_proof,
            temporal_commitment="3" * 64,
            observer_commitment="4" * 64,
            expected_channel_binding_sha256="5" * 64,
            expected_live_binding_sha256="6" * 64,
            expected_runtime_measurement_sha256="7" * 64,
            star=star,
            release_evidence=release_evidence,
            authorization_chain=authorization_chain,
            capability_id="shell:test",
        )
    return None
'''


@pytest.mark.parametrize(
    "changes",
    [
        {"module_after_capability": "CAPABILITY = object()"},
        {"module_after_custody": "CUSTODY = object()"},
        {"module_after_release": "RELEASE = object()"},
        {"boundary_after_constructor": "boundary = object()"},
        {"outcome_after_admission": "outcome = object()"},
        {"packet_after_handoff": "packet = object()"},
    ],
    ids=("capability", "custody", "release", "boundary", "outcome", "packet"),
)
def test_rebound_protection_symbols_never_earn_coverage(
    tmp_path: Path,
    changes: dict[str, str],
) -> None:
    _write(tmp_path, "rebound.py", _strict_registered_release_source(**changes))

    census = AUDITOR.audit(tmp_path)

    assert census["protected_count"] == 0
    assert census["blocker_count"] == 2
    assert all(item["classification"] == AUDITOR.BLOCKER for item in census["findings"])


@pytest.mark.parametrize(
    "changes",
    [
        {"admitted_raw": 'b"unrelated-safe-constant"'},
        {
            "module_prelude": 'UNTRUSTED_ARGUMENTS = ["echo", "global"]',
            "handler_argument": "UNTRUSTED_ARGUMENTS",
        },
        {
            "module_prelude": "request = object()",
            "handler_argument": "request.arguments",
        },
        {"handler_signature": "payload, unrelated", "handler_argument": "unrelated"},
    ],
    ids=("constant-admission", "global-data", "global-request", "unrelated-parameter"),
)
def test_unjoined_ingress_or_handler_data_never_earn_coverage(
    tmp_path: Path,
    changes: dict[str, str],
) -> None:
    _write(tmp_path, "unjoined.py", _strict_registered_release_source(**changes))

    census = AUDITOR.audit(tmp_path)

    assert census["protected_count"] == 0
    assert census["blocker_count"] == 2


@pytest.mark.parametrize(
    "changes",
    [
        {"boundary_constructor": "LocalOSProtectionBoundary()"},
        {"boundary_constructor": "LocalOSProtectionBoundary(**BOUNDARY_KWARGS)"},
        {"custody_insecure": "False"},
        {"release_insecure": "False"},
    ],
    ids=("missing-boundary-fields", "dynamic-boundary-kwargs", "custody-opt-out", "release-opt-out"),
)
def test_malformed_protection_constructors_never_earn_coverage(
    tmp_path: Path,
    changes: dict[str, str],
) -> None:
    _write(tmp_path, "malformed.py", _strict_registered_release_source(**changes))

    census = AUDITOR.audit(tmp_path)

    assert census["protected_count"] == 0
    assert census["blocker_count"] == 2


@pytest.mark.parametrize(
    "required_fragment",
    [
        '        purpose="fixture",\n',
        '            release_context_sha256="0" * 64,\n',
        '            star=star,\n',
    ],
    ids=("admission-purpose", "handoff-context", "release-star"),
)
def test_incomplete_boundary_calls_never_earn_coverage(
    tmp_path: Path,
    required_fragment: str,
) -> None:
    source = _strict_registered_release_source()
    assert source.count(required_fragment) == 1
    _write(tmp_path, "incomplete.py", source.replace(required_fragment, ""))

    census = AUDITOR.audit(tmp_path)

    assert census["protected_count"] == 0
    assert census["blocker_count"] == 2


@pytest.mark.parametrize(
    "bypass_source",
    [
        "def bypass(payload):\n    return shell_capability(payload)",
        "shell_alias = shell_capability\n\ndef bypass(payload):\n    return shell_alias(payload)",
    ],
    ids=("direct-call", "aliased-call"),
)
def test_registered_handler_reference_outside_registry_cannot_earn_protection(
    tmp_path: Path,
    bypass_source: str,
) -> None:
    _write(
        tmp_path,
        "registered_release_bypass.py",
        f'''
from aureon.plumber.os_protection import AdmittedHNC, LocalOSProtectionBoundary
from aureon.plumber.release_boundary_v02 import LocalDevelopmentReleaseBoundaryV02
from aureon.plumber.star_custody_v02 import (
    LocalDevelopmentStarCustodyV02,
    RegisteredCapabilityV02,
)
from flask import Flask
import subprocess

app = Flask(__name__)

def shell_capability(payload):
    return {{"status": subprocess.run(["echo", "registered"]).returncode}}

{bypass_source}

CAPABILITY = RegisteredCapabilityV02(
    capability_id="shell:test",
    measurement_sha256="1" * 64,
    policy_measurement_sha256="2" * 64,
    result_schema={{"status": "bool"}},
    handler=shell_capability,
)
CUSTODY = LocalDevelopmentStarCustodyV02(
    allow_insecure_same_process=True,
    source_authority=source_authority,
    source_private_key=source_private_key,
    state_store=state_store,
    authorization_trust=authorization_trust,
    capabilities={{"shell:test": CAPABILITY}},
)
RELEASE = LocalDevelopmentReleaseBoundaryV02(
    allow_insecure_same_process=True,
    state_store=state_store,
    epas_store=epas_store,
    custody=CUSTODY,
    recipient_verifier=recipient_verifier,
    star_trust=star_trust,
    release_evidence_trust=release_evidence_trust,
    authorization_trust=authorization_trust,
    receipt_authority=receipt_authority,
    receipt_private_key=receipt_private_key,
    capability_policies={{"shell:test": POLICY}},
    live_binding_probe=live_binding_probe,
    continuity_state_probe=continuity_state_probe,
    evidence_expectations_probe=evidence_expectations_probe,
)

@app.post("/command")
def route(payload):
    boundary = LocalOSProtectionBoundary(
        boundary_id="fixture",
        master_key_provider=lambda: b"fixture-key-material-that-is-long-enough",
    )
    outcome = boundary.admit_external(
        payload,
        source_id="fixture",
        ingress_kind="test",
        purpose="fixture",
    )
    if not isinstance(outcome, AdmittedHNC):
        raise RuntimeError("HOLD")
    packet = boundary.protect_for_magic_star(
        outcome.handle,
        custody=CUSTODY,
        release_context_sha256="0" * 64,
    )
    return RELEASE.release(
        packet,
        session_id="fixture",
        challenge=challenge,
        recipient_proof=recipient_proof,
        temporal_commitment="3" * 64,
        observer_commitment="4" * 64,
        expected_channel_binding_sha256="5" * 64,
        expected_live_binding_sha256="6" * 64,
        expected_runtime_measurement_sha256="7" * 64,
        star=star,
        release_evidence=release_evidence,
        authorization_chain=authorization_chain,
        capability_id="shell:test",
    )
''',
    )

    census = AUDITOR.audit(tmp_path)

    assert census["protected_count"] == 0
    assert census["blocker_count"] == 2
    assert {item["category"] for item in census["findings"]} == {
        "http-server-ingress",
        "subprocess-shell",
    }
    assert all(item["classification"] == AUDITOR.BLOCKER for item in census["findings"])


def test_v03_contract_import_and_construction_earn_zero_coverage(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        "contract_only.py",
        '''
from aureon.plumber.production_release_broker_v03 import ProductionReleaseBrokerV03

def construct(verifier, ledger, executor, receipt_signer):
    return ProductionReleaseBrokerV03(
        verifier=verifier,
        ledger=ledger,
        executor=executor,
        receipt_signer=receipt_signer,
    )
''',
    )

    census = AUDITOR.audit(tmp_path)

    assert census["detected_count"] == 0
    assert census["protected_count"] == 0
    assert census["blocker_count"] == 0


def test_v03_executor_dispatch_is_exactly_one_never_protected_blocker(
    tmp_path: Path,
) -> None:
    relative = "aureon/plumber/production_release_broker_v03.py"
    source = (ROOT / relative).read_text(encoding="utf-8")
    _write(tmp_path, relative, source)

    census = AUDITOR.audit(tmp_path)
    dispatches = [
        item
        for item in census["findings"]
        if item["category"] == "interprocess-capability-dispatch"
    ]

    assert len(dispatches) == 1
    assert dispatches[0]["scope"] == "ProductionReleaseBrokerV03.execute_release"
    assert dispatches[0]["operation"] == (
        "production-release-broker-v03-executor-dispatch"
    )
    assert dispatches[0]["classification"] == AUDITOR.BLOCKER
    assert dispatches[0]["evidence"] == ()
    assert census["protected_count"] == 0


@pytest.mark.parametrize(
    "missing_step",
    ["construction", "admission", "guard", "handoff"],
)
def test_incomplete_boundary_sequence_remains_a_blocker(
    tmp_path: Path,
    missing_step: str,
) -> None:
    construction = (
        "boundary = LocalOSProtectionBoundary(boundary_id='fixture', "
        "master_key_provider=lambda: b'fixture-key-material-that-is-long-enough')"
    )
    admission = (
        "outcome = boundary.admit_external(payload, source_id='fixture', "
        "ingress_kind='test', purpose='fixture')"
    )
    guard_open = "if isinstance(outcome, AdmittedHNC):"
    handoff = (
        "boundary.protect_for_magic_star(outcome.handle, custody=object(), "
        "release_context_sha256='0' * 64)"
    )
    if missing_step == "construction":
        construction = "boundary = supplied_boundary"
    if missing_step == "admission":
        admission = "outcome = supplied_outcome"
    if missing_step == "guard":
        guard_open = "if True:"
    if missing_step == "handoff":
        handoff = "pass"
    source = f'''
from aureon.plumber.os_protection import AdmittedHNC, LocalOSProtectionBoundary
import subprocess

def unsafe(payload, supplied_boundary=None, supplied_outcome=None):
    {construction}
    {admission}
    {guard_open}
        {handoff}
        return subprocess.run(["echo", "unsafe"])
    return None
'''
    _write(tmp_path, f"missing_{missing_step}.py", source)

    findings = _findings(tmp_path)

    assert len(findings) == 1
    assert findings[0]["classification"] == AUDITOR.BLOCKER


def test_explicit_false_gate_is_reported_separately(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "disabled.py",
        '''
import subprocess

def disabled():
    if False:
        subprocess.run(["echo", "unreachable"])
''',
    )

    findings = _findings(tmp_path)

    assert len(findings) == 1
    assert findings[0]["classification"] == AUDITOR.EXPLICIT_HOLD
    assert findings[0]["evidence"] == ("statically-unreachable-or-explicit-hold",)


@pytest.mark.parametrize(
    "source",
    [
        '''
import subprocess
LIVE_EXECUTION_ENABLED = False
LIVE_EXECUTION_ENABLED = True
if LIVE_EXECUTION_ENABLED:
    subprocess.run(["echo", "reachable"])
''',
        '''
import subprocess
LIVE_EXECUTION_ENABLED = False
def route(LIVE_EXECUTION_ENABLED):
    if LIVE_EXECUTION_ENABLED:
        subprocess.run(["echo", "caller-controlled"])
''',
    ],
    ids=("reassigned", "parameter-shadowed"),
)
def test_mutable_false_names_never_prove_an_explicit_hold(
    tmp_path: Path,
    source: str,
) -> None:
    _write(tmp_path, "mutable_hold.py", source)

    findings = _findings(tmp_path)

    assert len(findings) == 1
    assert findings[0]["classification"] == AUDITOR.BLOCKER


def test_flask_subclass_alias_and_factory_routes_are_detected(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "flask_subclass_factory.py",
        '''
try:
    from flask import Flask as ImportedFlask
except Exception:
    ImportedFlask = None

OptionalFlaskBase = ImportedFlask if ImportedFlask is not None else object

class HardenedApp(OptionalFlaskBase):
    pass

def create_app():
    local_app = HardenedApp(__name__)

    @local_app.route("/inside")
    def inside():
        return "inside"

    return local_app

returned_app = create_app()

@returned_app.post("/outside")
def outside():
    return "outside"
''',
    )

    findings = _findings(tmp_path)

    assert len(findings) == 2
    assert {item["operation"] for item in findings} == {
        "http-route-post",
        "http-route-route",
    }
    assert all(item["category"] == "http-server-ingress" for item in findings)
    assert all(item["classification"] == AUDITOR.BLOCKER for item in findings)


def test_flask_like_names_and_factory_annotation_do_not_forge_ingress(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        "fake_flask_names.py",
        '''
class DomainRouter:
    def route(self, _path):
        return lambda function: function

class VaultUIFlask(DomainRouter):
    pass

def create_app() -> "Flask":
    return VaultUIFlask()

app = create_app()

@app.route("/domain-only")
def domain_only():
    return "not-http"
''',
    )

    assert _findings(tmp_path) == []


def test_factory_must_return_the_proven_flask_instance(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "unused_flask_factory.py",
        '''
from flask import Flask

class DomainRouter:
    def route(self, _path):
        return lambda function: function

def create_app():
    unused = Flask(__name__)
    return DomainRouter()

app = create_app()

@app.route("/domain-only")
def domain_only():
    return "not-http"
''',
    )

    assert _findings(tmp_path) == []


def test_inferred_flask_receiver_is_lexically_shadow_safe(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "shadowed_flask_receiver.py",
        '''
from flask import Flask as ImportedFlask

class HardenedApp(ImportedFlask):
    pass

class DomainRouter:
    def route(self, _path):
        return lambda function: function

def create_app():
    app = HardenedApp(__name__)

    @app.route("/real")
    def real_route():
        return "real"

    def unrelated_scope():
        app = DomainRouter()

        @app.route("/domain-only")
        def domain_only():
            return "not-http"

        return domain_only

    return app
''',
    )

    findings = _findings(tmp_path)

    assert len(findings) == 1
    assert findings[0]["operation"] == "http-route-route"
    assert findings[0]["scope"] == "create_app.real_route"


def test_python_inventory_covers_every_requested_boundary_family(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "families.py",
        '''
import os
import pickle
import subprocess
from pathlib import Path
from flask import Flask

app = Flask(__name__)
bridge = LocalActionBridge()

@app.post("/command")
def command(payload):
    subprocess.Popen(["echo", "x"])
    eval(payload)
    pickle.loads(payload)
    Path("state.json").write_text(payload)
    Path(".env").write_text(payload)
    os.environ["API_TOKEN"] = payload
    bridge.execute(payload)
    client.create_order(symbol="BTCUSD")
''',
    )

    findings = _findings(tmp_path)
    categories = {item["category"] for item in findings}

    assert {
        "http-server-ingress",
        "subprocess-shell",
        "dynamic-code-execution",
        "unsafe-deserialization",
        "filesystem-mutation",
        "credential-config-write",
        "local-action-bridge",
        "economic-mutation",
    } <= categories
    assert all(item["classification"] == AUDITOR.BLOCKER for item in findings)


def test_typescript_comments_strings_and_imports_do_not_forge_protection(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        "hostile.ts",
        '''
import { AdmittedHNC, LocalOSProtectionBoundary } from "aureon/plumber/os_protection";
const fake = "admitExternal protectForMagicStar LocalOSProtectionBoundary";
// boundary.admitExternal(payload); boundary.protectForMagicStar(outcome.handle);
app.post("/command", handler);
eval(userCode);
fs.writeFile(target, payload, callback);
''',
    )

    findings = _findings(tmp_path)

    assert {item["category"] for item in findings} == {
        "http-server-ingress",
        "dynamic-code-execution",
        "filesystem-mutation",
    }
    assert all(item["classification"] == AUDITOR.BLOCKER for item in findings)


def test_fingerprints_are_line_independent(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    source = "import subprocess\ndef unsafe():\n    subprocess.run(['echo'])\n"
    _write(first, "same.py", source)
    _write(second, "same.py", "\n\n" + source)

    first_fingerprints = [item["fingerprint"] for item in _findings(first)]
    second_fingerprints = [item["fingerprint"] for item in _findings(second)]

    assert first_fingerprints == second_fingerprints


def test_parse_errors_are_explicit_and_prevent_certification(tmp_path: Path) -> None:
    _write(tmp_path, "broken.py", "def broken(:\n    pass\n")

    census = AUDITOR.audit(tmp_path)

    assert census["parse_errors"] == [
        {
            "file": "broken.py",
            "language": "python",
            "line": 1,
            "error": "SyntaxError:invalid syntax",
        }
    ]
    assert census["certified_full_os_protection"] is False


@pytest.fixture(scope="module")
def repository_census() -> dict[str, Any]:
    return AUDITOR.audit(ROOT)


def test_repository_census_is_exact_internally_and_truthfully_blocked(
    repository_census: dict[str, Any],
) -> None:
    assert repository_census["source_files_scanned"] > 4_000
    assert repository_census["detected_count"] == repository_census["classified_count"]
    assert repository_census["detected_count"] == sum(
        repository_census["counts_by_classification"].values()
    )
    assert repository_census["detected_count"] == sum(
        repository_census["counts_by_category"].values()
    )
    assert repository_census["blocker_count"] == len(repository_census["blockers"])
    assert repository_census["blocker_count"] > 0
    assert repository_census["certified_full_os_protection"] is False
    fingerprints = [item["fingerprint"] for item in repository_census["findings"]]
    assert len(fingerprints) == len(set(fingerprints))
    assert len(repository_census["inventory_sha256"]) == 64


def test_unknown_typescript_boundary_never_defaults_to_protected(
    repository_census: dict[str, Any],
) -> None:
    typescript = [
        item
        for item in repository_census["findings"]
        if item["language"] == "typescript"
    ]
    assert typescript
    assert all(item["classification"] != AUDITOR.PROTECTED for item in typescript)
