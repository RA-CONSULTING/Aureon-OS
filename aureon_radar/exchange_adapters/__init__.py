"""Exchange adapters for the Aureon radar (organism-controlled trading surfaces).

Each adapter follows the repo contract:
- keys are read from the environment / .env AT CALL TIME (never cached at import)
- secret VALUES are never logged or journaled — key NAMES only
- no keys -> honest paper/dry-run mode using REAL prices from the live public feed
- no fabricated data: paper entries are labeled paper_dry_run and carry real
  market prices where a price is claimed

Importing this package has no side effects (no network, no env mutation).
Adapters import defensively: parallel build tracks may land files at
different times — a missing sibling adapter must not break yours.
"""

__all__ = []

try:
    from .binance_adapter import BinanceAdapter, BinanceAdapterConfig
    __all__ += ["BinanceAdapter", "BinanceAdapterConfig"]
except ImportError:
    pass

try:
    from .kraken_adapter import KrakenAdapter, get_kraken_adapter
    __all__ += ["KrakenAdapter", "get_kraken_adapter"]
except ImportError:
    pass

try:
    from .alpaca_adapter import AlpacaAdapter
    __all__ += ["AlpacaAdapter"]
except ImportError:
    pass
