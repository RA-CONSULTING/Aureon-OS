"""Yahoo Finance connector implemented with yfinance.

Usage:
    connector = YahooConnector()
    df = connector.fetch(FetchRequest(dataset="prices_daily", symbols=["SPY"], start="2024-01-01", end="2024-01-10"))

Only public OHLCV data is retrieved. Corporate actions are applied downstream
using exchange bulletins to maintain compliance with provider terms.
"""

from __future__ import annotations

import os
from typing import Iterable

import pandas as pd
import yfinance as yf

from .base import DataConnector, FetchRequest


class YahooConnector(DataConnector):
    """Pull OHLCV candles from Yahoo Finance."""

    def __init__(self, session=None) -> None:
        self._session = session

    def fetch(self, request: FetchRequest) -> pd.DataFrame:
        tickers: Iterable[str] = request.symbols
        data = yf.download(
            tickers=list(tickers),
            start=request.start,
            end=request.end,
            interval="1d" if request.interval is None else request.interval,
            auto_adjust=False,
            progress=False,
            group_by="ticker",
            session=self._session,
        )
        frames = []
        for symbol in tickers:
            try:
                raw = data[symbol].reset_index()
            except KeyError:
                continue
            raw.columns = ["date_time", "open", "high", "low", "close", "adj_close", "volume"]
            raw.insert(1, "symbol", symbol)
            raw.insert(2, "exchange", os.getenv("OBSERVATORY_DEFAULT_EXCHANGE", "UNKNOWN"))
            frames.append(raw)
        result = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        return result[["date_time", "symbol", "exchange", "open", "high", "low", "close", "volume"]]
