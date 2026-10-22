"""🕸 API COMMUNION — shared SENSE layer for all Aureon Fusion data organs.

Auris node discipline: every outbound HTTP fetch from a data organ routes
through this module so the fleet behaves as one courteous organism instead
of N independent pollers.

Per-URL disk+memory cache with TTL · conditional GETs (ETag / Last-Modified,
304 => cached body) · per-host rate limiting (FIFO, never exceed the minimum
host interval) · exponential backoff with jitter (Retry-After honored) ·
circuit breaker (5 consecutive failures => 10 min open; stale cache served
while open; closes on next success) · timeouts · per-host stats · per-host
daily live-call budget counter with a default ceiling of 3000 live calls per
UTC day per host (AUREON_COMMUNION_DAILY_BUDGET). When the ceiling is hit the
host is served cache-only (stale-if-present) with reason
'daily_budget_exhausted' and no network traffic is generated.

Stdlib-first (urllib). Windows-safe (atomic tmp+replace writes, utf-8).
Import-time side effects are limited to ensuring the cache directory exists —
nothing is fetched at import.

CLI:
    python -m aureon_fusion.api_communion stats   # per-host call statistics
    python -m aureon_fusion.api_communion clear   # drop cache + stats
"""

import hashlib
import json
import os
import random
import sys
import threading
import time
from pathlib import Path
from typing import Optional
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse

from .paths import FUSION_STATE

CACHE_DIR = FUSION_STATE / "api_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
STATS_FILE = CACHE_DIR / "communion_stats.json"

DEFAULT_TIMEOUT = 10.0
DEFAULT_MIN_HOST_INTERVAL = 2.0  # seconds between LIVE calls to the same host
BACKOFF_BASE_S = 2.0
BACKOFF_CAP_S = 120.0
BACKOFF_JITTER = 0.25
BREAKER_THRESHOLD = 5            # consecutive failures before opening
BREAKER_OPEN_S = 600.0           # circuit stays open 10 minutes
STATS_SAVE_INTERVAL_S = 5.0

USER_AGENT = "AureonFusion-ApiCommunion/1.0 (SENSE-layer; shared-cache polling)"

_lock = threading.Lock()
_mem_cache: dict = {}   # url -> (fetched_at, body)
_hosts: dict = {}       # host -> mutable state dict
_stats_dirty_at = 0.0


def _new_host_state():
    return {
        "ticket": 0.0,            # next free slot for a live call (FIFO)
        "fails": 0,
        "next_allowed": 0.0,      # earliest live call after a failure
        "breaker_until": 0.0,     # circuit open until this time
        "probing": False,         # half-open: one probe call allowed
        "stats": {
            "live_calls": 0,
            "cache_hits": 0,
            "not_modified": 0,
            "refused_by_breaker": 0,
            "daily_budget_refusals": 0,
            # Daily budget accounting (UTC-day scoped, enforced below):
            "daily_date": "",          # YYYY-MM-DD the counters belong to
            "daily_live_calls": 0,     # live calls counted against the budget
            "daily_over_budget": 0,    # live calls beyond the daily budget
        },
    }


def _daily_budget():
    """Per-host daily live-call budget from AUREON_COMMUNION_DAILY_BUDGET.
    Default 3000 (conservative ceiling). Explicit 0/off/none disables the
    ceiling and allows unlimited live calls."""
    raw = os.environ.get("AUREON_COMMUNION_DAILY_BUDGET", "3000").strip()
    if raw.lower() in {"", "0", "off", "none"}:
        return None
    try:
        return max(1, int(raw))
    except ValueError:
        return None


def _bump_daily(st: dict):
    """Count one live call against the host's UTC-day budget. Stats only;
    never refuses or delays. Caller may hold _lock or not (re-acquires)."""
    today = time.strftime("%Y-%m-%d", time.gmtime())
    with _lock:
        s = st["stats"]
        if s.get("daily_date") != today:
            s["daily_date"] = today
            s["daily_live_calls"] = 0
            s["daily_over_budget"] = 0
        s["daily_live_calls"] = int(s.get("daily_live_calls", 0)) + 1
        budget = _daily_budget()
        if budget is not None and s["daily_live_calls"] > budget:
            s["daily_over_budget"] = int(s.get("daily_over_budget", 0)) + 1


# Aggregate counters are accumulated into the persisted stats file and then
# zeroed in memory. Daily counters are authoritative in memory (they are
# date-scoped and must survive per-call flushes so the daily ceiling is
# enforced correctly).
_AGGREGATE_STAT_KEYS = {
    "live_calls",
    "cache_hits",
    "not_modified",
    "refused_by_breaker",
    "daily_budget_refusals",
}
_DAILY_COUNT_KEYS = {"daily_live_calls", "daily_over_budget"}


