"""High level entry points for the trading bot framework.

The previous implementation eagerly imported every trading submodule. That
pulled in heavyweight scientific dependencies (``numpy``, ``scipy``) at import
time which makes simple utilities—like the private WebSocket helpers—hard to
test in isolation.  We expose the same public API but lazily load the modules
only when individual attributes are accessed.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any, Dict

__all__ = [
    "MarketSnapshot",
    "TradingBot",
    "LighthouseEvent",
    "QGITADetector",
    "ExchangeConnector",
    "ExchangeError",
    "OrderResult",
    "PaperExchange",
    "PortfolioManager",
    "PortfolioSnapshot",
    "Position",
    "RiskManager",
    "TradePlan",
    "private_ws",
]

_ATTR_TO_MODULE: Dict[str, str] = {
    "MarketSnapshot": "bot",
    "TradingBot": "bot",
    "LighthouseEvent": "detection",
    "QGITADetector": "detection",
    "ExchangeConnector": "execution",
    "ExchangeError": "execution",
    "OrderResult": "execution",
    "PaperExchange": "execution",
    "PortfolioManager": "portfolio",
    "PortfolioSnapshot": "portfolio",
    "Position": "portfolio",
    "RiskManager": "risk",
    "TradePlan": "risk",
}


def __getattr__(name: str) -> Any:  # pragma: no cover - trivial proxy
    if name == "private_ws":
        return import_module(f"{__name__}.private_ws")
    module_name = _ATTR_TO_MODULE.get(name)
    if module_name is None:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
    module = import_module(f"{__name__}.{module_name}")
    value = getattr(module, name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:  # pragma: no cover - simple reflection helper
    return sorted(set(__all__))

