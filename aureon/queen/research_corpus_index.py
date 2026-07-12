"""
ResearchCorpusIndex — keyword inverted index over the Aureon research
markdown corpus.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The Queen voice needs to ground her replies in the repo's research notes
(HNC white paper, Synthesis, Claims & Evidence, φ² chain, Ancient
Convergence, and ~170 other docs under ``docs/**/*.md``). She doesn't
need semantic embeddings — the technical vocabulary is narrow enough
that a keyword + idf index surfaces the right paragraphs.

Usage::

    idx = get_research_corpus_index()
    snippets = idx.search("master formula", top_k=3)
    for s in snippets:
        print(s.doc_id, s.score, s.text[:120])

Index is lazily built on first call and cached to
``state/research_index.json`` so server restarts skip the tokenization
pass. Rebuilt automatically when any indexed file's mtime is newer than
the cache.

No semantic embeddings. No vector DB. No third-party deps. Pure stdlib.
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
import threading
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

logger = logging.getLogger("aureon.queen.research_corpus_index")


# ─────────────────────────────────────────────────────────────────────────────
# Data types
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class Snippet:
    """One retrieved paragraph from the corpus."""

    doc_id: str          # relative path under the corpus root, e.g. "docs/HNC_UNIFIED_WHITE_PAPER.md"
    title: str           # first H1/H2 found in the doc, or filename
    paragraph_idx: int   # 0-based paragraph index within the doc
    text: str            # the paragraph text itself (already stripped of markdown)
    score: float = 0.0

    def to_dict(self) -> Dict[str, object]:
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "paragraph_idx": self.paragraph_idx,
            "text": self.text,
            "score": round(self.score, 6),
        }


@dataclass
class _Document:
    """Internal representation of one indexed document."""

    doc_id: str
    title: str
    mtime: float
    paragraphs: List[str]  # paragraph text, stripped


# ─────────────────────────────────────────────────────────────────────────────
# Stopwords — prune the noisiest English tokens before scoring
# ─────────────────────────────────────────────────────────────────────────────


_STOPWORDS = frozenset(
    """
    a an the and or but if then else of to from in on at by for with
    is are was were be been being am do does did have has had having
    this that these those it its as so not no nor yet we you they he
    she i me my mine your yours our ours their theirs his her them us
    will would can could may might must should shall into over under
    out about between among across through within without upon via
    which who whom whose what where when why how just only very much
    more most less least some any all each every other than also new
    old one two three four five six seven eight nine ten first second
    page line file files section document documents note notes
    """.split()
)


# ─────────────────────────────────────────────────────────────────────────────
# Tokenizer + markdown cleaner
# ─────────────────────────────────────────────────────────────────────────────


_WORD_RE = re.compile(r"[a-z0-9]+(?:['-][a-z0-9]+)*", re.IGNORECASE)
_CODE_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`[^`]*`")
_LINK_RE = re.compile(r"\[([^\]]+)\]\([^\)]+\)")
_HEADING_MARK_RE = re.compile(r"^#+\s*", re.MULTILINE)
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_TABLE_LINE_RE = re.compile(r"^\s*\|.*\|\s*$")
_TABLE_DIVIDER_RE = re.compile(r"^\s*\|?\s*:?-{3,}:?")
_BULLET_RE = re.compile(r"^\s*[-*+]\s+")
_FRONTMATTER_RE = re.compile(r"^---.*?---\s*", re.DOTALL)


def _strip_markdown(text: str) -> str:
    """
    Remove code fences, html, yaml front-matter, link syntax, and drop
    any line that looks like a markdown table row or divider. Tables
    give the corpus index false positives — a search for "master
    formula" used to surface `| Paper | Notes |` rows in INDEX.md
    instead of the actual prose paragraphs. Filtering them out at the
    cleaner layer fixes that cleanly for every downstream query.
    """
    text = _FRONTMATTER_RE.sub("", text)
    text = _CODE_FENCE_RE.sub(" ", text)
    text = _INLINE_CODE_RE.sub(" ", text)
    text = _LINK_RE.sub(r"\1", text)
    text = _HTML_TAG_RE.sub(" ", text)
    # Drop table lines line-by-line — we keep everything else intact.
    kept: List[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            kept.append("")
            continue
        if _TABLE_LINE_RE.match(stripped) or _TABLE_DIVIDER_RE.match(stripped):
            continue
        kept.append(line)
    text = "\n".join(kept)
    text = _HEADING_MARK_RE.sub("", text)
    return text


def _split_paragraphs(text: str) -> List[str]:
    """
    Split cleaned markdown into paragraphs on blank lines. Drops
    paragraphs that look like single headings, pure bullet-lists
    (< 40 chars), or lines of punctuation.
    """
    raw = [p.strip() for p in re.split(r"\n\s*\n", text)]
    out: List[str] = []
    for p in raw:
        if not p:
            continue
        # Collapse internal whitespace so table-row fragments that
        # slipped through show their true length.
        compact = re.sub(r"\s+", " ", p).strip()
        if len(compact) < 20:
            continue
        # Skip paragraphs where every non-empty line is a bullet
        # marker (usually navigation / section index blocks).
        lines = [ln.strip() for ln in p.splitlines() if ln.strip()]
        if lines and all(_BULLET_RE.match(ln) for ln in lines):
            # Collapse the bullets into one paragraph so the index
            # still sees the words, but only if the collapsed text
            # has real content.
            collapsed = " ".join(_BULLET_RE.sub("", ln) for ln in lines)
            if len(collapsed) >= 40:
                out.append(collapsed)
            continue
        out.append(compact)
    return out


def _tokenize(text: str) -> List[str]:
    toks = _WORD_RE.findall(text.lower())
    return [t for t in toks if t and t not in _STOPWORDS and len(t) > 1]


def _extract_title(text: str, fallback: str) -> str:
    """Pull the first H1/H2 from the doc, or fall back to the filename."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()[:120]
        if stripped.startswith("## "):
            return stripped[3:].strip()[:120]
    return fallback


