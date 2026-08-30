"""P1 repair: the HNC live connector forwards the FULL LighthouseEvent.

The `intelligence.lighthouse.event` payload used to carry only 4 of the event's
12 fields — the structural signature (c_linear / c_nonlinear / c_phi / g_eff /
q_anomaly / regime_before / regime_after) was dropped at the bridge, so no
downstream consumer could ever see WHY the Lighthouse fired. This drives the
real payload-construction path with a real LighthouseEvent and asserts the
original keys are unchanged (additive fix) and the signature is present.
"""

import time
from collections import deque

import numpy as np

from aureon.bridges.aureon_hnc_live_connector import HncLiveConnector
from aureon.bridges.aureon_hnc_surge_detector import SurgeWindow
from aureon.wisdom.aureon_qgita_framework import (
    FTCP,
    EventType,
    LighthouseEvent,
)

ORIGINAL_KEYS = {"symbol", "lighthouse_intensity", "confidence", "event_type", "timestamp"}
SIGNATURE_KEYS = {
    "c_linear", "c_nonlinear", "c_phi", "g_eff", "q_anomaly",
    "regime_before", "regime_after", "ftcp",
}


def _real_lighthouse_event() -> LighthouseEvent:
    ftcp = FTCP(
        timestamp=1000.0,
        knot_index=3,
        curvature=0.42,
        interval_ratio=0.618,
        phi_match=0.97,
        g_eff=0.55,
        local_contrast=0.0009,
        is_valid=True,
    )
    return LighthouseEvent(
        timestamp=1000.0,
        ftcp=ftcp,
        lighthouse_intensity=0.81,
        c_linear=0.72,
        c_nonlinear=0.68,
        c_phi=0.61,
        g_eff=0.55,
        q_anomaly=0.33,
        confidence=1.4,
        event_type=EventType.REGIME_CHANGE,
        regime_before="quasi-stable",
        regime_after="coherent",
    )


class _CaptureHub:
    def __init__(self):
        self.published = []

    def _publish_to_bus(self, topic, data):
        self.published.append((topic, data))
        return True

    def subscribe(self, *a, **k):
        pass


def test_lighthouse_payload_carries_all_twelve_fields(monkeypatch, tmp_path):
    connector = HncLiveConnector.__new__(HncLiveConnector)
    connector.hub = _CaptureHub()
    connector.thought_bus = None
    connector.bot_shape_scanner = None
    now = time.time()
    connector._source_timestamp_history = {
        "BTC/USD": deque(np.linspace(now - 39, now, 40), maxlen=40),
    }
    connector._receipt_id_history = {
        "BTC/USD": deque([f"receipt-{i}" for i in range(40)], maxlen=40),
    }
    connector._last_receipt = {
        "BTC/USD": {"source_timestamp": now, "receipt_id": "receipt-39"},
    }

    class _Lighthouse:
        def validate_ftcp(self, strongest, values):
            return _real_lighthouse_event()

    class _FtcpDetector:
        def detect_ftcps(self, times, values):
            return [object()]

        def get_strongest_ftcp(self, ftcps):
            return ftcps[0]

    class _Qgita:
        lighthouse = _Lighthouse()
        ftcp_detector = _FtcpDetector()

    connector.qgita = _Qgita()

    class _Detector:
        sample_rate = 2
        price_history = {"BTC/USD": list(np.linspace(100.0, 101.0, 40))}

    connector.detector = _Detector()

    surge = SurgeWindow(
        symbol="BTC/USD",
        start_time=990.0,
        end_time=1000.0,
        peak_time=995.0,
        intensity=0.7,
        primary_harmonic="528Hz",
    )
    connector._publish_surge(surge)

    lighthouse_events = [
        data for topic, data in connector.hub.published
        if topic == "intelligence.lighthouse.event"
    ]
    assert lighthouse_events, "lighthouse event never published"
    payload = lighthouse_events[-1]

    assert ORIGINAL_KEYS <= set(payload), "additive fix broke an original key"
    assert SIGNATURE_KEYS <= set(payload), (
        f"structural signature dropped again: missing "
        f"{sorted(SIGNATURE_KEYS - set(payload))}"
    )
    assert payload["c_linear"] == 0.72
    assert payload["regime_after"] == "coherent"
    assert payload["ftcp"]["phi_match"] == 0.97
    assert payload["event_type"] == EventType.REGIME_CHANGE.value
