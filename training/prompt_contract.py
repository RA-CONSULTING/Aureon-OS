"""The one definition of what Aureon asks its model to do.

Training and inference must not drift. `make_sft.py` builds its instructions
from these functions and `train_lora.py` takes SYSTEM from here, so the text
the model is trained on is byte-identical to the text it is asked at runtime.

Why this file exists: the adapter does not decide the prompt. `_build_payload`
prepends whatever `system=` string the caller passes and sends the messages
verbatim. A caller that invents "You are a helpful assistant" gets an assistant
that has never heard of Aureon-OS, and that looks exactly like a broken model.
Use these builders, or at minimum pass SYSTEM.
"""

from __future__ import annotations

SYSTEM = (
    "You are Aureon, a coding agent working inside the Aureon-OS repository. "
    "You write Python that matches the repository's existing module layout, "
    "type hints, and docstring conventions."
)

# Matches the adapter's own default limit: Aureon's LocalAdapter.prompt uses
# max_tokens=4096, and every pair was generated to fit a 4096-token window.
MAX_TOKENS = 4096


def implement_module(rel: str) -> str:
    return f"Write the complete Python module `{rel}` in the Aureon-OS repository."


def implement_symbol(kind: str, name: str, rel: str) -> str:
    return f"Write the {kind} `{name}` as it appears in `{rel}` in the Aureon-OS repository."


def continue_module(rel: str, line: int) -> str:
    return f"Continue `{rel}` in the Aureon-OS repository, starting at line {line}."


def explain_module(rel: str) -> str:
    return f"Describe the purpose and public surface of `{rel}` in the Aureon-OS repository."


def implement_file(rel: str) -> str:
    return f"Write the file `{rel}` from the Aureon-OS repository, matching its existing conventions."


def continue_file(rel: str, line: int) -> str:
    return f"Continue the file `{rel}` from the Aureon-OS repository, starting at line {line}."


def messages(instruction: str) -> list[dict]:
    """Message list as the adapter expects it, without the system turn."""
    return [{"role": "user", "content": instruction}]


def full_messages(instruction: str, system: str = SYSTEM) -> list[dict]:
    """Exactly what lands on the wire once the adapter prepends `system`."""
    return [{"role": "system", "content": system}, {"role": "user", "content": instruction}]


def check_contract(system: str) -> list[str]:
    """Return human-readable warnings for a runtime call that would drift.

    Call this before pointing a caller at a tuned endpoint; it catches the two
    silent failures — a different system prompt, and a model name the server
    will not recognise.
    """
    problems: list[str] = []
    if system != SYSTEM:
        problems.append(
            "system prompt differs from the training prompt; the tuned behaviour may not trigger"
        )
    if not system.strip():
        problems.append("empty system prompt; the adapter will send no system turn at all")
    return problems
