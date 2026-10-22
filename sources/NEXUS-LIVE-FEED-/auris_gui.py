import streamlit as st
import requests
import json
from PIL import Image
import base64
from io import BytesIO

st.set_page_config(page_title="AURIS Interface", layout="wide")

st.title("AURIS Temporal Aura Network Interface")

st.sidebar.title("Operator Input")
name = st.sidebar.text_input("Name", "Gary Leckey")
location = st.sidebar.text_input("Location", "Belfast, Northern Ireland")

if st.sidebar.button("Scan Me"):
    with st.spinner("Running Temporal Aura Scan..."):
        try:
            response = requests.post("http://localhost:8080/scan", json={"name": name, "location": location})
            if response.status_code == 200:
                scan_data = response.json()

                st.header(f"TEMPORAL AURA SCAN: {scan_data['operator']}")
                st.write(f"**Date:** {scan_data['timestamp']}")
                st.write(f"**Location:** {scan_data['location']}")
                st.write("---")

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Coherence Vector", f"{scan_data['coherence']:.3f}")
                with col2:
                    st.metric("Phase-Lock Ratio", f"{scan_data['phase_lock_ratio']:.3f}")
                with col3:
                    st.metric("Quantum Alignment", f"{scan_data['quantum_alignment']:.4f}")

                st.write(f"**Seal Hash (SHA3-512):** `{scan_data['seal_hash']}`")
                st.info("**Status:** Prime Sentinel Field Stable.")

                st.write("---")
                st.subheader("Visualizations")
                
                col1, col2 = st.columns(2)
                with col1:
                    if scan_data['plots']['frequency_plot']:
                        try:
                            with open(scan_data['plots']['frequency_plot'], "rb") as f:
                                st.image(f.read(), caption="Schumann Frequency Drift")
                        except FileNotFoundError:
                            st.warning(f"Plot not found at {scan_data['plots']['frequency_plot']}")

                with col2:
                    if scan_data['plots']['coherence_plot']:
                        try:
                            with open(scan_data['plots']['coherence_plot'], "rb") as f:
                                st.image(f.read(), caption="Temporal Coherence Field")
                        except FileNotFoundError:
                            st.warning(f"Plot not found at {scan_data['plots']['coherence_plot']}")

            else:
                st.error(f"Error: {response.status_code} - {response.text}")
        except requests.exceptions.ConnectionError:
            st.error("Connection Error: Is the AURIS API running at http://localhost:8080?")
        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")

st.sidebar.write("---")
st.sidebar.subheader("System Status")
try:
    status_response = requests.get("http://localhost:8080/status")
    if status_response.status_code == 200:
        status_data = status_response.json()
        st.sidebar.write(f"**System:** {status_data['system']}")
        st.sidebar.write(f"**Uptime (UTC):** {status_data['uptime_utc']}")
        st.sidebar.write(f"**Baseline Frequency:** {status_data['baseline_freq_hz']} Hz")
        st.sidebar.write(f"**Coherence Reference:** {status_data['coherence_reference']}")
    else:
        st.sidebar.warning("Could not fetch system status.")
except requests.exceptions.ConnectionError:
    st.sidebar.warning("API not running.")
