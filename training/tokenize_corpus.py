"""Turn the staged corpus into uint16 token shards the pretraining loop can mmap.

The corpus is 562 GB of parquet and gzip JSONL; a pretraining loop cannot read
that. It needs a flat array of token ids it can seek into, which is this step's
only job.

Two decisions worth stating:

- **uint16, not int32.** The vocabulary is 65,536, so every id fits in 16 bits
  except the largest (65,535) which still fits. Halving the width halves the
  bytes the loader has to page through, and the loader is the bottleneck at
  7B.
- **Resume at file granularity.** A 562 GB pass will be interrupted. Shards are
  written to `.tmp` then renamed, and the index is rewritten atomically after
  each one, so a kill costs the current shard and nothing else. Completed
  source files are recorded and skipped, never re-tokenised.

    python tokenize_corpus.py --tokenizer aureon_tokenizer.json \
        --data /projects/u6vs/pretrain/data --out /projects/u6vs/pretrain/tokens
"""

from __future__ import annotations

import argparse
import gzip
import json
import pathlib
import sys

import numpy as np
from tokenizers import Tokenizer

try:
    from pyarrow import ArrowException
except ImportError:  # pyarrow is only needed for parquet sources
    ArrowException = OSError

# Sources disagree on the field name: fineweb uses "text", codeparrot-clean
# stores the file body under "content".
TEXT_KEYS = ("text", "content", "raw_content")


def iter_texts(path: pathlib.Path):
    """Yield documents from one staged shard, whatever format it is in."""
    if path.suffix == ".parquet":
        import pyarrow.parquet as pq

        for batch in pq.ParquetFile(path).iter_batches(batch_size=1024):
            names = batch.schema.names
            key = next((k for k in TEXT_KEYS if k in names), None)
            if key is None:
                # Never return quietly here. smollm's python-edu parquet is a
                # metadata index (blob_id, repo_name, path, score) with no text
                # at all, and a silent return made it look like a finished
                # source that had simply produced zero tokens.
                raise ValueError(f"{path.name}: no text column among {names}")
            for text in batch.column(key).to_pylist():
                if text:
                    yield text
    elif path.name.endswith(".json.gz"):
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                for key in TEXT_KEYS:
                    text = rec.get(key)
                    if text:
                        yield text
                        break
    elif path.suffix in (".jsonl", ".json"):
        with path.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                text = rec.get("text") or rec.get("content")
                if text:
                    yield text


def source_files(data: pathlib.Path, sources: list[str]) -> list[tuple[str, pathlib.Path]]:
    found: list[tuple[str, pathlib.Path]] = []
    for source in sources:
        root = data / source
        if not root.is_dir():
            print(f"[tokenize] skip {source}: no directory", flush=True)
            continue
        files = sorted(
            p for p in root.rglob("*")
            if p.suffix in (".parquet", ".gz", ".jsonl") and p.is_file()
        )
        print(f"[tokenize] {source}: {len(files)} files", flush=True)
        found.extend((source, p) for p in files)
    return found


