"""HNC harmonic packet encryption and breaker checks.

This module gives Aureon a packet format that the HNC layer can inspect before
decoding: geometry, Auris node alignment, intent, and packet fingerprints are
authenticated with the payload. The secrecy carrier is AES-GCM with HKDF-SHA256
so the packet can be break-tested without putting credentials at risk.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any, Mapping

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from aureon.core.hnc_params import HNCParams, load_params
from aureon.harmonic.hnc_symbolic_route_seal import (
    build_symbolic_route_seal,
    symbolic_route_public_summary,
    validate_symbolic_route_seal,
)


PACKET_MAGIC = "AUREON-HNC-QP"
PACKET_SCHEMA_VERSION = 1
ENV_PACKET_PREFIX = "hncqp1:"
MASTER_KEY_ENV = "AUREON_HNC_PACKET_MASTER_KEY"
LEGACY_MASTER_KEY_ENV = "HNC_PACKET_MASTER_KEY"
MIN_MASTER_KEY_BYTES = 16

DEFAULT_AURIS_NODES = (
    {"name": "tiger", "frequency_hz": 186.0, "texture": "volatility"},
    {"name": "falcon", "frequency_hz": 210.0, "texture": "momentum"},
    {"name": "hummingbird", "frequency_hz": 324.0, "texture": "frequency"},
    {"name": "dolphin", "frequency_hz": 432.0, "texture": "liquidity"},
    {"name": "deer", "frequency_hz": 396.0, "texture": "stability"},
    {"name": "owl", "frequency_hz": 528.0, "texture": "pattern"},
    {"name": "panda", "frequency_hz": 639.0, "texture": "harmony"},
    {"name": "cargoship", "frequency_hz": 174.0, "texture": "volume"},
    {"name": "clownfish", "frequency_hz": 285.0, "texture": "resilience"},
)

DEFAULT_GEOMETRY = {
    "name": "metatron_phi_auris_9_node_lattice",
    "sha_alias": "sha_246_operator_phrase_mapped_to_sha_256",
    "phi": 1.6180339887,
    "schumann_anchor_hz": 7.83,
    "profit_anchor_hz": 188.0,
    "coherence_anchor_hz": 741.0,
    "unity_anchor_hz": 963.0,
    "auris_nodes": [dict(node) for node in DEFAULT_AURIS_NODES],
}

DEFAULT_HARMONIC_SLITS = (
    "seer_future_wave",
    "lyra_affect_wave",
    "king_accounting_truth",
    "auris_9_node_consensus",
    "hnc_master_equation",
)

SWARM_MODE_TWO_WAY = "hnc_swarm_two_way_locknotes_v1"


class HNCPacketError(ValueError):
    """Raised when an HNC packet cannot be validated or decoded."""


@dataclass(frozen=True)
class HNCDecodedPacket:
    plaintext: bytes
    packet: dict[str, Any]
    decode_report: dict[str, Any]

    def text(self) -> str:
        return self.plaintext.decode("utf-8")


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("ascii"))


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def sha256_hex(value: bytes | str | Mapping[str, Any]) -> str:
    if isinstance(value, bytes):
        data = value
    elif isinstance(value, str):
        data = value.encode("utf-8")
    else:
        data = canonical_json_bytes(value)
    return hashlib.sha256(data).hexdigest()


def _normalise_master_key(master_key: bytes | str) -> bytes:
    if isinstance(master_key, bytes):
        key_bytes = master_key
    else:
        raw = str(master_key or "").strip()
        if raw.startswith(ENV_PACKET_PREFIX):
            raise HNCPacketError("master_key_must_not_be_an_hnc_packet")
        try:
            key_bytes = _b64url_decode(raw)
            if len(key_bytes) < MIN_MASTER_KEY_BYTES:
                key_bytes = raw.encode("utf-8")
        except Exception:
            key_bytes = raw.encode("utf-8")
    if len(key_bytes) < MIN_MASTER_KEY_BYTES:
        raise HNCPacketError("master_key_too_short_minimum_16_bytes")
    return key_bytes


def packet_master_key_from_env(environ: Mapping[str, str] | None = None) -> str:
    env = os.environ if environ is None else environ
    return str(env.get(MASTER_KEY_ENV) or env.get(LEGACY_MASTER_KEY_ENV) or "").strip()


def build_hnc_alignment_context(
    *,
    purpose: str,
    hnc_params: HNCParams | None = None,
    geometry: Mapping[str, Any] | None = None,
    operator_aad: Mapping[str, Any] | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    params = hnc_params or load_params()
    route_seal = build_symbolic_route_seal(
        purpose=purpose,
        operator_aad=operator_aad,
        hnc_context=extra,
    )
    context = {
        "purpose": purpose,
        "geometry": dict(geometry or DEFAULT_GEOMETRY),
        "symbolic_route_seal": route_seal,
        "hnc_params": {
            "alpha": params.alpha,
            "g": params.g,
            "beta": params.beta,
            "tau": params.tau,
            "delta_t": params.delta_t,
            "fitted_at": params.fitted_at,
            "fitted_from": params.fitted_from,
            "r_squared": params.r_squared,
        },
        "packet_contract": {
            "decode_requires_hnc_alignment": True,
            "decode_requires_authentic_geometry": True,
            "decode_requires_packet_integrity": True,
            "plaintext_never_returned_in_status": True,
        },
    }
    if extra:
        context["extra"] = dict(extra)
    context["hnc_alignment_sha256"] = sha256_hex(
        {
            "purpose": context["purpose"],
            "geometry": context["geometry"],
            "symbolic_route_seal": context["symbolic_route_seal"],
            "hnc_params": context["hnc_params"],
            "packet_contract": context["packet_contract"],
            "extra": context.get("extra", {}),
        }
    )
    return context


def _derive_packet_key(master_key: bytes | str, metadata: Mapping[str, Any]) -> bytes:
    key_material = _normalise_master_key(master_key)
    salt = hashlib.sha256(
        canonical_json_bytes(
            {
                "magic": PACKET_MAGIC,
                "schema_version": PACKET_SCHEMA_VERSION,
                "purpose": metadata.get("purpose"),
                "hnc_alignment_sha256": metadata.get("hnc_alignment_sha256"),
                "geometry_name": (metadata.get("hnc_alignment") or {}).get("geometry", {}).get("name"),
            }
        )
    ).digest()
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=b"aureon-hnc-quantum-packet-v1",
    ).derive(key_material)


def _derive_agent_wrap_key(agent_secret: bytes | str, metadata: Mapping[str, Any], *, agent_id: str, pair_id: str) -> bytes:
    key_material = _normalise_master_key(agent_secret)
    salt = hashlib.sha256(
        canonical_json_bytes(
            {
                "magic": PACKET_MAGIC,
                "schema_version": PACKET_SCHEMA_VERSION,
                "swarm_mode": SWARM_MODE_TWO_WAY,
                "purpose": metadata.get("purpose"),
                "hnc_alignment_sha256": metadata.get("hnc_alignment_sha256"),
                "agent_id": agent_id,
                "pair_id": pair_id,
            }
        )
    ).digest()
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=b"aureon-hnc-swarm-locknote-v1",
    ).derive(key_material)


def _xor_bytes(left: bytes, right: bytes) -> bytes:
    if len(left) != len(right):
        raise HNCPacketError("xor_share_length_mismatch")
    return bytes(a ^ b for a, b in zip(left, right))


def _swarm_locknote_aad(metadata: Mapping[str, Any], *, agent_id: str, pair_id: str) -> bytes:
    return canonical_json_bytes(
        {
            "magic": PACKET_MAGIC,
            "schema_version": PACKET_SCHEMA_VERSION,
            "swarm_mode": SWARM_MODE_TWO_WAY,
            "purpose": metadata.get("purpose"),
            "hnc_alignment_sha256": metadata.get("hnc_alignment_sha256"),
            "agent_id": agent_id,
            "pair_id": pair_id,
        }
    )


def _packet_aad(metadata: Mapping[str, Any], operator_aad: Mapping[str, Any] | None) -> bytes:
    return canonical_json_bytes(
        {
            "magic": PACKET_MAGIC,
            "schema_version": PACKET_SCHEMA_VERSION,
            "metadata": metadata,
            "operator_aad": dict(operator_aad or {}),
        }
    )


def _without_packet_hash(packet: Mapping[str, Any]) -> dict[str, Any]:
    clean = dict(packet)
    clean.pop("packet_sha256", None)
    return clean


def build_hnc_quantum_packet(
    plaintext: bytes | str,
    master_key: bytes | str,
    *,
    purpose: str = "aureon.hnc.packet",
    operator_aad: Mapping[str, Any] | None = None,
    hnc_context: Mapping[str, Any] | None = None,
    geometry: Mapping[str, Any] | None = None,
    nonce: bytes | None = None,
) -> dict[str, Any]:
    payload = plaintext.encode("utf-8") if isinstance(plaintext, str) else bytes(plaintext)
    alignment = build_hnc_alignment_context(
        purpose=purpose,
        geometry=geometry,
        operator_aad=operator_aad,
        extra=hnc_context,
    )
    metadata = {
        "schema_version": PACKET_SCHEMA_VERSION,
        "algorithm": "AES-256-GCM",
        "kdf": "HKDF-SHA256",
        "digest": "SHA-256",
        "operator_packet_name": "HNC quantum harmonic packet",
        "purpose": purpose,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "plaintext_size_bytes": len(payload),
        "hnc_alignment": alignment,
        "hnc_alignment_sha256": alignment["hnc_alignment_sha256"],
    }
    packet_nonce = nonce or os.urandom(12)
    if len(packet_nonce) != 12:
        raise HNCPacketError("aes_gcm_nonce_must_be_12_bytes")
    packet_key = _derive_packet_key(master_key, metadata)
    aad = _packet_aad(metadata, operator_aad)
    ciphertext = AESGCM(packet_key).encrypt(packet_nonce, payload, aad)
    packet = {
        "magic": PACKET_MAGIC,
        "schema_version": PACKET_SCHEMA_VERSION,
        "metadata": metadata,
        "operator_aad": dict(operator_aad or {}),
        "nonce_b64": _b64url_encode(packet_nonce),
        "ciphertext_b64": _b64url_encode(ciphertext),
    }
    packet["packet_sha256"] = sha256_hex(_without_packet_hash(packet))
    return packet


def validate_hnc_packet_contract(packet: Mapping[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    metadata = packet.get("metadata") if isinstance(packet.get("metadata"), dict) else {}
    alignment = metadata.get("hnc_alignment") if isinstance(metadata.get("hnc_alignment"), dict) else {}
    geometry = alignment.get("geometry") if isinstance(alignment.get("geometry"), dict) else {}
    symbolic_route_seal = alignment.get("symbolic_route_seal")
    nodes = geometry.get("auris_nodes") if isinstance(geometry.get("auris_nodes"), list) else []
    expected_hash = metadata.get("hnc_alignment_sha256")
    computed_alignment_hash = sha256_hex(
        {
            "purpose": alignment.get("purpose"),
            "geometry": geometry,
            "symbolic_route_seal": symbolic_route_seal,
            "hnc_params": alignment.get("hnc_params"),
            "packet_contract": alignment.get("packet_contract"),
            "extra": alignment.get("extra", {}),
        }
    )
    computed_packet_hash = sha256_hex(_without_packet_hash(packet))

    if packet.get("magic") != PACKET_MAGIC:
        reasons.append("bad_magic")
    if packet.get("schema_version") != PACKET_SCHEMA_VERSION:
        reasons.append("unsupported_schema_version")
    if metadata.get("algorithm") != "AES-256-GCM":
        reasons.append("unsupported_algorithm")
    if metadata.get("kdf") != "HKDF-SHA256":
        reasons.append("unsupported_kdf")
    if metadata.get("digest") != "SHA-256":
        reasons.append("unsupported_digest")
    if expected_hash != computed_alignment_hash:
        reasons.append("hnc_alignment_hash_mismatch")
    if packet.get("packet_sha256") != computed_packet_hash:
        reasons.append("packet_hash_mismatch")
    if len(nodes) != 9:
        reasons.append("auris_9_node_lattice_missing")
    symbolic_route_validation = None
    if symbolic_route_seal is not None:
        symbolic_route_validation = validate_symbolic_route_seal(symbolic_route_seal)
        if not symbolic_route_validation["valid"]:
            reasons.append("symbolic_route_seal_mismatch")
    if not packet.get("nonce_b64") or not packet.get("ciphertext_b64"):
        reasons.append("missing_cipher_material")

    return {
        "valid": not reasons,
        "reasons": reasons,
        "packet_sha256": packet.get("packet_sha256"),
        "computed_packet_sha256": computed_packet_hash,
        "hnc_alignment_sha256": expected_hash,
        "computed_hnc_alignment_sha256": computed_alignment_hash,
        "auris_node_count": len(nodes),
        "symbolic_route": symbolic_route_validation,
        "purpose": metadata.get("purpose"),
    }


def decode_hnc_quantum_packet(
    packet: Mapping[str, Any],
    master_key: bytes | str,
    *,
    expected_purpose: str | None = None,
    expected_operator_aad: Mapping[str, Any] | None = None,
) -> HNCDecodedPacket:
    validation = validate_hnc_packet_contract(packet)
    if not validation["valid"]:
        raise HNCPacketError("packet_contract_failed:" + ",".join(validation["reasons"]))
    metadata = packet["metadata"]
    if expected_purpose and metadata.get("purpose") != expected_purpose:
        raise HNCPacketError("unexpected_packet_purpose")
    operator_aad = dict(packet.get("operator_aad") or {})
    if expected_operator_aad is not None and operator_aad != dict(expected_operator_aad):
        raise HNCPacketError("operator_aad_mismatch")
    try:
        nonce = _b64url_decode(str(packet["nonce_b64"]))
        ciphertext = _b64url_decode(str(packet["ciphertext_b64"]))
        packet_key = _derive_packet_key(master_key, metadata)
        plaintext = AESGCM(packet_key).decrypt(nonce, ciphertext, _packet_aad(metadata, operator_aad))
    except InvalidTag as exc:
        raise HNCPacketError("packet_authentication_failed") from exc
    except Exception as exc:
        raise HNCPacketError(f"packet_decode_failed:{type(exc).__name__}") from exc

    decode_report = {
        "decoded": True,
        "decoded_at": datetime.now(timezone.utc).isoformat(),
        "purpose": metadata.get("purpose"),
        "plaintext_size_bytes": len(plaintext),
        "plaintext_sha256_runtime_only": sha256_hex(plaintext),
        "packet_contract": validation,
        "secret_policy": "plaintext_returned_to_caller_only_not_status",
    }
    return HNCDecodedPacket(plaintext=plaintext, packet=dict(packet), decode_report=decode_report)


def build_hnc_swarm_packet(
    plaintext: bytes | str,
    agent_secrets: Mapping[str, bytes | str],
    *,
    purpose: str = "aureon.hnc.swarm.packet",
    operator_aad: Mapping[str, Any] | None = None,
    hnc_context: Mapping[str, Any] | None = None,
    geometry: Mapping[str, Any] | None = None,
    nonce: bytes | None = None,
) -> dict[str, Any]:
    """Build a packet that requires two independent agent locknotes to decode.

    Each agent receives only an encrypted half-share. The payload key is rebuilt
    from a pair of shares, so a single agent secret cannot decrypt the packet.
    For a small swarm this creates every valid two-agent pair.
    """

    agents = {str(agent_id).strip(): secret for agent_id, secret in agent_secrets.items() if str(agent_id).strip()}
    if len(agents) < 2:
        raise HNCPacketError("swarm_requires_at_least_two_agents")
    payload = plaintext.encode("utf-8") if isinstance(plaintext, str) else bytes(plaintext)
    alignment = build_hnc_alignment_context(
        purpose=purpose,
        geometry=geometry,
        operator_aad=operator_aad,
        extra={"swarm_mode": SWARM_MODE_TWO_WAY, **dict(hnc_context or {})},
    )
    metadata = {
        "schema_version": PACKET_SCHEMA_VERSION,
        "algorithm": "AES-256-GCM",
        "kdf": "HKDF-SHA256",
        "digest": "SHA-256",
        "operator_packet_name": "HNC swarm two-way harmonic locknote packet",
        "purpose": purpose,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "plaintext_size_bytes": len(payload),
        "hnc_alignment": alignment,
        "hnc_alignment_sha256": alignment["hnc_alignment_sha256"],
        "swarm_security": {
            "mode": SWARM_MODE_TWO_WAY,
            "threshold_agents": 2,
            "agent_count": len(agents),
            "pair_count": len(list(combinations(sorted(agents), 2))),
            "single_agent_can_decode": False,
            "locknote_policy": "any_valid_two_agent_pair_can_reconstruct_the_payload_key",
        },
    }
    data_key = os.urandom(32)
    packet_nonce = nonce or os.urandom(12)
    if len(packet_nonce) != 12:
        raise HNCPacketError("aes_gcm_nonce_must_be_12_bytes")
    ciphertext = AESGCM(data_key).encrypt(packet_nonce, payload, _packet_aad(metadata, operator_aad))
    locknotes: list[dict[str, Any]] = []
    for agent_a, agent_b in combinations(sorted(agents), 2):
        pair_id = sha256_hex({"agents": [agent_a, agent_b], "purpose": purpose})[:24]
        share_a = os.urandom(32)
        share_b = _xor_bytes(data_key, share_a)
        for agent_id, share in ((agent_a, share_a), (agent_b, share_b)):
            note_nonce = os.urandom(12)
            wrap_key = _derive_agent_wrap_key(agents[agent_id], metadata, agent_id=agent_id, pair_id=pair_id)
            encrypted_share = AESGCM(wrap_key).encrypt(
                note_nonce,
                share,
                _swarm_locknote_aad(metadata, agent_id=agent_id, pair_id=pair_id),
            )
            note = {
                "pair_id": pair_id,
                "agent_id": agent_id,
                "agent_slot_sha256": sha256_hex(agent_id),
                "nonce_b64": _b64url_encode(note_nonce),
                "encrypted_share_b64": _b64url_encode(encrypted_share),
                "share_size_bytes": len(share),
                "threshold_role": "two_way_locknote_half",
            }
            note["locknote_sha256"] = sha256_hex(note)
            locknotes.append(note)
    packet = {
        "magic": PACKET_MAGIC,
        "schema_version": PACKET_SCHEMA_VERSION,
        "metadata": metadata,
        "operator_aad": dict(operator_aad or {}),
        "nonce_b64": _b64url_encode(packet_nonce),
        "ciphertext_b64": _b64url_encode(ciphertext),
        "swarm_locknotes": locknotes,
    }
    packet["packet_sha256"] = sha256_hex(_without_packet_hash(packet))
    return packet


def _decrypt_swarm_share(
    note: Mapping[str, Any],
    metadata: Mapping[str, Any],
    agent_secret: bytes | str,
) -> bytes:
    agent_id = str(note.get("agent_id") or "")
    pair_id = str(note.get("pair_id") or "")
    expected_note_hash = note.get("locknote_sha256")
    clean_note = dict(note)
    clean_note.pop("locknote_sha256", None)
    if expected_note_hash != sha256_hex(clean_note):
        raise HNCPacketError("swarm_locknote_hash_mismatch")
    wrap_key = _derive_agent_wrap_key(agent_secret, metadata, agent_id=agent_id, pair_id=pair_id)
    try:
        return AESGCM(wrap_key).decrypt(
            _b64url_decode(str(note.get("nonce_b64") or "")),
            _b64url_decode(str(note.get("encrypted_share_b64") or "")),
            _swarm_locknote_aad(metadata, agent_id=agent_id, pair_id=pair_id),
        )
    except InvalidTag as exc:
        raise HNCPacketError("swarm_locknote_authentication_failed") from exc


def decode_hnc_swarm_packet(
    packet: Mapping[str, Any],
    agent_secrets: Mapping[str, bytes | str],
    *,
    expected_purpose: str | None = None,
    expected_operator_aad: Mapping[str, Any] | None = None,
) -> HNCDecodedPacket:
    validation = validate_hnc_packet_contract(packet)
    if not validation["valid"]:
        raise HNCPacketError("packet_contract_failed:" + ",".join(validation["reasons"]))
    metadata = packet["metadata"]
    swarm = metadata.get("swarm_security") if isinstance(metadata.get("swarm_security"), dict) else {}
    if swarm.get("mode") != SWARM_MODE_TWO_WAY:
        raise HNCPacketError("not_a_swarm_two_way_packet")
    if expected_purpose and metadata.get("purpose") != expected_purpose:
        raise HNCPacketError("unexpected_packet_purpose")
    operator_aad = dict(packet.get("operator_aad") or {})
    if expected_operator_aad is not None and operator_aad != dict(expected_operator_aad):
        raise HNCPacketError("operator_aad_mismatch")
    notes = packet.get("swarm_locknotes")
    if not isinstance(notes, list):
        raise HNCPacketError("swarm_locknotes_missing")
    available = {str(agent_id): secret for agent_id, secret in agent_secrets.items()}
    if len(available) < 2:
        raise HNCPacketError("two_agent_locknotes_required")
    notes_by_pair: dict[str, list[Mapping[str, Any]]] = {}
    for note in notes:
        if isinstance(note, dict):
            notes_by_pair.setdefault(str(note.get("pair_id") or ""), []).append(note)

    failures: list[str] = []
    for pair_id, pair_notes in notes_by_pair.items():
        usable_notes = [note for note in pair_notes if str(note.get("agent_id") or "") in available]
        if len(usable_notes) < 2:
            continue
        for first_index in range(len(usable_notes)):
            for second_index in range(first_index + 1, len(usable_notes)):
                left = usable_notes[first_index]
                right = usable_notes[second_index]
                if left.get("agent_id") == right.get("agent_id"):
                    continue
                try:
                    left_share = _decrypt_swarm_share(left, metadata, available[str(left["agent_id"])])
                    right_share = _decrypt_swarm_share(right, metadata, available[str(right["agent_id"])])
                    data_key = _xor_bytes(left_share, right_share)
                    plaintext = AESGCM(data_key).decrypt(
                        _b64url_decode(str(packet["nonce_b64"])),
                        _b64url_decode(str(packet["ciphertext_b64"])),
                        _packet_aad(metadata, operator_aad),
                    )
                    return HNCDecodedPacket(
                        plaintext=plaintext,
                        packet=dict(packet),
                        decode_report={
                            "decoded": True,
                            "decoded_at": datetime.now(timezone.utc).isoformat(),
                            "purpose": metadata.get("purpose"),
                            "swarm_mode": SWARM_MODE_TWO_WAY,
                            "pair_id": pair_id,
                            "agents_used": sorted([str(left["agent_id"]), str(right["agent_id"])]),
                            "single_agent_can_decode": False,
                            "packet_contract": validation,
                            "secret_policy": "plaintext_returned_to_caller_only_not_status",
                        },
                    )
                except (HNCPacketError, InvalidTag) as exc:
                    failures.append(str(exc))
                    continue
    raise HNCPacketError("no_valid_two_agent_locknote_pair:" + ",".join(failures[:3]))


def run_hnc_swarm_breaker_checks(packet: Mapping[str, Any], agent_secrets: Mapping[str, bytes | str]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    try:
        decode_hnc_swarm_packet(packet, agent_secrets)
        checks.append({"name": "valid_two_agent_pair_decode", "passed": True, "result": "decoded"})
    except HNCPacketError as exc:
        checks.append({"name": "valid_two_agent_pair_decode", "passed": False, "result": str(exc)})

    first_agent = next(iter(agent_secrets))
    try:
        decode_hnc_swarm_packet(packet, {first_agent: agent_secrets[first_agent]})
        checks.append({"name": "single_agent_decode_blocked", "passed": False, "result": "single_agent_accepted"})
    except HNCPacketError as exc:
        checks.append({"name": "single_agent_decode_blocked", "passed": True, "result": str(exc)})

    wrong = {agent: "wrong-agent-secret-for-breaker" for agent in agent_secrets}
    try:
        decode_hnc_swarm_packet(packet, wrong)
        checks.append({"name": "wrong_agent_secret_blocked", "passed": False, "result": "wrong_secret_accepted"})
    except HNCPacketError as exc:
        checks.append({"name": "wrong_agent_secret_blocked", "passed": True, "result": str(exc)})

    tampered = copy.deepcopy(dict(packet))
    if tampered.get("swarm_locknotes"):
        note = tampered["swarm_locknotes"][0]
        note["encrypted_share_b64"] = note["encrypted_share_b64"][:-1] + ("A" if note["encrypted_share_b64"][-1] != "A" else "B")
    try:
        decode_hnc_swarm_packet(tampered, agent_secrets)
        checks.append({"name": "locknote_tamper_blocked", "passed": False, "result": "tamper_accepted"})
    except HNCPacketError as exc:
        checks.append({"name": "locknote_tamper_blocked", "passed": True, "result": str(exc)})

    missing = copy.deepcopy(dict(packet))
    if missing.get("swarm_locknotes"):
        missing["swarm_locknotes"] = missing["swarm_locknotes"][:1]
        missing["packet_sha256"] = sha256_hex(_without_packet_hash(missing))
    try:
        decode_hnc_swarm_packet(missing, agent_secrets)
        checks.append({"name": "missing_pair_locknote_blocked", "passed": False, "result": "missing_pair_accepted"})
    except HNCPacketError as exc:
        checks.append({"name": "missing_pair_locknote_blocked", "passed": True, "result": str(exc)})

    return {
        "schema_version": PACKET_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "swarm_mode": SWARM_MODE_TWO_WAY,
        "packet_sha256": packet.get("packet_sha256"),
        "checks": checks,
        "passed": all(check["passed"] for check in checks),
        "secret_policy": "breaker_does_not_emit_plaintext",
    }


def encode_env_packet(value: str, master_key: bytes | str, *, env_key: str) -> str:
    packet = build_hnc_quantum_packet(
        value,
        master_key,
        purpose=f"env:{env_key}",
        operator_aad={"env_key": env_key},
        hnc_context={"domain": "local_env_credentials", "env_key": env_key},
    )
    return ENV_PACKET_PREFIX + _b64url_encode(canonical_json_bytes(packet))


def is_env_packet(value: Any) -> bool:
    return str(value or "").strip().startswith(ENV_PACKET_PREFIX)


def decode_env_packet(token: str, master_key: bytes | str, *, env_key: str) -> str:
    raw = str(token or "").strip()
    if not raw.startswith(ENV_PACKET_PREFIX):
        return raw
    packet = json.loads(_b64url_decode(raw[len(ENV_PACKET_PREFIX) :]).decode("utf-8"))
    decoded = decode_hnc_quantum_packet(
        packet,
        master_key,
        expected_purpose=f"env:{env_key}",
        expected_operator_aad={"env_key": env_key},
    )
    return decoded.text()


def env_packet_summary(token: str) -> dict[str, Any]:
    raw = str(token or "").strip()
    if not raw.startswith(ENV_PACKET_PREFIX):
        return {"encoded": False}
    try:
        packet = json.loads(_b64url_decode(raw[len(ENV_PACKET_PREFIX) :]).decode("utf-8"))
        validation = validate_hnc_packet_contract(packet)
        return {
            "encoded": True,
            "format": ENV_PACKET_PREFIX.rstrip(":"),
            "valid_contract": validation["valid"],
            "purpose": validation["purpose"],
            "packet_sha256": validation["packet_sha256"],
            "hnc_alignment_sha256": validation["hnc_alignment_sha256"],
            "blockers": validation["reasons"],
        }
    except Exception as exc:
        return {"encoded": True, "valid_contract": False, "error": type(exc).__name__}


def packet_public_summary(packet: Mapping[str, Any]) -> dict[str, Any]:
    validation = validate_hnc_packet_contract(packet)
    metadata = packet.get("metadata") if isinstance(packet.get("metadata"), dict) else {}
    alignment = metadata.get("hnc_alignment") if isinstance(metadata.get("hnc_alignment"), dict) else {}
    return {
        "magic": packet.get("magic"),
        "schema_version": packet.get("schema_version"),
        "purpose": metadata.get("purpose"),
        "algorithm": metadata.get("algorithm"),
        "kdf": metadata.get("kdf"),
        "digest": metadata.get("digest"),
        "plaintext_size_bytes": metadata.get("plaintext_size_bytes"),
        "hnc_alignment_sha256": metadata.get("hnc_alignment_sha256"),
        "packet_sha256": packet.get("packet_sha256"),
        "auris_node_count": validation.get("auris_node_count"),
        "valid_contract": validation["valid"],
        "blockers": validation["reasons"],
        "geometry_name": (alignment.get("geometry") or {}).get("name"),
        "symbolic_route": symbolic_route_public_summary(alignment.get("symbolic_route_seal")),
        "secret_policy": "no_plaintext_no_key_material",
    }


def _probability_weights(seed: str, count: int) -> list[float]:
    raw: list[int] = []
    for index in range(count):
        digest = hashlib.sha256(f"{seed}:{index}".encode("utf-8")).digest()
        raw.append(max(1, int.from_bytes(digest[:4], "big")))
    total = float(sum(raw)) or 1.0
    return [round(value / total, 8) for value in raw]


def stream_hnc_probability_fragments(
    packet: Mapping[str, Any],
    *,
    fragment_size: int = 700,
    slit_names: tuple[str, ...] = DEFAULT_HARMONIC_SLITS,
) -> list[dict[str, Any]]:
    """Split an encrypted packet into order-independent HNC probability fragments.

    The fragments expose only transport geometry and packet hashes. The receiver
    must gather every fragment, verify the hashes, reassemble the packet, then
    pass the HNC packet contract before any plaintext can be decoded.
    """

    validation = validate_hnc_packet_contract(packet)
    if not validation["valid"]:
        raise HNCPacketError("packet_contract_failed:" + ",".join(validation["reasons"]))
    if fragment_size < 128:
        raise HNCPacketError("fragment_size_too_small_minimum_128")
    packet_bytes = canonical_json_bytes(packet)
    chunks = [packet_bytes[index : index + fragment_size] for index in range(0, len(packet_bytes), fragment_size)]
    stream_id = sha256_hex(
        {
            "packet_sha256": packet.get("packet_sha256"),
            "chunk_count": len(chunks),
            "slit_names": list(slit_names),
        }
    )
    weights = _probability_weights(stream_id, len(chunks))
    manifest = {
        "schema_version": PACKET_SCHEMA_VERSION,
        "stream_type": "hnc_temporal_probability_stream",
        "stream_id": stream_id,
        "packet_sha256": packet.get("packet_sha256"),
        "fragment_count": len(chunks),
        "packet_bytes_sha256": sha256_hex(packet_bytes),
        "slit_names": list(slit_names),
        "reassembly_rule": "all_fragments_required_then_hnc_contract_decode",
        "plaintext_visible_before_reassembly": False,
    }
    manifest_sha256 = sha256_hex(manifest)
    fragments: list[dict[str, Any]] = []
    for index, chunk in enumerate(chunks):
        slit_name = slit_names[index % len(slit_names)]
        fragments.append(
            {
                "schema_version": PACKET_SCHEMA_VERSION,
                "stream_type": "hnc_temporal_probability_fragment",
                "stream_id": stream_id,
                "manifest_sha256": manifest_sha256,
                "manifest": manifest,
                "fragment_index": index,
                "fragment_count": len(chunks),
                "slit_name": slit_name,
                "probability_weight": weights[index],
                "phase_hint": round((index + 1) / max(1, len(chunks)), 8),
                "chunk_b64": _b64url_encode(chunk),
                "chunk_sha256": sha256_hex(chunk),
                "secret_policy": "ciphertext_fragment_only_no_plaintext",
            }
        )
    return fragments


def reassemble_hnc_probability_fragments(fragments: list[Mapping[str, Any]]) -> dict[str, Any]:
    if not fragments:
        raise HNCPacketError("no_fragments")
    stream_ids = {str(fragment.get("stream_id")) for fragment in fragments}
    if len(stream_ids) != 1:
        raise HNCPacketError("mixed_stream_fragments")
    first = fragments[0]
    manifest = first.get("manifest") if isinstance(first.get("manifest"), dict) else {}
    manifest_hash = sha256_hex(manifest)
    expected_manifest_hash = first.get("manifest_sha256")
    if manifest_hash != expected_manifest_hash:
        raise HNCPacketError("manifest_hash_mismatch")
    expected_count = int(manifest.get("fragment_count") or first.get("fragment_count") or 0)
    if expected_count <= 0:
        raise HNCPacketError("invalid_fragment_count")
    by_index: dict[int, Mapping[str, Any]] = {}
    for fragment in fragments:
        if fragment.get("manifest_sha256") != expected_manifest_hash:
            raise HNCPacketError("fragment_manifest_mismatch")
        index = int(fragment.get("fragment_index"))
        if index in by_index:
            raise HNCPacketError("duplicate_fragment_index")
        by_index[index] = fragment
    if sorted(by_index) != list(range(expected_count)):
        raise HNCPacketError("missing_fragments")

    chunks: list[bytes] = []
    for index in range(expected_count):
        fragment = by_index[index]
        chunk = _b64url_decode(str(fragment.get("chunk_b64") or ""))
        if sha256_hex(chunk) != fragment.get("chunk_sha256"):
            raise HNCPacketError("fragment_chunk_hash_mismatch")
        chunks.append(chunk)
    packet_bytes = b"".join(chunks)
    if sha256_hex(packet_bytes) != manifest.get("packet_bytes_sha256"):
        raise HNCPacketError("packet_bytes_hash_mismatch")
    packet = json.loads(packet_bytes.decode("utf-8"))
    validation = validate_hnc_packet_contract(packet)
    if not validation["valid"]:
        raise HNCPacketError("packet_contract_failed:" + ",".join(validation["reasons"]))
    if packet.get("packet_sha256") != manifest.get("packet_sha256"):
        raise HNCPacketError("packet_sha256_manifest_mismatch")
    return packet


def run_hnc_packet_breaker_checks(packet: Mapping[str, Any], master_key: bytes | str) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def attempt(name: str, mutator) -> None:
        candidate = copy.deepcopy(dict(packet))
        mutator(candidate)
        try:
            decode_hnc_quantum_packet(candidate, master_key)
            checks.append({"name": name, "passed": False, "result": "tamper_accepted"})
        except HNCPacketError as exc:
            checks.append({"name": name, "passed": True, "result": str(exc)})

    attempt("ciphertext_bit_flip", lambda p: p.__setitem__("ciphertext_b64", p["ciphertext_b64"][:-1] + ("A" if p["ciphertext_b64"][-1] != "A" else "B")))
    attempt("geometry_frequency_tamper", lambda p: p["metadata"]["hnc_alignment"]["geometry"].__setitem__("profit_anchor_hz", 189.0))
    attempt("purpose_tamper", lambda p: p["metadata"].__setitem__("purpose", "env:ATTACKER_KEY"))
    attempt("operator_aad_tamper", lambda p: p.__setitem__("operator_aad", {"env_key": "ATTACKER_KEY"}))
    attempt("packet_hash_tamper", lambda p: p.__setitem__("packet_sha256", "0" * 64))

    try:
        fragments = stream_hnc_probability_fragments(packet, fragment_size=256)
        missing = fragments[:-1]
        try:
            reassemble_hnc_probability_fragments(missing)
            checks.append({"name": "temporal_fragment_missing", "passed": False, "result": "missing_fragment_accepted"})
        except HNCPacketError as exc:
            checks.append({"name": "temporal_fragment_missing", "passed": True, "result": str(exc)})
        tampered = copy.deepcopy(fragments)
        tampered[0]["chunk_b64"] = tampered[0]["chunk_b64"][:-1] + ("A" if tampered[0]["chunk_b64"][-1] != "A" else "B")
        try:
            reassemble_hnc_probability_fragments(tampered)
            checks.append({"name": "temporal_fragment_tamper", "passed": False, "result": "tampered_fragment_accepted"})
        except HNCPacketError as exc:
            checks.append({"name": "temporal_fragment_tamper", "passed": True, "result": str(exc)})
    except HNCPacketError as exc:
        checks.append({"name": "temporal_stream_build", "passed": False, "result": str(exc)})

    return {
        "schema_version": PACKET_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "packet_sha256": packet.get("packet_sha256"),
        "checks": checks,
        "passed": all(check["passed"] for check in checks),
        "secret_policy": "breaker_does_not_emit_plaintext",
    }


def write_hnc_packet_evidence(summary: Mapping[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": PACKET_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evidence": dict(summary),
        "secret_policy": "metadata_only_no_values_returned",
    }
    tmp = path.with_suffix(path.suffix + f".tmp-{int(time.time() * 1000)}")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)
    return path


__all__ = [
    "ENV_PACKET_PREFIX",
    "HNCPacketError",
    "HNCDecodedPacket",
    "LEGACY_MASTER_KEY_ENV",
    "MASTER_KEY_ENV",
    "PACKET_MAGIC",
    "build_hnc_alignment_context",
    "build_hnc_quantum_packet",
    "canonical_json_bytes",
    "build_hnc_swarm_packet",
    "decode_env_packet",
    "decode_hnc_quantum_packet",
    "decode_hnc_swarm_packet",
    "encode_env_packet",
    "env_packet_summary",
    "is_env_packet",
    "packet_master_key_from_env",
    "packet_public_summary",
    "reassemble_hnc_probability_fragments",
    "run_hnc_packet_breaker_checks",
    "run_hnc_swarm_breaker_checks",
    "sha256_hex",
    "stream_hnc_probability_fragments",
    "SWARM_MODE_TWO_WAY",
    "validate_hnc_packet_contract",
    "write_hnc_packet_evidence",
]
