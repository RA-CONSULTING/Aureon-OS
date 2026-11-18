"""Train Aureon's own BPE vocabulary on the Aureon corpus.

Why a private vocab rather than reusing Qwen's: Aureon's code is dense with
identifiers that general tokenizers shred -- `hnc_coherence_field` becomes
five or six tokens, and every one of those is a chance to reproduce the name
slightly wrong. Merges learned from this corpus keep such names whole, which
shortens every sequence and makes symbol names cheaper to emit exactly.

Trains on the `train` split only; the holdout stays unseen, so its
compression figure is an honest one.

    python train_tokenizer.py --corpus ../corpus --out aureon_tokenizer.json
"""

from __future__ import annotations

import argparse
import json
import pathlib

from tokenizers import Regex, Tokenizer, decoders, models, pre_tokenizers, trainers

SPECIALS = ["<pad>", "<eos>", "<bos>", "<unk>"]

# A leading space is folded into the following punctuation so " ," stays one
# unit, matching how the text actually appears. Byte-level follows, so any
# byte sequence remains encodable and nothing is ever <unk>.
CODE_PATTERN = (
    r"[A-Za-z_][A-Za-z0-9_]*"      # identifiers kept whole
    r"|\d{1,3}"                     # short digit runs, not whole long numbers
    r"| ?[^\sA-Za-z0-9_]+"          # operators and punctuation
    r"|\s+"                         # whitespace runs
)


def build(vocab_size: int, min_frequency: int) -> Tokenizer:
    tok = Tokenizer(models.BPE(unk_token="<unk>"))
    tok.pre_tokenizer = pre_tokenizers.Sequence([
        # Regex(), not a bare str: Split treats a plain string as a literal
        # separator, so passing the pattern as str makes it match nothing and
        # hands BPE each whole file as one enormous "word".
        pre_tokenizers.Split(pattern=Regex(CODE_PATTERN), behavior="isolated", invert=False),
        pre_tokenizers.ByteLevel(add_prefix_space=False, use_regex=False),
    ])
    tok.decoder = decoders.ByteLevel()
    return tok


def iter_records(corpus: pathlib.Path, split: str):
    with (corpus / "files.jsonl").open(encoding="utf-8") as fh:
        for line in fh:
            rec = json.loads(line)
            if rec.get("split", "train") != split:
                continue
            text = rec.get("text") or ""
            if text:
                yield rec["path"], rec["ext"], text


def train(tok: Tokenizer, corpus: pathlib.Path, split: str, budget_bytes: int,
          vocab_size: int, min_frequency: int) -> int:
    def corpus_iter():
        used = 0
        for _path, _ext, text in iter_records(corpus, split):
            if used >= budget_bytes:
                return
            used += len(text.encode("utf-8"))
            yield text

    trainer = trainers.BpeTrainer(
        vocab_size=vocab_size,
        min_frequency=min_frequency,
        special_tokens=SPECIALS,
        initial_alphabet=pre_tokenizers.ByteLevel.alphabet(),
        show_progress=False,
    )
    tok.train_from_iterator(corpus_iter(), trainer=trainer)
    return tok.get_vocab_size()


def measure(tok: Tokenizer, corpus: pathlib.Path, split: str, limit_bytes: int) -> dict:
    per_ext: dict[str, list[int]] = {}
    used = 0
    for _path, ext, text in iter_records(corpus, split):
        if used >= limit_bytes:
            break
        used += len(text.encode("utf-8"))
        bucket = per_ext.setdefault(ext or "?", [0, 0])
        bucket[0] += len(text)
        bucket[1] += len(tok.encode(text).ids)

    rows = {
        ext: {
            "chars": c,
            "tokens": t,
            "chars_per_token": round(c / t, 3) if t else 0.0,
        }
        for ext, (c, t) in sorted(per_ext.items(), key=lambda kv: -kv[1][0])[:8]
    }
    total_chars = sum(c for c, _ in per_ext.values())
    total_tokens = sum(t for _, t in per_ext.values())
    return {
        "split": split,
        "bytes_measured": used,
        "chars_per_token": round(total_chars / total_tokens, 3) if total_tokens else 0.0,
        "tokens_for_measured_text": total_tokens,
        "by_ext": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--out", required=True, help="path to write tokenizer.json")
    ap.add_argument("--vocab-size", type=int, default=65536)
    ap.add_argument("--min-frequency", type=int, default=2)
    ap.add_argument("--sample-mb", type=int, default=256, help="training text budget")
    ap.add_argument("--probe-mb", type=int, default=8, help="holdout text budget")
    args = ap.parse_args()

    corpus = pathlib.Path(args.corpus)
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    tok = build(args.vocab_size, args.min_frequency)
    actual = train(tok, corpus, "train", args.sample_mb * 1024 * 1024,
                   args.vocab_size, args.min_frequency)

    # Self-check: a tokenizer that cannot reproduce its input byte-for-byte is
    # broken, and that failure is silent until generation time.
    probe = "def hnc_coherence_field(self, *, alpha=0.5) -> float:\n    return 42\n"
    round_trip_ok = tok.decode(tok.encode(probe).ids) == probe

    tok.save(str(out))

    report = {
        "vocab_size": actual,
        "vocab_requested": args.vocab_size,
        "round_trip_ok": round_trip_ok,
        "identifiers": {
            name: len(tok.encode(name).ids)
            for name in (
                "hnc_coherence_field",
                "aureon_swarm_search",
                "reconstruction_error",
                "self_coder_benchmark",
                "x",
            )
        },
        "holdout": measure(tok, corpus, "holdout", args.probe_mb * 1024 * 1024),
    }
    (out.with_suffix(".report.json")).write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    return 0 if round_trip_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
