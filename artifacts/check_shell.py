"""Check the Space shell scripts for the constructs this project relies on.

There is no real bash on this host (bash.exe is the WSL stub), so syntax cannot
be executed. These checks at least prove the edited regions are self-consistent:
balanced quotes, a closed if/fi for the GPU probe, and no dangling line
continuations in the exec blocks.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "deploy" / "huggingface"


def check(name: str) -> list[str]:
    text = (ROOT / name).read_text(encoding="utf-8")
    problems: list[str] = []
    lines = text.splitlines()

    # A backslash-continued statement must not be followed by a blank line.
    for index, line in enumerate(lines):
        stripped = line.rstrip()
        if stripped.endswith("\\") and index + 1 < len(lines):
            if not lines[index + 1].strip():
                problems.append(f"{name}:{index + 1}: continuation followed by blank line")

    # Every `if` needs a matching `fi` at the same nesting depth.
    depth = 0
    for index, line in enumerate(lines):
        token = line.strip()
        if token.startswith("#"):
            continue
        if re.match(r"^if\b", token):
            depth += 1
        elif re.match(r"^fi\b", token):
            depth -= 1
            if depth < 0:
                problems.append(f"{name}:{index + 1}: fi without if")
                depth = 0
    if depth != 0:
        problems.append(f"{name}: {depth} unclosed if block(s)")

    # Odd quote counts usually mean a broken string.
    for index, line in enumerate(lines):
        if line.strip().startswith("#"):
            continue
        if line.count('"') % 2:
            problems.append(f"{name}:{index + 1}: odd number of double quotes")
        if line.count("'") % 2 and '"' not in line:
            problems.append(f"{name}:{index + 1}: odd number of single quotes")
    return problems


def main() -> int:
    problems: list[str] = []
    for name in ("entrypoint.sh", "model_service.sh"):
        problems.extend(check(name))
    if problems:
        print("\n".join(problems))
        return 1
    print("shell structure checks passed for entrypoint.sh and model_service.sh")
    return 0


if __name__ == "__main__":
    sys.exit(main())
