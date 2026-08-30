#!/usr/bin/env python3
"""Validate a GPS provider observation and derive its nearest street reference.

Usage: python -m aureon.utils.update_gary_location path/to/gps_observation.json
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict

from aureon.queen.queen_street_homing import QueenStreetLevelHoming


def update_location(observation: Dict[str, Any]) -> Dict[str, Any]:
    result = QueenStreetLevelHoming().home_on_street(observation)
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    path = Path(sys.argv[1]).resolve()
    if not path.is_file():
        raise SystemExit(f"GPS_OBSERVATION_FILE_NOT_FOUND:{path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("GPS_OBSERVATION_OBJECT_REQUIRED")
    update_location(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
