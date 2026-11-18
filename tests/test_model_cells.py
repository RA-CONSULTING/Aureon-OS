"""Magnification stack: one 7B genome, as many passes as the prompt names."""

import threading
import unittest

from aureon.core.aureon_connectome import Connectome
from aureon.core.aureon_thought_bus import ThoughtBus
from aureon.core.model_cells import (
    CHECKPOINT,
    Colony,
    MagnificationError,
    magnification_for,
)


class MagnificationTests(unittest.TestCase):
    def test_no_scale_is_one(self):
        self.assertEqual(magnification_for("summarise the notes"), 1)

    def test_explicit_forms(self):
        self.assertEqual(magnification_for("do this at 3x"), 3)
        self.assertEqual(magnification_for("magnification=4"), 4)
        self.assertEqual(magnification_for("start 2x then magnification=6"), 6)

    def test_out_of_range_is_refused(self):
        for prompt in ("0x", "10001x", "magnification=10001", "3x and 10001x"):
            with self.assertRaises(MagnificationError):
                magnification_for(prompt)


class ColonyTests(unittest.TestCase):
    def setUp(self):
        self.bus = ThoughtBus(max_memory=50_000)
        self.colony = Colony(self.bus)

    def test_one_x_is_the_zygote(self):
        cells = self.colony.divide_to("1x")

        self.assertEqual(len(cells), 1)
        zygote = cells[0]
        self.assertEqual(zygote.generation, 0)
        self.assertIsNone(zygote.parent_id)
        self.assertEqual(zygote.checkpoint, CHECKPOINT)
        self.assertEqual(zygote.module, "aureon.cells.m0")

    def test_plain_prompt_stays_one_x(self):
        self.assertEqual(len(self.colony.divide_to("what should Aureon do next")), 1)

    def test_three_x_is_one_parent_chain(self):
        cells = self.colony.divide_to("need 3x throughput")

        self.assertEqual([cell.generation for cell in cells], [0, 1, 2])
        self.assertEqual(cells[1].parent_id, cells[0].id)
        self.assertEqual(cells[2].parent_id, cells[1].id)
        self.assertEqual({cell.checkpoint for cell in cells}, {CHECKPOINT})
        board = self.bus.recall("cell.board", limit=10)
        self.assertEqual([item["payload"]["generation"] for item in board], [0, 1, 2])

    def test_ten_thousand_records_share_one_checkpoint(self):
        cells = self.colony.divide_to("10000x")

        self.assertEqual(len(cells), 10000)
        self.assertEqual(cells[0].generation, 0)
        self.assertEqual(cells[-1].generation, 9999)
        self.assertEqual(cells[-1].parent_id, cells[-2].id)
        self.assertTrue(all(cell.checkpoint == CHECKPOINT for cell in cells))

    def test_above_the_cap_does_not_change_the_stack(self):
        self.colony.divide_to("3x")
        before = list(self.colony.cells)

        with self.assertRaises(MagnificationError):
            self.colony.divide_to("10001x")

        self.assertEqual(self.colony.cells, before)

    def test_only_the_holder_writes_the_board(self):
        cells = self.colony.divide_to("3x")
        before = len(self.bus.recall("cell.board", limit=10))

        with self.assertRaises(PermissionError):
            self.colony.write_board(cells[0].id, "lower layer cannot write")

        self.assertEqual(len(self.bus.recall("cell.board", limit=10)), before)

    def test_connectome_hears_each_baton(self):
        self.colony.divide_to("3x")
        ear = Connectome.__new__(Connectome)
        ear._linked = set()
        ear._lock = threading.RLock()

        for thought in self.bus.recall("baton.link", limit=10):
            Connectome._on_baton(ear, thought)

        self.assertEqual(ear._linked, {f"aureon.cells.m{i}" for i in range(3)})


if __name__ == "__main__":
    unittest.main()
