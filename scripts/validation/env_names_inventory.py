#!/usr/bin/env python3
"""List every environment variable name the Python code reads, names only.

It scans the repository for ``os.environ.get("NAME")``, ``os.getenv("NAME")``
and ``os.environ["NAME"]`` with a literal upper-case name, and compares the
result with the names written in ``.env.example`` (set or commented out).

  --check   exit 1 if the code reads a name that .env.example never mentions
  --write   rewrite the generated block at the end of .env.example

The generated block is commented out on purpose: every line is ``# NAME=``,
so copying the template to ``.env`` sets nothing and changes no default.
No value is ever read from the environment or written by this script.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ".env.example"
BEGIN = "# >>> generated: env names read by code (scripts/validation/env_names_inventory.py --write)"
END = "# <<< generated"

SKIP_DIRS = {
    ".git", "node_modules", ".venv", "venv", "__pycache__", "imports", "data",
    "huggingface", "tests", "archive", "site-packages", "build", "dist",
}
# Interpreter, OS and test-runner names: not Aureon settings.
STANDARD = {
    "PATH", "HOME", "USER", "USERNAME", "USERPROFILE", "APPDATA", "LOCALAPPDATA",
    "PROGRAMDATA", "SYSTEMROOT", "WINDIR", "COMPUTERNAME", "HOSTNAME", "TMP",
    "TEMP", "TMPDIR", "SHELL", "TERM", "LANG", "PWD", "TZ", "DISPLAY", "COLUMNS",
    "NO_COLOR", "CI", "VIRTUAL_ENV",
}
STANDARD_PREFIXES = ("PYTHON", "PYTEST_", "LC_", "XDG_", "GITHUB_", "CONDA_")
# Names kept out of the public template on purpose (machine-local paths;
# see tests/test_portability.py). They are never written, and --check skips them.
KEPT_OUT = {"SERO_WORKSPACE"}

READ_RE = re.compile(
    r"""(?:environ\.get|getenv|environ\.setdefault)\(\s*['"]([A-Z][A-Z0-9_]{2,})['"]"""
    r"""|environ\[\s*['"]([A-Z][A-Z0-9_]{2,})['"]\s*\]"""
)
LISTED_RE = re.compile(r"^\s*#?\s*([A-Z][A-Z0-9_]*)=", re.M)


def is_standard(name: str) -> bool:
    return name in STANDARD or name.startswith(STANDARD_PREFIXES)


def scan(root: Path = ROOT) -> dict[str, list[str]]:
    found: dict[str, set[str]] = defaultdict(set)
    for path in root.rglob("*.py"):
        rel = path.relative_to(root)
        if any(part in SKIP_DIRS for part in rel.parts[:-1]):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for m in READ_RE.finditer(text):
            name = m.group(1) or m.group(2)
            if not is_standard(name) and name not in KEPT_OUT:
                found[name].add(rel.as_posix())
    return {k: sorted(v) for k, v in found.items()}


def split_example(text: str) -> tuple[str, str]:
    """Return (hand-written part, generated block or '')."""
    if BEGIN in text:
        head, _, rest = text.partition(BEGIN)
        _, _, tail = rest.partition(END)
        return head.rstrip("\n") + "\n" + tail.lstrip("\n"), BEGIN + rest.split(END)[0] + END
    return text, ""


def listed(text: str) -> set[str]:
    return set(LISTED_RE.findall(text))


def missing(found: dict[str, list[str]], hand_text: str) -> dict[str, list[str]]:
    have = listed(hand_text)
    return {k: v for k, v in found.items() if k not in have}


def render_block(miss: dict[str, list[str]]) -> str:
    lines = [
        BEGIN,
        "# Names the code reads that the sections above do not document.",
        "# Names only. Every line is commented out, so copying this file to .env",
        "# sets nothing and each program keeps its own built-in default.",
        "# Uncomment a line only if you know what that setting does.",
        f"# Count: {len(miss)}",
    ]
    groups: dict[str, list[str]] = defaultdict(list)
    for name in sorted(miss):
        groups[name.split("_", 1)[0]].append(name)
    for prefix in sorted(groups):
        lines.append("#")
        lines.append(f"# --- {prefix} ---")
        for name in groups[prefix]:
            files = miss[name]
            where = files[0] + (f" (+{len(files) - 1} more)" if len(files) > 1 else "")
            lines.append(f"# {name}=    # read in {where}")
    lines.append(END)
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", type=Path, default=ROOT)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--check", action="store_true")
    g.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)

    example = args.root / EXAMPLE
    text = example.read_text(encoding="utf-8") if example.exists() else ""
    hand, _block = split_example(text)
    found = scan(args.root)
    miss = missing(found, hand)

    if args.write:
        new = hand.rstrip("\n") + "\n\n" + render_block(miss) if miss else hand
        example.write_text(new, encoding="utf-8")
        print(f"{len(found)} names read by code; {len(miss)} written to the generated block")
        return 0

    undocumented = sorted(set(found) - listed(text))
    if args.check:
        if undocumented:
            print(f"{len(undocumented)} names read by code are not in {EXAMPLE}:")
            for name in undocumented:
                print(f"  {name}  ({found[name][0]})")
            return 1
        print(f"OK: all {len(found)} names read by code appear in {EXAMPLE}")
        return 0

    for name in sorted(found):
        print(name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