def _host_state(host: str) -> dict:
    st = _hosts.get(host)
    if st is None:
        st = _new_host_state()
        # Seed today's daily counters from the persisted file so a process
        # restart does not reset the daily budget to zero.
        today = time.strftime("%Y-%m-%d", time.gmtime())
        try:
            data = _load_stats_file()
            persisted = data.get(host, {})
            if persisted.get("daily_date") == today:
                st["stats"]["daily_date"] = today
                for key in _DAILY_COUNT_KEYS:
                    st["stats"][key] = int(persisted.get(key, 0))
        except Exception:
            pass
        _hosts[host] = st
    return st


# ───────────────────────────── disk cache ──────────────────────────────────

def _cache_path(url: str) -> Path:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]
    return CACHE_DIR / f"{digest}.json"


def _read_disk(url: str):
    """Return (fetched_at, etag, last_modified, body) or None."""
    path = _cache_path(url)
    try:
        with open(path, "r", encoding="utf-8") as f:
            rec = json.load(f)
        return (float(rec.get("fetched_at", 0.0)),
                rec.get("etag") or None,
                rec.get("last_modified") or None,
                rec.get("body"))
    except Exception:
        return None


def _write_disk(url: str, fetched_at: float, etag, last_modified, body):
    rec = {
        "url": url,
        "fetched_at": fetched_at,
        "etag": etag or "",
        "last_modified": last_modified or "",
        "body": body,
    }
    path = _cache_path(url)
    tmp = path.with_suffix(".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False)
        os.replace(tmp, path)
    except Exception:
        try:
            if tmp.exists():
                tmp.unlink()
        except Exception:
            pass


# ───────────────────────────── stats ───────────────────────────────────────

def _load_stats_file() -> dict:
    try:
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_stats_file():
    global _stats_dirty_at
    data = _load_stats_file()
    with _lock:
        for host, st in _hosts.items():
            merged = dict(data.get(host, {}))
            for k, v in st["stats"].items():
                if k == "daily_date":
                    continue
                if k in _AGGREGATE_STAT_KEYS:
                    if isinstance(v, int):
                        merged[k] = int(merged.get(k, 0)) + int(v)
                elif k in _DAILY_COUNT_KEYS:
                    merged[k] = int(v)
            # Daily accounting is UTC-day scoped: a date change starts a
            # fresh counter in the persisted file.
            day = st["stats"].get("daily_date")
            if day:
                if merged.get("daily_date") != day:
                    merged["daily_date"] = day
                    for key in _DAILY_COUNT_KEYS:
                        merged[key] = 0
            data[host] = merged
        for st in _hosts.values():
            # Zero only aggregate counters; keep daily counters in memory so
            # the budget ceiling remains accurate between flushes.
            for k in _AGGREGATE_STAT_KEYS:
                st["stats"][k] = 0
    tmp = STATS_FILE.with_suffix(".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, STATS_FILE)
    except Exception:
        pass
    _stats_dirty_at = time.time()


def _touch_stats():
    global _stats_dirty_at
    if time.time() - _stats_dirty_at > STATS_SAVE_INTERVAL_S:
        _save_stats_file()


def stats_snapshot() -> dict:
    """Persisted totals merged with in-memory counters not yet flushed."""
    _save_stats_file()
    return _load_stats_file()


def clear_all():
    """Drop every cached response and reset stats."""
    for p in CACHE_DIR.glob("*.json"):
        try:
            p.unlink()
        except Exception:
            pass
    for p in (STATS_FILE,):
        try:
            p.unlink()
        except Exception:
            pass
    with _lock:
        _mem_cache.clear()
        for st in _hosts.values():
            st["stats"] = _new_host_state()["stats"]
            st["fails"] = 0
            st["breaker_until"] = 0.0
            st["next_allowed"] = 0.0


# ───────────────────────────── core fetch ──────────────────────────────────

def _backoff_delay(fails: int, retry_after=None) -> float:
    if retry_after is not None:
        try:
            return max(1.0, min(float(retry_after), 300.0))
        except (TypeError, ValueError):
            pass
    delay = min(BACKOFF_CAP_S, BACKOFF_BASE_S * (2.0 ** max(0, fails - 1)))
    delay *= 1.0 + random.uniform(0.0, BACKOFF_JITTER)
    return delay


def _serve_stale(url: str, st: dict, reason: str = None):
    """Best-effort stale serving; counts as a cache hit.

    FAIL-CLOSED marker: a stale body is never returned bare — it always
    carries ``stale: true`` and ``stale_age_s`` so no consumer can mistake
    it for live telemetry. Dict bodies get the markers merged in (any
    existing ``source`` tag is preserved); other body shapes are wrapped as
    ``{"stale": …, "stale_age_s": …, "body": …}``. Display/last-known
    consumers may use the value; live-telemetry consumers must treat
    ``stale: true`` as unusable for real-valued fields. If ``reason`` is
    supplied it is emitted as ``budget_reason`` so callers know why the
    live call was skipped.
    """
    cached = _read_disk(url)
    if cached is not None:
        fetched_at, etag, last_modified, body = cached
        with _lock:
            _mem_cache[url] = (fetched_at, body)
            st["stats"]["cache_hits"] += 1
        _touch_stats()
        age_s = max(0.0, time.time() - float(fetched_at or 0.0))
        if isinstance(body, dict):
            marked = dict(body)
            marked.setdefault("source", "stale_cache")
            marked["stale"] = True
            marked["stale_age_s"] = round(age_s, 3)
            if reason:
                marked["budget_reason"] = reason
            return marked
        wrapped = {"stale": True, "stale_age_s": round(age_s, 3),
                   "source": "stale_cache", "body": body}
        if reason:
            wrapped["budget_reason"] = reason
        return wrapped
    return None


def get_json(url: str, ttl_s: float = 60.0, timeout: float = DEFAULT_TIMEOUT,
             headers: dict = None, min_host_interval: float = None,
             bypass_backoff: bool = False):
    """Fetch JSON through the communion cache.

    Returns the parsed JSON body (dict/list/str/…), a cached body when fresh
    or when revalidation answers 304, a stale cached body (always marked
    ``stale: true`` + ``stale_age_s``) when the live call is refused by the
    circuit breaker / backoff and cached data exists, or None when there is
    no usable data. Telemetry consumers must treat ``stale: true`` bodies
    as unusable for real-valued fields.

    ttl_s           freshness window; within it no network traffic occurs
    bypass_backoff  internal escape hatch for deliberate scheme fallbacks
                    (e.g. https->http retry of the same resource)
    """
    data = _commune(url, ttl_s=ttl_s, timeout=timeout, headers=headers,
                    min_host_interval=min_host_interval,
                    bypass_backoff=bypass_backoff, as_text=False)
    if data is None or isinstance(data, str):
        return data
    return data


def get_text(url: str, ttl_s: float = 60.0, timeout: float = DEFAULT_TIMEOUT,
             headers: dict = None, min_host_interval: float = None,
             bypass_backoff: bool = False) -> Optional[str]:
    """Fetch a URL as decoded text (UTF-8, errors replaced) through the
    same cache / rate-limit / backoff / circuit-breaker discipline as
    get_json. Returns None when no usable data exists. A stale cached
    body is returned as a marked dict (``stale: true``, ``stale_age_s``,
    ``body``) — never as bare text that could pass for live."""
    return _commune(url, ttl_s=ttl_s, timeout=timeout, headers=headers,
                    min_host_interval=min_host_interval,
                    bypass_backoff=bypass_backoff, as_text=True)


def _commune(url: str, ttl_s: float, timeout: float, headers: dict,
             min_host_interval: float, bypass_backoff: bool, as_text: bool):
    now = time.time()
    interval = (DEFAULT_MIN_HOST_INTERVAL if min_host_interval is None
                else float(min_host_interval))

    # 1) memory cache
    with _lock:
        mem = _mem_cache.get(url)
        if mem and now - mem[0] < ttl_s:
            _host_state(urlparse(url).netloc)["stats"]["cache_hits"] += 1
        else:
            mem = None
    if mem:
        _touch_stats()
        return mem[1]

    # 2) disk cache
    cached = _read_disk(url)
    etag = last_modified = None
    if cached is not None:
        fetched_at, etag, last_modified, body = cached
        if now - fetched_at < ttl_s:
            with _lock:
                _mem_cache[url] = (fetched_at, body)
                _host_state(urlparse(url).netloc)["stats"]["cache_hits"] += 1
            _touch_stats()
            return body
    else:
        fetched_at, body = 0.0, None

    host = urlparse(url).netloc
    st = _host_state(host)

    # 3) circuit breaker
    if now < st["breaker_until"] and not st["probing"]:
        st["stats"]["refused_by_breaker"] += 1
        _touch_stats()
        return _serve_stale(url, st)

    # 4) failure backoff gate
    if not bypass_backoff and now < st["next_allowed"]:
        return _serve_stale(url, st)

    # 4.5) daily live-call budget ceiling
    budget = _daily_budget()
    today = time.strftime("%Y-%m-%d", time.gmtime())
    s = st["stats"]
    if s.get("daily_date") != today:
        s["daily_date"] = today
        s["daily_live_calls"] = 0
        s["daily_over_budget"] = 0
        s["daily_budget_refusals"] = 0
    if budget is not None and int(s.get("daily_live_calls", 0)) >= budget:
        s["daily_budget_refusals"] = int(s.get("daily_budget_refusals", 0)) + 1
        _touch_stats()
        return _serve_stale(url, st, reason="daily_budget_exhausted")

    # 5) rate limit: FIFO ticket — wait for our slot, never exceed interval
    with _lock:
        slot = max(st["ticket"], time.time())
        st["ticket"] = slot + interval
    wait = slot - time.time()
    while wait > 0:
        time.sleep(min(wait, 0.5))
        wait = slot - time.time()

    # 6) conditional GET
    accept = "*/*" if as_text else "application/json"
    req_headers = {"User-Agent": USER_AGENT, "Accept": accept}
    if headers:
        req_headers.update(headers)
    if etag:
        req_headers["If-None-Match"] = etag
    elif last_modified:
        req_headers["If-Modified-Since"] = last_modified

    req = urlrequest.Request(url, headers=req_headers)
    try:
        with urlrequest.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            new_etag = resp.headers.get("ETag")
            new_lm = resp.headers.get("Last-Modified")
            data = raw if as_text else json.loads(raw)
    except HTTPError as e:
        if e.code == 304:
            # Not modified: cached body stays valid — refresh freshness
            if cached is not None:
                _write_disk(url, time.time(), etag, last_modified, body)
                with _lock:
                    _mem_cache[url] = (time.time(), body)
                    st["stats"]["not_modified"] += 1
                _touch_stats()
                return body
            return None
        retry_after = e.headers.get("Retry-After") if e.headers else None
        return _record_failure(url, st, host, retry_after)
    except (URLError, OSError, ValueError):
        return _record_failure(url, st, host, None)

    # 7) success
    with _lock:
        st["fails"] = 0
        st["next_allowed"] = 0.0
        st["breaker_until"] = 0.0
        st["probing"] = False
        st["stats"]["live_calls"] += 1
        _mem_cache[url] = (time.time(), data)
    _bump_daily(st)  # stats-only daily budget accounting
    _write_disk(url, time.time(), new_etag, new_lm, data)
    _touch_stats()
    return data


def _record_failure(url: str, st: dict, host: str, retry_after):
    now = time.time()
    with _lock:
        st["fails"] += 1
        st["probing"] = False
        delay = _backoff_delay(st["fails"], retry_after)
        st["next_allowed"] = now + delay
        if st["fails"] >= BREAKER_THRESHOLD:
            st["breaker_until"] = now + BREAKER_OPEN_S
    _touch_stats()
    return _serve_stale(url, st)


# ───────────────────────────── CLI ─────────────────────────────────────────

def _print_stats():
    snap = stats_snapshot()
    print("═" * 72)
    print("🕸 API COMMUNION — per-host statistics")
    print("═" * 72)
    if not snap:
        print("  (no traffic recorded yet)")
        return
    budget = _daily_budget()
    budget_hdr = f"{'daily':>7}" + (f"/{budget}" if budget else "")
    print(f"  {'host':<30} {'live':>6} {'hits':>7} {'304s':>6} {'breaker':>8} {'budget':>8} {budget_hdr:>9}")
    for host, s in sorted(snap.items(),
                          key=lambda kv: -kv[1].get("live_calls", 0)):
        over = s.get("daily_over_budget", 0)
        refusals = s.get("daily_budget_refusals", 0)
        daily = f"{s.get('daily_live_calls', 0)}"
        if budget:
            daily += f"/{budget}" + (f" (+{over} over)" if over else "")
        print(f"  {host:<30} {s.get('live_calls', 0):>6} "
              f"{s.get('cache_hits', 0):>7} {s.get('not_modified', 0):>6} "
              f"{s.get('refused_by_breaker', 0):>8} {refusals:>8} {daily:>12}")
    print("═" * 72)
    if budget:
        print(f"  daily budget: {budget} live calls/host/day (enforced; "
              "excess served as stale cache-only)")


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    argv = list(sys.argv[1:] if argv is None else argv)
    verb = argv[0] if argv else "stats"
    if verb == "stats":
        _print_stats()
        return 0
    if verb == "clear":
        clear_all()
        print("api_communion: cache + stats cleared")
        return 0
    print("usage: python -m aureon_fusion.api_communion [stats|clear]",
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
