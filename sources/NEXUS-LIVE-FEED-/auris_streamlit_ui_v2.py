"""Streamlit UI for interacting with the extended Temporal Aura Scan Engine."""
from __future__ import annotations

from typing import Dict, List, Optional

import csv
import datetime as dt
import io

import requests
import streamlit as st

from temporal_aura_scan_ext import EARTH_ZIP, batch_run_temporal_scans, run_temporal_aura_scan


st.set_page_config(page_title="AURIS Temporal Aura Interface", layout="wide")


def _validate_iso_date(value: str, field_name: str) -> str:
    try:
        dt.datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:  # noqa: PERF203 - clarity beats micro-optimisation here
        raise ValueError(f"{field_name} must be in YYYY-MM-DD format.") from exc
    return value


def _prepare_user_payload(
    name: str,
    location: Optional[str],
    birth_date: dt.date,
    temporal_id: Optional[str],
) -> Dict[str, Optional[str]]:
    if not name.strip():
        raise ValueError("Name is required for a scan.")

    birth_iso = birth_date.isoformat() if birth_date else None
    temporal_value = (temporal_id or "").strip() or birth_iso
    if temporal_value:
        _validate_iso_date(temporal_value, "Temporal ID")

    payload = {
        "name": name.strip(),
        "location": location.strip() if location else None,
        "birth_date": birth_iso,
        "temporal_id": temporal_value,
    }
    return payload


def _display_report(report: Dict[str, object]) -> None:
    st.subheader("Scan Result")
    st.json(report)


st.title("AURIS Temporal Aura Console v2")
st.caption("Capture, seal, and verify temporal aura scans with extended metadata.")


default_zip_path = st.sidebar.text_input(
    "Schumann ZIP path", value=str(EARTH_ZIP), help="Path to the Schumann resonance data archive."
)


with st.form("single_scan_form"):
    st.subheader("Single Scan")
    name = st.text_input("Name", placeholder="Operator name")
    birth_date = st.date_input(
        "Birth Date", value=dt.date(1990, 1, 1), format="YYYY-MM-DD"
    )
    location = st.text_input("Location", placeholder="City, Region")
    temporal_id = st.text_input(
        "Temporal ID", placeholder="Defaults to birth date if left blank (YYYY-MM-DD)"
    )
    submitted = st.form_submit_button("Run Scan")

    if submitted:
        try:
            payload = _prepare_user_payload(name, location, birth_date, temporal_id)
            report = run_temporal_aura_scan(
                payload["name"],
                payload["location"],
                default_zip_path,
                birth_date=payload["birth_date"],
                temporal_id=payload["temporal_id"],
            )
            st.success("Scan complete. Quantum seal generated.")
            _display_report(report)
        except ValueError as exc:
            st.error(str(exc))
        except FileNotFoundError:
            st.error("Schumann resonance ZIP path could not be located.")
        except Exception as exc:  # pragma: no cover - streamlit surface level safeguard
            st.error(f"Unexpected error while running scan: {exc}")


st.subheader("Batch Scan")
st.write(
    "Upload a CSV containing columns: name, birth_date, location, temporal_id."
)

batch_file = st.file_uploader("Batch CSV", type="csv", accept_multiple_files=False)

if batch_file is not None:
    try:
        content = batch_file.getvalue().decode("utf-8")
        reader = csv.DictReader(io.StringIO(content))
        missing_columns = {"name", "birth_date", "location", "temporal_id"} - set(
            reader.fieldnames or []
        )
        if missing_columns:
            raise ValueError(
                "CSV is missing required columns: " + ", ".join(sorted(missing_columns))
            )
        users: List[Dict[str, Optional[str]]] = []
        for row in reader:
            if not any(row.values()):
                continue
            name = (row.get("name") or "").strip()
            birth_raw = (row.get("birth_date") or "").strip()
            location = (row.get("location") or "").strip() or None
            temporal_raw = (row.get("temporal_id") or "").strip() or None
            if not name:
                raise ValueError("Each row must include a name.")
            if birth_raw:
                _validate_iso_date(birth_raw, "Birth date")
            else:
                raise ValueError(f"Birth date missing for row with name '{name}'.")
            if temporal_raw:
                _validate_iso_date(temporal_raw, "Temporal ID")
            payload = {
                "name": name,
                "location": location,
                "birth_date": birth_raw,
                "temporal_id": temporal_raw or birth_raw,
            }
            users.append(payload)

        if not users:
            raise ValueError("No valid rows detected in the uploaded CSV.")

        reports = batch_run_temporal_scans(users, default_zip_path)
        st.success(f"Batch complete. Processed {len(reports)} scans.")
        for idx, report in enumerate(reports, start=1):
            st.markdown(f"### Report {idx}")
            st.json(report)
    except ValueError as exc:
        st.error(str(exc))
    except FileNotFoundError:
        st.error("Schumann resonance ZIP path could not be located.")
    except Exception as exc:  # pragma: no cover
        st.error(f"Unexpected error during batch processing: {exc}")


st.divider()
st.subheader("Verify a Quantum Seal")

verification_col1, verification_col2 = st.columns([2, 3])

with verification_col1:
    verification_service = st.text_input(
        "Verification Service URL",
        value="http://localhost:8080",
        help="Base URL for the FastAPI verification endpoint.",
    )
with verification_col2:
    seal_hash = st.text_input("Seal Hash", placeholder="Paste SHA3-512 seal hash")

if st.button("Verify Seal"):
    if not seal_hash.strip():
        st.warning("Enter a seal hash to verify.")
    else:
        try:
            response = requests.get(
                verification_service.rstrip("/") + "/seal/verify",
                params={"hash": seal_hash.strip()},
                timeout=10,
            )
            if response.status_code == 200:
                st.json(response.json())
            else:
                st.error(
                    f"Verification service responded with status {response.status_code}: {response.text}"
                )
        except requests.RequestException as exc:  # pragma: no cover - network guard
            st.error(f"Failed to contact verification service: {exc}")
