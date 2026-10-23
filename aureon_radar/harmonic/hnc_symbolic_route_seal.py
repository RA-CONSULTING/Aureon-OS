"""HNC symbolic route seals.

This layer binds Aureon's rune/star research catalogs to encrypted packets as
authenticated metadata. It is evidence and routing context, not a replacement
for AES-GCM, HKDF, DPAPI, or key custody.
"""

from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping


SCHEMA_VERSION = "aureon-hnc-symbolic-route-seal-v1"
REPO_ROOT = Path(__file__).resolve().parents[2]

CATALOG_PATHS = {
    "elder_futhark_runes": "public/elder-futhark-runes.json",
    "mogollon_star_symbols": "public/mogollon-star-symbols.json",
    "japanese_star_symbols": "public/japanese-star-symbols.json",
    "aztec_star_glyphs": "public/aztec-star-glyphs.json",
    "auris_symbols": "public/auris_symbols.json",
}

PROVENANCE_PATHS = {
    "maeshowe_seer_decode": "aureon/wisdom/maeshowe_seer_decode.py",
    "civilizational_dna": "aureon/wisdom/civilizational_dna.py",
    "tandem_in_unity_v1": "docs/research/whitepapers/Tandem_in_Unity_Unifying_Resonant_Fields_v1.pdf",
    "tandem_in_unity_v2": "docs/research/whitepapers/Tandem_in_Unity_Unifying_Resonant_Fields_v2.pdf",
}


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


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except Exception:
        return str(path)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def _file_record(name: str, relative_path: str, *, parse_json: bool = False) -> dict[str, Any]:
    path = REPO_ROOT / relative_path
    record: dict[str, Any] = {
        "name": name,
        "path": relative_path,
        "present": path.exists(),
    }
    if not path.exists():
        record["reason"] = "missing"
        return record
    data = path.read_bytes()
    record.update(
        {
            "size_bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "modified_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
        }
    )
    if parse_json:
        try:
            parsed = _read_json(path)
            record["json_valid"] = True
            if isinstance(parsed, dict):
                record["schema"] = parsed.get("schema")
                if isinstance(parsed.get("runes"), list):
                    record["symbol_count"] = len(parsed["runes"])
                elif isinstance(parsed.get("symbols"), list):
                    record["symbol_count"] = len(parsed["symbols"])
                elif isinstance(parsed.get("sacred_symbols"), list):
                    record["symbol_count"] = len(parsed["sacred_symbols"])
                elif isinstance(parsed.get("glyphs"), list):
                    record["symbol_count"] = len(parsed["glyphs"])
                else:
                    record["symbol_count"] = len(parsed)
            elif isinstance(parsed, list):
                record["symbol_count"] = len(parsed)
        except Exception as exc:
            record["json_valid"] = False
            record["reason"] = f"json_parse_failed:{type(exc).__name__}"
    return record


def _items_from_catalog(relative_path: str) -> list[dict[str, Any]]:
    path = REPO_ROOT / relative_path
    if not path.exists():
        return []
    try:
        data = _read_json(path)
    except Exception:
        return []
    if isinstance(data, dict):
        for key in ("runes", "symbols", "sacred_symbols", "glyphs", "items"):
            if isinstance(data.get(key), list):
                return [item for item in data[key] if isinstance(item, dict)]
        return [{"id": key, "value": value} for key, value in data.items() if isinstance(value, (str, int, float, dict))]
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


@lru_cache(maxsize=1)
def load_symbolic_catalog_manifest() -> dict[str, Any]:
    catalogs = {
        name: _file_record(name, path, parse_json=True)
        for name, path in CATALOG_PATHS.items()
    }
    provenance = {
        name: _file_record(name, path, parse_json=False)
        for name, path in PROVENANCE_PATHS.items()
    }
    present_catalogs = [record for record in catalogs.values() if record.get("present")]
    present_provenance = [record for record in provenance.values() if record.get("present")]
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "catalogs": catalogs,
        "provenance": provenance,
        "summary": {
            "catalog_count": len(catalogs),
            "catalogs_present": len(present_catalogs),
            "provenance_count": len(provenance),
            "provenance_present": len(present_provenance),
            "symbol_count": sum(int(record.get("symbol_count") or 0) for record in present_catalogs),
        },
        "security_boundary": {
            "role": "authenticated_symbolic_context_and_route_selection",
            "not_a_secret": True,
            "does_not_replace": "AES-GCM, HKDF, DPAPI, KMS, HSM, OS permissions, or key custody",
        },
    }
    manifest["catalog_manifest_sha256"] = sha256_hex(
        {
            "catalogs": {
                name: {
                    "path": record.get("path"),
                    "present": record.get("present"),
                    "sha256": record.get("sha256"),
                    "symbol_count": record.get("symbol_count"),
                }
                for name, record in catalogs.items()
            },
            "provenance": {
                name: {
                    "path": record.get("path"),
                    "present": record.get("present"),
                    "sha256": record.get("sha256"),
                }
                for name, record in provenance.items()
            },
        }
    )
    return manifest


def _pick(items: list[dict[str, Any]], seed: str, offset: int = 0) -> dict[str, Any]:
    if not items:
        return {"id": "missing", "name": "missing", "reason": "catalog_empty_or_missing"}
    digest = hashlib.sha256(f"{seed}:{offset}".encode("utf-8")).digest()
    index = int.from_bytes(digest[:8], "big") % len(items)
    item = dict(items[index])
    return {
        "id": str(item.get("id") or item.get("name") or item.get("symbol") or item.get("unicode") or index),
        "name": str(item.get("name") or item.get("id") or item.get("title") or item.get("symbol") or item.get("meaning") or index),
        "unicode": item.get("unicode"),
        "meaning": item.get("meaning") or item.get("description") or item.get("lesson"),
        "domain": item.get("domain") or (item.get("trading_signal") or {}).get("domain"),
        "trading_signal": item.get("trading_signal") if isinstance(item.get("trading_signal"), dict) else None,
        "source_index": index,
    }


