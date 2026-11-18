"""Harvest Zenodo metadata, then pull only the files worth the bytes.

Two stages on purpose. The API is cheap -- metadata for millions of records is
a few GB of JSON -- while the files behind those records run to petabytes and
are mostly irrelevant to a code model. Stage 1 records what exists; stage 2
decides what is worth disk.

    fetch_zenodo.py --probe
    fetch_zenodo.py --harvest --out /projects/u6vs/zenodo
    fetch_zenodo.py --harvest --type dataset --out /projects/u6vs/zenodo
    fetch_zenodo.py --stats --meta /projects/u6vs/zenodo/meta.jsonl
    fetch_zenodo.py --pull  --meta /projects/u6vs/zenodo/meta.jsonl --budget-gb 200

Three API behaviours drive the design, all measured on 2026-10-26:

* `size=100` is rejected with HTTP 400; `size=25` is accepted. PAGE is 25.
* The result window is 10,000 (Elasticsearch from+size). At size=25 page 400 is
  fine and page 401 is 400, so no single query can return more than 10k records.
  Queries above that are partitioned by publication year, then by month.
* A bare `q=limit order book` is an OR match: it reports 354k hits, almost all
  records that merely contain the word "order". Phrase-quoting is therefore the
  default -- it turns that 354k into 79 records actually about limit order
  books. `--no-phrase` restores the OR behaviour if it is ever wanted.
* Throttled requests answer with a body that has no "hits" key at all, so an
  unchecked caller sees a KeyError rather than a rate limit. _request backs off
  on 429 explicitly.

Only public records are pulled. Restricted and embargoed records stay in the
metadata so the shape of what exists is known, then are skipped at download
time -- their bytes are not obtainable, by design of the archive.
"""

from __future__ import annotations

import argparse
import calendar
import json
import pathlib
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://zenodo.org/api/records"
UA = "aureon-research/1.0 (research corpus staging; contact gary@aureonzorzatechnologies.com)"
PAGE = 25
RATE_SLEEP = 1.5  # anonymous throttling answered HTTP 429 at ~2 req/s
WINDOW = 10_000  # Elasticsearch refuses from+size beyond this
FIRST_YEAR = 2000
CURRENT_YEAR = 2026

# Phrase queries. Totals were measured on 2026-10-26 (all types / datasets only):
# limit order book 79/14, order book 261/26, high frequency trading 180/6,
# market microstructure 491/69, tick data 59, order flow 161, stock prices
# 6127/5315, stock market 8451/5419, cryptocurrency 5018/244, bitcoin 3718/365,
# ohlcv 87/46, intraday 959/64, trading strategy 629/14, backtesting 380/33,
# price prediction 677/40, exchange rates 1102/114, volatility 9080/508.
DEFAULT_QUERIES = [
    "limit order book",
    "order book",
    "high frequency trading",
    "market microstructure",
    "financial time series",
    "tick data",
    "order flow",
    "stock prices",
    "stock market",
    "cryptocurrency",
    "bitcoin",
    "ohlcv",
    "intraday",
    "trading strategy",
    "backtesting",
    "price prediction",
    "exchange rates",
    "volatility",
]

# .md and .pdf matter: a probe of real records showed the payload is usually a
# README plus a paper, not a tidy CSV. PDFs need text extraction later, but
# storing them now is cheap and extraction can happen once, off-cluster.
# Office and spreadsheet formats are included because they hold prose and tables
# (1,117 .docx and 507 .xlsx in the harvest); images and video are not, since a
# text model has no use for them.
TEXT_EXT = (
    ".csv", ".tsv", ".parquet", ".json", ".jsonl", ".txt", ".md",
    ".zip", ".gz", ".tar", ".bz2", ".xz", ".zst", ".7z",
    ".pdf", ".docx", ".doc", ".xlsx", ".xls", ".ods", ".ots", ".rtf", ".tex",
)


def _request(params: dict, tries: int = 6) -> dict:
    url = f"{API}?{urllib.parse.urlencode(params)}"
    last: Exception | None = None
    for attempt in range(tries):
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            if "hits" not in body:
                # Throttled and error bodies are valid JSON without "hits".
                raise RuntimeError(f"no hits in response: {str(body)[:200]}")
            return body
        except urllib.error.HTTPError as exc:
            last = exc
            time.sleep(30 * (attempt + 1) if exc.code == 429 else 2 * (attempt + 1))
        except Exception as exc:  # noqa: BLE001 - retry anything transient
            last = exc
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"request failed after {tries} tries: {url}: {last}")


