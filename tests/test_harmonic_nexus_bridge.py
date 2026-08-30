import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from aureon.harmonic.harmonic_nexus_bridge import DomainAnomaly, HarmonicNexusBridge


def _anomaly(domain, when, receipt_id):
    timestamp = when.timestamp()
    return DomainAnomaly(
        anomaly_id=f"{domain}-{receipt_id}", domain=domain, observed_at=when,
        lagrangian_score=12.85 if domain == "geopolitical" else 5.0,
        coherence=0.88, energy_value=1.0, energy_unit="unit", summary="observed",
        source="provider", metadata={"severity": "HIGH"}, source_id="provider.source",
        source_timestamp=timestamp, received_at=timestamp + 1.0, receipt_id=receipt_id,
        truth_status="real_observed", generated_values=False,
    )


def test_receipt_gate_preserves_clustering_and_rejects_incomplete_input(monkeypatch):
    now = datetime.now(timezone.utc)
    bridge = HarmonicNexusBridge()
    assert bridge.register(DomainAnomaly(
        anomaly_id="bad", domain="plasma", observed_at=now, lagrangian_score=1.0,
        coherence=0.5, energy_value=1.0, energy_unit="unit", summary="bad", source="bad",
    )) is False
    assert bridge.analyze().to_dict()["status"] == "no_data"
    assert bridge.register(_anomaly("geopolitical", now - timedelta(seconds=26), "geo-1")) is True
    assert bridge.register(_anomaly("plasma", now, "plasma-1")) is True
    report = bridge.analyze()
    assert report.status == "Analyzed"
    assert report.avg_temporal_proximity_sec == 26
    assert report.clustering_score == bridge.expected_window_seconds / 26


def test_injection_writes_only_validated_provenance(tmp_path):
    now = datetime.now(timezone.utc)
    bridge = HarmonicNexusBridge()
    assert bridge.register(_anomaly("geopolitical", now, "geo-1"))
    path = tmp_path / "network.json"
    assert bridge.inject_into_planetary_network(path) == path
    data = json.loads(path.read_text(encoding="utf-8"))
    signature = data["harmonic_signatures"][0]
    assert signature["receipt_id"] == "geo-1"
    assert signature["generated_values"] is False
