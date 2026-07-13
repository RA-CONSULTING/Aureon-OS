"""
Aureon Operator — unified connections catalog.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Every external source Aureon touches — trading exchanges, market data, NASA /
space weather, on-chain / whale feeds, news, notifications, ephemeris — described
in one categorized table. It powers the Connections dashboard, the connectivity
probes, and the "full operational capacity" readiness report.

Seeded from the repo's own definitions so it stays truthful:
  • credential env vars + categories  ← aureon/autonomous/aureon_data_ocean.py
  • secret-key set + aliases          ← aureon/core/aureon_env.py
  • the LLM providers                 ← aureon/operator/provider_catalog.py

No secrets live here — only *where* each credential belongs, how to reach the
source, and what it unlocks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

# ── categories (display order) ────────────────────────────────────────────────
CATEGORIES: Tuple[Tuple[str, str], ...] = (
    ("ai_llm", "AI / LLM models"),
    ("exchange", "Trading exchanges"),
    ("market_data", "Market data & macro"),
    ("space_science", "Space & science (NASA / NOAA / USGS)"),
    ("ephemeris", "Ephemeris & astronomy"),
    ("onchain_whale", "On-chain & whale flow"),
    ("news_social", "News & social"),
    ("notifications", "Notifications"),
)

Requirement = str  # "required" | "optional" | "keyless"


@dataclass(frozen=True)
class Connection:
    id: str
    label: str
    category: str
    requirement: Requirement            # required | optional | keyless
    consumed_by: str                    # operator | trader | both
    credential_env: Tuple[str, ...] = ()   # first is the primary key; rest are secondary
    probe_url: str = ""                 # a cheap GET for the connectivity test
    probe_auth: str = "none"            # none | header | query | bearer
    probe_header: str = ""              # header name when probe_auth == "header"
    probe_query_param: str = "api_key"  # query param name when probe_auth == "query"
    get_keys_url: str = ""
    docs_url: str = ""
    unlocks: str = ""                   # what turning this on gives the system
    notes: str = ""
    secondary_labels: Tuple[str, ...] = field(default_factory=tuple)  # UI labels for extra fields

    @property
    def key_env(self) -> str:
        return self.credential_env[0] if self.credential_env else ""

    @property
    def extra_envs(self) -> Tuple[str, ...]:
        return self.credential_env[1:] if len(self.credential_env) > 1 else ()

    def to_public_dict(self) -> Dict[str, object]:
        return {
            "id": self.id,
            "label": self.label,
            "category": self.category,
            "requirement": self.requirement,
            "consumed_by": self.consumed_by,
            "credential_env": list(self.credential_env),
            "key_env": self.key_env,
            "extra_envs": list(self.extra_envs),
            "secondary_labels": list(self.secondary_labels),
            "has_probe": bool(self.probe_url),
            "get_keys_url": self.get_keys_url,
            "docs_url": self.docs_url,
            "unlocks": self.unlocks,
            "notes": self.notes,
        }


CATALOG: List[Connection] = [
    # ── Trading exchanges (consumed by the trader via .env — delegate writes) ──
    Connection("binance", "Binance", "exchange", "optional", "trader",
               ("BINANCE_API_KEY", "BINANCE_API_SECRET"),
               probe_url="https://api.binance.com/api/v3/ping",
               get_keys_url="https://www.binance.com/en/my/settings/api-management",
               docs_url="https://binance-docs.github.io/apidocs/spot/en/",
               unlocks="Spot/margin order execution + balances + market data",
               secondary_labels=("API secret",)),
    Connection("kraken", "Kraken", "exchange", "optional", "trader",
               ("KRAKEN_API_KEY", "KRAKEN_API_SECRET"),
               probe_url="https://api.kraken.com/0/public/SystemStatus",
               get_keys_url="https://www.kraken.com/u/security/api",
               docs_url="https://docs.kraken.com/rest/",
               unlocks="Order execution + balances + margin",
               secondary_labels=("API secret",)),
    Connection("alpaca", "Alpaca", "exchange", "optional", "trader",
               ("ALPACA_API_KEY", "ALPACA_SECRET_KEY"),
               probe_url="https://paper-api.alpaca.markets/v2/clock",
               get_keys_url="https://app.alpaca.markets/paper/dashboard/overview",
               docs_url="https://docs.alpaca.markets/",
               unlocks="US stock/ETF execution + account",
               secondary_labels=("Secret key",)),
    Connection("capital", "Capital.com", "exchange", "optional", "trader",
               ("CAPITAL_API_KEY", "CAPITAL_IDENTIFIER", "CAPITAL_PASSWORD"),
               probe_url="https://api-capital.backend-capital.com/api/v1/time",
               get_keys_url="https://capital.com/trading/platform/settings",
               docs_url="https://open-api.capital.com/",
               unlocks="CFD / FX / index / equity execution + balances",
               secondary_labels=("Identifier (email)", "API password")),

    # ── Market data & macro ────────────────────────────────────────────────────
    Connection("coinapi", "CoinAPI", "market_data", "optional", "operator",
               ("COINAPI_KEY",),
               probe_url="https://rest.coinapi.io/v1/exchanges",
               probe_auth="header", probe_header="X-CoinAPI-Key",
               get_keys_url="https://www.coinapi.io/pricing?apikey",
               docs_url="https://docs.coinapi.io/",
               unlocks="Cross-exchange market history + anomaly detection"),
    Connection("coingecko", "CoinGecko", "market_data", "optional", "operator",
               ("COINGECKO_API_KEY",),
               probe_url="https://api.coingecko.com/api/v3/ping",
               get_keys_url="https://www.coingecko.com/en/api/pricing",
               docs_url="https://docs.coingecko.com/",
               unlocks="Reference prices, market cap, trending (works keyless; key raises limits)"),
    Connection("fred", "FRED (macro)", "market_data", "optional", "operator",
               ("FRED_API_KEY",),
               probe_url="https://api.stlouisfed.org/fred/releases",
               probe_auth="query",
               get_keys_url="https://fredaccount.stlouisfed.org/apikeys",
               docs_url="https://fred.stlouisfed.org/docs/api/fred/",
               unlocks="Rates, CPI, GDP, employment macro series"),
    Connection("fmp", "Financial Modeling Prep", "market_data", "optional", "operator",
               ("FMP_API_KEY",),
               probe_url="https://financialmodelingprep.com/api/v3/is-the-market-open",
               probe_auth="query", probe_query_param="apikey",
               get_keys_url="https://site.financialmodelingprep.com/developer/docs",
               docs_url="https://site.financialmodelingprep.com/developer/docs",
               unlocks="Economic / earnings / IPO / dividend calendar"),

    # ── Space & science (mostly keyless public) ────────────────────────────────
    Connection("nasa", "NASA (DONKI / NEO)", "space_science", "optional", "both",
               ("NASA_API_KEY",),
               probe_url="https://api.nasa.gov/DONKI/notifications",
               probe_auth="query",
               get_keys_url="https://api.nasa.gov/",
               docs_url="https://ccmc.gsfc.nasa.gov/tools/DONKI/",
               unlocks="Solar flares, geomagnetic storms, CMEs, near-Earth objects (DEMO_KEY works, rate-limited)"),
    Connection("firms", "NASA FIRMS (wildfires)", "space_science", "optional", "operator",
               ("FIRMS_MAP_KEY",),
               probe_url="https://firms.modaps.eosdis.nasa.gov/api/data_availability/csv/-/VIIRS_SNPP_NRT",
               get_keys_url="https://firms.modaps.eosdis.nasa.gov/api/map_key/",
               docs_url="https://firms.modaps.eosdis.nasa.gov/api/",
               unlocks="Global active wildfire detections (VIIRS)"),
    Connection("noaa_swpc", "NOAA SWPC (space weather)", "space_science", "keyless", "both",
               (), probe_url="https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json",
               docs_url="https://www.swpc.noaa.gov/products",
               unlocks="Kp index, solar wind, Bz, GOES X-ray flares — the Λ(t) space-weather driver"),
    Connection("noaa_cdo", "NOAA NCEI Climate Data Online", "space_science", "optional", "operator",
               ("NOAA_API_KEY",),
               probe_url="https://www.ncei.noaa.gov/cdo-web/api/v2/datasets?limit=1",
               probe_auth="header", probe_header="token",
               get_keys_url="https://www.ncdc.noaa.gov/cdo-web/token",
               docs_url="https://www.ncei.noaa.gov/cdo-web/webservices/v2",
               unlocks="NOAA historical climate data (GHCND daily summaries, normals, etc.)"),
    Connection("usgs_water", "USGS Water Data", "space_science", "optional", "operator",
               ("USGS_API_KEY",),
               probe_url="https://api.waterdata.usgs.gov/ogcapi/v0/collections",
               probe_auth="header", probe_header="X-Api-Key",
               get_keys_url="https://api.waterdata.usgs.gov/docs/ogcapi/keys/",
               docs_url="https://api.waterdata.usgs.gov/docs/",
               unlocks="USGS water data (streamflow, sites, monitoring locations) via the OGC API"),
    Connection("usgs_quake", "USGS earthquakes", "space_science", "keyless", "operator",
               (), probe_url="https://earthquake.usgs.gov/fdsnws/event/1/version",
               docs_url="https://earthquake.usgs.gov/fdsnws/event/1/",
               unlocks="Seismic event feeds (Earth-resonance correlation)"),
    Connection("nasa_eonet", "NASA EONET (events)", "space_science", "keyless", "operator",
               (), probe_url="https://eonet.gsfc.nasa.gov/api/v3/events?limit=1",
               docs_url="https://eonet.gsfc.nasa.gov/docs/v3",
               unlocks="Natural-event catalogue"),

    # ── Ephemeris & astronomy (keyless) ────────────────────────────────────────
    Connection("jpl_horizons", "JPL Horizons / Skyfield", "ephemeris", "keyless", "operator",
               (), probe_url="https://ssd.jpl.nasa.gov/api/horizons.api?format=text&COMMAND=%27499%27",
               docs_url="https://ssd-api.jpl.nasa.gov/doc/horizons.html",
               unlocks="Planetary ephemeris (DE440) + Horizons truth positions for the HNC sweep"),

    # ── On-chain & whale flow (the "surveillance" feeds) ───────────────────────
    Connection("etherscan", "Etherscan", "onchain_whale", "optional", "operator",
               ("ETHERSCAN_API_KEY",),
               probe_url="https://api.etherscan.io/api?module=stats&action=ethsupply",
               probe_auth="query", probe_query_param="apikey",
               get_keys_url="https://etherscan.io/myapikey",
               docs_url="https://docs.etherscan.io/",
               unlocks="ETH + ERC-20 large-transfer (whale) tracking"),
    Connection("alchemy", "Alchemy", "onchain_whale", "optional", "operator",
               ("ALCHEMY_API_KEY", "ALCHEMY_NETWORK"),
               get_keys_url="https://dashboard.alchemy.com/",
               docs_url="https://docs.alchemy.com/",
               unlocks="On-chain transfers / enrichment",
               notes="ALCHEMY_NETWORK defaults to eth-mainnet.",
               secondary_labels=("Network (e.g. eth-mainnet)",)),
    Connection("covalent", "Covalent", "onchain_whale", "optional", "operator",
               ("COVALENT_API_KEY",),
               probe_url="https://api.covalenthq.com/v1/1/block_v2/latest/",
               probe_auth="bearer",
               get_keys_url="https://www.covalenthq.com/platform/auth/register/",
               docs_url="https://www.covalenthq.com/docs/api/",
               unlocks="Multi-chain on-chain transfers"),
    Connection("glassnode", "Glassnode", "onchain_whale", "optional", "operator",
               ("GLASSNODE_API_KEY",),
               probe_url="https://api.glassnode.com/v1/metrics/market/price_usd_close",
               probe_auth="query",
               get_keys_url="https://studio.glassnode.com/settings/api",
               docs_url="https://docs.glassnode.com/", unlocks="On-chain crypto metrics (paid)"),
    Connection("unusual_whales", "Unusual Whales", "onchain_whale", "optional", "operator",
               ("UNUSUAL_WHALES_API_KEY",),
               probe_url="https://api.unusualwhales.com/api/market/market-tide",
               probe_auth="bearer",
               get_keys_url="https://unusualwhales.com/settings/api",
               docs_url="https://api.unusualwhales.com/docs", unlocks="Options / whale flow (paid)"),

    # ── News & social ──────────────────────────────────────────────────────────
    Connection("world_news", "World News API", "news_social", "optional", "operator",
               ("WORLD_NEWS_API_KEY",),
               probe_url="https://api.worldnewsapi.com/search-news?text=markets&number=1",
               probe_auth="header", probe_header="x-api-key",
               get_keys_url="https://worldnewsapi.com/", docs_url="https://worldnewsapi.com/docs/",
               unlocks="News + geopolitical sentiment feed"),

    # ── Notifications ──────────────────────────────────────────────────────────
    Connection("telegram", "Telegram bot", "notifications", "optional", "operator",
               ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"),
               get_keys_url="https://core.telegram.org/bots#how-do-i-create-a-bot",
               docs_url="https://core.telegram.org/bots/api",
               unlocks="Outbound trade / alert messages",
               secondary_labels=("Chat ID",)),
]

_BY_ID: Dict[str, Connection] = {c.id: c for c in CATALOG}


def get_connection(conn_id: str) -> Connection | None:
    return _BY_ID.get(conn_id)


def connection_ids() -> List[str]:
    return [c.id for c in CATALOG]


def by_category() -> list[tuple[str, str, list[Connection]]]:
    """(category_id, category_label, [connections]) in display order."""
    out = []
    for cat_id, cat_label in CATEGORIES:
        out.append((cat_id, cat_label, [c for c in CATALOG if c.category == cat_id]))
    return out


__all__ = [
    "Connection", "CATALOG", "CATEGORIES",
    "get_connection", "connection_ids", "by_category",
]