def _search(query: str, page: int, type_filter: str | None) -> dict:
    params = {"q": query, "size": PAGE, "page": page, "sort": "mostrecent"}
    if type_filter:
        params["type"] = type_filter
    return _request(params)


def _total(query: str, type_filter: str | None) -> int:
    body = _search(query, 1, type_filter)
    return int((body.get("hits") or {}).get("total") or 0)


def _phrase(query: str) -> str:
    """Quote a plain query so it matches as a phrase, not as an OR of its words."""
    return query if query.startswith('"') else f'"{query}"'


def trim(rec: dict, query: str) -> dict:
    md = rec.get("metadata") or {}
    access = rec.get("access") or {}
    lic = md.get("license")
    if isinstance(lic, dict):
        lic = lic.get("id") or lic.get("title")
    files = []
    for f in rec.get("files") or []:
        links = f.get("links") or {}
        files.append({
            "key": f.get("key"),
            "size": f.get("size") or 0,
            "url": links.get("self"),
        })
    rtype = md.get("resource_type") or {}
    return {
        "id": rec.get("id"),
        "doi": rec.get("doi") or md.get("doi"),
        "title": (md.get("title") or "")[:300],
        "date": md.get("publication_date"),
        "type": rtype.get("type") if isinstance(rtype, dict) else rtype,
        "access": access.get("files") or md.get("access_right"),
        "license": lic,
        "files": files,
        "query": query,
    }


def probe() -> int:
    data = _search('"limit order book"', 1, None)
    hits = data.get("hits") or {}
    print("phrase total:", hits.get("total"))
    recs = hits.get("hits") or []
    if not recs:
        print("no records returned")
        return 1
    one = trim(recs[0], "probe")
    print("trimmed keys:", sorted(one))
    print("id:", one["id"], "access:", one["access"], "type:", one["type"])
    print("files:", one["files"][:3])
    return 0


def plan(query: str, type_filter: str | None) -> list[tuple[str, int]]:
    """Split a query into slices small enough for the 10k result window."""
    total = _total(query, type_filter)
    if total <= WINDOW:
        return [(query, total)]
    print(f"  {query} has {total} hits > {WINDOW}; splitting by date", flush=True)
    slices: list[tuple[str, int]] = []
    for year in range(FIRST_YEAR, CURRENT_YEAR + 1):
        qy = f"{query} AND publication_date:[{year}-01-01 TO {year}-12-31]"
        ty = _total(qy, type_filter)
        time.sleep(RATE_SLEEP)
        if ty == 0:
            continue
        if ty <= WINDOW:
            slices.append((qy, ty))
            continue
        for month in range(1, 13):
            last = calendar.monthrange(year, month)[1]
            qm = f"{query} AND publication_date:[{year}-{month:02d}-01 TO {year}-{month:02d}-{last:02d}]"
            tm = _total(qm, type_filter)
            time.sleep(RATE_SLEEP)
            if tm == 0:
                continue
            if tm > WINDOW:
                print(f"  warning: {year}-{month:02d} alone has {tm} hits; taking newest {WINDOW}", flush=True)
            slices.append((qm, min(tm, WINDOW)))
    return slices


def harvest(queries: list[str], out: pathlib.Path, max_records: int,
            type_filter: str | None, phrase: bool) -> int:
    out.parent.mkdir(parents=True, exist_ok=True)
    seen: set = set()
    written = 0
    if out.exists():
        with out.open(encoding="utf-8") as fh:
            for line in fh:
                try:
                    seen.add(json.loads(line)["id"])
                except (ValueError, KeyError):
                    continue
        print(f"resuming: {len(seen)} records already harvested", flush=True)

    with out.open("a", encoding="utf-8") as fh:
        for query in queries:
            q = _phrase(query) if phrase else query
            query_new = 0
            for slice_q, total in plan(q, type_filter):
                page = 1
                while True:
                    try:
                        data = _search(slice_q, page, type_filter)
                    except Exception as exc:  # noqa: BLE001
                        print(f"  page {page} failed: {exc}", flush=True)
                        break
                    recs = (data.get("hits") or {}).get("hits") or []
                    if not recs:
                        break
                    for rec in recs:
                        rid = rec.get("id")
                        if rid in seen:
                            continue
                        seen.add(rid)
                        fh.write(json.dumps(trim(rec, query), ensure_ascii=False) + "\n")
                        written += 1
                        query_new += 1
                    fh.flush()
                    if len(recs) < PAGE:
                        break
                    if max_records and written >= max_records:
                        print(f"reached --max-records {max_records}", flush=True)
                        return written
                    page += 1
                    time.sleep(RATE_SLEEP)
            print(f"{query!r}: +{query_new} new (total {len(seen)})", flush=True)
    return written


