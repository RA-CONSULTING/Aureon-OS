#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cross-domain harmonic bridge for neutral research simulations.

The bridge aligns public-record geopolitical L(t) findings with synthetic
plasma-coherence events inside the same temporal clustering framework.
"""


from aureon.utils.console_utf8 import ensure_utf8_stdout

ensure_utf8_stdout()

import argparse
import importlib.util
import json
import logging
import sys as _sys
import time as _time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Optional, Sequence, Tuple


def _load_geopolitical_module():
    try:
        from aureon.analytics import geopolitical_forensics as module  # type: ignore
        return module
    except Exception:
        module_path = Path(__file__).with_name('geopolitical_forensics.py')
        module_name = 'aureon.geopolitical_forensics'
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            raise ImportError(f'Unable to load {module_name} from {module_path}')
        module = importlib.util.module_from_spec(spec)
        _sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module


_GEO = _load_geopolitical_module()
GeopoliticalForensicsEngine = _GEO.GeopoliticalForensicsEngine

logger = logging.getLogger(__name__)

DEFAULT_EXPECTED_WINDOW_SECONDS = 72 * 60
DEFAULT_PLANETARY_NETWORK_PATH = Path(__file__).resolve().parents[1] / 'planetary_harmonic_network.json'


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


@dataclass(frozen=True)
class CrossDomainAnalysis:
    status: str
    geo_count: int
    plasma_count: int
    avg_temporal_proximity_sec: int
    clustering_score: float
    interpretation: str
    note: str

    def to_dict(self) -> Dict[str, object]:
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

    def register(self, anomaly: DomainAnomaly) -> None:
        self.anomalies.append(anomaly)

    def analyze(self) -> CrossDomainAnalysis:
        geo_events = [event for event in self.anomalies if event.domain == 'geopolitical']
        plasma_events = [event for event in self.anomalies if event.domain == 'plasma']
        if not geo_events or not plasma_events:
            return CrossDomainAnalysis(
                status='InsufficientData',
                geo_count=len(geo_events),
                plasma_count=len(plasma_events),
                avg_temporal_proximity_sec=0,
                clustering_score=0.0,
                interpretation='INCONCLUSIVE',
                note='At least one geopolitical and one plasma anomaly are required.',
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

    def build_demo_anomalies(self) -> Tuple[DomainAnomaly, DomainAnomaly]:
        geo_finding = GeopoliticalForensicsEngine().analyze('magamyman')[0]
        base_time = datetime(2026, 2, 28, 1, 34, tzinfo=timezone.utc)
        geo_event = DomainAnomaly(
            anomaly_id=geo_finding.case.cluster_id,
            domain='geopolitical',
            observed_at=base_time,
            lagrangian_score=geo_finding.lt_score,
            coherence=geo_finding.case.coherence,
            energy_value=geo_finding.case.energy_rate_per_minute_usd,
            energy_unit='USD/min',
            summary='Public-record geopolitical timing anomaly',
            source='aureon.geopolitical_forensics',
            metadata={'severity': geo_finding.case.severity},
        )
        plasma_event = DomainAnomaly(
            anomaly_id='EPOS-SIM-001',
            domain='plasma',
            observed_at=base_time + timedelta(minutes=26),
            lagrangian_score=5.0,
            coherence=0.88,
            energy_value=1.0,
            energy_unit='W/m^3',
            summary='Synthetic plasma coherence event for research validation',
            source='simulation',
            metadata={'mode': 'test-only'},
        )
        return geo_event, plasma_event

    def run_demo(self) -> CrossDomainAnalysis:
        self.anomalies.clear()
        for anomaly in self.build_demo_anomalies():
            self.register(anomaly)
        return self.analyze()

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

        # Load existing network (or start fresh skeleton)
        if network_path.exists():
            with open(network_path, encoding='utf-8') as fh:
                network = json.load(fh)
        else:
            network = {
                'metadata': {
                    'sweep_timestamp': _time.time(),
                    'sweep_date': datetime.now(timezone.utc).isoformat(),
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
        for anomaly in self.anomalies:
            if anomaly.domain != 'geopolitical':
                continue
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
            }
            network['harmonic_signatures'].append(sig)
            existing_names.add(entity_name)
            injected += 1

        # Update metadata counts
        network['metadata']['total_signatures'] = len(network['harmonic_signatures'])
        entity_names = {s.get('entity_name') for s in network['harmonic_signatures']}
        network['metadata']['total_entities'] = len(entity_names)
        network['metadata']['last_injection'] = datetime.now(timezone.utc).isoformat()

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
    geo_event, plasma_event = bridge.build_demo_anomalies()
    lines = [
        '=' * 70,
        'HARMONIC NEXUS BRIDGE - Cross-Domain Anomaly Fusion',
        'Research Mode: Geopolitical L(t) <-> Plasma Coherence',
        '=' * 70,
        '',
        f'[GEO] Registered: L={geo_event.lagrangian_score:.2f}, Coherence={geo_event.coherence:.2f}, Energy=${geo_event.energy_value / 1000:.1f}k/min',
        f'[PLASMA] Registered: L={plasma_event.lagrangian_score:.2f}, Coherence={plasma_event.coherence:.2f}, Density={plasma_event.energy_value:.1f} {plasma_event.energy_unit}',
        '',
        '=' * 70,
        'CROSS-DOMAIN ANALYSIS',
        '=' * 70,
        f'Temporal proximity: {report.avg_temporal_proximity_sec} seconds ({report.avg_temporal_proximity_sec // 60} minutes)',
        f'Clustering score: {report.clustering_score:.2f}x expected',
        f'Assessment: {report.interpretation}',
        '',
        'NEXUS REPORT SUMMARY',
        '=' * 70,
        f'Total anomalies tracked: {report.geo_count + report.plasma_count}',
        json.dumps(report.to_dict(), indent=2),
    ]
    return '\n'.join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Run the harmonic nexus bridge demo.')
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
    report = bridge.run_demo()

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