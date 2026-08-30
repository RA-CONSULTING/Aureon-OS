from __future__ import annotations

import hashlib
from dataclasses import replace
from typing import Any, Mapping

from aureon.autonomous.aureon_full_stack_release_gate import (
    CANONICAL_STACK_LAYERS,
    LOCAL_ACCEPTANCE,
    REQUIRED_LAYER_CONTROLS,
    FullStackReleaseGate,
    FullStackReleaseRequest,
    build_full_stack_bundle,
    build_layer_evidence,
)

FULL_STACK_NOW = 1_787_100_000.0


class StaticFullStackResolver:
    resolver_id = "tests:trusted-full-stack-resolver"

    def __init__(self, bundle: Mapping[str, Any] | None = None, *, error: bool = False) -> None:
        self.bundle = dict(bundle) if bundle is not None else None
        self.error = error
        self.calls = 0

    def resolve_full_stack_evidence(self, request: FullStackReleaseRequest):
        del request
        self.calls += 1
        if self.error:
            raise RuntimeError("test resolver unavailable")
        return dict(self.bundle) if self.bundle is not None else None


def build_test_full_stack_bundle(
    request: FullStackReleaseRequest,
    *,
    provider_readback: bool = False,
    now: float = FULL_STACK_NOW,
) -> dict[str, Any]:
    kinds = ["offline_contract"]
    if provider_readback:
        kinds.append("provider_readback")
    layers = []
    for layer_id in CANONICAL_STACK_LAYERS:
        provider_ids = [f"provider:{layer_id}:readback"] if provider_readback else []
        source_ids = [f"acceptance:{layer_id}:contract", *provider_ids]
        layers.append(
            build_layer_evidence(
                layer_id=layer_id,
                environment=request.environment,
                scope_digest=request.scope_digest,
                checked_at=now - 10.0,
                expires_at=now + 300.0,
                evidence_kinds=kinds,
                control_ids=list(REQUIRED_LAYER_CONTROLS[layer_id]),
                source_receipt_ids=source_ids,
                provider_readback_receipt_ids=provider_ids,
                summary_digest=hashlib.sha256(layer_id.encode()).hexdigest(),
            )
        )
    return build_full_stack_bundle(
        resolver_id=StaticFullStackResolver.resolver_id,
        request=request,
        issued_at=now - 5.0,
        layers=layers,
    )


def build_test_full_stack_gate(
    *,
    scope_digest: str,
    release_id: str = "self-code:test-release",
    environment: str = "local",
    assurance_level: str = LOCAL_ACCEPTANCE,
    provider_readback: bool = False,
) -> tuple[FullStackReleaseGate, FullStackReleaseRequest, StaticFullStackResolver]:
    request = FullStackReleaseRequest(
        release_id=release_id,
        environment=environment,
        assurance_level=assurance_level,
        scope_digest=scope_digest,
    )
    resolver = StaticFullStackResolver()
    resolver.bundle = build_test_full_stack_bundle(
        request,
        provider_readback=provider_readback,
    )
    gate = FullStackReleaseGate(resolver=resolver, now=lambda: FULL_STACK_NOW)
    return gate, request, resolver


def request_with(request: FullStackReleaseRequest, **changes: Any) -> FullStackReleaseRequest:
    return replace(request, **changes)


__all__ = [
    "FULL_STACK_NOW",
    "StaticFullStackResolver",
    "build_test_full_stack_bundle",
    "build_test_full_stack_gate",
    "request_with",
]
