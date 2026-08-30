from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_randomized_stream_emitters_are_not_packaged_as_data_feeds() -> None:
    data_feeds = REPO_ROOT / "aureon" / "data_feeds"

    assert not (data_feeds / "emit_test_stream.py").exists()
    assert not (data_feeds / "emit_test_stream_aura.py").exists()