def load_meta(path: pathlib.Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
    return rows


def stats(path: pathlib.Path) -> int:
    rows = load_meta(path)
    by_access: dict[str, int] = {}
    by_type: dict[str, int] = {}
    by_ext: dict[str, int] = {}
    total_bytes = 0
    files = 0
    for row in rows:
        by_access[str(row.get("access"))] = by_access.get(str(row.get("access")), 0) + 1
        by_type[str(row.get("type"))] = by_type.get(str(row.get("type")), 0) + 1
        for f in row.get("files") or []:
            files += 1
            total_bytes += int(f.get("size") or 0)
            key = str(f.get("key") or "")
            ext = pathlib.PurePosixPath(key).suffix.lower() or "(none)"
            by_ext[ext] = by_ext.get(ext, 0) + 1
    print(json.dumps({
        "records": len(rows),
        "files": files,
        "total_gb": round(total_bytes / 1e9, 1),
        "by_access": dict(sorted(by_access.items(), key=lambda kv: -kv[1])),
        "by_type": dict(sorted(by_type.items(), key=lambda kv: -kv[1])[:10]),
        "by_ext": dict(sorted(by_ext.items(), key=lambda kv: -kv[1])[:12]),
    }, indent=2))
    return 0


def plan_pull(meta: pathlib.Path, max_file_gb: float, exts: tuple[str, ...]) -> int:
    """Project what --pull would actually download, without downloading it.

    The nominal total is misleading: it counts restricted records whose bytes
    cannot be fetched, extensions nobody wants, and single files larger than the
    per-file cap. This reports the bill first.
    """
    cap = int(max_file_gb * 1e9) if max_file_gb > 0 else 0
    keep = 0
    keep_bytes = 0
    by_ext: dict[str, list[int]] = {}
    dropped_ext: dict[str, int] = {}
    skip = {"restricted": [0, 0], "ext": [0, 0], "too_big": [0, 0], "no_url": [0, 0]}
    for row in load_meta(meta):
        open_access = str(row.get("access")).lower() in ("public", "open")
        for f in row.get("files") or []:
            key = str(f.get("key") or "")
            size = int(f.get("size") or 0)
            ext = pathlib.PurePosixPath(key).suffix.lower() or "(none)"
            if not f.get("url") or not size:
                skip["no_url"][0] += 1
                skip["no_url"][1] += size
                continue
            if not open_access:
                skip["restricted"][0] += 1
                skip["restricted"][1] += size
                continue
            if exts and ext not in exts:
                skip["ext"][0] += 1
                skip["ext"][1] += size
                dropped_ext[ext] = dropped_ext.get(ext, 0) + size
                continue
            if cap and size > cap:
                skip["too_big"][0] += 1
                skip["too_big"][1] += size
                continue
            keep += 1
            keep_bytes += size
            slot = by_ext.setdefault(ext, [0, 0])
            slot[0] += 1
            slot[1] += size
    print(json.dumps({
        "pullable_files": keep,
        "pullable_gb": round(keep_bytes / 1e9, 1),
        "by_ext_gb": {k: round(v[1] / 1e9, 1)
                      for k, v in sorted(by_ext.items(), key=lambda kv: -kv[1][1])[:12]},
        "dropped_by_ext_gb": {k: round(v / 1e9, 1)
                              for k, v in sorted(dropped_ext.items(), key=lambda kv: -kv[1])[:10]},
        "skipped": {k: {"files": v[0], "gb": round(v[1] / 1e9, 1)} for k, v in skip.items()},
    }, indent=2))
    return 0


def verify(meta: pathlib.Path, out: pathlib.Path) -> int:
    """Compare every file on disk against the size the metadata promised.

    Three states matter and only one is safe to resume: a file smaller than
    expected is a partial (`curl -C -` continues it), a file of exactly the
    expected size is done, and a file *larger* than expected is corrupt -- that
    is what two concurrent writers produce, and resuming it can never succeed.
    """
    ok = partial = oversize = 0
    corrupt = []
    for row in load_meta(meta):
        if str(row.get("access")).lower() not in ("public", "open"):
            continue
        for f in row.get("files") or []:
            key = str(f.get("key") or "")
            size = int(f.get("size") or 0)
            if not size:
                continue
            dest = out / str(row["id"]) / key
            if not dest.exists():
                continue
            got = dest.stat().st_size
            if got == size:
                ok += 1
            elif got < size:
                partial += 1
            else:
                oversize += 1
                corrupt.append((dest, got, size))
    print(json.dumps({
        "complete": ok,
        "partial_in_flight": partial,
        "oversized_or_corrupt": oversize,
    }, indent=2))
    for dest, got, size in corrupt[:20]:
        print(f"  CORRUPT {dest.relative_to(out)}: {got} bytes, expected {size} (+{got - size})")
    return 0 if not oversize else 2


def curl(url: str, dest: pathlib.Path) -> bool:
    import subprocess

    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "curl", "-fL", "-C", "-",
        "--retry", "5", "--retry-delay", "5", "--retry-all-errors",
        "--speed-limit", "1024", "--speed-time", "60",
        "--connect-timeout", "30",
        "-o", str(dest), url,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"    curl {proc.returncode}: {proc.stderr.strip()[:160]}", flush=True)
        return False
    return True


