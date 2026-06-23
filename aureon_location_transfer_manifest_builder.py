#!/usr/bin/env python3
"""Build the warehouse-floor Azyra location transfer manifest from the photo."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from aureon_location_transfer_common import TRANSFER_ROOT, write_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(TRANSFER_ROOT))
    args = parser.parse_args()

    result = write_manifest(Path(args.output_dir))
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
