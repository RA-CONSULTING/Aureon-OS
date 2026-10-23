#!/usr/bin/env python3
"""Installer utility for the A.L.F.I.E. Evolution Pack.

This script expands the supplied Evolution ZIP archive into the desired
runtime directory, validates the contents against ``FILE_INDEX.json``,
prints the boot plan contained in ``alfie_sandbox_manifest.json`` and
creates a ``alfie_runtime_state.json`` file that mirrors the information
exposed by the legacy installer shared with the team.

An optional ``--create-api-stub`` flag can be used to emit a lightweight
``alfie_runtime_api.py`` helper that demonstrates how a mission-control
script might interact with the generated runtime artefacts.
"""
from __future__ import annotations

import argparse
import json
import sys
import textwrap
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, Tuple


EXIT_OK = 0
EXIT_INDEX_MISSING = 2
EXIT_INTEGRITY_FAILURE = 3
EXIT_MANIFEST_MISSING = 4


def compute_sha16(path: Path) -> str:
    """Return the first 16 hex digits of the file's SHA-256 digest.

    The upstream FILE_INDEX.json that ships with the Evolution Pack stores
    truncated SHA-256 values. We mirror the original utility's behaviour so
    installers generated with the reference tooling remain compatible.
    """

    try:
        data = path.read_text(encoding="utf-8")
        digest_source: bytes = data.encode("utf-8")
    except UnicodeDecodeError:
        digest_source = path.read_bytes()
    import hashlib

    return hashlib.sha256(digest_source).hexdigest()[:16]


def validate_against_index(dest: Path, index: Dict[str, Dict[str, str]]) -> Iterable[Tuple[str, str]]:
    """Yield ``(filename, reason)`` tuples for every validation failure."""

    for fname, meta in index.items():
        fpath = dest / fname
        if not fpath.exists():
            yield fname, "missing"
            continue

        expected = meta.get("sha16")
        if expected is None:
            yield fname, "missing sha16 entry in index"
            continue

        actual = compute_sha16(fpath)
        if actual != expected:
            yield fname, f"checksum mismatch: {actual} != {expected}"


def load_json(path: Path, *, error_code: int) -> Dict:
    """Read ``path`` as JSON, exiting with ``error_code`` on failure."""

    if not path.exists():
        print(f"ERROR: {path.name} missing after extraction.", file=sys.stderr)
        sys.exit(error_code)

    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:
        print(f"ERROR: {path.name} is not valid JSON: {exc}", file=sys.stderr)
        sys.exit(error_code)


def print_boot_plan(manifest: Dict[str, object]) -> None:
    seq = manifest.get("alfie_init_sequence", [])
    layers = {layer.get("id"): layer for layer in manifest.get("layers", [])}

    print("\n✅ Integrity verified. Boot plan:")
    for step, layer_id in enumerate(seq, start=1):
        layer = layers.get(layer_id, {})
        path = layer.get("path", "?")
        phase = layer.get("phase", "?")
        required = " [required]" if layer.get("required") else ""
        print(f" {step:02d}. {layer_id}  → {path}  (phase {phase}){required}")

    safety = manifest.get("safety", {})
    if safety:
        print("\n🛡  Safety constraints:")
        for key, value in safety.items():
            print(f"  - {key}: {value}")


def write_runtime_state(dest: Path, manifest: Dict[str, object]) -> Path:
    runtime_state = {
        "installed_at": datetime.now(timezone.utc).isoformat(),
        "pack": {
            "name": manifest.get("name"),
            "version": manifest.get("version"),
        },
        "coherence_targets": {
            "gamma_min": 0.90,
            "gamma_nominal": 0.987,
        },
        "explainability": True,
        "status": "READY",
    }

    runtime_path = dest / "alfie_runtime_state.json"
    with runtime_path.open("w", encoding="utf-8") as handle:
        json.dump(runtime_state, handle, indent=2)
        handle.write("\n")
    return runtime_path


