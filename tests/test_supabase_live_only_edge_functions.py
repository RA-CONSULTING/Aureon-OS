from __future__ import annotations

import hashlib
import json
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FUNCTIONS_ROOT = REPO_ROOT / "supabase" / "functions"
ARCHIVE_ROOT = (
    REPO_ROOT
    / "docs"
    / "evidence"
    / "supabase"
    / "edge-functions"
    / "20260811"
)
MANIFEST_PATH = ARCHIVE_ROOT / "manifest.json"
CONFIG_PATH = REPO_ROOT / "supabase" / "config.toml"

EXPECTED_PROVIDER = {
    "client-portal-api": (
        "a7a648d8-ea46-47c0-8d32-1349f49f12b9",
        4,
        "5025e28637771c94ba3e099239d626ecf18dd4c7991c464ba1ab101b7ea4cc16",
    ),
    "chronicle-data-manager": (
        "4d60bff6-3857-45f0-9608-b5d410a12844",
        4,
        "89dcc8a674bdd4080d662df643db3f4ec6b02ba879a07959364872c758893444",
    ),
    "nexus-api-gateway": (
        "0cdcfe64-c50b-4505-8b43-e194a7de2b49",
        4,
        "c44b11cef0be723226dccccf0491c172c50fc17339497ac72762989dac8ab09e",
    ),
    "spiritual-data-manager": (
        "fe25c03e-ccbc-42bb-8bce-d1a7afe01db7",
        7,
        "0a930d4f72753e7e3218a381d90e12ae2856d93998f6095814ef804114568fea",
    ),
    "realtime-data-stream": (
        "ce2623c5-4d57-4251-b337-cc808f05565a",
        4,
        "10a1b8e85c6083c53bcd3333a73d1cb35031afa68a7096d4a0ff7cafc40f6150",
    ),
    "data-ingestion-pipeline": (
        "561a621a-6fbd-4277-b5a5-a0e43f8ca967",
        4,
        "dd1fe21e07985183231c2ac5701c09c7943c137acc8d4194f1ba7ca9829dc11e",
    ),
    "backend-health-monitor": (
        "0e790974-03b9-46ca-93c5-8b6c2fc1a318",
        4,
        "8ca76562cb238826bd1d298758b9bf95817064e076239d29f24587e1dab4e364",
    ),
    "distributed-health-monitor": (
        "72dcfd76-8b6b-41e6-abb3-4d2c2f157977",
        4,
        "48ff5d8bb3b07a084efc4e7dccb5b6f5f3b3ece363773f145520bcd797cf38de",
    ),
    "realtime-session-manager": (
        "98449a3d-da8e-441e-9c80-f4c5991f606a",
        4,
        "d30a6db51d36762da16d5b6773625e7e1632ba528975b34bd304723732d7cdf9",
    ),
    "realtime-sessions-api": (
        "d29ba7e3-c1fb-43f4-9248-b6169a7d5c94",
        4,
        "e8cf794b4b4dcedc30c56645ca500f91d76267614da6194eef0b54ce2cd54da0",
    ),
    "nexus-database-api": (
        "6291175f-362a-4ce6-9f64-2f8039235989",
        3,
        "79a82fc6df8e22545f6380091a9397a02138637e85454246195ed811b3b5b524",
    ),
}

BANNED_RUNTIME_FRAGMENTS = (
    "access-control-allow-origin",
    "authorization",
    "createclient",
    "deno.env",
    "fetch(",
    "math.random",
    "supabase_",
    "upgradewebsocket",
    ".from(",
    ".insert(",
    ".update(",
    ".upsert(",
    ".delete(",
    ".rpc(",
    ".json(",
)


def _manifest() -> dict[str, object]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_live_only_functions_are_explicit_gateway_quarantines() -> None:
    config = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    functions = config["functions"]

    assert set(EXPECTED_PROVIDER).issubset(functions)
    for slug in EXPECTED_PROVIDER:
        assert functions[slug]["verify_jwt"] is True


def test_quarantine_handlers_are_deterministic_and_inert() -> None:
    for slug in EXPECTED_PROVIDER:
        source = (FUNCTIONS_ROOT / slug / "index.ts").read_text(
            encoding="utf-8"
        )
        lowered = source.lower()

        assert f'const FUNCTION_NAME = "{slug}";' in source
        assert source.count("Deno.serve") == 1
        assert 'error: "function_quarantined"' in source
        assert 'status: "gone"' in source
        assert "status: 410" in source
        assert '"Cache-Control": "no-store"' in source
        assert '"X-Content-Type-Options": "nosniff"' in source
        for fragment in BANNED_RUNTIME_FRAGMENTS:
            assert fragment not in lowered, (slug, fragment)


def test_archive_is_hash_bound_to_the_provider_receipt() -> None:
    manifest = _manifest()

    assert (
        manifest["schema_version"]
        == "aureon.supabase.live_only_edge_function_archive.v1"
    )
    assert manifest["project_ref"] == "siihxcwetdjdsrfdexmb"
    assert manifest["capture_mode"] == "read_only_supabase_get_edge_function"
    assert manifest["source_normalization"] == "lf_with_single_final_newline"
    assert manifest["do_not_deploy"] is True
    assert manifest["provider_mutated"] is False
    assert manifest["provider_hash_readback_verified"] is True
    assert manifest["function_count"] == len(EXPECTED_PROVIDER) == 11

    entries = {
        entry["slug"]: entry
        for entry in manifest["functions"]
    }
    assert set(entries) == set(EXPECTED_PROVIDER)

    for slug, (provider_id, version, expected_sha256) in (
        EXPECTED_PROVIDER.items()
    ):
        entry = entries[slug]
        relative_path = (
            f"docs/evidence/supabase/edge-functions/20260811/{slug}.ts"
        )
        assert entry["provider_id"] == provider_id
        assert entry["provider_version"] == version
        assert entry["provider_verify_jwt"] is False
        assert entry["archive_path"] == relative_path
        assert entry["sha256"] == expected_sha256

        archive = REPO_ROOT / relative_path
        payload = archive.read_bytes()
        assert entry["archive_bytes"] == len(payload)
        assert hashlib.sha256(payload).hexdigest() == expected_sha256
        assert FUNCTIONS_ROOT not in archive.parents

    notice = (ARCHIVE_ROOT / "README_DO_NOT_DEPLOY.md").read_text(
        encoding="utf-8"
    )
    assert "DO NOT DEPLOY" in notice
    assert "No table row content" in notice


def test_audit_note_preserves_the_local_only_boundary() -> None:
    note = (
        REPO_ROOT
        / "docs"
        / "SUPABASE_LIVE_ONLY_EDGE_FUNCTIONS_20260811.md"
    ).read_text(encoding="utf-8")
    normalized_note = " ".join(note.split())

    assert "Production status: unchanged" in note
    assert "No Edge Function was invoked, deployed" in note
    assert (
        "Unknown external callers remain a compatibility risk"
        in normalized_note
    )
