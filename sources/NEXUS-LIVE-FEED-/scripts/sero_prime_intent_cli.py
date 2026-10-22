"""Command line diagnostic for the Sero Prime Intent Gate.

This utility mirrors the gating logic that protects the Illumination Engine's
highest actuators.  It inspects an actuation request, evaluates the "Prime
Love Index" (compassion minus malice, clipped to the [0, 1] interval), and
performs the same semantic checks for love-aligned language that appear in the
TypeScript `sero-prime-intent-gate.ts` implementation.

The tool can ingest a JSON envelope that matches the Nexus API payload or be
driven entirely from command-line flags.  Results are presented as a human
readable report by default, or as JSON with ``--json`` for downstream
automation.

Example usages::

    # Inspect a full request stored on disk
    python scripts/sero_prime_intent_cli.py --request data/sample_actuation.json

    # Ad-hoc evaluation with explicit metrics
    python scripts/sero_prime_intent_cli.py \
        --intent "Stabilise auric lattice with love and compassion" \
        --compassion 0.82 --malice 0.05 --declaration pure_of_heart

The exit code is 0 when the gate passes and 1 when it blocks the actuation.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, MutableMapping, Optional


LOVE_PATTERN = re.compile(
    r"\b(love|compassion|care|kindness|mercy|alleviate harm|healing)\b",
    re.IGNORECASE,
)

AVOID_PATTERN = re.compile(
    r"\b(retaliat|punish|dominat|coerc|weapon|harm)\b",
    re.IGNORECASE,
)


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    """Clamp ``value`` into the inclusive range [lower, upper]."""

    return max(lower, min(upper, value))


def _safe_float(value: Optional[float]) -> float:
    """Convert ``value`` to a float in [0, 1], treating ``None`` as 0."""

    if value is None:
        return 0.0
    try:
        numeric = float(value)
    except (TypeError, ValueError):  # pragma: no cover - defensive guard
        return 0.0
    return _clamp(numeric)


def _ensure_dict(obj: Optional[MutableMapping[str, Any]]) -> Dict[str, Any]:
    """Return a shallow copy of ``obj`` if it is a mapping, else an empty dict."""

    if isinstance(obj, MutableMapping):
        return dict(obj)
    return {}


def _parse_key_value_pairs(pairs: Iterable[str]) -> Dict[str, Any]:
    """Parse ``KEY=VALUE`` pairs, attempting JSON decoding for the values."""

    result: Dict[str, Any] = {}
    for item in pairs:
        if "=" not in item:
            raise argparse.ArgumentTypeError(
                f"Expected KEY=VALUE format for --param, received: {item!r}"
            )
        key, raw_value = item.split("=", 1)
        try:
            parsed_value = json.loads(raw_value)
        except json.JSONDecodeError:
            parsed_value = raw_value
        result[key] = parsed_value
    return result


@dataclass
class HeartEvidence:
    """Relevant coherence metrics used by the Prime Intent Gate."""

    compassion_index: float = 0.0
    malice_index: float = 0.0
    declaration: str = "neutral"
    hrv_coherence: Optional[float] = None


@dataclass
class ActuationRequest:
    """Simplified model of the request inspected by the Prime Intent Gate."""

    intent: str
    params: Dict[str, Any] = field(default_factory=dict)
    ethos: Dict[str, Any] = field(default_factory=dict)

    @property
    def heart(self) -> HeartEvidence:
        heart_dict = _ensure_dict(self.ethos.get("heart"))
        return HeartEvidence(
            compassion_index=_safe_float(heart_dict.get("compassion_index")),
            malice_index=_safe_float(heart_dict.get("malice_index")),
            declaration=str(heart_dict.get("declaration", "neutral")),
            hrv_coherence=heart_dict.get("hrv_coherence"),
        )


@dataclass
class EvaluationResult:
    """Outcome of the Prime Intent assessment."""

    passed: bool
    prime_love_index: float
    love_semantics: bool
    compassion_index: float
    malice_index: float
    declaration: str
    required_threshold: float = 0.5
    notes: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


def _load_json_file(path: str) -> Dict[str, Any]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf8"))
    except FileNotFoundError as exc:  # pragma: no cover - CLI error handling
        raise SystemExit(f"Request file not found: {path}") from exc
    except json.JSONDecodeError as exc:  # pragma: no cover - CLI error handling
        raise SystemExit(f"Invalid JSON in request file {path!r}: {exc}") from exc
    if not isinstance(data, MutableMapping):
        raise SystemExit(
            f"Expected the request file {path!r} to contain a JSON object."
        )
    return dict(data)


def _merge_request(args: argparse.Namespace) -> ActuationRequest:
    envelope: Dict[str, Any] = {}
    if args.request:
        envelope = _load_json_file(args.request)

    intent = args.intent or envelope.get("intent") or ""

    params = _ensure_dict(envelope.get("params"))
    params.update(_parse_key_value_pairs(args.param or []))

    ethos = _ensure_dict(envelope.get("ethos"))
    heart = _ensure_dict(ethos.get("heart"))

    if args.compassion is not None:
        heart["compassion_index"] = args.compassion
    if args.malice is not None:
        heart["malice_index"] = args.malice
    if args.declaration is not None:
        heart["declaration"] = args.declaration
    if args.hrv_coherence is not None:
        heart["hrv_coherence"] = args.hrv_coherence

    ethos["heart"] = heart

    if args.ethos_note:
        notes = list(map(str, ethos.get("notes", [])))
        notes.append(args.ethos_note)
        ethos["notes"] = notes

    if args.append_text:
        intent = f"{intent} {args.append_text}".strip()

    return ActuationRequest(intent=intent, params=params, ethos=ethos)


def evaluate_request(request: ActuationRequest) -> EvaluationResult:
    heart = request.heart

    combined_text = " ".join(
        part
        for part in (
            request.intent,
            json.dumps(request.params, sort_keys=True),
            json.dumps(request.ethos, sort_keys=True),
        )
        if part
    )

    love_semantics = bool(LOVE_PATTERN.search(combined_text)) and not bool(
        AVOID_PATTERN.search(combined_text)
    )

    pli = _clamp(heart.compassion_index - heart.malice_index)

    passed = love_semantics and pli >= 0.5

    notes: List[str] = [
        f"Love semantics detected: {'yes' if love_semantics else 'no'}",
        f"Prime Love Index (compassion - malice): {pli:.3f}",
    ]

    recommendations: List[str] = []
    if not love_semantics:
        recommendations.append(
            "Reaffirm the compassionate motivation explicitly (e.g. mention love, kindness, or healing)."
        )
    if pli < 0.5:
        shortfall = 0.5 - pli
        recommendations.append(
            f"Increase compassion_index by at least {shortfall:.3f} or decrease malice_index accordingly."
        )

    if passed:
        notes.append(
            "Prime Intent Gate clear: compassion outweighs malice and language affirms love-aligned intent."
        )
    else:
        notes.append(
            "Prime Intent Gate blocked: thresholds not satisfied for love alignment."
        )

    return EvaluationResult(
        passed=passed,
        prime_love_index=pli,
        love_semantics=love_semantics,
        compassion_index=heart.compassion_index,
        malice_index=heart.malice_index,
        declaration=heart.declaration,
        notes=notes,
        recommendations=recommendations,
    )


def _format_result(result: EvaluationResult) -> str:
    status = "PASS" if result.passed else "FAIL"
    lines = [
        "Sero Prime Intent Diagnostic",
        "==============================",
        f"Status            : {status}",
        f"Prime Love Index : {result.prime_love_index:.3f} (>= {result.required_threshold:.2f})",
        f"Compassion Index : {result.compassion_index:.3f}",
        f"Malice Index     : {result.malice_index:.3f}",
        f"Love Semantics   : {'yes' if result.love_semantics else 'no'}",
        f"Heart Declaration: {result.declaration}",
        "",
        "Observations:",
    ]

    lines.extend(f"  - {note}" for note in result.notes)

    if result.recommendations:
        lines.append("")
        lines.append("Recommendations:")
        lines.extend(f"  * {rec}" for rec in result.recommendations)

    return "\n".join(lines)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate whether an actuation request satisfies the Prime Intent Gate.",
    )
    parser.add_argument(
        "--request",
        help="Path to a JSON file containing an actuation request envelope.",
    )
    parser.add_argument(
        "--intent",
        help="Intent description to evaluate (overrides the value in --request).",
    )
    parser.add_argument(
        "--append-text",
        dest="append_text",
        help="Additional text appended to the intent before semantic analysis.",
    )
    parser.add_argument(
        "--param",
        action="append",
        metavar="KEY=VALUE",
        help="Inline parameter override; VALUE is parsed as JSON when possible.",
    )
    parser.add_argument(
        "--compassion",
        type=float,
        help="Override compassion_index for the heart evidence (0..1).",
    )
    parser.add_argument(
        "--malice",
        type=float,
        help="Override malice_index for the heart evidence (0..1).",
    )
    parser.add_argument(
        "--hrv-coherence",
        dest="hrv_coherence",
        type=float,
        help="Optional HRV coherence measurement to embed into the ethos.",
    )
    parser.add_argument(
        "--declaration",
        choices=["pure_of_heart", "neutral", "unclear"],
        help="Manual declaration for the heart evidence.",
    )
    parser.add_argument(
        "--ethos-note",
        help="Append a textual note to the ethos payload.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the evaluation result as JSON instead of text.",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    request = _merge_request(args)
    result = evaluate_request(request)

    if args.json:
        print(json.dumps(asdict(result), indent=2))
    else:
        print(_format_result(result))

    return 0 if result.passed else 1


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    sys.exit(main())