def pull(meta: pathlib.Path, out: pathlib.Path, budget_gb: float,
         max_file_gb: float, exts: tuple[str, ...]) -> int:
    budget = int(budget_gb * 1e9) if budget_gb > 0 else 0
    cap = int(max_file_gb * 1e9) if max_file_gb > 0 else 0
    out.mkdir(parents=True, exist_ok=True)
    done_path = out / "pulled.jsonl"
    done: set = set()
    got = 0
    if done_path.exists():
        with done_path.open(encoding="utf-8") as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                done.add((rec["id"], rec["key"]))
                got += int(rec.get("bytes") or 0)
        print(f"resuming: {len(done)} files, {got / 1e9:.1f} GB already pulled", flush=True)

    with done_path.open("a", encoding="utf-8") as fh:
        for row in load_meta(meta):
            if budget and got >= budget:
                print(f"budget reached: {got / 1e9:.1f} GB", flush=True)
                break
            if str(row.get("access")).lower() not in ("public", "open"):
                continue
            for f in row.get("files") or []:
                key = str(f.get("key") or "")
                size = int(f.get("size") or 0)
                url = f.get("url")
                if not url or not size:
                    continue
                if (row["id"], key) in done:
                    continue
                if cap and size > cap:
                    continue
                if exts and pathlib.PurePosixPath(key).suffix.lower() not in exts:
                    continue
                dest = out / str(row["id"]) / key
                if dest.exists() and dest.stat().st_size == size:
                    continue
                print(f"  {row['id']}/{key}  {size / 1e6:.1f} MB", flush=True)
                if not curl(url, dest):
                    continue
                got += size
                fh.write(json.dumps({
                    "id": row["id"], "key": key, "bytes": size,
                    "type": row.get("type"), "license": row.get("license"),
                    "title": row.get("title"),
                }, ensure_ascii=False) + "\n")
                fh.flush()
    print(f"pulled {got / 1e9:.2f} GB into {out}", flush=True)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--harvest", action="store_true")
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--plan", action="store_true",
                    help="project what --pull would download, using --max-file-gb/--exts")
    ap.add_argument("--verify", action="store_true",
                    help="compare on-disk files against metadata sizes; exit 2 if any is oversized")
    ap.add_argument("--pull", action="store_true")
    ap.add_argument("--query", action="append", default=None,
                    help="repeatable; defaults to the measured finance phrase set")
    ap.add_argument("--type", default="any",
                    help="Zenodo resource type filter: any, dataset, publication, ...")
    ap.add_argument("--no-phrase", action="store_true",
                    help="send the query as a loose OR match instead of a phrase")
    ap.add_argument("--out", default="zenodo")
    ap.add_argument("--meta", default="zenodo/meta.jsonl")
    ap.add_argument("--max-records", type=int, default=0)
    ap.add_argument("--budget-gb", type=float, default=0.0)
    ap.add_argument("--max-file-gb", type=float, default=2.0)
    ap.add_argument("--exts", default=",".join(TEXT_EXT))
    args = ap.parse_args()

    type_filter = None if args.type in ("any", "") else args.type

    if args.probe:
        return probe()
    if args.harvest:
        queries = args.query or DEFAULT_QUERIES
        n = harvest(queries, pathlib.Path(args.out) / "meta.jsonl", args.max_records,
                    type_filter, not args.no_phrase)
        print(f"harvested {n} new records")
        return 0
    if args.stats:
        return stats(pathlib.Path(args.meta))
    if args.plan:
        exts = tuple(e.strip().lower() for e in args.exts.split(",") if e.strip())
        return plan_pull(pathlib.Path(args.meta), args.max_file_gb, exts)
    if args.verify:
        return verify(pathlib.Path(args.meta), pathlib.Path(args.out))
    if args.pull:
        exts = tuple(e.strip().lower() for e in args.exts.split(",") if e.strip())
        return pull(pathlib.Path(args.meta), pathlib.Path(args.out), args.budget_gb,
                    args.max_file_gb, exts)
    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
