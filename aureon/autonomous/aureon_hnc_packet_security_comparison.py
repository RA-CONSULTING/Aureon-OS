"""HNC packet security comparison report.

This report compares Aureon's HNC harmonic packet layer with common credential
storage and transport security patterns. It keeps the HNC contract visible while
being explicit about the real security boundary: authenticated encryption and
operator-managed key handling.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aureon.harmonic.hnc_quantum_packet_crypto import (
    MASTER_KEY_ENV,
    build_hnc_quantum_packet,
    build_hnc_swarm_packet,
    packet_public_summary,
    run_hnc_packet_breaker_checks,
    run_hnc_swarm_breaker_checks,
    stream_hnc_probability_fragments,
)
from aureon.harmonic.hnc_symbolic_route_seal import load_symbolic_catalog_manifest

SCHEMA_VERSION = "aureon-hnc-packet-security-comparison-v1"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_JSON = REPO_ROOT / "docs/audits/aureon_hnc_packet_security_comparison.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs/audits/aureon_hnc_packet_security_comparison.md"
DEFAULT_PUBLIC_JSON = REPO_ROOT / "frontend/public/aureon_hnc_packet_security_comparison.json"
HNC_PACKET_EVIDENCE_PATH = REPO_ROOT / "state/aureon_hnc_quantum_packet_last_run.json"

REFERENCES = [
    {
        "title": "NIST SP 800-38D: Galois/Counter Mode",
        "url": "https://nvlpubs.nist.gov/nistpubs/legacy/sp/nistspecialpublication800-38d.pdf",
        "used_for": "AES-GCM authenticated encryption expectations",
    },
    {
        "title": "RFC 5869: HMAC-based Extract-and-Expand Key Derivation Function",
        "url": "https://datatracker.ietf.org/doc/html/rfc5869",
        "used_for": "HKDF-SHA256 key derivation basis",
    },
    {
        "title": "NIST FIPS 180-4: Secure Hash Standard",
        "url": "https://csrc.nist.gov/pubs/fips/180-4/upd1/final",
        "used_for": "SHA-256 digest/fingerprint basis",
    },
    {
        "title": "NIST SP 800-57 Part 1 Rev. 5: Recommendation for Key Management",
        "url": "https://csrc.nist.gov/pubs/sp/800/57/pt1/r5/final",
        "used_for": "split knowledge, dual control, and key custody basis",
    },
]

COMPARISON_ROWS = [
    {
        "method": "Plaintext .env values",
        "category": "local_file",
        "score": 8,
        "confidentiality": "none",
        "integrity": "none",
        "key_management": "none",
        "tamper_detection": "none",
        "aureon_fit": "bootstrap only; acceptable for local dev, weak for live credentials",
        "limitation": "any process or user reading the file sees the secret",
    },
    {
        "method": "Base64/encoding only",
        "category": "obfuscation",
        "score": 12,
        "confidentiality": "none",
        "integrity": "none",
        "key_management": "none",
        "tamper_detection": "none",
        "aureon_fit": "not acceptable for real credential protection",
        "limitation": "encoding is reversible without a key",
    },
    {
        "method": "SHA-256 hash only",
        "category": "digest",
        "score": 24,
        "confidentiality": "one-way fingerprint only",
        "integrity": "detects equality when original is known",
        "key_management": "none",
        "tamper_detection": "partial",
        "aureon_fit": "good for packet fingerprints, not for storing API keys Aureon must reuse",
        "limitation": "cannot decrypt; API clients need the original secret",
    },
    {
        "method": "AES-CBC without separate authentication",
        "category": "legacy_encryption",
        "score": 46,
        "confidentiality": "medium when implemented correctly",
        "integrity": "weak unless paired with a MAC",
        "key_management": "operator-managed",
        "tamper_detection": "weak",
        "aureon_fit": "not preferred because tamper detection is easy to get wrong",
        "limitation": "malleability and padding risks without authenticated design",
    },
    {
        "method": "Aureon HNC harmonic packet v1",
        "category": "authenticated_local_envelope",
        "score": 78,
        "confidentiality": "AES-GCM payload secrecy",
        "integrity": "packet hash, AES-GCM authentication, HNC geometry, and symbolic route seal",
        "key_management": "operator-managed AUREON_HNC_PACKET_MASTER_KEY",
        "tamper_detection": "strong packet, geometry, symbolic route, AAD, and fragment checks",
        "aureon_fit": "strong local upgrade for .env credential-at-rest protection and HNC decode proof",
        "limitation": "security depends on keeping the master key outside git and away from leaked logs/process dumps",
    },
    {
        "method": "Aureon HNC swarm two-way locknote packet v1",
        "category": "split_knowledge_dual_control_envelope",
        "score": 86,
        "confidentiality": "AES-GCM payload secrecy with two-agent key-share reconstruction",
        "integrity": "packet hash, AES-GCM authentication, locknote authentication, HNC geometry, and symbolic route contract",
        "key_management": "two independent agent master keys required per decode",
        "tamper_detection": "strong packet, locknote, AAD, geometry, symbolic route, and missing-pair checks",
        "aureon_fit": "best local HNC design for high-value secrets because a single agent/key cannot decode alone",
        "limitation": "still depends on keeping agent master keys separate and protected outside git/logs/process dumps",
    },
    {
        "method": "Generic AES-GCM envelope encryption",
        "category": "authenticated_local_envelope",
        "score": 82,
        "confidentiality": "AES-GCM payload secrecy",
        "integrity": "AES-GCM authentication",
        "key_management": "operator-managed or app-managed",
        "tamper_detection": "strong",
        "aureon_fit": "excellent baseline; HNC packet adds Aureon-specific authenticated context",
        "limitation": "still only as strong as key storage and nonce discipline",
    },
    {
        "method": "OS keychain / Windows Credential Manager",
        "category": "local_secret_store",
        "score": 88,
        "confidentiality": "OS-protected secret storage",
        "integrity": "OS-managed",
        "key_management": "user/session/OS-managed",
        "tamper_detection": "strong through OS APIs",
        "aureon_fit": "best next local upgrade: store the HNC master key outside .env",
        "limitation": "less portable across headless/server deployments",
    },
    {
        "method": "Cloud KMS / HSM-backed envelope encryption",
        "category": "managed_key_infrastructure",
        "score": 94,
        "confidentiality": "strong with hardware or managed key custody",
        "integrity": "managed audit and policy controls",
        "key_management": "centralized, rotatable, auditable",
        "tamper_detection": "strong",
        "aureon_fit": "best production/server target when multiple users or hosted SaaS are involved",
        "limitation": "requires external account, permissions, cost, and network availability",
    },
    {
        "method": "Post-quantum / hybrid public-key envelope",
        "category": "future_hybrid",
        "score": 76,
        "confidentiality": "depends on selected standardized/hybrid scheme",
        "integrity": "scheme dependent",
        "key_management": "more complex",
        "tamper_detection": "strong when paired with AEAD",
        "aureon_fit": "future transport upgrade; not required for local symmetric .env protection today",
        "limitation": "does not remove the need for AEAD payload encryption and key custody",
    },
]


def _read_json(path: Path) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return None


def build_hnc_packet_security_comparison(repo_root: Path | None = None) -> dict[str, Any]:
    root = repo_root or REPO_ROOT
    sample_key = b"H" * 32
    sample_packet = build_hnc_quantum_packet(
        "comparison-sample-secret",
        sample_key,
        purpose="security:comparison",
        operator_aad={"report": "security_comparison"},
        hnc_context={"domain": "security_comparison", "scope": "self_breaker"},
    )
    fragments = stream_hnc_probability_fragments(sample_packet, fragment_size=256)
    sample_summary = packet_public_summary(sample_packet)
    breaker = run_hnc_packet_breaker_checks(sample_packet, sample_key)
    swarm_agents = {
        "seer": b"S" * 32,
        "lyra": b"L" * 32,
        "king": b"K" * 32,
    }
    swarm_packet = build_hnc_swarm_packet(
        "comparison-swarm-secret",
        swarm_agents,
        purpose="security:swarm_comparison",
        operator_aad={"report": "security_comparison", "mode": "swarm"},
        hnc_context={"domain": "security_comparison", "scope": "two_way_locknote_breaker"},
    )
    swarm_summary = packet_public_summary(swarm_packet)
    swarm_breaker = run_hnc_swarm_breaker_checks(swarm_packet, swarm_agents)
    symbolic_manifest = load_symbolic_catalog_manifest()
    live_evidence = _read_json(root / HNC_PACKET_EVIDENCE_PATH.relative_to(REPO_ROOT))
    rows = [dict(row) for row in COMPARISON_ROWS]
    hnc_row = next(row for row in rows if row["method"] == "Aureon HNC harmonic packet v1")
    swarm_row = next(row for row in rows if row["method"] == "Aureon HNC swarm two-way locknote packet v1")
    hnc_row["breaker_passed"] = bool(breaker.get("passed"))
    hnc_row["fragment_count_in_self_test"] = len(fragments)
    hnc_row["live_evidence_present"] = bool(live_evidence)
    hnc_row["master_key_env_present"] = bool(os.environ.get(MASTER_KEY_ENV))
    hnc_row["symbolic_route_present"] = bool((sample_summary.get("symbolic_route") or {}).get("valid"))
    swarm_row["breaker_passed"] = bool(swarm_breaker.get("passed"))
    swarm_row["agent_count_in_self_test"] = len(swarm_agents)
    swarm_row["single_agent_can_decode"] = False
    swarm_row["symbolic_route_present"] = bool((swarm_summary.get("symbolic_route") or {}).get("valid"))

    plaintext = next(row for row in rows if row["method"] == "Plaintext .env values")
    base64_row = next(row for row in rows if row["method"] == "Base64/encoding only")
    sha_row = next(row for row in rows if row["method"] == "SHA-256 hash only")
    kms = next(row for row in rows if row["method"] == "Cloud KMS / HSM-backed envelope encryption")
    os_keychain = next(row for row in rows if row["method"] == "OS keychain / Windows Credential Manager")

    summary = {
        "current_hnc_score": hnc_row["score"],
        "current_swarm_score": swarm_row["score"],
        "current_hnc_rating": "strong_local_envelope_when_master_key_is_protected",
        "current_swarm_rating": "stronger_split_knowledge_local_envelope_when_agent_keys_are_separated",
        "compared_methods": len(rows),
        "beats_plaintext_by": hnc_row["score"] - plaintext["score"],
        "beats_base64_by": hnc_row["score"] - base64_row["score"],
        "beats_sha_only_by": hnc_row["score"] - sha_row["score"],
        "below_os_keychain_by": os_keychain["score"] - hnc_row["score"],
        "below_kms_hsm_by": kms["score"] - hnc_row["score"],
        "breaker_passed": bool(breaker.get("passed")),
        "swarm_breaker_passed": bool(swarm_breaker.get("passed")),
        "swarm_beats_hnc_by": swarm_row["score"] - hnc_row["score"],
        "swarm_below_os_keychain_by": os_keychain["score"] - swarm_row["score"],
        "swarm_below_kms_hsm_by": kms["score"] - swarm_row["score"],
        "fragment_self_test_count": len(fragments),
        "swarm_agent_self_test_count": len(swarm_agents),
        "master_key_env_present": bool(os.environ.get(MASTER_KEY_ENV)),
        "live_packet_evidence_present": bool(live_evidence),
        "symbolic_route_bound_to_packets": bool((sample_summary.get("symbolic_route") or {}).get("valid"))
        and bool((swarm_summary.get("symbolic_route") or {}).get("valid")),
        "symbolic_route_catalogs_present": symbolic_manifest["summary"]["catalogs_present"],
        "symbolic_route_symbol_count": symbolic_manifest["summary"]["symbol_count"],
        "main_weakness": "operator-managed key custody",
        "top_recommendation": "store HNC/swarm agent keys in Windows Credential Manager or another OS secret store, keep only hncqp1 packets and public locknotes in .env/state, and require two agent keys for high-value decode",
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "comparison_ready",
        "summary": summary,
        "rows": sorted(rows, key=lambda row: row["score"]),
        "hnc_packet_self_breaker": breaker,
        "hnc_swarm_self_breaker": swarm_breaker,
        "references": REFERENCES,
        "security_boundary": {
            "hnc_geometry_role": "authenticated decode contract and evidence context",
            "symbolic_route_role": "authenticated rune/star/Maeshowe context seal; proves route intent and catalog provenance but is not secret key material",
            "cryptographic_secret_role": "AES-GCM payload secrecy under a master key or two-agent swarm key-share reconstruction",
            "swarm_locknote_role": "split-knowledge dual-control gate where one agent key cannot decode alone",
            "what_hnc_does_not_replace": "key custody, OS permissions, KMS/HSM policy, endpoint authentication, and process memory protection",
        },
        "next_upgrades": [
            "Move AUREON_HNC_PACKET_MASTER_KEY and swarm agent keys out of .env and into Windows Credential Manager or an equivalent local secret store.",
            "Use two-way swarm locknotes for high-value credentials and keep single-master HNC packets for lower-risk local bootstrap values.",
            "Add key rotation: decrypt old hncqp1 tokens, re-encrypt with a new master key, and write a rotation evidence report.",
            "Add optional KMS/HSM envelope mode for hosted or multi-user deployments.",
            "Keep breaker checks in CI so tampered geometry, fragments, or AAD never decode.",
            "Keep the symbolic route catalogs under audit so rune/star route seals stay reproducible and evidence-linked.",
        ],
        "secret_policy": "metadata_only_no_secret_values",
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    lines = [
        "# Aureon HNC Packet Security Comparison",
        "",
        f"Generated: `{report.get('generated_at')}`",
        "",
        "## Summary",
        "",
        f"- Current HNC packet score: `{summary.get('current_hnc_score')}/100`",
        f"- Current HNC swarm score: `{summary.get('current_swarm_score')}/100`",
        f"- Rating: `{summary.get('current_hnc_rating')}`",
        f"- Breaker checks passed: `{summary.get('breaker_passed')}`",
        f"- Swarm breaker checks passed: `{summary.get('swarm_breaker_passed')}`",
        f"- Symbolic route bound to packets: `{summary.get('symbolic_route_bound_to_packets')}`",
        f"- Symbolic route catalogs present: `{summary.get('symbolic_route_catalogs_present')}`",
        f"- Symbolic route symbols indexed: `{summary.get('symbolic_route_symbol_count')}`",
        f"- Main weakness: `{summary.get('main_weakness')}`",
        f"- Top recommendation: {summary.get('top_recommendation')}",
        "",
        "## Comparison",
        "",
        "| Method | Score | Confidentiality | Integrity | Key management | Aureon fit |",
        "| --- | ---: | --- | --- | --- | --- |",
    ]
    for row in sorted(report.get("rows", []), key=lambda item: item.get("score", 0), reverse=True):
        lines.append(
            "| {method} | {score} | {confidentiality} | {integrity} | {key_management} | {aureon_fit} |".format(
                method=row.get("method"),
                score=row.get("score"),
                confidentiality=row.get("confidentiality"),
                integrity=row.get("integrity"),
                key_management=row.get("key_management"),
                aureon_fit=row.get("aureon_fit"),
            )
        )
    lines.extend(
        [
            "",
            "## Security Boundary",
            "",
            f"- HNC geometry role: {report['security_boundary']['hnc_geometry_role']}",
            f"- Symbolic route role: {report['security_boundary']['symbolic_route_role']}",
            f"- Cryptographic secret role: {report['security_boundary']['cryptographic_secret_role']}",
            f"- Swarm locknote role: {report['security_boundary']['swarm_locknote_role']}",
            f"- HNC does not replace: {report['security_boundary']['what_hnc_does_not_replace']}",
            "",
            "## Next Upgrades",
            "",
        ]
    )
    for item in report.get("next_upgrades", []):
        lines.append(f"- {item}")
    lines.extend(["", "## References", ""])
    for reference in report.get("references", []):
        lines.append(f"- [{reference['title']}]({reference['url']}) - {reference['used_for']}")
    lines.append("")
    return "\n".join(lines)


def write_hnc_packet_security_comparison(
    report: dict[str, Any],
    output_json: Path = DEFAULT_OUTPUT_JSON,
    output_md: Path = DEFAULT_OUTPUT_MD,
    public_json: Path = DEFAULT_PUBLIC_JSON,
) -> tuple[Path, Path, Path]:
    for path in (output_json, output_md, public_json):
        path.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, indent=2, sort_keys=True, default=str), encoding="utf-8")
    output_md.write_text(render_markdown(report), encoding="utf-8")
    public_json.write_text(json.dumps(report, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return output_json, output_md, public_json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate Aureon HNC packet security comparison.")
    parser.add_argument("--json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--md", type=Path, default=DEFAULT_OUTPUT_MD)
    parser.add_argument("--public-json", type=Path, default=DEFAULT_PUBLIC_JSON)
    args = parser.parse_args(argv)
    report = build_hnc_packet_security_comparison()
    write_hnc_packet_security_comparison(report, args.json, args.md, args.public_json)
    print(json.dumps({"ok": True, "status": report["status"], "outputs": [str(args.json), str(args.md), str(args.public_json)]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
