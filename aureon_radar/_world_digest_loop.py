#!/usr/bin/env python3
"""
World Digest Producer
═══════════════════════════════════════════════════════════════════
Build item: WORLD DIGEST PRODUCER (news / geo / social energy flows).

- Writes aureon-os-upstream/aureon/data_feeds/state/news_geo_digest.json
  every ~10 minutes.
- Sources: GDELT (geopolitical), queen_open_source_data_engine (news/social),
  DefiLlama (funding energy), Ollama cloud (narrative).
- Fail-closed: any source dead -> null + stated reason; digest still writes.
- Rate discipline: GDELT max 1 call / 10 min; Reddit / CryptoCompare max
  1 / 10 min each; HN Algolia max 1 / 10 min; DefiLlama max 1 / 10 min.
- Ollama: uses aureon.ollama_config for base URL / key / headers, caches
  45 min, counts calls, 20-call / day self cap.

Usage:
    PYTHONUTF8=1 PYTHONPATH=../aureon-os-upstream python _world_digest_loop.py --once
    nohup PYTHONUTF8=1 PYTHONPATH=../aureon-os-upstream python _world_digest_loop.py > /tmp/world_digest.log 2>&1 &
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
import sys
import time
import urllib.error
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Put the upstream package on PYTHONPATH if it isn't already.
WORKSPACE = Path(__file__).resolve().parents[1]
UPSTREAM = WORKSPACE / "aureon-os-upstream"
if str(UPSTREAM) not in sys.path:
    sys.path.insert(0, str(UPSTREAM))

# Aureon config for Ollama (secret-safe: we never print the key).
from aureon.ollama_config import (  # noqa: E402
    OLLAMA_CLOUD_NATIVE_BASE_URL,
    OllamaDailyBudgetExceeded,
    check_ollama_daily_budget,
    ensure_ollama_shared_budget,
    is_ollama_cloud_url,
    ollama_authorization_headers,
    resolve_ollama_api_key,
    resolve_ollama_native_base_url,
)
from aureon.queen.queen_open_source_data_engine import (  # noqa: E402
    AIOHTTP_AVAILABLE,
    OpenSourceDataEngine,
)

# ─── PATHS ────────────────────────────────────────────────────────────────────
RADAR = Path(__file__).resolve().parent
STATE_DIR = RADAR / "state"
STATE_DIR.mkdir(exist_ok=True)
OUT_DIR = UPSTREAM / "aureon" / "data_feeds" / "state"
OUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_PATH = OUT_DIR / "news_geo_digest.json"
META_PATH = STATE_DIR / "world_digest_meta.json"
NARRATIVE_CACHE = RADAR / "ollama_cache" / "world_digest_narrative.json"
NARRATIVE_CACHE.parent.mkdir(exist_ok=True)

# ─── CONSTANTS ────────────────────────────────────────────────────────────────
INTERVAL_S = int(os.getenv("WORLD_DIGEST_INTERVAL", "600"))
GDELT_INTERVAL_S = 600
SOURCE_INTERVALS = {
    "gdelt": 600,
    "cryptocompare": 600,
    "reddit": 600,
    "hn_algolia": 600,
    "defillama": 600,
}
OLLAMA_TTL_S = int(os.getenv("WORLD_DIGEST_OLLAMA_TTL", "2700"))  # 45 min
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def iso_to_dt(iso: str) -> datetime:
    return datetime.fromisoformat(iso)


def load_meta() -> Dict[str, Any]:
    if not META_PATH.exists():
        return {
            "last_fetch": {},
            "ollama_calls": {},
            "cycle_errors": [],
        }
    try:
        with open(META_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"last_fetch": {}, "ollama_calls": {}, "cycle_errors": []}


def save_meta(meta: Dict[str, Any]) -> None:
    tmp = META_PATH.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    os.replace(tmp, META_PATH)


def rate_gate_ok(source: str, meta: Dict[str, Any], interval: int) -> bool:
    last = meta.get("last_fetch", {}).get(source)
    if not last:
        return True
    try:
        elapsed = (datetime.now(timezone.utc) - iso_to_dt(last)).total_seconds()
        return elapsed >= interval
    except Exception:
        return True


def mark_fetched(source: str, meta: Dict[str, Any]) -> None:
    meta.setdefault("last_fetch", {})[source] = now_utc()


def prov(source: str, ok: bool, reason: Optional[str] = None, detail: Optional[Dict] = None) -> Dict[str, Any]:
    p: Dict[str, Any] = {
        "source": source,
        "fetched_at": now_utc(),
        "ok": ok,
        "reason": reason if not ok else None,
    }
    if detail:
        p["detail"] = detail
    return p


def http_json(url: str, timeout: int = 25, headers: Optional[Dict[str, str]] = None,
              method: str = "GET", data: Optional[bytes] = None) -> Tuple[Optional[Any], Optional[str]]:
    h = {"User-Agent": UA, "Accept": "application/json"}
    if headers:
        h.update(headers)
    try:
        req = urllib.request.Request(url, headers=h, method=method, data=data)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            if not body:
                return {}, None
            return json.loads(body.decode("utf-8", "replace")), None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}: {e.reason}"
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


# ═══════════════════════════════════════════════════════════════════════════════
# GDELT (geopolitical headlines + geo risk)
# ═══════════════════════════════════════════════════════════════════════════════

NEGATIVE_WORDS = [
    "war", "attack", "sanction", "bomb", "kill", "death", "crisis",
    "conflict", "invasion", "missile", "strike", "tension", "threat",
    "nuclear", "weapon", "fighting", "clash", "protest", "riot",
    "collapse", "crash", "recession", "debt", "default", "tariff",
    "trade war", "embargo", "blockade", "hostage", "terror",
    "assassination", "coup", "rebellion", "uprising", "massacre",
    "genocide", "famine", "disaster", "emergency", "alert",
]

POSITIVE_WORDS = [
    "peace", "agreement", "deal", "cooperation", "treaty", "alliance",
    "partnership", "growth", "recovery", "boom", "prosperity",
    "breakthrough", "success", "victory", "celebration", "unity",
    "dialogue", "negotiation", "compromise", "reconciliation",
]

COUNTRY_MAP = {
    "us": "USA", "united states": "USA", "america": "USA", "washington": "USA",
    "china": "CHN", "chinese": "CHN", "beijing": "CHN",
    "russia": "RUS", "russian": "RUS", "moscow": "RUS", "putin": "RUS",
    "iran": "IRN", "iranian": "IRN", "tehran": "IRN",
    "north korea": "PRK", "dprk": "PRK", "kim": "PRK",
    "ukraine": "UKR", "ukrainian": "UKR", "kyiv": "UKR", "kiev": "UKR",
    "israel": "ISR", "israeli": "ISR", "gaza": "PSE", "palestine": "PSE",
    "turkey": "TUR", "turkish": "TUR", "erdogan": "TUR",
    "syria": "SYR", "assad": "SYR",
    "iraq": "IRQ", "baghdad": "IRQ",
    "afghanistan": "AFG", "taliban": "AFG",
    "venezuela": "VEN", "maduro": "VEN",
    "cuba": "CUB", "havana": "CUB",
    "pakistan": "PAK", "islamabad": "PAK",
    "india": "IND", "indian": "IND", "modi": "IND",
    "japan": "JPN", "japanese": "JPN", "tokyo": "JPN",
    "germany": "DEU", "german": "DEU", "berlin": "DEU",
    "france": "FRA", "french": "FRA", "paris": "FRA",
    "uk": "GBR", "britain": "GBR", "british": "GBR", "london": "GBR",
    "south korea": "KOR", "seoul": "KOR",
    "taiwan": "TWN", "taiwanese": "TWN", "tsmc": "TWN",
    "saudi": "SAU", "riyadh": "SAU",
    "uae": "ARE", "dubai": "ARE", "abu dhabi": "ARE",
    "qatar": "QAT", "doha": "QAT",
    "egypt": "EGY", "cairo": "EGY",
    "libya": "LBY", "tripoli": "LBY",
    "yemen": "YEM", "sanaa": "YEM",
    "somalia": "SOM", "mogadishu": "SOM",
    "ethiopia": "ETH", "addis": "ETH",
    "sudan": "SDN", "khartoum": "SDN",
}


def estimate_tone(title: str) -> float:
    t = title.lower()
    neg = sum(1 for w in NEGATIVE_WORDS if w in t)
    pos = sum(1 for w in POSITIVE_WORDS if w in t)
    return max(-10.0, min(10.0, (pos - neg) * 2.0))


def extract_countries(title: str) -> List[str]:
    t = title.lower()
    found = []
    for kw, code in COUNTRY_MAP.items():
        if kw in t and code not in found:
            found.append(code)
    return found


def fetch_gdelt(meta: Dict[str, Any], force: bool = False) -> Tuple[Optional[List[Dict]], Optional[float], Dict[str, Any]]:
    if not force and not rate_gate_ok("gdelt", meta, GDELT_INTERVAL_S):
        return None, None, prov("gdelt", False, "rate-gated: fetched within last 10 min")

    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=6)
    start_str = start.strftime("%Y%m%d%H%M%S")
    url = (
        "https://api.gdeltproject.org/api/v2/doc/doc"
        "?query=conflict%20OR%20war%20OR%20sanction%20OR%20tension%20OR%20crisis"
        "&mode=ArtList&maxrecords=50&format=json"
        f"&startdatetime={start_str}"
    )

    err = None
    data = None
    for attempt in range(3):
        data, err = http_json(url, timeout=30)
        if data is not None:
            break
        if err and "429" in err and attempt < 2:
            time.sleep(15 * (attempt + 1))
            continue
        break

    if data is None:
        mark_fetched("gdelt", meta)
        return None, None, prov("gdelt", False, err or "empty response")

    articles = data.get("articles", []) if isinstance(data, dict) else []
    events = []
    for art in articles:
        title = art.get("title", "")
        if not title:
            continue
        events.append({
            "title": title,
            "url": art.get("url", ""),
            "source": art.get("source", art.get("domain", "gdelt")),
            "timestamp": art.get("seendate", ""),
            "tone": estimate_tone(title),
            "countries": extract_countries(title),
        })

    if not events:
        mark_fetched("gdelt", meta)
        return None, None, prov("gdelt", False, "no articles returned")

    risk = calculate_geo_risk(events)
    top = sorted(events, key=lambda x: -abs(x.get("tone", 0)))[:10]
    mark_fetched("gdelt", meta)
    return top, risk, prov("gdelt", True, detail={"event_count": len(events), "risk": risk})


def calculate_geo_risk(events: List[Dict]) -> float:
    major_powers = {"USA", "CHN", "RUS", "IRN", "PRK"}
    total_weight = 0.0
    for ev in events:
        weight = max(0.0, -ev.get("tone", 0))
        countries = ev.get("countries", [])
        if len(countries) >= 2:
            weight *= 1.5
        if any(c in major_powers for c in countries):
            weight *= 2.0
        total_weight += weight
    risk = min(100.0, (total_weight / (len(events) * 5)) * 100)
    return round(risk, 2)


# ═══════════════════════════════════════════════════════════════════════════════
# ENGINE-WIRED NEWS & SOCIAL
# ═══════════════════════════════════════════════════════════════════════════════

async def _run_engine_news_social() -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """Run the dormant queen_open_source_data_engine news + social fetchers once.

    Returns (news_payload, social_payload, raw_engine_state).
    """
    engine = OpenSourceDataEngine()
    # Pre-seed a neutral sentiment so news sentiment assignment is safe.
    if engine.sentiment is None:
        from aureon.queen.queen_open_source_data_engine import SentimentData
        engine.sentiment = SentimentData(fear_greed_index=50, fear_greed_label="Neutral")

    news_err = None
    try:
        await engine._fetch_crypto_news()
    except Exception as e:
        news_err = f"{type(e).__name__}: {e}"

    social_err = None
    try:
        await engine._fetch_reddit_sentiment()
    except Exception as e:
        social_err = f"{type(e).__name__}: {e}"

    news_payload = engine.get_news(limit=20)
    social_payload = engine.get_social_sentiment()
    return news_payload, social_payload, {
        "news_error": news_err,
        "social_error": social_err,
        "data_points": engine.data_points_received,
    }


def fetch_engine_news_social(meta: Dict[str, Any], force: bool = False) -> Tuple[Optional[List[Dict]], Optional[Dict], Optional[Dict], Dict[str, Any], Dict[str, Any]]:
    """Returns (crypto_headlines, reddit_social, engine_state, news_prov, social_prov)."""
    if not AIOHTTP_AVAILABLE:
        return None, None, None, prov("cryptocompare", False, "aiohttp not installed"), prov("reddit", False, "aiohttp not installed")

    if not force:
        if not rate_gate_ok("cryptocompare", meta, SOURCE_INTERVALS["cryptocompare"]):
            return None, None, None, prov("cryptocompare", False, "rate-gated"), prov("reddit", False, "rate-gated")

    news_payload, social_payload, raw_state = asyncio.run(_run_engine_news_social())

    mark_fetched("cryptocompare", meta)
    mark_fetched("reddit", meta)

    crypto_headlines = news_payload.get("headlines", []) if isinstance(news_payload, dict) else []
    news_ok = bool(crypto_headlines)
    news_prov = prov(
        "cryptocompare" if news_ok else "cryptocompare",
        news_ok,
        None if news_ok else "fetch yielded no usable headlines (endpoint may require auth or be blocked)",
        detail={"headline_count": len(crypto_headlines)} if news_ok else None,
    )

    reddit = social_payload.get("reddit") if isinstance(social_payload, dict) else None
    reddit_ok = isinstance(reddit, dict) and reddit.get("post_count", 0) > 0
    reddit_prov = prov(
        "reddit_json",
        reddit_ok,
        None if reddit_ok else "fetch yielded no posts (blocked or unreachable from this network)",
        detail={"post_count": reddit.get("post_count") if reddit_ok else 0},
    )

    return crypto_headlines, reddit, raw_state, news_prov, reddit_prov


# ═══════════════════════════════════════════════════════════════════════════════
# HN ALGOLIA SOCIAL FALLBACK
# ═══════════════════════════════════════════════════════════════════════════════

TOKEN_RE = re.compile(
    r"\b(btc|bitcoin|eth|ethereum|sol|solana|xrp|ripple|ada|cardano|doge|"
    r"dogecoin|dot|polkadot|link|chainlink|avax|avalanche|matic|polygon|uni|"
    r"uniswap|atom|cosmos|ltc|litecoin|bch|bitcoin cash)\b",
    re.IGNORECASE,
)


def fetch_hn_social(meta: Dict[str, Any], force: bool = False) -> Tuple[Optional[Dict], Dict[str, Any]]:
    if not force and not rate_gate_ok("hn_algolia", meta, SOURCE_INTERVALS["hn_algolia"]):
        return None, prov("hn_algolia", False, "rate-gated")

    since = int(time.time() - 24 * 3600)
    queries = ["crypto", "bitcoin", "ethereum"]
    all_hits: Dict[str, Dict] = {}
    token_counts: Dict[str, int] = {}

    for q in queries:
        url = (
            "http://hn.algolia.com/api/v1/search?"
            f"query={q}&tags=story&"
            f"numericFilters=created_at_i>{since}&hitsPerPage=20"
        )
        data, err = http_json(url, timeout=20)
        if data is None:
            continue
        for h in data.get("hits", []):
            oid = h.get("objectID")
            if oid and oid not in all_hits:
                all_hits[oid] = h
                text = f"{h.get('title', '')} {h.get('url', '')}"
                for m in TOKEN_RE.findall(text):
                    token = m.upper()
                    token_counts[token] = token_counts.get(token, 0) + 1

    if not all_hits:
        mark_fetched("hn_algolia", meta)
        return None, prov("hn_algolia", False, "no 24h stories matched crypto/bitcoin/ethereum")

    top_tokens = [t for t, _ in sorted(token_counts.items(), key=lambda kv: -kv[1])[:5]]
    mention_volume = len(all_hits)

    mark_fetched("hn_algolia", meta)
    return (
        {
            "source": "hn_algolia",
            "mention_volume": mention_volume,
            "top_tokens": top_tokens,
        },
        prov("hn_algolia", True, detail={"hits_returned": mention_volume, "queries": queries, "top_tokens": top_tokens}),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# DEFILLAMA FUNDING ENERGY
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_funding_energy(meta: Dict[str, Any], force: bool = False) -> Tuple[Optional[Dict], Dict[str, Any]]:
    if not force and not rate_gate_ok("defillama", meta, SOURCE_INTERVALS["defillama"]):
        return None, prov("defillama", False, "rate-gated")

    url = "https://api.llama.fi/protocols"
    data, err = http_json(url, timeout=45)
    if data is None:
        return None, prov("defillama", False, err or "empty response")

    protocols = data if isinstance(data, list) else []
    parsed = []
    for p in protocols:
        tvl = p.get("tvl") or 0
        change_1d = p.get("change_1d") or 0
        if tvl and change_1d:
            parsed.append({
                "name": p.get("name", "unknown"),
                "chain": p.get("chain", "unknown"),
                "tvl_usd": round(float(tvl), 2),
                "change_1d_pct": round(float(change_1d), 4),
                "est_flow_usd": round(float(tvl) * float(change_1d) / 100, 2),
            })

    notable = sorted(parsed, key=lambda x: -abs(x["est_flow_usd"]))[:5]
    total_sampled = round(sum(p["tvl_usd"] for p in parsed), 2) if parsed else None

    mark_fetched("defillama", meta)
    return (
        {
            "source": "defillama_protocols",
            "as_of": now_utc(),
            "notable_flows": notable,
            "total_defi_tvl_sampled_usd": total_sampled,
        },
        prov("defillama", True, detail={"protocols_parsed": len(parsed), "notable_count": len(notable)}),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# OLLAMA NARRATIVE
# ═══════════════════════════════════════════════════════════════════════════════

def build_narrative_prompt(gdelt_headlines: List[Dict], crypto_headlines: List[Dict], funding: Optional[Dict]) -> str:
    lines = ["Current world-energy headlines:"]
    for i, h in enumerate(gdelt_headlines[:5], 1):
        lines.append(f"{i}. {h.get('title','')}")
    if crypto_headlines:
        lines.append("\nCrypto / market headlines:")
        for i, h in enumerate(crypto_headlines[:4], 1):
            lines.append(f"{i}. {h.get('title','')}")
    if funding and funding.get("notable_flows"):
        lines.append("\nNotable DeFi capital flows:")
        for f in funding["notable_flows"][:3]:
            lines.append(f"- {f.get('name','?')}: ${f.get('est_flow_usd',0):,.0f} ({f.get('change_1d_pct',0):+.2f}%)")
    lines.append(
        "\nIn exactly 3 sentences, write a compact narrative synthesizing "
        "geopolitical risk, market/social energy, and capital flow signals. "
        "No bullets, no headings."
    )
    return "\n".join(lines)


def load_cached_narrative() -> Optional[str]:
    if not NARRATIVE_CACHE.exists():
        return None
    try:
        with open(NARRATIVE_CACHE, "r", encoding="utf-8") as f:
            c = json.load(f)
        ts = c.get("ts")
        if not ts:
            return None
        age = (datetime.now(timezone.utc) - iso_to_dt(ts)).total_seconds()
        if age > OLLAMA_TTL_S:
            return None
        return c.get("narrative")
    except Exception:
        return None


def save_cached_narrative(text: str) -> None:
    tmp = NARRATIVE_CACHE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"ts": now_utc(), "narrative": text}, f, ensure_ascii=False)
    os.replace(tmp, NARRATIVE_CACHE)


def _ollama_budget_summary() -> Tuple[int, int, str]:
    """Return (calls_used_today, shared_daily_cap, day) from the shared budget."""
    rec = ensure_ollama_shared_budget()
    cap = int(rec.get("cap", 0))
    remaining = int(rec.get("remaining_calls", 0))
    used = max(0, cap - remaining)
    day = str(rec.get("day") or datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    return used, cap, day


def fetch_ollama_narrative(
    gdelt_headlines: List[Dict],
    crypto_headlines: List[Dict],
    funding: Optional[Dict],
    meta: Dict[str, Any],
    force: bool = False,
) -> Tuple[Optional[str], Dict[str, Any]]:
    cached = load_cached_narrative() if not force else None
    if cached is not None:
        return cached, prov("ollama_cloud", True, detail={"cached": True, "ttl_s": OLLAMA_TTL_S})

    # Resolve cloud endpoint / key via aureon config (never print the key).
    base_url = os.environ.get("OLLAMA_API_URL", OLLAMA_CLOUD_NATIVE_BASE_URL)
    native_url = resolve_ollama_native_base_url(base_url)
    key = resolve_ollama_api_key()

    if is_ollama_cloud_url(native_url) and not key:
        return None, prov("ollama_cloud", False, "api key not configured (OLLAMA_API_KEY / AUREON_OLLAMA_API_KEY)")

    # Shared, cross-consumer Ollama budget: fail-closed, atomic decrement.
    try:
        check_ollama_daily_budget()
    except OllamaDailyBudgetExceeded:
        return None, prov("ollama_cloud", False, "shared_budget_exhausted")

    prompt = build_narrative_prompt(gdelt_headlines, crypto_headlines, funding)
    payload = {
        "model": os.environ.get("OLLAMA_MODEL", DEFAULT_MODEL),
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 220},
    }
    headers = {"Content-Type": "application/json"}
    auth_headers = ollama_authorization_headers(native_url)
    headers.update(auth_headers)

    url = f"{native_url.rstrip('/')}/api/generate"
    body = json.dumps(payload).encode("utf-8")
    data, err = http_json(url, timeout=90, headers=headers, method="POST", data=body)
    if data is None:
        return None, prov("ollama_cloud", False, err or "no response")

    narrative = data.get("response", "").strip() if isinstance(data, dict) else ""
    if not narrative:
        return None, prov("ollama_cloud", False, "empty model response")

    save_cached_narrative(narrative)
    return narrative, prov("ollama_cloud", True, detail={"model": payload["model"], "cached": False})


# ═══════════════════════════════════════════════════════════════════════════════
# BUILD & WRITE DIGEST
# ═══════════════════════════════════════════════════════════════════════════════

def build_digest(force: bool = False) -> Dict[str, Any]:
    meta = load_meta()
    meta["cycle_errors"] = []

    # Ensure the shared Ollama budget is initialized/reset at day start.
    ensure_ollama_shared_budget()

    gdelt_headlines, geo_risk, gdelt_prov = fetch_gdelt(meta, force=force)
    crypto_headlines, reddit, engine_state, news_prov, reddit_prov = fetch_engine_news_social(meta, force=force)
    hn_social, hn_prov = fetch_hn_social(meta, force=force)
    funding, funding_prov = fetch_funding_energy(meta, force=force)

    # Compose social_pulse: prefer Reddit if live, else HN, else None.
    social_pulse = None
    social_prov = prov("social_pulse", False, "no live social source returned data")
    if isinstance(reddit, dict):
        mentions = reddit.get("mentions", {})
        top_tokens = [t for t, _ in sorted(
            ((k, v.get("count", 0)) for k, v in mentions.items()),
            key=lambda kv: -kv[1],
        )[:5]]
        social_pulse = {
            "source": "reddit_json",
            "mention_volume": reddit.get("post_count", 0),
            "top_tokens": top_tokens,
        }
        social_prov = reddit_prov
    elif isinstance(hn_social, dict):
        social_pulse = hn_social
        social_prov = hn_prov

    narrative, ollama_prov = fetch_ollama_narrative(gdelt_headlines or [], crypto_headlines or [], funding, meta, force=force)

    provenance = {
        "gdelt_headlines": gdelt_prov,
        "geo_risk_hint": gdelt_prov if gdelt_headlines is not None else prov("gdelt", False, gdelt_prov.get("reason") or "gdelt unavailable"),
        "social_pulse": social_prov,
        "funding_energy": funding_prov,
        "ollama_narrative": ollama_prov,
    }

    ollama_count, ollama_cap, ollama_day = _ollama_budget_summary()

    digest = {
        "ts": now_utc(),
        "gdelt_headlines": gdelt_headlines,
        "geo_risk_hint": geo_risk,
        "social_pulse": social_pulse,
        "funding_energy": funding,
        "ollama_narrative": narrative,
        "provenance": provenance,
        "meta": {
            "interval_s": INTERVAL_S,
            "ollama_calls_today": ollama_count,
            "ollama_day": ollama_day,
            "ollama_daily_cap": ollama_cap,
            "engine_state": engine_state,
            "cycle_errors": meta["cycle_errors"],
        },
    }

    # Atomically write digest.
    tmp = OUT_PATH.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(digest, f, ensure_ascii=False, indent=2)
    os.replace(tmp, OUT_PATH)

    save_meta(meta)
    return digest


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def next_due_at(meta: Dict[str, Any]) -> float:
    """Return the earliest timestamp at which at least one source may refresh."""
    now = time.time()
    last_fetches = meta.get("last_fetch", {})
    if not last_fetches:
        return now
    earliest_next: Optional[float] = None
    for source, last_iso in last_fetches.items():
        interval = SOURCE_INTERVALS.get(source, INTERVAL_S)
        try:
            last_ts = iso_to_dt(last_iso).timestamp()
        except Exception:
            last_ts = 0.0
        nxt = last_ts + interval
        if earliest_next is None or nxt < earliest_next:
            earliest_next = nxt
    return earliest_next if earliest_next is not None else now


def main() -> None:
    parser = argparse.ArgumentParser(description="World Digest Producer")
    parser.add_argument("--once", action="store_true", help="run one cycle and exit")
    parser.add_argument("--force", action="store_true", help="ignore rate gates (still respects Ollama cap)")
    args = parser.parse_args()

    if args.once:
        digest = build_digest(force=args.force)
        print(json.dumps(digest, ensure_ascii=False, indent=2))
        return

    print(f"[world_digest] loop online — interval {INTERVAL_S}s", flush=True)
    while True:
        meta = load_meta()
        nxt = next_due_at(meta)
        now_ts = time.time()
        if nxt > now_ts:
            wait = nxt - now_ts
            print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] rate-gated; sleeping {wait:.0f}s", flush=True)
            time.sleep(wait)

        started = time.time()
        try:
            build_digest(force=args.force)
            print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] digest written -> {OUT_PATH}", flush=True)
        except Exception as e:
            print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] cycle FAILED: {e}", flush=True)
        elapsed = time.time() - started
        time.sleep(max(5.0, INTERVAL_S - elapsed))


if __name__ == "__main__":
    main()
