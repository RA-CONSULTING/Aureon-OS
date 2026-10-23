from abc import ABC, abstractmethod
from collections import deque


class Strategy(ABC):
    @abstractmethod
    def on_price(self, price: float) -> None: ...

    @abstractmethod
    def signal(self) -> str: ...  # BUY, SELL, HOLD


class MeanReversion(Strategy):
    def __init__(self, window=30, z=1.0):
        self.window = window
        self.z = z
        self.buf = deque(maxlen=window)

    def on_price(self, price: float) -> None:
        self.buf.append(price)

    def signal(self) -> str:
        if len(self.buf) < 5:
            return 'HOLD'
        mean = sum(self.buf)/len(self.buf)
        dev = max(1e-12, (sum((p-mean)**2 for p in self.buf)/len(self.buf))**0.5)
        last = self.buf[-1]
        zscore = (last-mean)/dev
        if zscore <= -self.z:
            return 'BUY'
        if zscore >= self.z:
            return 'SELL'
        return 'HOLD'


class Momentum(Strategy):
    def __init__(self, fast=5, slow=20):
        self.fast = fast
        self.slow = slow
        self.buf = deque(maxlen=max(fast, slow))

    def on_price(self, price: float) -> None:
        self.buf.append(price)

    def _ema(self, period):
        if not self.buf:
            return 0.0
        alpha = 2/(period+1)
        ema = self.buf[0]
        for p in list(self.buf)[1:]:
            ema = alpha*p + (1-alpha)*ema
        return ema

    def signal(self) -> str:
        if len(self.buf) < self.slow:
            return 'HOLD'
        f = self._ema(self.fast)
        s = self._ema(self.slow)
        if f > s:
            return 'BUY'
        if f < s:
            return 'SELL'
        return 'HOLD'
