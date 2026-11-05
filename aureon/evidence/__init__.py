"""Fixed-seed measurements of the HNC field, Auris nodes, and QGITA analyzer.

The numbers come from the implementations already in this repository.
The harness adds synthetic inputs, baselines, and bookkeeping. It does not
add a formula for those three systems, and it does not call an external model.
"""

__all__ = ["main"]


def main(argv: list[str] | None = None) -> int:
    from aureon.evidence.runner import main as run_main

    return run_main(argv)
