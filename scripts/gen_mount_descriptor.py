"""
Generate the static Mount integration descriptor.

Writes `.well-known/aureon-mount.json` at the repo root — a committed, static
snapshot of `aureon.operator.mount.integration_manifest()`. A flagship / AGI agent
that clones the repo but has not yet started the server can read this file directly
to learn how to mount (base_url swap, engines, the contract) without running
anything. The runtime routes (`GET /v1/integration`, `/.well-known/aureon-mount.json`,
`GET /api/mount`) serve the same manifest live.

`tests/test_operator_mount.py::test_static_descriptor_matches_manifest` fails if
this file drifts from `integration_manifest()`, so re-run this after any change:

    python -m scripts.gen_mount_descriptor
"""

from __future__ import annotations

import json
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_OUT = _REPO_ROOT / ".well-known" / "aureon-mount.json"


def main() -> int:
    from aureon.operator.mount import integration_manifest

    _OUT.parent.mkdir(parents=True, exist_ok=True)
    _OUT.write_text(json.dumps(integration_manifest(), indent=2) + "\n", encoding="utf-8")
    print(f"wrote {_OUT.relative_to(_REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
