#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Receipt-gated cross-domain harmonic clustering bridge."""

import argparse
import importlib.util
import json
import logging
import math
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

logger = logging.getLogger(__name__)

DEFAULT_EXPECTED_WINDOW_SECONDS = 72 * 60
DEFAULT_PLANETARY_NETWORK_PATH = Path(__file__).resolve().parents[1] / 'planetary_harmonic_network.json'
MAX_RECEIPT_AGE_SECONDS = 300.0
FUTURE_SKEW_SECONDS = 30.0


@dataclass(frozen=True)
class DomainAnomaly:
    anomaly_id: str
    domain: str
    observed_at: datetime
    lagrangian_score: float
    coherence: float
    energy_value: float
    energy_unit: str
    summary: str
    source: str
    metadata: Dict[str, object] = field(default_factory=dict)
    source_id: Optional[str] = None
    source_timestamp: Optional[float] = None
    received_at: Optional[float] = None
    receipt_id: Optional[str] = None
    truth_status: str = 'no_data'
    generated_values: bool = False


@dataclass(frozen=True)
class CrossDomainAnalysis:
    status: str
    geo_count: Optional[int]
    plasma_count: Optional[int]
    avg_temporal_proximity_sec: Optional[int]
    clustering_score: Optional[float]
    interpretation: str
    note: str

    def to_dict(self) -> Dict[str, object]:
        if self.status == 'no_data':
            return {
                'status': 'no_data',
                'truth_status': 'no_data',
                'generated_values': False,
                'eligible_for_action': False,
                'eligible_for_accounting': False,
                'eligible_for_learning': False,
                'note': self.note,
            }
        return {
            'status': self.status,
            'geo_count': self.geo_count,
            'plasma_count': self.plasma_count,
            'avg_temporal_proximity_sec': self.avg_temporal_proximity_sec,
            'clustering_score': round(self.clustering_score, 2),
            'interpretation': self.interpretation,
            'note': self.note,
        }


