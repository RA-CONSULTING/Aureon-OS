"""The Orca entrypoint must not wrap sys.stdout.buffer on Windows."""

from pathlib import Path


def _orca_files() -> list[Path]:
    here = Path(__file__).resolve()
    roots = [here.parents[1], here.parents[2]]
    found: list[Path] = []
    for root in roots:
        for relative in (
            Path("aureon") / "bots" / "orca_complete_kill_cycle.py",
            Path("aureon-os-upstream") / "aureon" / "bots" / "orca_complete_kill_cycle.py",
            Path("aureon_radar") / "bots" / "orca_complete_kill_cycle.py",
        ):
            path = root / relative
            if path.is_file() and path not in found:
                found.append(path)
    return found


def _main_block(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    marker = 'if __name__ == "__main__":'
    assert marker in text
    return text[text.rindex(marker) :]


def test_orca_main_does_not_wrap_stdout_buffer() -> None:
    files = _orca_files()
    assert files, "no Orca entrypoint found"
    for path in files:
        block = _main_block(path)
        assert "codecs.getwriter" not in block
        assert "sys.stdout.buffer" not in block
        assert "sys.stdout.reconfigure" in block
        assert "sys.stderr.reconfigure" in block
        assert "PYTHONUTF8" in block
