import numpy as np

class RingBuffer:
    def __init__(self, size: int, channels: int = 1, dtype=np.float32):
        self.size = size
        self.channels = channels
        self.buf = np.zeros((size, channels), dtype=dtype)
        self.idx = 0
        self.full = False

    def push(self, x):
        """x: array-like shape (channels,) or scalar"""
        x = np.asarray(x, dtype=self.buf.dtype).reshape(1, self.channels)
        self.buf[self.idx] = x
        self.idx = (self.idx + 1) % self.size
        if self.idx == 0:
            self.full = True

    def read(self, last_n=None):
        n = self.size if (last_n is None or (self.full and last_n >= self.size)) else last_n
        if not self.full and self.idx == 0:
            return np.zeros((0, self.channels), dtype=self.buf.dtype)
        if not self.full:
            data = self.buf[:self.idx]
            return data[-n:] if n is not None else data
        # full buffer
        if n is None: n = self.size
        start = (self.idx - n) % self.size
        if start < self.idx:
            return self.buf[start:self.idx]
        return np.vstack((self.buf[start:], self.buf[:self.idx]))
