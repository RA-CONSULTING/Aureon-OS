"""Dry-run dashboard. Same process as ``python -m aureon_fusion.http_service``.

Requires AUREON_FUSION_API_TOKEN. Binds to loopback unless AUREON_FUSION_BIND
is set. Live trading stays off.
"""

from __future__ import annotations

from .http_service import main

if __name__ == "__main__":
    raise SystemExit(main())
