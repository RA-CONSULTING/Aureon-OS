"""Offline tail-reader regressions; no runtime imports, processes or providers."""
import ast
import asyncio
from collections import deque
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest import mock


SOURCE = Path(__file__).resolve().parents[1] / "neural_canvas.py"


def load_isolated_canvas():
    """Compile the actual definitions without importing paths or starting organs."""
    parsed = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
    names = {"_tail_jsonl", "_utc_now", "Hub", "Collector"}
    constants = {"JSONL_TAIL_BLOCK_BYTES", "JSONL_TAIL_MAX_BYTES",
                 "SPARK_MAX", "EVENTS_MAX", "SQLITE_CACHE_S", "POLL_INTERVAL_S"}
    body = [node for node in parsed.body
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names
            or isinstance(node, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id in constants for t in node.targets)]
    namespace = {"Path": Path, "os": os, "json": json, "datetime": datetime,
                 "timezone": timezone, "threading": threading, "time": time,
                 "deque": deque, "hashlib": hashlib, "asyncio": asyncio}
    exec(compile(ast.Module(body=body, type_ignores=[]), str(SOURCE), "exec"), namespace)
    return namespace


class CountingReader(io.BytesIO):
    def __init__(self, content):
        super().__init__(content)
        self.read_requests = []
        self.total_read = 0

    def read(self, size=-1):
        if size < 0:
            raise AssertionError("An unbounded read is forbidden")
        self.read_requests.append(size)
        result = super().read(size)
        self.total_read += len(result)
        return result


