"""Streamlit WebSocket client for the Auris Unified Interface v4 backend."""

from __future__ import annotations

import json
import queue
import threading
import time
from typing import Any, Dict, List

import pandas as pd
import requests
import streamlit as st

try:
    import websocket  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    websocket = None

VALIDATION_KEYS = [
    ("C1", "🕰️", "Temporal Coherence"),
    ("C2inv", "🧘", "1−Entropy"),
    ("C4", "🌍", "Schumann Coupling"),
    ("C5_BQI", "💓", "Bio-Quantum Integrity"),
    ("UVC", "🧭", "Unified Validation Coherence"),
]


def nexus_style() -> None:
    st.markdown(
        """
        <style>
        body {
            background: radial-gradient(1200px 800px at 10% 0%, #0b132b 0%, #0a0f25 45%, #070a19 100%);
            color: #e3ecff;
        }
        .stMetric {
            background: rgba(20, 30, 60, 0.45);
            border-radius: 16px;
            padding: 6px 12px;
        }
        .metric-card {
            background: rgba(20, 30, 60, 0.45);
            border: 1px solid rgba(120, 180, 255, 0.12);
            box-shadow: 0 0 20px rgba(0, 180, 255, 0.08) inset;
            border-radius: 16px;
            padding: 10px;
        }
        .nexus-title {
            text-align: center;
            letter-spacing: 0.08em;
        }
        .nexus-caption {
            text-align: center;
            color: #a8c7ff;
            margin-bottom: 1rem;
        }
        .stProgress > div > div {
            background-image: linear-gradient(90deg, #38bdf8, #a855f7);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


BACKEND_DEFAULT = st.secrets.get("AURIS_BACKEND", "http://localhost:8080")

st.set_page_config(page_title="Nexus Live Feed (WS)", page_icon="🛰️", layout="wide")

nexus_style()

st.markdown("<h1 class='nexus-title'>🌀 NEXUS • LIVE • FEED — WebSocket</h1>", unsafe_allow_html=True)
st.markdown(
    "<div class='nexus-caption'>Harmonic Nexus Core — instant coherence telemetry</div>",
    unsafe_allow_html=True,
)


with st.sidebar:
    backend = st.text_input("Unified API base URL", value=BACKEND_DEFAULT)
    ws_url = backend.replace("http://", "ws://").replace("https://", "wss://") + "/ws"
    surge_thresh = st.slider("Surge Threshold (UVC)", 0.70, 0.99, 0.90)
    manual_refresh = st.button("Manual refresh")
    st.write(f"WebSocket: {ws_url}")


if "event_q" not in st.session_state:
    st.session_state.event_q = queue.Queue()
if "ws_running" not in st.session_state:
    st.session_state.ws_running = False
if "initialized" not in st.session_state:
    st.session_state.initialized = False
if "validation_history" not in st.session_state:
    st.session_state.validation_history = {key: [] for key, _, _ in VALIDATION_KEYS}
if "feed_data" not in st.session_state:
    st.session_state.feed_data = {"uvc": [], "components": {}, "recent": []}
if "last_fetch_error" not in st.session_state:
    st.session_state.last_fetch_error = None
if "brainwave_data" not in st.session_state:
    st.session_state.brainwave_data = {"current": {}, "series": {}, "error": None}


status_ph = st.empty()
data_status_ph = st.empty()
event_log_ph = st.empty()


def ws_worker(url: str, q: "queue.Queue[Dict[str, Any]]") -> None:
    while True:
        try:
            def on_message(_ws: Any, message: str) -> None:
                try:
                    payload = json.loads(message)
                except json.JSONDecodeError:
                    return
                q.put(payload)

            def on_error(_ws: Any, err: Any) -> None:
                q.put({"type": "ws_error", "error": str(err)})

            def on_close(_ws: Any, status_code: int, msg: str) -> None:
                q.put({"type": "ws_closed", "code": status_code, "msg": str(msg)})

            ws = websocket.WebSocketApp(  # type: ignore[operator]
                url,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
            )
            ws.run_forever()
        except Exception as exc:  # pragma: no cover - background thread guard
            q.put({"type": "ws_exception", "error": str(exc)})
        finally:
            time.sleep(2.0)


if websocket is None:
    status_ph.error("websocket-client not installed. Run: pip install websocket-client")
else:
    if not st.session_state.ws_running:
        threading.Thread(
            target=ws_worker,
            args=(ws_url, st.session_state.event_q),
            daemon=True,
        ).start()
        st.session_state.ws_running = True
        status_ph.info("Connecting to WebSocket…")


validation_expander = st.expander("🧭 Harmonic Validation Interface — the proof layer", expanded=True)
uvc_chart = st.empty()
uvc_metric = st.empty()
components_chart = st.empty()
brainwave_container = st.container()
list_ph = st.empty()


def _render_recent(records: List[Dict[str, Any]]) -> None:
    container = list_ph.container()
    container.subheader("Recent Bioscans")
    if not records:
        container.info("No bioscans available yet.")
        return
    columns = container.columns(3)
    for index, record in enumerate(records[:9]):
        layer_scores = record.get("layer_scores", {})
        column = columns[index % 3]
        column.markdown(f"**{record.get('session_id', '(no id)')}**")
        column.metric("BCI", f"{record.get('bci', 0):.3f}")
        column.write(
            "CRC:**{crc:.2f}** NFC:**{nfc:.2f}** PEB:**{peb:.2f}** "
            "BHS:**{bhs:.2f}** PLA:**{pla:.2f}**".format(
                crc=(layer_scores.get("crc", {}).get("mu") or 0),
                nfc=(layer_scores.get("nfc", {}).get("mu") or 0),
                peb=(layer_scores.get("peb", {}).get("mu") or 0),
                bhs=(layer_scores.get("bhs", {}).get("mu") or 0),
                pla=(layer_scores.get("pla", {}).get("mu") or 0),
            )
        )
        seals = record.get("seals") or {}
        column.caption(f"Seal: {seals.get('report_hash', '…')[:18]}…")


def render_validation_panel(container: Any, history: Dict[str, List[float]]) -> None:
    with container:
        container.caption("Precision-weighted coherence snapshot (last 60 samples).")
        progress_cols = container.columns(len(VALIDATION_KEYS))
        spark_cols = container.columns(len(VALIDATION_KEYS))
        for idx, (key, emoji, label) in enumerate(VALIDATION_KEYS):
            values = history.get(key) or []
            latest = values[-1] if values else None
            col = progress_cols[idx]
            col.markdown(f"**{emoji} {label}**")
            if latest is not None:
                col.metric("Score", f"{latest:.3f}")
                progress_value = int(max(0, min(100, round(latest * 100))))
                col.progress(progress_value)
            else:
                col.info("Awaiting data…")
            spark_col = spark_cols[idx]
            spark_data = values[-60:]
            if spark_data:
                spark_col.line_chart({f"{emoji} {label}": spark_data}, use_container_width=True)
                spark_col.caption("Last 60 samples")
            else:
                spark_col.caption("No samples yet.")


def refresh_from_backend(base: str) -> bool:
    try:
        feed = requests.get(f"{base}/surge/uvc?n=240", timeout=4).json()
        recent = requests.get(f"{base}/bioscan/recent?n=12", timeout=4).json().get("results", [])
    except Exception as exc:  # pragma: no cover - Streamlit feedback path
        st.session_state.last_fetch_error = str(exc)
        return False

    st.session_state.feed_data = {
        "uvc": feed.get("uvc", []),
        "components": feed.get("components", {}),
        "recent": recent,
    }
    history = st.session_state.validation_history
    uvc_series = st.session_state.feed_data.get("uvc", [])
    history["UVC"] = uvc_series[-60:] if uvc_series else []
    for key in ("C1", "C2inv", "C4", "C5_BQI"):
        series = st.session_state.feed_data.get("components", {}).get(key, [])
        history[key] = series[-60:] if series else []
    st.session_state.last_fetch_error = None
    st.session_state.initialized = True
    return True


def render_feed(feed: Dict[str, Any], error: str | None) -> None:
    uvc = feed.get("uvc") or []
    components = feed.get("components") or {}
    recent = feed.get("recent") or []

    if uvc:
        delta_value = None
        if len(uvc) > 1:
            delta_value = f"{(uvc[-1] - uvc[-2]):+.3f}"
        uvc_chart.line_chart({"UVC": uvc}, use_container_width=True)
        uvc_metric.metric("Current UVC", f"{uvc[-1]:.3f}", delta=delta_value)
    else:
        uvc_chart.info("No bioscans available yet.")
        uvc_metric.empty()

    if error:
        data_status_ph.error(f"Backend fetch failed: {error}")
    else:
        if uvc:
            if uvc[-1] >= surge_thresh:
                data_status_ph.success("Surge window active")
            else:
                data_status_ph.info("Monitoring…")
        else:
            data_status_ph.info("Awaiting bioscans…")

    if components:
        try:
            components_chart.line_chart(
                {
                    "C1 Temporal": components.get("C1", []),
                    "1−Entropy": components.get("C2inv", []),
                    "Schumann": components.get("C4", []),
                    "BQI": components.get("C5_BQI", []),
                },
                use_container_width=True,
            )
        except Exception:  # pragma: no cover - visualization guard
            components_chart.warning("Component chart could not be rendered.")
    else:
        components_chart.info("Component feed pending bioscans.")

    _render_recent(recent)


def refresh_brainwaves(base: str) -> None:
    try:
        current = requests.get(f"{base}/eeg/current", timeout=4).json()
        series = requests.get(f"{base}/eeg/recent?n=240", timeout=4).json()
    except Exception as exc:
        st.session_state.brainwave_data = {"current": {}, "series": {}, "error": str(exc)}
        return

    st.session_state.brainwave_data = {"current": current, "series": series, "error": None}


def _clean_series(values: List[Any]) -> List[float]:
    cleaned: List[float] = []
    for value in values:
        if value is None:
            cleaned.append(float("nan"))
        else:
            try:
                cleaned.append(float(value))
            except Exception:
                cleaned.append(float("nan"))
    return cleaned


def render_brainwave_section(container: Any, payload: Dict[str, Any]) -> None:
    with container:
        container.subheader("🧠 Live Brainwaves")
        error = payload.get("error")
        if error:
            container.error(f"EEG fetch failed: {error}")
            return

        current = payload.get("current") or {}
        bands = current.get("bands") or {}
        ratios = current.get("ratios") or {}
        series = payload.get("series") or {}
        history = series.get("bands") or {}

        if not bands and not history:
            container.info("Awaiting EEG data…")
            return

        if bands:
            df = pd.DataFrame(
                {
                    "Band": ["Δ delta", "θ theta", "α alpha", "β beta", "γ gamma"],
                    "Power": [
                        bands.get("delta", 0.0),
                        bands.get("theta", 0.0),
                        bands.get("alpha", 0.0),
                        bands.get("beta", 0.0),
                        bands.get("gamma", 0.0),
                    ],
                }
            ).set_index("Band")
            container.bar_chart(df, use_container_width=True)
            container.caption("Δ, θ, α, β, γ distribution (normalized)")

        if history:
            container.line_chart(
                {
                    "Δ delta": _clean_series(history.get("delta", [])),
                    "θ theta": _clean_series(history.get("theta", [])),
                    "α alpha": _clean_series(history.get("alpha", [])),
                    "β beta": _clean_series(history.get("beta", [])),
                    "γ gamma": _clean_series(history.get("gamma", [])),
                },
                use_container_width=True,
            )
            container.caption("EEG band powers over time (oldest → newest)")

        if ratios:
            col1, col2, col3 = container.columns(3)
            col1.metric("α/θ", f"{ratios.get('alpha_theta', 0.0):.2f}")
            col2.metric("β/α", f"{ratios.get('beta_alpha', 0.0):.2f}")
            col3.metric("γ/α", f"{ratios.get('gamma_alpha', 0.0):.2f}")


refresh_needed = manual_refresh or not st.session_state.initialized


event_notes: List[str] = []
while not st.session_state.event_q.empty():
    try:
        event = st.session_state.event_q.get_nowait()
    except queue.Empty:
        break
    event_type = event.get("type")
    if event_type == "bioscan":
        refresh_needed = True
        status_ph.success("WebSocket connected")
        event_notes.append(
            "New bioscan {session} • BCI {bci:.3f}".format(
                session=event.get("session_id", "?"), bci=event.get("bci", 0.0)
            )
        )
    elif event_type == "ws_error":
        status_ph.error(f"WebSocket error: {event.get('error')}")
        event_notes.append(f"WebSocket error: {event.get('error')}")
    elif event_type == "ws_closed":
        status_ph.warning("WebSocket closed — attempting to reconnect")
        event_notes.append("WebSocket closed — reconnecting…")
    elif event_type == "ws_exception":
        status_ph.error(f"WebSocket exception: {event.get('error')}")
        event_notes.append(f"WebSocket exception: {event.get('error')}")


if refresh_needed:
    if refresh_from_backend(backend):
        refresh_brainwaves(backend)

render_validation_panel(validation_expander, st.session_state.validation_history)
render_feed(st.session_state.feed_data, st.session_state.last_fetch_error)
render_brainwave_section(brainwave_container, st.session_state.brainwave_data)

if event_notes:
    event_log_ph.write("\n".join(event_notes))
