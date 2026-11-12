"""The .env.example inventory lists names only and changes no setting."""
import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "env_names_inventory", ROOT / "scripts" / "validation" / "env_names_inventory.py"
)
inv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(inv)


def _repo(tmp_path, example):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "a.py").write_text(
        "import os\n"
        "x = os.environ.get('AUREON_ALPHA', '1')\n"
        "y = os.getenv(\"BETA_KEY\")\n"
        "z = os.environ['GAMMA_PATH']\n"
        "p = os.environ.get('PYTHONIOENCODING')\n",
        encoding="utf-8",
    )
    (tmp_path / "imports").mkdir()
    (tmp_path / "imports" / "b.py").write_text("os.getenv('SNAPSHOT_ONLY')\n", encoding="utf-8")
    (tmp_path / ".env.example").write_text(example, encoding="utf-8")
    return tmp_path


def test_check_fails_then_write_lists_only_commented_names(tmp_path):
    root = _repo(tmp_path, "# header\nAUREON_ALPHA=1\n")
    assert inv.main(["--root", str(root), "--check"]) == 1
    assert inv.main(["--root", str(root), "--write"]) == 0
    text = (root / ".env.example").read_text(encoding="utf-8")
    assert "# BETA_KEY=    # read in pkg/a.py" in text
    assert "# GAMMA_PATH=    # read in pkg/a.py" in text
    assert "SNAPSHOT_ONLY" not in text          # imports/ is skipped
    assert "PYTHONIOENCODING" not in text       # interpreter names skipped
    assert text.count("AUREON_ALPHA=") == 1     # already documented, not repeated
    active = [l for l in text.splitlines() if l and not l.lstrip().startswith("#")]
    assert active == ["AUREON_ALPHA=1"]         # no new active setting
    assert inv.main(["--root", str(root), "--check"]) == 0


def test_write_is_idempotent(tmp_path):
    root = _repo(tmp_path, "AUREON_ALPHA=1\n")
    inv.main(["--root", str(root), "--write"])
    first = (root / ".env.example").read_text(encoding="utf-8")
    inv.main(["--root", str(root), "--write"])
    assert (root / ".env.example").read_text(encoding="utf-8") == first


def test_repo_example_generated_block_has_no_values():
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    if inv.BEGIN not in text:
        return
    block = text.split(inv.BEGIN, 1)[1].split(inv.END, 1)[0]
    for line in block.splitlines():
        assert line == "" or line.startswith("#"), line
        m = re.match(r"^# ([A-Z][A-Z0-9_]*)=(.*)$", line)
        if m:
            assert m.group(2).startswith("    # read in "), line
