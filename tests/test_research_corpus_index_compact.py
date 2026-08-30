from __future__ import annotations

import json
from pathlib import Path

from aureon.queen.research_corpus_index import (
    CACHE_VERSION,
    ResearchCorpusIndex,
)


def test_path_fragment_exclusions_are_platform_neutral(
    tmp_path: Path,
) -> None:
    included = tmp_path / "src" / "included.py"
    excluded = tmp_path / "data" / "research" / "grants" / "excluded.py"
    included.parent.mkdir(parents=True)
    excluded.parent.mkdir(parents=True)
    included.write_text("def included():\n    return 'indexed'\n", encoding="utf-8")
    excluded.write_text("def excluded():\n    return 'not indexed'\n", encoding="utf-8")

    index = ResearchCorpusIndex(
        root=str(tmp_path),
        cache_path=None,
        exclude=("data/research/grants",),
        ingest_exts=(".py",),
    )

    relative = {
        Path(path).relative_to(tmp_path).as_posix()
        for path in index._iter_source_files()
    }
    assert relative == {"src/included.py"}


def test_compact_postings_preserve_tf_and_cache_roundtrip(
    tmp_path: Path,
) -> None:
    source = tmp_path / "research.md"
    cache = tmp_path / "index.json"
    source.write_text(
        "# Compact index\n\n"
        "resonance resonance resonance appears in this paragraph.\n\n"
        "resonance appears once in this second paragraph.",
        encoding="utf-8",
    )
    cold = ResearchCorpusIndex(
        root=str(tmp_path),
        cache_path=str(cache),
        ingest_exts=(".md",),
    )
    cold.ensure_built()

    values = cold._postings["resonance"]
    assert sorted(values[2::3]) == [1, 3]
    cold_hits = cold.search("resonance", top_k=2)
    assert cold_hits[0].paragraph_idx == 0

    payload = json.loads(cache.read_text(encoding="utf-8"))
    assert payload["version"] == CACHE_VERSION
    cached_values = payload["postings"]["resonance"]
    assert isinstance(cached_values, str)
    assert payload["posting_value_count"] == sum(
        len(postings) for postings in cold._postings.values()
    )

    warm = ResearchCorpusIndex(
        root=str(tmp_path),
        cache_path=str(cache),
        ingest_exts=(".md",),
    )
    warm.ensure_built()
    warm_hits = warm.search("resonance", top_k=2)
    assert [hit.to_dict() for hit in warm_hits] == [
        hit.to_dict() for hit in cold_hits
    ]


def test_legacy_cache_is_rejected_before_full_json_parse(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cache = tmp_path / "legacy.json"
    cache.write_text(
        '{"version":1,"root":"legacy","docs":this-is-not-valid-json',
        encoding="utf-8",
    )
    index = ResearchCorpusIndex(root=str(tmp_path), cache_path=str(cache))

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("legacy cache should fail prefix preflight")

    monkeypatch.setattr(json, "load", fail_if_called)
    assert index._try_load_cache() is False


def test_unindexable_source_does_not_force_warm_rebuild(
    tmp_path: Path,
    monkeypatch,
) -> None:
    (tmp_path / "empty.md").write_text("", encoding="utf-8")
    (tmp_path / "indexed.md").write_text(
        "A searchable research paragraph with enough text to retain.",
        encoding="utf-8",
    )
    cache = tmp_path / "index.json"
    cold = ResearchCorpusIndex(
        root=str(tmp_path),
        cache_path=str(cache),
        ingest_exts=(".md",),
    )
    cold.ensure_built()
    assert len(cold._source_mtimes) == 2
    assert cold.doc_count() == 1

    warm = ResearchCorpusIndex(
        root=str(tmp_path),
        cache_path=str(cache),
        ingest_exts=(".md",),
    )

    def fail_if_rebuilt(*_args, **_kwargs):
        raise AssertionError("valid warm cache should not rebuild")

    monkeypatch.setattr(warm, "build", fail_if_rebuilt)
    warm.ensure_built()
    assert warm.doc_count() == 1