def write_runtime_api_stub(dest: Path) -> Path:
    stub_path = dest / "alfie_runtime_api.py"
    stub_source = textwrap.dedent(
        '''
        """Lightweight runtime helper for the A.L.F.I.E. sandbox.

        This module is intentionally tiny: it demonstrates how callers can load the
        manifest and runtime state produced by the Evolution installer and provides a
        handful of ergonomic helpers that scripts may wish to build upon.
        """
        from __future__ import annotations

        import json
        from pathlib import Path
        from typing import Iterable, Tuple


        class AlfieRuntime:
            """In-memory wrapper around the unpacked runtime artefacts."""

            def __init__(self, runtime_root: str | Path):
                self.runtime_root = Path(runtime_root)
                manifest_path = self.runtime_root / "alfie_sandbox_manifest.json"
                state_path = self.runtime_root / "alfie_runtime_state.json"

                with manifest_path.open("r", encoding="utf-8") as handle:
                    self.manifest = json.load(handle)
                with state_path.open("r", encoding="utf-8") as handle:
                    self.state = json.load(handle)

                self.mode: str = self.state.get("status", "IDLE")
                self._thrust_vector: Tuple[float, float, float] = (0.0, 0.0, 0.0)

            # -- Mission helpers -------------------------------------------------
            def thrust_vector(self, x: float, y: float, z: float) -> Tuple[float, float, float]:
                """Record the desired thrust vector and return the normalised tuple."""

                self._thrust_vector = (float(x), float(y), float(z))
                return self._thrust_vector

            def set_mode(self, mode: str) -> None:
                """Switch the runtime mode if it is defined by any manifest layer."""

                declared_modes = {
                    layer.get("mode")
                    for layer in self.manifest.get("layers", [])
                    if isinstance(layer, dict) and layer.get("mode")
                }

                if declared_modes and mode not in declared_modes:
                    raise ValueError(
                        f"Mode '{mode}' not declared in manifest (allowed: {sorted(declared_modes)})"
                    )

                self.mode = mode

            def get_gamma(self) -> float:
                """Return the nominal Γ target stored in the runtime state."""

                coherence = self.state.get("coherence_targets", {})
                return float(coherence.get("gamma_nominal", 1.0))

            # -- Introspection ---------------------------------------------------
            @property
            def thrust_history(self) -> Tuple[float, float, float]:
                """Expose the most recently requested thrust vector."""

                return self._thrust_vector

            def available_layers(self) -> Iterable[str]:
                """Yield the identifiers of all manifest layers."""

                for layer in self.manifest.get("layers", []):
                    if isinstance(layer, dict) and layer.get("id"):
                        yield layer["id"]
        '''
    ).lstrip()

    with stub_path.open("w", encoding="utf-8") as handle:
        handle.write(stub_source)
    return stub_path


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="One-click installer for the A.L.F.I.E. Evolution Pack",
    )
    parser.add_argument("--zip", default="ALFIE_Evolution_v1.zip", help="Path to Evolution Pack ZIP")
    parser.add_argument("--dest", default="ALFIE_Runtime", help="Destination directory")
    parser.add_argument(
        "--create-api-stub",
        action="store_true",
        help="Emit an alfie_runtime_api.py helper beside the unpacked assets",
    )
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    zip_path = Path(args.zip).expanduser().resolve()
    dest = Path(args.dest).expanduser().resolve()
    dest.mkdir(parents=True, exist_ok=True)

    print("🧭 A.L.F.I.E. Evolution Installer")
    print(" • ZIP:", zip_path)
    print(" • DEST:", dest)

    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(dest)

    index_path = dest / "FILE_INDEX.json"
    index = load_json(index_path, error_code=EXIT_INDEX_MISSING)

    failures = list(validate_against_index(dest, index))
    if failures:
        print("❌ Integrity check failed:")
        for fname, reason in failures:
            print(f"   - {fname}: {reason}")
        return EXIT_INTEGRITY_FAILURE

    manifest_path = dest / "alfie_sandbox_manifest.json"
    manifest = load_json(manifest_path, error_code=EXIT_MANIFEST_MISSING)

    print_boot_plan(manifest)

    runtime_path = write_runtime_state(dest, manifest)
    print("\n🌟 A.L.F.I.E. Evolution pack is READY.")
    print("   Runtime state:", runtime_path)

    if args.create_api_stub:
        stub_path = write_runtime_api_stub(dest)
        print("   API stub:", stub_path)

    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