def build_symbolic_route_seal(
    *,
    purpose: str,
    operator_aad: Mapping[str, Any] | None = None,
    hnc_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    manifest = load_symbolic_catalog_manifest()
    seed_material = {
        "purpose": purpose,
        "operator_aad_sha256": sha256_hex(operator_aad or {}),
        "hnc_context_sha256": sha256_hex(hnc_context or {}),
        "catalog_manifest_sha256": manifest["catalog_manifest_sha256"],
    }
    seed = sha256_hex(seed_material)
    rune = _pick(_items_from_catalog(CATALOG_PATHS["elder_futhark_runes"]), seed, 1)
    mogollon = _pick(_items_from_catalog(CATALOG_PATHS["mogollon_star_symbols"]), seed, 2)
    japanese = _pick(_items_from_catalog(CATALOG_PATHS["japanese_star_symbols"]), seed, 3)
    aztec = _pick(_items_from_catalog(CATALOG_PATHS["aztec_star_glyphs"]), seed, 4)
    auris = _pick(_items_from_catalog(CATALOG_PATHS["auris_symbols"]), seed, 5)
    route = {
        "threshold_layer": "threshold_people_crossing_from_observation_to_authenticated_action",
        "caller_voice": "operator_intent",
        "seer_voice": "present_observation",
        "emergent_route_rule": "meaning_exists_when_caller_and_seer_are_bound_by_authenticated_context",
        "selected_rune": rune,
        "selected_star_symbols": {
            "mogollon": mogollon,
            "japanese": japanese,
            "aztec": aztec,
        },
        "selected_auris_symbol": auris,
        "maeshowe_protocol": {
            "role": "two_voice_route_model",
            "caller": "L(t)_identity_function",
            "seer": "O(t)_present_observation",
            "source": PROVENANCE_PATHS["maeshowe_seer_decode"],
        },
    }
    seal = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "purpose": purpose,
        "seed_sha256": seed,
        "catalog_manifest_sha256": manifest["catalog_manifest_sha256"],
        "catalog_summary": manifest["summary"],
        "route": route,
        "source_paths": {
            **{name: record["path"] for name, record in manifest["catalogs"].items()},
            **{name: record["path"] for name, record in manifest["provenance"].items()},
        },
        "security_boundary": manifest["security_boundary"],
    }
    seal["route_seal_sha256"] = route_seal_digest(seal)
    return seal


def route_seal_digest(seal: Mapping[str, Any]) -> str:
    clean = dict(seal)
    clean.pop("route_seal_sha256", None)
    clean.pop("generated_at", None)
    return sha256_hex(clean)


def validate_symbolic_route_seal(seal: Mapping[str, Any] | None) -> dict[str, Any]:
    reasons: list[str] = []
    if not isinstance(seal, Mapping):
        return {"valid": False, "reasons": ["missing_symbolic_route_seal"]}
    if seal.get("schema_version") != SCHEMA_VERSION:
        reasons.append("unsupported_symbolic_route_schema")
    if seal.get("route_seal_sha256") != route_seal_digest(seal):
        reasons.append("symbolic_route_hash_mismatch")
    boundary = seal.get("security_boundary") if isinstance(seal.get("security_boundary"), Mapping) else {}
    if boundary.get("not_a_secret") is not True:
        reasons.append("symbolic_route_secret_boundary_missing")
    route = seal.get("route") if isinstance(seal.get("route"), Mapping) else {}
    if not route.get("selected_rune"):
        reasons.append("symbolic_route_rune_missing")
    if not route.get("selected_star_symbols"):
        reasons.append("symbolic_route_star_symbols_missing")
    return {
        "valid": not reasons,
        "reasons": reasons,
        "route_seal_sha256": seal.get("route_seal_sha256"),
        "catalog_manifest_sha256": seal.get("catalog_manifest_sha256"),
        "purpose": seal.get("purpose"),
    }


def symbolic_route_public_summary(seal: Mapping[str, Any] | None) -> dict[str, Any]:
    validation = validate_symbolic_route_seal(seal)
    if not isinstance(seal, Mapping):
        return validation
    route = seal.get("route") if isinstance(seal.get("route"), Mapping) else {}
    selected_stars = route.get("selected_star_symbols") if isinstance(route.get("selected_star_symbols"), Mapping) else {}
    return {
        **validation,
        "threshold_layer": route.get("threshold_layer"),
        "rune": (route.get("selected_rune") or {}).get("name") if isinstance(route.get("selected_rune"), Mapping) else None,
        "star_symbols": {
            name: item.get("name") if isinstance(item, Mapping) else None
            for name, item in selected_stars.items()
        },
        "auris_symbol": (route.get("selected_auris_symbol") or {}).get("name") if isinstance(route.get("selected_auris_symbol"), Mapping) else None,
        "security_boundary": "authenticated_context_not_secret_key_material",
    }


def write_symbolic_route_manifest(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest = load_symbolic_catalog_manifest()
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=True), encoding="utf-8")
    return path


__all__ = [
    "CATALOG_PATHS",
    "PROVENANCE_PATHS",
    "SCHEMA_VERSION",
    "build_symbolic_route_seal",
    "load_symbolic_catalog_manifest",
    "route_seal_digest",
    "symbolic_route_public_summary",
    "validate_symbolic_route_seal",
    "write_symbolic_route_manifest",
]
