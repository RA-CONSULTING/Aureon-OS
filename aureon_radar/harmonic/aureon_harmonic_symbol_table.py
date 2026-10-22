# aureon_harmonic_symbol_table.py
# EXPANDED: Now uses 2-byte IDs (0x0000-0xFFFF) to support 65,000+ symbols

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import json
import os
import zlib
import threading
from typing import Dict, Optional, Tuple

# Windows UTF-8 Fix
import sys
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

SYMBOL_TABLE_FILE = "harmonic_symbol_table.json"

# Reserve 0x0000 for invalid/unknown
# Reserve 0x0001-0x00FF for Core/Major assets (hardcoded)
# Reserve 0xFFFF for 'Expansion' (future use)
# Dynamic range: 0x0100 - 0xFFFE (65,278 symbols!)

CORE_SYMBOLS = {
    "BTC/USD": 0x01,
    "ETH/USD": 0x02,
    "SOL/USD": 0x03,
    "XRP/USD": 0x04,
    "AD/USD": 0x05,   # ADA often listed as AD on some legacy
    "ADA/USD": 0x05,
    "DOGE/USD": 0x06,
    "DOT/USD": 0x07,
    "MATIC/USD": 0x08,
    "LTC/USD": 0x09,
    "LINK/USD": 0x0A,
    "BCH/USD": 0x0B,
    "XLM/USD": 0x0C,
    "ALGO/USD": 0x0D,
    "ATOM/USD": 0x0E,
    "UNI/USD": 0x0F,
    
    # Major Stocks (Top 10)
    "AAPL": 0x20,
    "MSFT": 0x21,
    "GOOG": 0x22,
    "AMZN": 0x23,
    "NVDA": 0x24,
    "TSLA": 0x25,
    "META": 0x26,
    "BRK.B": 0x27,
    "TSM": 0x28,
    "V": 0x29
}

class HarmonicSymbolTable:
    def __init__(self):
        self._lock = threading.RLock()
        self._symbol_to_id: Dict[str, int] = CORE_SYMBOLS.copy()
        self._id_to_symbol: Dict[int, str] = {v: k for k, v in CORE_SYMBOLS.items()}
        self._next_dynamic_id = 0x0100  # Start dynamic IDs at 256 (2-byte range)
        self._dirty = False
        self._load()

    def _load(self):
        with self._lock:
            if os.path.exists(SYMBOL_TABLE_FILE):
                try:
                    with open(SYMBOL_TABLE_FILE, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        # Merge dynamic symbols
                        for sym, sid in data.get("symbols", {}).items():
                            self._symbol_to_id[sym] = sid
                            self._id_to_symbol[sid] = sym
                            if sid >= self._next_dynamic_id:
                                self._next_dynamic_id = sid + 1
                except Exception as e:
                    print(f"[HarmonicSymbolTable] Error loading table: {e}")

    def _save(self):
        if not self._dirty:
            return
        
        with self._lock:
            # We only save dynamic symbols (>= 0x40) to keep file clean
            # or we can save everything. Saving everything is safer for consistency.
            export_data = {
                "symbols": self._symbol_to_id,
                "next_id": self._next_dynamic_id
            }
            try:
                # Write to temp file then rename for atomic safety
                tmp_file = SYMBOL_TABLE_FILE + ".tmp"
                with open(tmp_file, "w", encoding="utf-8") as f:
                    json.dump(export_data, f, indent=2)
                os.replace(tmp_file, SYMBOL_TABLE_FILE)
                self._dirty = False
            except Exception as e:
                print(f"[HarmonicSymbolTable] Error saving table: {e}")

    def get_id(self, symbol: str) -> int:
        if not symbol:
            return 0x0000
        
        sym_key = symbol.strip().upper()
        
        with self._lock:
            if sym_key in self._symbol_to_id:
                return self._symbol_to_id[sym_key]
            
            # Create new ID (2-byte range: 0x0100 - 0xFFFE = 65,278 dynamic symbols)
            new_id = self._next_dynamic_id
            if new_id > 0xFFFE:
                # Table truly full (65,000+ symbols!) - use CRC fallback
                # This should never happen with 21,955 symbols
                crc_id = (zlib.crc32(sym_key.encode("utf-8")) & 0xFFFF)
                if crc_id < 0x0100:
                    crc_id += 0x0100  # Keep in dynamic range
                return crc_id

            self._symbol_to_id[sym_key] = new_id
            self._id_to_symbol[new_id] = sym_key
            self._next_dynamic_id += 1
            self._dirty = True
            
            # Throttle saves - only save every 100 new symbols
            if self._next_dynamic_id % 100 == 0:
                self._save()
            return new_id

    def get_symbol(self, sid: int) -> Optional[str]:
        with self._lock:
            return self._id_to_symbol.get(sid)

# Singleton instance
_instance = HarmonicSymbolTable()

def get_symbol_id(symbol: str) -> int:
    return _instance.get_id(symbol)

def get_symbol_from_id(sid: int) -> Optional[str]:
    return _instance.get_symbol(sid)
