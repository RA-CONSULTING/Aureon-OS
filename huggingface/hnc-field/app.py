"""HNC field Space. Calls the repo modules. Does not place orders."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import guard
import gradio as gr

REPLAY = guard.SPACE_DIR / "replay" / "brain.json"
HOLD = (
    "Trade readiness: HOLD. "
    "Auris joined to Lambda: HOLD. "
    "QGITA detection rate: HOLD. "
    "Schumann f0: null. HOLD."
)
LINK = (
    f"https://github.com/RA-CONSULTING/Aureon-OS/blob/{guard.COMMIT}/{guard.BRAIN_FILE}"
)


def _blank(value: object) -> bool:
    return value is None or str(value).strip() == ""


def _float_box(value: object) -> float | None:
    if _blank(value):
        return None
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


def _load_replay() -> dict | None:
    if not REPLAY.is_file():
        return None
    loaded = json.loads(REPLAY.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else None


def _same(fresh: object, committed: object) -> bool:
    return json.loads(json.dumps(fresh)) == committed


def _brain_table() -> str:
    """Both committed paths. The class default is multiverse on."""

    loaded = _load_replay()
    hnc = loaded.get("hnc") if isinstance(loaded, dict) else None
    if not isinstance(hnc, dict):
        return "Both brain paths: unavailable. replay/brain.json is missing."
    steps = hnc.get("steps")
    if isinstance(steps, bool) or not isinstance(steps, int) or steps < 1:
        return "Both brain paths: unavailable. The committed step count is missing."
    from aureon.harmonic.aureon_harmonic_reality import HarmonicRealityField

    def measure(factory):
        field = factory()
        series = [float(field.step()) for _ in range(steps)]
        return {
            "on": bool(field.enable_multiverse),
            "coherence": float(field.coherence),
            "lambda_last": series[-1],
            "state_name": field.state.name,
            "state_value": field.state.value,
            "series": series,
        }

    default = measure(HarmonicRealityField)
    off = measure(lambda: HarmonicRealityField(enable_multiverse=False))
    extension = hnc.get("multiverse_extension") if isinstance(hnc.get("multiverse_extension"), dict) else {}
    default_match = (
        default["on"] is True
        and _same(default["coherence"], extension.get("coherence"))
        and _same(default["lambda_last"], extension.get("lambda_last"))
        and default["state_value"] == extension.get("state")
    )
    off_match = (
        off["on"] is False
        and _same(off["coherence"], hnc.get("coherence"))
        and _same(off["lambda_last"], hnc.get("lambda_last"))
        and off["state_value"] == hnc.get("state")
        and _same(off["series"], hnc.get("series"))
    )
    return "\n".join(
        [
            "The class default `HarmonicRealityField()` is the multiverse-on path.",
            "The figures on the `enable_multiverse=False` row are the multiverse-off path.",
            "",
            "| Path | Coherence | Last Lambda | State |",
            "| --- | --- | --- | --- |",
            (
                "| Class default HarmonicRealityField() (multiverse on) | "
                f"{default['coherence']} | {default['lambda_last']} | {default['state_name']} |"
            ),
            (
                "| enable_multiverse=False (multiverse off) | "
                f"{off['coherence']} | {off['lambda_last']} | {off['state_name']} |"
            ),
            "",
            (
                "Class default rerun matches brain.json multiverse_extension: "
                + ("yes" if default_match else "no")
                + ". Label: cited."
            ),
            (
                "Multiverse-off rerun matches brain.json: "
                + ("yes" if off_match else "no")
                + ". Label: cited."
            ),
        ]
    )


def _formula(record: dict | None, params: dict | None, steps: int | None) -> list[str]:
    if steps is None or steps < 1:
        return ["Formula Gamma: unavailable", "Formula Lambda: unavailable"]
    from aureon.harmonic.aureon_harmonic_reality import HarmonicRealityField

    kwargs = {"enable_multiverse": False}
    if params:
        kwargs.update(params)
    field = HarmonicRealityField(**kwargs)
    series = [float(field.step()) for _ in range(steps)]
    gamma = float(field.coherence)
    lam = series[-1]
    lines = [
        f"Formula Gamma: {gamma}",
        f"Formula Lambda (last): {lam}",
        f"Formula state: {field.state.value}",
        f"Steps: {steps}",
        "Label: inferred. This is a rerun of HarmonicRealityField.step in this process.",
    ]
    if record is not None:
        committed_gamma = record.get("coherence")
        committed_lambda = record.get("lambda_last")
        rounded = json.loads(json.dumps({"coherence": gamma, "lambda_last": lam, "series": series}))
        match = (
            rounded["coherence"] == committed_gamma
            and rounded["lambda_last"] == committed_lambda
            and rounded["series"] == record.get("series")
        )
        lines.append(
            "Committed replay Gamma: "
            f"{guard.show(committed_gamma)} (cited, {guard.BRAIN_FILE})."
        )
        lines.append(
            "Committed replay Lambda: "
            f"{guard.show(committed_lambda)} (cited, {guard.BRAIN_FILE})."
        )
        lines.append(
            "Local rerun matches the committed brain replay: "
            + ("yes" if match else "no")
        )
        if match:
            lines.append(
                "The brain runs are deterministic (no seed). "
                "Only the organism fault block is seeded (20261024)."
            )
    return lines


def _canonical(trace_text: str) -> list[str]:
    from aureon.core.hnc_field import blend_field, read_canonical_field

    previous = os.environ.get("AUREON_HNC_TRACE_PATH")
    temp_path: Path | None = None
    try:
        if not _blank(trace_text):
            temp = tempfile.NamedTemporaryFile(
                prefix="hnc-trace-", suffix=".jsonl", delete=False
            )
            temp_path = Path(temp.name)
            temp.write(trace_text.strip().encode("utf-8"))
            if not trace_text.endswith("\n"):
                temp.write(b"\n")
            temp.close()
            os.environ["AUREON_HNC_TRACE_PATH"] = str(temp_path)
        else:
            os.environ.pop("AUREON_HNC_TRACE_PATH", None)
        field = read_canonical_field()
        blended = blend_field()
    finally:
        if previous is None:
            os.environ.pop("AUREON_HNC_TRACE_PATH", None)
        else:
            os.environ["AUREON_HNC_TRACE_PATH"] = previous
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
    body = field.to_dict()
    blend = blended.to_dict()
    lines = [
        "Canonical field reader: aureon.core.hnc_field.read_canonical_field.",
        "Blend reader: aureon.core.hnc_field.blend_field.",
    ]
    if body.get("available") is True:
        lines.append(f"Canonical Gamma: {guard.show(body.get('coherence_gamma'))}")
        lines.append(f"Canonical Lambda: {guard.show(body.get('lambda_t'))}")
        lines.append("Label: inferred. Read from the envelope supplied to this process.")
    else:
        lines.append("Canonical Gamma: unavailable")
        lines.append("Canonical Lambda: unavailable")
        lines.append(
            "No fresh canonical envelope was available. "
            "The bundled brain replay is a formula record, not a canonical envelope."
        )
    if blend.get("available") is True:
        lines.append(f"Blended Gamma: {guard.show(blend.get('coherence_gamma'))}")
        lines.append(
            f"Blended symbolic life score: {guard.show(blend.get('symbolic_life_score'))}"
        )
    else:
        lines.append("Blended field: unavailable")
    return lines


def _lambda_engine(readings_text: str) -> list[str]:
    if _blank(readings_text):
        return ["LambdaEngine path: unavailable. No readings were supplied."]
    try:
        payload = json.loads(readings_text)
    except json.JSONDecodeError:
        return ["LambdaEngine path: unavailable. The readings text is not JSON."]
    if not isinstance(payload, dict) or "volatility" not in payload or "readings" not in payload:
        return ["LambdaEngine path: unavailable. volatility and readings are required."]
    volatility = payload.get("volatility")
    rows = payload.get("readings")
    if isinstance(volatility, bool) or not isinstance(volatility, (int, float)):
        return ["LambdaEngine path: unavailable. volatility is missing."]
    if not isinstance(rows, list) or len(rows) < 2:
        return ["LambdaEngine path: unavailable. At least two readings are required."]
    from aureon.core.aureon_lambda_engine import LambdaEngine, SubsystemReading

    parsed = []
    for row in rows:
        if not isinstance(row, dict):
            return ["LambdaEngine path: unavailable. A reading is missing fields."]
        name = row.get("name")
        value = row.get("value")
        confidence = row.get("confidence")
        state = row.get("state")
        if (
            not isinstance(name, str)
            or not name.strip()
            or isinstance(value, bool)
            or not isinstance(value, (int, float))
            or isinstance(confidence, bool)
            or not isinstance(confidence, (int, float))
            or not isinstance(state, str)
            or not state.strip()
        ):
            return ["LambdaEngine path: unavailable. A reading is missing fields."]
        parsed.append(
            SubsystemReading(
                name=name.strip(),
                value=float(value),
                confidence=float(confidence),
                state=state.strip(),
            )
        )
    engine = LambdaEngine(state_path=Path(tempfile.gettempdir()) / "hnc-space-lambda.json")
    state = engine.step(parsed, volatility=float(volatility), auto_persist=False)
    return [
        f"LambdaEngine Lambda: {state.lambda_t}",
        f"LambdaEngine Gamma: {state.coherence_gamma}",
        "Label: inferred. LambdaEngine.step on the supplied readings.",
        "This path is not the committed brain replay.",
    ]


def run(
    mode: str,
    alpha: str,
    beta: str,
    tau: str,
    g_value: str,
    delta_t: str,
    steps_text: str,
    trace_text: str,
    readings_text: str,
) -> str:
    lines = [
        f"Licence: {guard.LICENCE}",
        "Replay label: recorded formula replay from the committed brain run.",
        f"Commit: {guard.COMMIT}",
        f"Link: {LINK}",
        HOLD,
        "This Space makes no track-record, return, or performance claim.",
        guard.REFUSAL,
    ]
    params = None
    steps = None
    if mode == "user inputs":
        boxes = {
            "alpha": _float_box(alpha),
            "beta": _float_box(beta),
            "tau": _float_box(tau),
            "g": _float_box(g_value),
            "delta_t": _float_box(delta_t),
        }
        step_number = _float_box(steps_text)
        if any(value is None for value in boxes.values()) or step_number is None:
            lines.append("User parameter path: unavailable. A user input is missing.")
        elif not step_number.is_integer() or step_number < 1:
            lines.append("User parameter path: unavailable. steps is missing.")
        else:
            params = boxes
            steps = int(step_number)
            lines.append("User parameter path, separate from the two committed brain paths:")
            lines.extend(_formula(None, params, steps))
        lines.extend(_lambda_engine(readings_text))
    else:
        lines.append("LambdaEngine path: unavailable on the committed replay. No readings ship with it.")
    try:
        table = _brain_table()
    except Exception:
        table = "Both brain paths: unavailable."
    lines.extend(_canonical("" if mode == "committed replay" and _blank(trace_text) else trace_text))
    bullet = "\n".join(f"- {line}" for line in lines)
    return bullet + "\n\n" + table


def example() -> str:
    return run("committed replay", "", "", "", "", "", "", "", "")


with gr.Blocks(title="HNC field") as demo:
    gr.Markdown(
        f"""# HNC field

