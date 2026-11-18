"""Magnification stack for the one Aureon 7B checkpoint.

One checkpoint is 1x. A cell is one pass in a stack of that same checkpoint.
The prompt states the magnification, from 1x to 10000x. Division adds a layer.
It does not copy the weights and it does not load the model.

The thought bus carries ``cell.divide`` and ``cell.board``. The baton is an
explicit ``baton.link`` whose payload module is the name Connectome already
records. ``link_system`` is not called.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

CHECKPOINT = "runs/aureon-7b-v65k"
MAX_MAGNIFICATION = 10000

_SCALE = re.compile(
    r"(?<![\w.])(?:magnification\s*=\s*(\d+)|(\d+)x)\b",
    re.IGNORECASE,
)


class MagnificationError(ValueError):
    """The prompt asked for a scale outside 1..10000."""


@dataclass(frozen=True)
class Cell:
    id: str
    parent_id: str | None
    generation: int
    checkpoint: str
    module: str
    topic: str


def magnification_for(prompt: str) -> int:
    """Read the scale from the prompt. No stated scale means 1x.

    ``1x``, ``10000x``, and ``magnification=N`` are the accepted forms. When
    several in-range scales appear, the last one wins. Any scale below 1 or
    above 10000 refuses the whole prompt.
    """
    ordered = [int(match.group(1) or match.group(2)) for match in _SCALE.finditer(prompt)]
    if not ordered:
        return 1
    if any(value < 1 or value > MAX_MAGNIFICATION for value in ordered):
        raise MagnificationError(
            f"magnification must be from 1 to {MAX_MAGNIFICATION}"
        )
    return ordered[-1]


class Colony:
    """One genome, stacked into as many passes as the prompt requests."""

    def __init__(self, bus, checkpoint: str = CHECKPOINT) -> None:
        self.bus = bus
        self.checkpoint = checkpoint
        self.cells: list[Cell] = []
        zygote = self._make(parent=None, generation=0)
        self.cells.append(zygote)
        self._holder = zygote.id
        self._announce(zygote)
        self.write_board(zygote.id)

    def divide_to(self, prompt: str) -> list[Cell]:
        """Grow the stack until it holds the prompt's magnification.

        A scale the stack already meets leaves the cells as they are. An
        illegal scale raises ``MagnificationError`` and writes nothing.
        """
        target = magnification_for(prompt)
        while len(self.cells) < target:
            self._divide_once()
        return list(self.cells)

    def write_board(self, cell_id: str, note: str = "") -> None:
        cell = self._cell(cell_id)
        if cell.id != self._holder:
            raise PermissionError(f"{cell.module} does not hold the baton")
        self.bus.publish(
            "cell.board",
            {
                "generation": cell.generation,
                "cell_id": cell.id,
                "parent_id": cell.parent_id,
                "checkpoint": cell.checkpoint,
                "module": cell.module,
                "note": note,
            },
            source=cell.module,
        )

    def pass_baton(self, to_cell: Cell) -> None:
        holder = self._cell(self._holder)
        if to_cell.parent_id != holder.id or to_cell.generation != holder.generation + 1:
            raise PermissionError("baton only moves from a cell to its daughter")
        self._holder = to_cell.id
        self._announce(to_cell)

    def _divide_once(self) -> Cell:
        parent = self._cell(self._holder)
        daughter = self._make(parent=parent, generation=parent.generation + 1)
        self.cells.append(daughter)
        self.bus.publish(
            "cell.divide",
            {
                "parent_id": parent.id,
                "cell_id": daughter.id,
                "generation": daughter.generation,
                "checkpoint": daughter.checkpoint,
                "module": daughter.module,
            },
            source=parent.module,
        )
        self.pass_baton(daughter)
        self.write_board(daughter.id)
        return daughter

    def _make(self, parent: Cell | None, generation: int) -> Cell:
        return Cell(
            id=str(uuid.uuid4()),
            parent_id=None if parent is None else parent.id,
            generation=generation,
            checkpoint=self.checkpoint,
            module=f"aureon.cells.m{generation}",
            topic=f"cell.m{generation}",
        )

    def _announce(self, cell: Cell) -> None:
        self.bus.publish("baton.link", {"module": cell.module}, source=cell.module)

    def _cell(self, cell_id: str) -> Cell:
        for cell in self.cells:
            if cell.id == cell_id:
                return cell
        raise KeyError(cell_id)
