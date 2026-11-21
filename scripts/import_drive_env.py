"""Import one read-only Drive env file into Aureon's local configuration.

Only recognized Aureon runtime variable names are imported. Values are never
printed. Existing non-empty local values win, so this cannot silently replace
existing configuration. Run only after reviewing the selected Drive file.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aureon.connectors.google_drive import DriveConnector
from aureon.core.aureon_env import _parse_env_line

NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
SAFE_PREFIXES = (
    "AUREON_",
    "KRAKEN_",
    "BINANCE_",
    "ALPACA_",
    "APCA_",
    "CAPITAL_",
    "COINAPI_",
    "NASA_",
    "NOAA_",
    "USGS_",
    "FRED_",
    "FIRMS_",
    "QUICKBOOKS_",
    "SUPABASE_",
    "OPENAI_",
    "ANTHROPIC_",
    "GEMINI_",
    "XAI_",
    "OLLAMA_",
)


def selected(text: str) -> dict[str, str]:
    selected_values: dict[str, str] = {}
    for line in text.splitlines():
        parsed = _parse_env_line(line)
        if parsed and NAME.fullmatch(parsed[0]) and parsed[0].startswith(SAFE_PREFIXES):
            selected_values[parsed[0]] = parsed[1]
    return selected_values


def merge(target: Path, values: dict[str, str]) -> list[str]:
    current = target.read_text(encoding="utf-8") if target.is_file() else ""
    existing = {parsed[0] for line in current.splitlines() if (parsed := _parse_env_line(line))}
    added = [key for key in values if key not in existing]
    if added:
        with target.open("a", encoding="utf-8", newline="\n") as handle:
            if current and not current.endswith("\n"):
                handle.write("\n")
            handle.write("# Imported from the operator-authorized read-only Drive file.\n")
            for key in added:
                handle.write(f"{key}={values[key]}\n")
    return added


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file_id", help="Drive file id selected from search/list results")
    parser.add_argument("--target", type=Path, default=ROOT / ".env.local")
    args = parser.parse_args()
    result = DriveConnector().read(args.file_id)
    if not result.available or not result.record or result.record.text is None:
        raise SystemExit(f"Drive file unavailable: {result.blocker or 'not a readable text file'}")
    values = selected(result.record.text)
    if not values:
        raise SystemExit("The selected file contains no recognized Aureon runtime variables.")
    added = merge(args.target, values)
    print(
        json.dumps(
            {
                "target": str(args.target),
                "imported_names": added,
                "existing_names_kept": sorted(set(values) - set(added)),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
