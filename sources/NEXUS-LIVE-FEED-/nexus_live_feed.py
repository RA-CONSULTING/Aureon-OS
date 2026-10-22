"""Streamlit client for the Auris Unified Interface V4 backend."""

from __future__ import annotations

from typing import Any, Dict, List

import requests
import streamlit as st

BACKEND_DEFAULT = st.secrets.get("AURIS_BACKEND", "http://localhost:8080")
POLL_DEFAULT = 5
COMPONENT_LABELS = {
    "C1": ("C1 Temporal", "Temporal Coherence"),
    "C2inv": ("1−Entropy", "Entropy Inversion"),
    "C4": ("Schumann", "Schumann Coupling"),
    "C5_BQI": ("BQI", "Bio-Quantum Integrity"),
}

st.set_page_config(page_title="Nexus Live Feed", page_icon="🌀", layout="wide")

with st.sidebar:
    st.subheader("Backend")
    BACKEND = st.text_input(
        "Unified API base URL",
        value=BACKEND_DEFAULT,
    )
    POLL_SEC = st.slider("Refresh (seconds)", 2, 20, POLL_DEFAULT)
    surge_thresh = st.slider("Surge Threshold (UVC)", 0.70, 0.99, 0.90)
    st.write("Status:")
    try:
        status = requests.get(f"{BACKEND}/status", timeout=2).json()
    except Exception as exc:  # pragma: no cover - direct UI feedback
        st.error(f"Backend not reachable: {exc}")
    else:
        system_name = status.get("system", "Unified API")
        version = status.get("version")
        caption = f"{system_name} online"
        if version:
            caption += f" — v{version}"
        st.success(caption)

st.autorefresh(interval=int(POLL_SEC * 1000), key="nexus-poller")

col_left, col_right = st.columns([3, 2])


def fetch_json(url: str, timeout: int = 4) -> Dict[str, Any]:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    payload: Dict[str, Any] = response.json()
    return payload


feed_data: Dict[str, Any] = {}
feed_error: str | None = None
try:
    feed_data = fetch_json(f"{BACKEND}/surge/uvc?n=240")
except requests.HTTPError as exc:
    status_code = exc.response.status_code if exc.response is not None else "?"
    feed_error = f"HTTP {status_code}"
except requests.RequestException as exc:
    feed_error = str(exc)

recent_records: List[Dict[str, Any]] = []
recent_error: str | None = None
try:
    payload = fetch_json(f"{BACKEND}/bioscan/recent?n=12")
    recent_records = payload.get("results", []) if isinstance(payload, dict) else []
except requests.HTTPError as exc:
    status_code = exc.response.status_code if exc.response is not None else "?"
    recent_error = f"HTTP {status_code}"
except requests.RequestException as exc:
    recent_error = str(exc)

with col_left:
    st.subheader("🧭 Harmonic Surge Monitor")
    if feed_error:
        st.error(f"UVC fetch failed: {feed_error}")
    else:
        uvc_series = feed_data.get("uvc") or []
        components = feed_data.get("components") or {}
        if uvc_series:
            st.line_chart({"UVC": uvc_series}, use_container_width=True)
            delta_value = None
            if len(uvc_series) > 1:
                delta_value = f"{(uvc_series[-1] - uvc_series[-2]):+.3f}"
            st.metric("Current UVC", f"{uvc_series[-1]:.3f}", delta=delta_value)
            if uvc_series[-1] >= surge_thresh:
                st.success("Surge window active")
            else:
                st.info("Monitoring…")
        else:
            st.info("No bioscans available yet.")

        if components:
            try:
                st.line_chart(
                    {
                        COMPONENT_LABELS.get("C1", ("C1", ""))[0]: components.get("C1", []),
                        COMPONENT_LABELS.get("C2inv", ("C2inv", ""))[0]: components.get("C2inv", []),
                        COMPONENT_LABELS.get("C4", ("C4", ""))[0]: components.get("C4", []),
                        COMPONENT_LABELS.get("C5_BQI", ("C5_BQI", ""))[0]: components.get("C5_BQI", []),
                    },
                    use_container_width=True,
                )
                st.caption("Component coherence history (latest 240 samples)")
            except Exception:  # pragma: no cover - visualization guard
                st.warning("Component chart could not be rendered.")
        else:
            st.caption("Component feed pending bioscans.")

with col_right:
    st.subheader("📡 Component Snapshot")
    if feed_error:
        st.info("Component snapshot unavailable until feed recovers.")
    else:
        components = feed_data.get("components") or {}
        if components:
            latest_values = {
                key: (values[-1] if values else None)
                for key, values in components.items()
            }
            for key, (label, description) in COMPONENT_LABELS.items():
                col = st.container()
                value = latest_values.get(key)
                if value is None:
                    col.info(f"{label}: awaiting data…")
                    continue
                col.metric(label, f"{value:.3f}")
                if description:
                    col.caption(description)
        else:
            st.info("Awaiting component telemetry…")

st.divider()

st.subheader("🧬 Recent Bioscans")
if recent_error:
    st.error(f"Recent bioscans fetch failed: {recent_error}")
else:
    if recent_records:
        columns = st.columns(3)
        for index, record in enumerate(recent_records[:9]):
            layer_scores = record.get("layer_scores", {}) if isinstance(record, dict) else {}
            with columns[index % 3]:
                st.markdown(f"**{record.get('session_id', '(no id)')}**")
                st.metric("BCI", f"{record.get('bci', 0):.3f}")
                st.write(
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
                st.caption(f"Seal: {seals.get('report_hash', '…')[:18]}…")
    else:
        st.info("No bioscans available yet.")