# ─────────────────────────────────────────────────────────────────────────────
# ResearchCorpusIndex
# ─────────────────────────────────────────────────────────────────────────────


DEFAULT_CORPUS_ROOT = "docs"
DEFAULT_CACHE_PATH = os.path.join("state", "research_index.json")


class ResearchCorpusIndex:
    """
    Inverted keyword index over a markdown corpus.

    Build once with ``build(root)``, query with ``search(q, top_k)``.
    Persists to a JSON cache so the warm reload skips re-tokenization.
    """

    def __init__(
        self,
        *,
        root: str = DEFAULT_CORPUS_ROOT,
        cache_path: Optional[str] = DEFAULT_CACHE_PATH,
        exclude: Optional[Sequence[str]] = None,
        ingest_exts: Optional[Sequence[str]] = None,
    ):
        self.root = root
        self.cache_path = cache_path
        self.exclude = tuple(exclude or ())
        # Widen the ingestible extension set per-instance (shadows the class
        # attribute) so a repo-wide index can index .py/.txt source too, while
        # the default docs index stays markdown+pdf only. Backward-compatible.
        if ingest_exts:
            self._INGEST_EXTS = tuple(e.lower() for e in ingest_exts)
        self._docs: Dict[str, _Document] = {}        # doc_id → _Document
        self._postings: Dict[str, List[Tuple[str, int]]] = {}  # token → [(doc_id, para_idx)]
        self._idf: Dict[str, float] = {}             # token → idf weight
        self._built = False
        self._lock = threading.RLock()

    # ─────────────────────────────────────────────────────────────────
    # Build / load
    # ─────────────────────────────────────────────────────────────────

    def build(self, root: Optional[str] = None) -> None:
        """Walk ``root`` for *.md files and (re)build the index."""
        with self._lock:
            if root is not None:
                self.root = root
            self._docs.clear()
            self._postings.clear()
            self._idf.clear()

            if not os.path.isdir(self.root):
                logger.warning("ResearchCorpusIndex: root %r does not exist", self.root)
                self._built = True
                return

            t0 = time.time()
            doc_count = 0
            md_count = 0
            pdf_count = 0
            for abs_path in self._iter_source_files():
                raw = self._load_source(abs_path)
                if raw is None:
                    continue
                cleaned = _strip_markdown(raw)
                paragraphs = _split_paragraphs(cleaned)
                if not paragraphs:
                    continue
                title = _extract_title(raw, fallback=os.path.basename(abs_path))
                mtime = os.path.getmtime(abs_path)
                if abs_path.lower().endswith(".pdf"):
                    pdf_count += 1
                else:
                    md_count += 1
                # doc_id is the path RELATIVE to root, always forward-slashed,
                # prefixed with the root's basename so callers can match on
                # "docs/HNC_UNIFIED_WHITE_PAPER.md" regardless of where the
                # repo lives on disk.
                doc_id = self._doc_id_for(abs_path)
                doc = _Document(
                    doc_id=doc_id,
                    title=title,
                    mtime=mtime,
                    paragraphs=paragraphs,
                )
                self._docs[doc_id] = doc
                doc_count += 1

                for idx, para in enumerate(paragraphs):
                    seen_this_doc: set = set()
                    for tok in _tokenize(para):
                        key = (doc_id, idx)
                        self._postings.setdefault(tok, []).append(key)
                        seen_this_doc.add(tok)

            self._compute_idf()
            self._built = True
            elapsed = (time.time() - t0) * 1000.0
            logger.info(
                "ResearchCorpusIndex: built %d docs (%d md, %d pdf), "
                "%d tokens in %.0f ms",
                doc_count, md_count, pdf_count, len(self._postings), elapsed,
            )
            if self.cache_path:
                try:
                    self._save_cache()
                except Exception as e:
                    logger.debug("cache save failed: %s", e)

    # File extensions we can ingest. Markdown is always on; PDFs require
    # pypdf at extract time (graceful skip if not installed).
    _INGEST_EXTS: tuple = (".md", ".pdf")

    def _iter_md_files(self) -> Iterable[str]:
        """Backward-compatible alias — walks every ingestible file."""
        yield from self._iter_source_files()

    def _iter_source_files(self) -> Iterable[str]:
        for dirpath, _dirnames, filenames in os.walk(self.root):
            # Skip deny-list directories.
            if any(part in self.exclude for part in dirpath.split(os.sep)):
                continue
            for name in filenames:
                lower = name.lower()
                if not lower.endswith(self._INGEST_EXTS):
                    continue
                path = os.path.join(dirpath, name)
                if any(x in path for x in self.exclude):
                    continue
                yield path

    def _load_source(self, abs_path: str) -> Optional[str]:
        """
        Read the raw text from a source file. Returns None if the file
        could not be loaded (PDF without pypdf, read error, etc.).
        """
        lower = abs_path.lower()
        if lower.endswith(".pdf"):
            return self._load_pdf(abs_path)
        # Markdown and any other widened plaintext extension (.py/.txt/.rst…)
        # are read as UTF-8 text. Code files index their docstrings, comments,
        # and identifiers — enough for keyword grounding across the whole repo.
        try:
            with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except Exception as e:
            logger.debug("source read failed %s: %s", abs_path, e)
            return None

    _pdf_backend: Optional[str] = None
    _pdf_backend_logged: bool = False

    def _load_pdf(self, abs_path: str) -> Optional[str]:
        """
        Extract text from a PDF using pypdf if available. Returns None
        if no PDF backend is installed — the user can
        ``pip install pypdf`` to opt in. The first missing-backend event
        is logged once per process so we don't spam the logs.
        """
        backend = self._resolve_pdf_backend()
        if backend is None:
            return None
        try:
            if backend == "pypdf":
                import pypdf  # type: ignore
                reader = pypdf.PdfReader(abs_path)
                parts = []
                for page in reader.pages:
                    try:
                        parts.append(page.extract_text() or "")
                    except Exception:
                        continue
                return "\n\n".join(parts)
            if backend == "PyPDF2":
                import PyPDF2  # type: ignore
                reader = PyPDF2.PdfReader(abs_path)
                parts = []
                for page in reader.pages:
                    try:
                        parts.append(page.extract_text() or "")
                    except Exception:
                        continue
                return "\n\n".join(parts)
            if backend == "pdfminer":
                from pdfminer.high_level import extract_text  # type: ignore
                return extract_text(abs_path)
        except Exception as e:
            logger.debug("pdf extract failed %s: %s", abs_path, e)
            return None
        return None

    @classmethod
    def _resolve_pdf_backend(cls) -> Optional[str]:
        """Probe for a PDF library at most once per process."""
        if cls._pdf_backend is not None:
            return cls._pdf_backend if cls._pdf_backend != "-" else None
        for name in ("pypdf", "PyPDF2", "pdfminer"):
            try:
                __import__(name)
                cls._pdf_backend = name
                if not cls._pdf_backend_logged:
                    logger.info("ResearchCorpusIndex: PDF backend = %s", name)
                    cls._pdf_backend_logged = True
                return name
            except Exception:
                continue
        cls._pdf_backend = "-"
        if not cls._pdf_backend_logged:
            logger.info(
                "ResearchCorpusIndex: no PDF backend installed "
                "(pip install pypdf to expand the corpus with whitepapers)"
            )
            cls._pdf_backend_logged = True
        return None

    def _doc_id_for(self, abs_path: str) -> str:
        """
        Build the stable doc_id for an absolute path: ``<root_basename>/<rel>``
        with forward slashes. This way ``docs/HNC_UNIFIED_WHITE_PAPER.md`` is
        the id whether the repo lives in ``/home/user/aureon-trading`` or
        ``C:\\Users\\ayman kattan\\aureon-trading``.
        """
        try:
            rel = os.path.relpath(abs_path, start=self.root)
        except Exception:
            rel = os.path.basename(abs_path)
        rel = rel.replace(os.sep, "/").lstrip("./")
        root_tag = os.path.basename(os.path.normpath(self.root)) or "docs"
        return f"{root_tag}/{rel}"

    def _compute_idf(self) -> None:
        """Inverse-document-frequency weight per token."""
        n_docs = max(1, len(self._docs))
        # For each token, count how many unique docs it appears in.
        doc_count_per_token: Dict[str, int] = {}
        for tok, postings in self._postings.items():
            unique_docs = {doc_id for doc_id, _ in postings}
            doc_count_per_token[tok] = len(unique_docs)
        for tok, cnt in doc_count_per_token.items():
            # Standard idf with smoothing: log((N + 1) / (df + 1)) + 1
            self._idf[tok] = math.log((n_docs + 1) / (cnt + 1)) + 1.0

    def ensure_built(self) -> None:
        """Build the index from cache if possible, otherwise from scratch."""
        with self._lock:
            if self._built:
                return
            if self._try_load_cache():
                self._built = True
                return
            self.build()

    # ─────────────────────────────────────────────────────────────────
    # Persistence
    # ─────────────────────────────────────────────────────────────────

    def _save_cache(self) -> None:
        if not self.cache_path:
            return
        os.makedirs(os.path.dirname(self.cache_path) or ".", exist_ok=True)
        payload = {
            "version": 1,
            "root": self.root,
            "saved_at": time.time(),
            "docs": {
                doc_id: {
                    "title": d.title,
                    "mtime": d.mtime,
                    "paragraphs": d.paragraphs,
                }
                for doc_id, d in self._docs.items()
            },
            "postings": {
                tok: [[doc_id, idx] for (doc_id, idx) in postings]
                for tok, postings in self._postings.items()
            },
            "idf": self._idf,
        }
        tmp = self.cache_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        os.replace(tmp, self.cache_path)

    def _try_load_cache(self) -> bool:
        """Return True if a usable cache was loaded."""
        if not self.cache_path or not os.path.exists(self.cache_path):
            return False
        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except Exception as e:
            logger.debug("cache load failed: %s", e)
            return False
        if payload.get("root") != self.root:
            return False

        # Validate: if any on-disk file has a newer mtime than the cache
        # entry, or a file was added/removed, the cache is stale.
        # PDFs only count when a PDF backend is installed — otherwise
        # they are never indexed so they mustn't appear in the
        # expected-set comparison.
        cached_docs = payload.get("docs") or {}
        try:
            actual_paths: Dict[str, str] = {}  # doc_id → abs_path
            pdf_backend = self._resolve_pdf_backend()
            for abs_path in self._iter_source_files():
                if abs_path.lower().endswith(".pdf") and pdf_backend is None:
                    continue
                actual_paths[self._doc_id_for(abs_path)] = abs_path
        except Exception:
            return False
        if set(cached_docs.keys()) != set(actual_paths.keys()):
            return False
        for doc_id, d in cached_docs.items():
            abs_path = actual_paths.get(doc_id)
            if not abs_path:
                return False
            try:
                disk_mtime = os.path.getmtime(abs_path)
            except Exception:
                return False
            if float(d.get("mtime", 0)) < disk_mtime - 1e-6:
                return False

        self._docs = {
            doc_id: _Document(
                doc_id=doc_id,
                title=str(d.get("title", "")),
                mtime=float(d.get("mtime", 0)),
                paragraphs=list(d.get("paragraphs", [])),
            )
            for doc_id, d in cached_docs.items()
        }
        self._postings = {
            tok: [tuple(p) for p in postings]  # type: ignore[misc]
            for tok, postings in (payload.get("postings") or {}).items()
        }
        self._idf = {k: float(v) for k, v in (payload.get("idf") or {}).items()}
        logger.info("ResearchCorpusIndex: loaded cache with %d docs", len(self._docs))
        return True

    # ─────────────────────────────────────────────────────────────────
    # Search
    # ─────────────────────────────────────────────────────────────────

    def search(self, query: str, top_k: int = 3) -> List[Snippet]:
        """
        Rank paragraphs across the corpus by ``sum(tf * idf)`` over the
        query tokens, biased toward paragraphs 40-400 chars long so we
        don't surface lone headings or fragments.
        """
        self.ensure_built()
        q_tokens = _tokenize(query)
        if not q_tokens:
            return []

        # Score each (doc_id, para_idx) pair that any query token hits.
        scores: Dict[Tuple[str, int], float] = defaultdict(float)
        for tok in q_tokens:
            postings = self._postings.get(tok)
            if not postings:
                continue
            idf = self._idf.get(tok, 1.0)
            # tf per (doc, para) is the count of appearances.
            tf: Counter = Counter(postings)
            for key, count in tf.items():
                scores[key] += count * idf

        if not scores:
            return []

        # Length bias: paragraphs in the [40, 400] char sweet-spot get a
        # small boost, single-line headings/fragments get a penalty.
        def length_factor(length: int) -> float:
            if length < 20:
                return 0.2
            if length < 40:
                return 0.7
            if length <= 400:
                return 1.15
            if length <= 800:
                return 1.0
            return 0.85

        snippets: List[Snippet] = []
        for (doc_id, para_idx), raw_score in scores.items():
            doc = self._docs.get(doc_id)
            if doc is None or para_idx >= len(doc.paragraphs):
                continue
            para_text = doc.paragraphs[para_idx]
            score = raw_score * length_factor(len(para_text))
            snippets.append(Snippet(
                doc_id=doc_id,
                title=doc.title,
                paragraph_idx=para_idx,
                text=para_text,
                score=score,
            ))

        snippets.sort(key=lambda s: s.score, reverse=True)
        return snippets[: max(0, int(top_k))]

    # ─────────────────────────────────────────────────────────────────
    # Introspection helpers
    # ─────────────────────────────────────────────────────────────────

    def doc_count(self) -> int:
        self.ensure_built()
        return len(self._docs)

    def token_count(self) -> int:
        self.ensure_built()
        return len(self._postings)

    def idf_of(self, token: str) -> float:
        self.ensure_built()
        return self._idf.get(token.lower(), 0.0)

    def list_doc_ids(self) -> List[str]:
        self.ensure_built()
        return sorted(self._docs.keys())


# ─────────────────────────────────────────────────────────────────────────────
# Module-level singleton
# ─────────────────────────────────────────────────────────────────────────────


_singleton: Optional[ResearchCorpusIndex] = None
_singleton_lock = threading.Lock()


def get_research_corpus_index(
    *,
    root: str = DEFAULT_CORPUS_ROOT,
    cache_path: Optional[str] = DEFAULT_CACHE_PATH,
) -> ResearchCorpusIndex:
    """Return the process-wide singleton, creating it on first call."""
    global _singleton
    with _singleton_lock:
        if _singleton is None:
            _singleton = ResearchCorpusIndex(root=root, cache_path=cache_path)
            _singleton.ensure_built()
        return _singleton


def reset_research_corpus_index() -> None:
    """Drop the singleton — used by tests."""
    global _singleton
    with _singleton_lock:
        _singleton = None


__all__ = [
    "ResearchCorpusIndex",
    "Snippet",
    "DEFAULT_CORPUS_ROOT",
    "DEFAULT_CACHE_PATH",
    "get_research_corpus_index",
    "reset_research_corpus_index",
]