class HarmonicNexusBridge:
    def __init__(self, expected_window_seconds: int = DEFAULT_EXPECTED_WINDOW_SECONDS):
        self.expected_window_seconds = expected_window_seconds
        self.anomalies: list[DomainAnomaly] = []

    @staticmethod
    def _finite(value: Any) -> Optional[float]:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if math.isfinite(number) else None

    def _valid_anomaly(self, anomaly: Any) -> bool:
        if not isinstance(anomaly, DomainAnomaly):
            return False
        if (
            anomaly.truth_status not in {'real_observed', 'real_derived'}
            or anomaly.generated_values is not False
            or not isinstance(anomaly.source_id, str) or not anomaly.source_id.strip()
            or not isinstance(anomaly.receipt_id, str) or not anomaly.receipt_id.strip()
            or not isinstance(anomaly.observed_at, datetime)
        ):
            return False
        source_timestamp = self._finite(anomaly.source_timestamp)
        received_at = self._finite(anomaly.received_at)
        now = time.time()
        if (
            source_timestamp is None or received_at is None
            or source_timestamp <= 0 or received_at <= 0
            or source_timestamp > now + FUTURE_SKEW_SECONDS
            or received_at > now + FUTURE_SKEW_SECONDS
            or received_at < source_timestamp - FUTURE_SKEW_SECONDS
            or now - source_timestamp > MAX_RECEIPT_AGE_SECONDS
            or anomaly.observed_at.tzinfo is None
            or abs(anomaly.observed_at.timestamp() - source_timestamp) > FUTURE_SKEW_SECONDS
            or any(self._finite(value) is None for value in (
                anomaly.lagrangian_score, anomaly.coherence, anomaly.energy_value,
            ))
        ):
            return False
        return bool(str(anomaly.anomaly_id).strip() and str(anomaly.domain).strip())

    def register(self, anomaly: DomainAnomaly) -> bool:
        """Record a complete fresh observation only; invalid input is inert."""
        if not self._valid_anomaly(anomaly):
            return False
        self.anomalies.append(anomaly)
        return True

    def analyze(self) -> CrossDomainAnalysis:
        geo_events = [event for event in self.anomalies if event.domain == 'geopolitical']
        plasma_events = [event for event in self.anomalies if event.domain == 'plasma']
        if not geo_events or not plasma_events:
            return CrossDomainAnalysis(
                status='no_data',
                geo_count=None,
                plasma_count=None,
                avg_temporal_proximity_sec=None,
                clustering_score=None,
                interpretation='INCONCLUSIVE',
                note='complete fresh geopolitical and plasma receipts are required.',
            )

        proximities = []
        for geo_event in geo_events:
            for plasma_event in plasma_events:
                delta = abs((plasma_event.observed_at - geo_event.observed_at).total_seconds())
                proximities.append(int(delta))

        avg_proximity = int(sum(proximities) / len(proximities))
        effective_proximity = max(avg_proximity, 1)
        clustering_score = self.expected_window_seconds / effective_proximity

        if clustering_score >= 2.0:
            interpretation = 'CORRELATED'
            note = 'Clustering >2x expected suggests non-random temporal alignment'
        elif clustering_score >= 1.0:
            interpretation = 'WEAKLY_CORRELATED'
            note = 'Temporal proximity exceeds the naive baseline but is not decisive'
        else:
            interpretation = 'UNRELATED'
            note = 'Observed spacing does not exceed the naive baseline'

        return CrossDomainAnalysis(
            status='Analyzed',
            geo_count=len(geo_events),
            plasma_count=len(plasma_events),
            avg_temporal_proximity_sec=avg_proximity,
            clustering_score=clustering_score,
            interpretation=interpretation,
            note=note,
        )

    # ────────────────────────────────────────────────────────────
    # Planetary network injection
    # ────────────────────────────────────────────────────────────

    def inject_into_planetary_network(
        self,
        network_path: Optional[Path | str] = None,
    ) -> Path:
        """Merge forensic harmonic nodes into planetary_harmonic_network.json.

        For every registered geopolitical anomaly that originates from
        `aureon.geopolitical_forensics`, a harmonic-signature entry is
        appended to the network file (deduplicating by entity_name).

        Returns the path that was written.
        """
        network_path = Path(network_path or DEFAULT_PLANETARY_NETWORK_PATH)

        validated = [a for a in self.anomalies if self._valid_anomaly(a) and a.domain == 'geopolitical']
        if not validated:
            return network_path

        # Load existing network (or start fresh skeleton) without inventing source time.
        if network_path.exists():
            with open(network_path, encoding='utf-8') as fh:
                network = json.load(fh)
        else:
            network = {
                'metadata': {
                    'sweep_timestamp': None,
                    'sweep_date': None,
                    'total_entities': 0,
                    'total_signatures': 0,
                    'total_coordination_links': 0,
                    'total_counter_measures': 0,
                },
                'harmonic_signatures': [],
                'coordination_network': [],
                'counter_measures': [],
                'threat_analysis': {'critical_links': [], 'high_links': []},
            }

        existing_names = {
            sig.get('entity_name') for sig in network.get('harmonic_signatures', [])
        }

        injected = 0
        for anomaly in validated:
            entity_name = anomaly.anomaly_id  # e.g. MAGAMYMAN-001
            if entity_name in existing_names:
                continue

            sig = {
                'entity_name': entity_name,
                'entity_type': 'Geopolitical L(t)',
                'symbol': 'GEO/USD',
                'dominant_cycle_hours': round(
                    anomaly.lagrangian_score, 4
                ),
                'frequency_hz': round(
                    1.0 / max(anomaly.lagrangian_score, 0.01), 6
                ),
                'phase_angle_degrees': round(anomaly.coherence * 360, 2),
                'amplitude': anomaly.energy_value,
                'sacred_match': 'GEOPOLITICAL_LT',
                'sacred_alignment_pct': round(anomaly.coherence * 100, 2),
                'timestamp': anomaly.observed_at.timestamp(),
                'lt_score': anomaly.lagrangian_score,
                'severity': anomaly.metadata.get('severity', 'UNKNOWN'),
                'source_module': 'aureon.harmonic_nexus_bridge',
                'source_id': anomaly.source_id,
                'source_timestamp': anomaly.source_timestamp,
                'received_at': anomaly.received_at,
                'receipt_id': anomaly.receipt_id,
                'truth_status': anomaly.truth_status,
                'generated_values': False,
            }
            network['harmonic_signatures'].append(sig)
            existing_names.add(entity_name)
            injected += 1

        # Update metadata counts
        network['metadata']['total_signatures'] = len(network['harmonic_signatures'])
        entity_names = {s.get('entity_name') for s in network['harmonic_signatures']}
        network['metadata']['total_entities'] = len(entity_names)
        network['metadata']['last_injection_source_timestamp'] = max(
            anomaly.source_timestamp for anomaly in validated
        )

        # Atomic write
        network_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = network_path.with_suffix(network_path.suffix + '.tmp')
        with open(tmp_path, 'w', encoding='utf-8') as fh:
            json.dump(network, fh, indent=2)
        tmp_path.replace(network_path)

        logger.info(
            'Injected %d geopolitical nodes into %s (total signatures: %d)',
            injected,
            network_path,
            network['metadata']['total_signatures'],
        )
        return network_path


    # ────────────────────────────────────────────────────────────
    # Emerald Tablet cross-reference
    # ────────────────────────────────────────────────────────────

    def emerald_cross_reference(self) -> Dict[str, object]:
        """Cross-reference registered anomalies with Emerald Tablet verses.

        Returns a dict mapping each anomaly_id to the tablet verses whose
        parameters share a structural relationship with the anomaly's scores.
        """
        try:
            from aureon.decoders.emerald_spec import EmeraldSeer, _VERSE_CATALOG
        except ImportError:
            try:
                spec = importlib.util.spec_from_file_location(
                    'aureon.decoders.emerald_spec',
                    Path(__file__).parent / 'decoders' / 'emerald_spec.py',
                )
                if spec is None or spec.loader is None:
                    return {'error': 'emerald_spec not found'}
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                EmeraldSeer = mod.EmeraldSeer
                _VERSE_CATALOG = mod._VERSE_CATALOG
            except Exception:
                return {'error': 'emerald_spec not loadable'}

        seer = EmeraldSeer()
        result: Dict[str, object] = {}
        for anomaly in self.anomalies:
            grade = seer.classify_score(anomaly.lagrangian_score)
            stone = seer.verify_philosophers_stone(anomaly.lagrangian_score)
            matching_verses = []
            for verse in _VERSE_CATALOG:
                # link verses whose parameters mention a relevant score/domain
                params = verse.parameters
                if 'lt_score' in params and stone:
                    matching_verses.append(verse.key)
                elif 'severity' in params and anomaly.metadata.get('severity') == params.get('severity'):
                    matching_verses.append(verse.key)
                elif 'domains' in params and anomaly.domain in params['domains']:
                    matching_verses.append(verse.key)
                elif 'clustering_score' in params and anomaly.domain == 'geopolitical':
                    matching_verses.append(verse.key)
            result[anomaly.anomaly_id] = {
                'domain': anomaly.domain,
                'lt_score': anomaly.lagrangian_score,
                'hermetic_grade': grade,
                'stone_verified': stone,
                'matching_verses': matching_verses,
            }
        return result