Licence: **{guard.LICENCE}** (same as the Aureon OS `LICENSE`).

Runs `HarmonicRealityField.step`, `read_canonical_field`, and `blend_field`.
The class default `HarmonicRealityField()` is the multiverse-on path.
The other row is the multiverse-off path, `enable_multiverse=False`.

| Path | Coherence | Last Lambda | State |
| --- | --- | --- | --- |
| Class default HarmonicRealityField() (multiverse on) | 0.857719007627168 | 0.002306037019850606 | LOCKED |
| enable_multiverse=False (multiverse off) | 0.9331334813083556 | 1.409626852655939 | UNIFIED |

Both rows are cited from `reports/measured/brain.json`. A missing input stays unavailable.

{HOLD}

This Space makes no track-record, return, or performance claim.
{guard.REFUSAL}
"""
    )
    mode = gr.Radio(["committed replay", "user inputs"], value="committed replay", label="Source")
    with gr.Row():
        alpha = gr.Textbox(label="alpha")
        beta = gr.Textbox(label="beta")
        tau = gr.Textbox(label="tau")
    with gr.Row():
        g_value = gr.Textbox(label="g")
        delta_t = gr.Textbox(label="delta_t")
        steps_text = gr.Textbox(label="steps")
    trace_text = gr.Textbox(label="Canonical envelope JSONL", lines=4)
    readings_text = gr.Textbox(label="LambdaEngine readings JSON", lines=4)
    output = gr.Markdown()
    gr.Button("Run").click(
        run,
        [mode, alpha, beta, tau, g_value, delta_t, steps_text, trace_text, readings_text],
        output,
    )


if __name__ == "__main__":
    demo.launch(
        server_name="127.0.0.1",
        server_port=int(os.environ.get("PORT", "7860")),
        share=False,
    )
