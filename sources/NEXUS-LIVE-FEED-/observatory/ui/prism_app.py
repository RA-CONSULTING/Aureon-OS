"""Streamlit Prism dashboard for Observatory metrics."""

from __future__ import annotations

import pathlib

import pandas as pd
import streamlit as st

from observatory.metrics.registry import RegistryClient

st.set_page_config(page_title="Observatory Prism", layout="wide")

st.title("Observatory Prism")
st.caption("Transparent market resonance metrics built from public data.")

registry_path = pathlib.Path("/tmp/observatory_registry.json")
registry = RegistryClient(registry_path)

runs = registry._load_runs()

if not runs:
    st.info("No metric runs recorded yet. Trigger the daily pipeline to populate data.")
    st.stop()

latest = runs[-1]
metrics_path = pathlib.Path(latest["metrics_path"])
frame = pd.read_parquet(metrics_path)

col1, col2 = st.columns(2)
col1.metric("Integrity (Dₜ)", f"{frame['integrity_perturbation'].iloc[-1]:.2f}")
col1.metric("CCI", f"{frame['CCI'].iloc[-1]:.2f}")
col1.metric("Polaris ΔCₜ", f"{frame['deltaC_polaris'].iloc[-1]:.2f}")

col2.metric("Choerance Φₜ", f"{frame['choerance_phi'].iloc[-1]:.2f}")
col2.metric("Unity Uₜ", f"{frame['unity_index'].iloc[-1]:.2f}")
col2.metric("Coherence Index", f"{frame['coherence_score'].iloc[-1]:.2f}")

st.subheader("Storm-Glass Dashboard")
st.line_chart(frame.set_index("date")["CCI"])

st.subheader("Integrity Heatmap")
heatmap_cols = [
    "integrity_perturbation",
    "flag_volume_spike",
    "flag_impact",
    "flag_rv",
    "flag_benford",
]
st.dataframe(
    frame.set_index("date").reindex(columns=heatmap_cols, fill_value=False),
    use_container_width=True,
)

st.subheader("Resonance Panel")
st.line_chart(frame.set_index("date").reindex(columns=["pingpong_corr", "grav_corr"]))

st.subheader("Downloads")
st.download_button("Download daily metrics (Parquet)", metrics_path.read_bytes(), file_name="market_observatory_daily.parquet")