class ShardWriter:
    def __init__(self, out: pathlib.Path, shard_tokens: int) -> None:
        self.out = out
        self.shard_tokens = shard_tokens
        self.index_path = out / "index.json"
        self.entries: list[dict] = []
        self.done_files: list[str] = []
        self.skipped_files: list[str] = []
        self.failed_files: list[str] = []
        if self.index_path.exists():
            prior = json.loads(self.index_path.read_text(encoding="utf-8"))
            self.entries = prior.get("shards", [])
            self.done_files = prior.get("done_files", [])
            self.skipped_files = prior.get("skipped_files", [])
            self.failed_files = prior.get("failed_files", [])
            print(f"[tokenize] resuming: {len(self.entries)} shards, "
                  f"{len(self.done_files)} files already done", flush=True)
        self.buffer: list[np.ndarray] = []
        self.pending = 0

    def add(self, ids: list[int]) -> None:
        self.buffer.append(np.asarray(ids, dtype=np.uint16))
        self.pending += len(ids)
        while self.pending >= self.shard_tokens:
            self.flush(self.shard_tokens)

    def flush(self, take: int | None = None) -> None:
        if not self.buffer:
            return
        flat = np.concatenate(self.buffer)
        if take is not None and len(flat) > take:
            self.write(flat[:take])
            rest = flat[take:]
            self.buffer = [rest] if len(rest) else []
            self.pending = len(rest)
        else:
            self.write(flat)
            self.buffer = []
            self.pending = 0

    def write(self, arr: np.ndarray) -> None:
        name = f"shard_{len(self.entries):05d}.bin"
        path = self.out / name
        tmp = path.with_suffix(".bin.tmp")
        arr.tofile(tmp)
        tmp.replace(path)
        self.entries.append({"name": name, "tokens": int(arr.size)})
        self.save_index()
        print(f"[tokenize] wrote {name}  {arr.size/1e6:.1f}M tokens  "
              f"total {sum(e['tokens'] for e in self.entries)/1e9:.2f}B", flush=True)

    def save_index(self) -> None:
        tmp = self.index_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps({
            "shard_tokens": self.shard_tokens,
            "total_tokens": sum(e["tokens"] for e in self.entries),
            "shards": self.entries,
            "done_files": self.done_files,
            "skipped_files": self.skipped_files,
            "failed_files": self.failed_files,
        }, indent=2), encoding="utf-8")
        tmp.replace(self.index_path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tokenizer", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--sources", nargs="*",
                    default=["fineweb-edu", "fineweb", "code"],
                    help="staged sources that actually hold text; smollm's "
                         "python-edu is a metadata index and yields none")
    ap.add_argument("--shard-tokens", type=int, default=200_000_000,
                    help="200M uint16 tokens = 400 MB per shard")
    ap.add_argument("--batch-docs", type=int, default=512)
    ap.add_argument("--worker", type=int, default=0, help="0-based worker id")
    ap.add_argument("--workers", type=int, default=1,
                    help="total workers; each takes files by index %% workers")
    ap.add_argument("--max-files", type=int, default=0, help="smoke: stop after N files")
    ap.add_argument("--retry-failed", action="store_true",
                    help="re-attempt files recorded in failed_files (after repairing them)")
    args = ap.parse_args()

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    # Parallel workers each own a private output dir, so two processes never
    # write the same index. They are merged by the reader side, not here.
    if args.workers > 1:
        out = out / f"worker_{args.worker:02d}"
        out.mkdir(parents=True, exist_ok=True)
    tok = Tokenizer.from_file(args.tokenizer)
    vocab = tok.get_vocab_size(with_added_tokens=True)
    if vocab > 65536:
        print(f"[tokenize] vocabulary {vocab} does not fit uint16", flush=True)
        return 2

    files = source_files(pathlib.Path(args.data), args.sources)
    if args.workers > 1:
        files = [f for i, f in enumerate(files) if i % args.workers == args.worker]
        print(f"[tokenize] worker {args.worker}/{args.workers}: {len(files)} files", flush=True)
    writer = ShardWriter(out, args.shard_tokens)
    done = set(writer.done_files)

    # <eos> separates documents so the model learns a real boundary rather than
    # running one file into the next. Without it, packing produces sequences
    # that are half one document and half another with nothing marking the seam.
    eos = tok.token_to_id("<eos>")

    def emit(texts: list[str]) -> None:
        for enc in tok.encode_batch(texts):
            writer.add(enc.ids + [eos] if eos is not None else enc.ids)

    processed = 0
    skipped = set(writer.skipped_files)
    retry = set() if args.retry_failed else set(writer.failed_files)
    for source, path in files:
        key = f"{source}/{path.name}"
        if key in done or key in skipped or key in retry:
            continue
        batch: list[str] = []
        try:
            for text in iter_texts(path):
                batch.append(text)
                if len(batch) >= args.batch_docs:
                    emit(batch)
                    batch = []
            if batch:
                emit(batch)
        except ValueError as exc:
            # A file with no text column is a source that was never usable,
            # not a finished one. Record it so later runs do not re-read it.
            writer.skipped_files.append(key)
            writer.save_index()
            print(f"[tokenize] SKIP {key}: {exc}", flush=True)
            continue
        except (OSError, ArrowException) as exc:
            # A truncated download parses its footer and then fails part-way
            # through the page stream. That aborted whole workers: 7744255_0
            # to _5 each died ~3.5 h in on one such shard, taking their
            # remaining file sets with them. One bad file must cost one file.
            writer.failed_files.append(key)
            writer.save_index()
            print(f"[tokenize] FAIL {key}: {exc}", flush=True)
            continue

        writer.done_files.append(key)
        writer.save_index()
        processed += 1
        print(f"[tokenize] {key}  running total "
              f"{sum(e['tokens'] for e in writer.entries)/1e9:.2f}B tokens", flush=True)
        if args.max_files and processed >= args.max_files:
            break

    writer.flush()
    total = sum(e["tokens"] for e in writer.entries)
    print(json.dumps({
        "shards": len(writer.entries),
        "total_tokens": total,
        "approx_gb": round(total * 2 / 1e9, 1),
        "files_this_run": processed,
    }, indent=2), flush=True)
    return 0 if total else 1


if __name__ == "__main__":
    sys.exit(main())