def _format_console_output(bridge: HarmonicNexusBridge, report: CrossDomainAnalysis) -> str:
    lines = [
        '=' * 70,
        'HARMONIC NEXUS BRIDGE - Cross-Domain Anomaly Fusion',
        'Research Mode: Geopolitical L(t) <-> Plasma Coherence',
        '=' * 70,
        '',
        f'Registered validated anomalies: {len(bridge.anomalies)}',
        '',
        '=' * 70,
        'CROSS-DOMAIN ANALYSIS',
        '=' * 70,
        f'Temporal proximity: {report.avg_temporal_proximity_sec} seconds' if report.avg_temporal_proximity_sec is not None else 'Temporal proximity: no_data',
        f'Clustering score: {report.clustering_score:.2f}x expected' if report.clustering_score is not None else 'Clustering score: no_data',
        f'Assessment: {report.interpretation}',
        '',
        'NEXUS REPORT SUMMARY',
        '=' * 70,
        f'Total anomalies tracked: {report.geo_count + report.plasma_count}',
        json.dumps(report.to_dict(), indent=2),
    ]
    return '\n'.join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Analyze receipt-bearing harmonic anomalies.')
    parser.add_argument(
        '--input-json', required=True,
        help='JSON array of complete provider anomaly receipts.',
    )
    parser.add_argument(
        '--expected-window-seconds',
        type=int,
        default=DEFAULT_EXPECTED_WINDOW_SECONDS,
        help='Expected baseline temporal window for clustering comparison.',
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Emit only the JSON analysis summary.',
    )
    parser.add_argument(
        '--inject-planetary',
        metavar='PATH',
        nargs='?',
        const=str(DEFAULT_PLANETARY_NETWORK_PATH),
        default=None,
        help='Inject geopolitical harmonic nodes into a planetary network JSON file.',
    )
    args = parser.parse_args(argv)

    bridge = HarmonicNexusBridge(expected_window_seconds=args.expected_window_seconds)
    try:
        records = json.loads(Path(args.input_json).read_text(encoding='utf-8'))
    except Exception as exc:
        parser.error(f'input receipt file unavailable: {exc}')
    for record in records if isinstance(records, list) else []:
        if not isinstance(record, dict):
            continue
        observed_at = record.get('observed_at')
        try:
            observed = datetime.fromisoformat(str(observed_at).replace('Z', '+00:00'))
        except (TypeError, ValueError):
            continue
        bridge.register(DomainAnomaly(
            anomaly_id=str(record.get('anomaly_id') or ''), domain=str(record.get('domain') or ''),
            observed_at=observed, lagrangian_score=record.get('lagrangian_score'),
            coherence=record.get('coherence'), energy_value=record.get('energy_value'),
            energy_unit=str(record.get('energy_unit') or ''), summary=str(record.get('summary') or ''),
            source=str(record.get('source') or ''), metadata=dict(record.get('metadata') or {}),
            source_id=record.get('source_id'), source_timestamp=record.get('source_timestamp'),
            received_at=record.get('received_at'), receipt_id=record.get('receipt_id'),
            truth_status=str(record.get('truth_status') or 'no_data'),
            generated_values=record.get('generated_values'),
        ))
    report = bridge.analyze()

    if args.inject_planetary:
        net_path = bridge.inject_into_planetary_network(args.inject_planetary)
        if not args.json:
            print(f'Planetary network updated: {net_path}')

    if args.json:
        payload = report.to_dict()
        if args.inject_planetary:
            payload['planetary_network_path'] = str(args.inject_planetary)
        print(json.dumps(payload, indent=2))
    else:
        print(_format_console_output(bridge, report))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
