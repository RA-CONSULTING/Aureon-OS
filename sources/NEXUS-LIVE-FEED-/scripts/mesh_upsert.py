"""Seed the support network mesh configuration for the backend."""
from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict

import importlib.util

_requests_spec = importlib.util.find_spec("requests")
if _requests_spec is None:  # pragma: no cover - requires optional dependency
    raise SystemExit("The 'requests' package is required to seed the mesh.")

import requests  # type: ignore  # noqa: E402

MESH_PAYLOAD: Dict[str, Any] = {
    "anchor_id": "gary.leckey",
    "anchor_name": "Gary Leckey",
    "members": [
        {
            "member_id": "deirdre.leckey",
            "name": "Deirdre Leckey",
            "birth_date": "1974-08-27",
            "relation": "family",
            "weight": 0.92,
            "consent": True,
            "roles": ["guardian", "resonator"],
        },
        {
            "member_id": "philip.leckey",
            "name": "Philip Leckey",
            "birth_date": "1965-08-28",
            "relation": "family",
            "weight": 0.9,
            "consent": True,
            "roles": ["guardian"],
        },
        {
            "member_id": "jeannette.leckey",
            "name": "Jeannete Leckey",
            "birth_date": "1961-11-19",
            "relation": "family",
            "weight": 0.88,
            "consent": True,
            "roles": ["resonator"],
        },
        {
            "member_id": "alice.leckey",
            "name": "Alice Leckey",
            "birth_date": "1967-09-22",
            "relation": "family",
            "weight": 0.89,
            "consent": True,
            "roles": ["resonator"],
        },
        {
            "member_id": "ann.leckey",
            "name": "Ann Leckey",
            "birth_date": "1969-11-13",
            "relation": "family",
            "weight": 0.9,
            "consent": True,
            "roles": ["notifier"],
        },
        {
            "member_id": "susan.leckey",
            "name": "Susan Leckey",
            "birth_date": "1963-08-24",
            "relation": "family",
            "weight": 0.91,
            "consent": True,
            "roles": ["notifier"],
        },
        {
            "member_id": "samuel.og.leckey",
            "name": "Samuel O G Leckey",
            "birth_date": "1971-05-19",
            "relation": "family",
            "weight": 0.9,
            "consent": True,
            "roles": ["guardian"],
        },
        {
            "member_id": "samuel.leckey",
            "name": "Samuel Leckey",
            "birth_date": "1942-03-08",
            "relation": "family",
            "weight": 0.87,
            "consent": True,
            "roles": ["resonator"],
        },
    ],
    "edges": [
        {"a": "deirdre.leckey", "b": "gary.leckey", "weight": 0.95},
        {"a": "philip.leckey", "b": "gary.leckey", "weight": 0.93},
    ],
}


def upsert_mesh(base_url: str) -> Dict[str, Any]:
    """Send the configured mesh payload to the backend."""

    endpoint = f"{base_url.rstrip('/')}/mesh/upsert"
    response = requests.post(endpoint, json=MESH_PAYLOAD, timeout=10.0)
    response.raise_for_status()
    return response.json()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the support network mesh")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("MESH_SERVICE_BASE_URL")
        or os.environ.get("AURIS_MESH_BASE_URL")
        or os.environ.get("AURIS_BACKEND_BASE_URL")
        or "http://localhost:8000",
        help="Mesh service base URL (default from environment or http://localhost:8000)",
    )
    args = parser.parse_args()
    result = upsert_mesh(args.base_url)
    print(json.dumps(result, indent=2))
 

if __name__ == "__main__":
    main()