class NeuralCanvasTailTests(unittest.TestCase):
    def setUp(self):
        self.canvas = load_isolated_canvas()
        self.tail = self.canvas["_tail_jsonl"]
        self.status = {}

    def read_bytes(self, content, limit, reader_type=CountingReader):
        reader = reader_type(content)
        def open_reader(path, mode, **kwargs):
            self.assertEqual(mode, "rb")
            self.assertEqual(kwargs, {"buffering": 0})
            return reader
        with mock.patch.dict(self.canvas, {"open": open_reader}):
            result = self.tail(Path("offline.jsonl"), limit, status=self.status)
        self.assertEqual(reader.total_read, self.status["bytes_read"])
        self.assertLessEqual(reader.total_read, self.canvas["JSONL_TAIL_MAX_BYTES"])
        self.assertTrue(all(n <= self.canvas["JSONL_TAIL_BLOCK_BYTES"]
                            for n in reader.read_requests))
        return result, reader

    def test_normal_last_records_keep_order_values_and_source_timestamps(self):
        records = [{"index": i, "ts": "2020-01-01T00:00:00Z", "value": 0}
                   for i in range(9)]
        content = "\n".join(json.dumps(row) for row in records).encode()
        result, _ = self.read_bytes(content, 3)
        self.assertEqual(result, records[-3:])
        self.assertEqual(self.status["status"], "ok")
        self.assertFalse(self.status["truncated"])

    def test_empty_file_is_empty_without_reading(self):
        result, reader = self.read_bytes(b"", 40)
        self.assertEqual(result, [])
        self.assertEqual(reader.read_requests, [])
        self.assertEqual(self.status["status"], "ok")
        self.assertEqual(self.status["file_size_bytes"], 0)

    def test_missing_file_remains_empty_and_distinct_from_empty_file(self):
        with tempfile.TemporaryDirectory(prefix="canvas-tail-test-") as directory:
            self.assertEqual(self.tail(Path(directory) / "missing.jsonl", 40,
                                       status=self.status), [])
        self.assertEqual(self.status["status"], "missing")
        self.assertIsNone(self.status["file_size_bytes"])
        self.assertEqual(self.status["bytes_read"], 0)

    def test_malformed_and_blank_lines_consume_window_without_backfill(self):
        content = b'{"older":true}\n\nnot json\n{"new":true}\n{"partial":'
        result, _ = self.read_bytes(content, 4)
        self.assertEqual(result, [{"new": True}])
        self.assertEqual(self.status["selected_lines"], 4)
        self.assertEqual(self.status["malformed_lines"], 2)
        self.assertFalse(self.status["truncated"])

    def test_crlf_multibyte_and_block_boundaries_match_original_window(self):
        records = [{"padding": "x" * 65000}, {"name": "\u03b3\U0001f40d" * 500},
                   {"final": 0}]
        content = ("\r\n".join(json.dumps(row, ensure_ascii=False) for row in records)
                   + "\r\n").encode("utf-8")
        result, _ = self.read_bytes(content, 3)
        self.assertEqual(result, records)
        self.assertEqual(self.status["status"], "ok")

    def test_large_history_reads_only_small_tail_and_returns_last_40(self):
        old = b'{"old":true,"padding":"' + b'x' * 200 + b'"}\n'
        latest = [{"cycle": i, "source_ts": "2021-02-03T04:05:06Z"}
                  for i in range(40)]
        content = old * 16000 + b''.join(json.dumps(r).encode() + b'\n'
                                         for r in latest)
        result, reader = self.read_bytes(content, 40)
        self.assertEqual(result, latest)
        self.assertLess(reader.total_read, len(content) // 20)
        self.assertFalse(self.status["truncated"])

    def test_large_carriage_return_history_preserves_text_mode_line_semantics(self):
        content = b'{"old":true}\r' * 100000 + b'{"latest":0}\r'
        result, reader = self.read_bytes(content, 2)
        self.assertEqual(result, [{"old": True}, {"latest": 0}])
        self.assertLess(reader.total_read, self.canvas["JSONL_TAIL_MAX_BYTES"])
        self.assertFalse(self.status["truncated"])

    def test_requested_window_over_byte_budget_is_explicitly_incomplete(self):
        content = b'{"entry":1}\n' * 200000
        result, reader = self.read_bytes(content, 200000)
        self.assertTrue(result)
        self.assertLess(len(result), 200000)
        self.assertEqual(reader.total_read, self.canvas["JSONL_TAIL_MAX_BYTES"])
        self.assertEqual(self.status["status"], "truncated")
        self.assertEqual(self.status["reason"], "byte_budget_exhausted")

    def test_oversized_leading_fragment_cannot_become_fabricated_record(self):
        budget = self.canvas["JSONL_TAIL_MAX_BYTES"]
        content = b'x' * (budget + 200) + b'{"not_a_record":true}\n{"real":0}\n'
        result, _ = self.read_bytes(content, 2)
        self.assertEqual(result, [{"real": 0}])
        self.assertTrue(self.status["truncated"])

    def test_single_oversized_trailing_record_yields_no_older_substitute(self):
        budget = self.canvas["JSONL_TAIL_MAX_BYTES"]
        content = b'{"older":true}\n{"huge":"' + b'x' * (budget + 10) + b'"}\n'
        result, _ = self.read_bytes(content, 40)
        self.assertEqual(result, [])
        self.assertEqual(self.status["status"], "truncated")

    def test_short_read_from_concurrent_truncation_returns_unavailable(self):
        class ShortReader(CountingReader):
            def read(self, size=-1):
                return super().read(max(0, size - 1))
        result, _ = self.read_bytes(b'{"event":1}\n', 40, ShortReader)
        self.assertEqual(result, [])
        self.assertEqual(self.status["reason"], "file_changed_during_read")
        self.assertEqual(self.status["status"], "unavailable")

    def test_read_error_does_not_reuse_old_records_or_status(self):
        self.read_bytes(b'{"event":1}\n', 40)
        with mock.patch.dict(self.canvas, {"open": mock.Mock(side_effect=PermissionError)}):
            result = self.tail(Path("offline.jsonl"), 40, status=self.status)
        self.assertEqual(result, [])
        self.assertEqual(self.status["status"], "unavailable")
        self.assertEqual(self.status["parsed_records"], 0)
        self.assertEqual(self.status["bytes_read"], 0)

    def test_zero_requested_lines_performs_no_io(self):
        with mock.patch.dict(self.canvas, {"open": mock.Mock(side_effect=AssertionError)}):
            self.assertEqual(self.tail(Path("offline.jsonl"), 0, status=self.status), [])
        self.assertEqual(self.status["bytes_read"], 0)

    def test_collector_snapshot_exposes_each_source_read_status(self):
        with tempfile.TemporaryDirectory(prefix="canvas-collector-test-") as directory:
            root = Path(directory)
            paths = {name: root / name for name in (
                "REPORTS_FILE", "HNC_STATE_FILE", "LAMBDA_HISTORY_FILE",
                "ORGAN_REGISTRY_FILE", "CONVERSATION_FILE", "DOORS_JOURNAL_FILE",
                "LEARNING_JOURNAL_FILE")}
            original_tail = self.tail
            def fake_source_open(path, mode, **kwargs):
                if path == paths["REPORTS_FILE"]:
                    return CountingReader(b'x' * (self.canvas["JSONL_TAIL_MAX_BYTES"] + 1))
                if path == paths["DOORS_JOURNAL_FILE"]:
                    return CountingReader(b'')
                raise FileNotFoundError
            with mock.patch.dict(self.canvas, {**paths, "open": fake_source_open,
                                               "_tail_jsonl": original_tail,
                                               "_read_json": lambda path, default: {},
                                               "_sqlite_counts": lambda: {}}):
                hub = self.canvas["Hub"]()
                self.canvas["Collector"](hub).collect()
                source_reads = hub.snapshot()["tail_reads"]
        self.assertEqual(source_reads["reports"]["status"], "truncated")
        self.assertEqual(source_reads["doors"]["status"], "ok")
        self.assertEqual(source_reads["learning"]["status"], "missing")


if __name__ == "__main__":
    unittest.main()
