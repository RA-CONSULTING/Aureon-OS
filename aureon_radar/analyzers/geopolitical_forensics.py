#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Public-record geopolitical forensics scoring for Aureon research flows.

This module is intentionally limited to neutral, public-record analysis.
It does not identify real-world individuals behind pseudonymous accounts,
infer non-public facts, or make legal conclusions.
"""


from aureon.utils.console_utf8 import ensure_utf8_stdout

ensure_utf8_stdout()

import argparse
import json
import logging
import shutil
import subprocess
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, Mapping, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

PUBLIC_RECORD_CUTOFF = '2026-03-06'
EXTREME_THRESHOLD = 10.0
HIGH_THRESHOLD = 7.5
MODERATE_THRESHOLD = 5.0

COURT_NEUTRAL_DISCLAIMER = (
    'This report summarizes public-record, pseudonymous activity only. '
    'It does not identify real-world persons, assert culpability, or '
    'substitute for legal process, subpoena power, or KYC records.'
)


@dataclass(frozen=True)
class LikelihoodComponent:
    key: str
    label: str
    raw_score: float
    narrative: str
    evidence_sources: Tuple[str, ...] = field(default_factory=tuple)

    @property
    def display_score(self) -> float:
        return round(self.raw_score, 2)


@dataclass(frozen=True)
class GeopoliticalClusterCase:
    cluster_key: str
    cluster_id: str
    display_name: str
    public_labels: Tuple[str, ...]
    market_question: str
    event_date: str
    public_record_notes: Tuple[str, ...]
    evidence_sources: Tuple[str, ...]
    components: Tuple[LikelihoodComponent, ...]
    coherence: float
    energy_rate_per_minute_usd: float
    identity_status: str = (
        'No verified real-world identities, photographs, or KYC-linked '
        'disclosures are asserted in public record.'
    )

    @property
    def lt_score(self) -> float:
        return round(sum(component.raw_score for component in self.components), 2)

    @property
    def severity(self) -> str:
        return classify_lt_score(self.lt_score)


@dataclass(frozen=True)
class HarmonicNodeReference:
    node_id: str
    label: str
    node_type: str
    lt_score: float
    severity: str
    coherence: float
    source_module: str = 'aureon.geopolitical_forensics'


@dataclass(frozen=True)
class ForensicFinding:
    case: GeopoliticalClusterCase
    generated_at: str
    public_record_cutoff: str = PUBLIC_RECORD_CUTOFF
    methodology: str = 'L(t) = sum(public-record likelihood components)'
    disclaimer: str = COURT_NEUTRAL_DISCLAIMER

    @property
    def lt_score(self) -> float:
        return self.case.lt_score

    @property
    def evidence_filename(self) -> str:
        return f'evidence_{self.case.cluster_id}_L{self.lt_score:.2f}.json'

    def to_harmonic_node(self) -> HarmonicNodeReference:
        return HarmonicNodeReference(
            node_id=self.case.cluster_id,
            label=self.case.display_name,
            node_type='geopolitical_lt',
            lt_score=self.lt_score,
            severity=self.case.severity,
            coherence=self.case.coherence,
        )

    def to_dict(self) -> Dict[str, object]:
        return {
            'cluster_key': self.case.cluster_key,
            'cluster_id': self.case.cluster_id,
            'display_name': self.case.display_name,
            'public_labels': list(self.case.public_labels),
            'market_question': self.case.market_question,
            'event_date': self.case.event_date,
            'generated_at': self.generated_at,
            'public_record_cutoff': self.public_record_cutoff,
            'lt_score': self.lt_score,
            'severity': self.case.severity,
            'coherence': self.case.coherence,
            'energy_rate_per_minute_usd': self.case.energy_rate_per_minute_usd,
            'methodology': self.methodology,
            'disclaimer': self.disclaimer,
            'identity_status': self.case.identity_status,
            'public_record_notes': list(self.case.public_record_notes),
            'evidence_sources': list(self.case.evidence_sources),
            'components': [
                {
                    'key': component.key,
                    'label': component.label,
                    'raw_score': component.raw_score,
                    'display_score': component.display_score,
                    'narrative': component.narrative,
                    'evidence_sources': list(component.evidence_sources),
                }
                for component in self.case.components
            ],
            'planetary_harmonic_node': {
                'node_id': self.case.cluster_id,
                'label': self.case.display_name,
                'node_type': 'geopolitical_lt',
                'lt_score': self.lt_score,
                'severity': self.case.severity,
                'coherence': self.case.coherence,
                'source_module': 'aureon.geopolitical_forensics',
            },
        }


@dataclass(frozen=True)
class OutputArtifacts:
    evidence_files: Tuple[Path, ...]
    report_file: Path


def classify_lt_score(score: float) -> str:
    if score >= EXTREME_THRESHOLD:
        return 'EXTREME'
    if score >= HIGH_THRESHOLD:
        return 'HIGH'
    if score >= MODERATE_THRESHOLD:
        return 'MODERATE'
    return 'LOW'


def _build_case_catalog() -> Dict[str, GeopoliticalClusterCase]:
    common_sources = (
        'Bubblemaps',
        'NPR',
        'Forbes',
        'The Block',
        'Congressional record',
    )
    return {
        'magamyman': GeopoliticalClusterCase(
            cluster_key='magamyman',
            cluster_id='MAGAMYMAN-001',
            display_name='Magamyman',
            public_labels=('Magamyman',),
            market_question='US strikes Iran by February 28, 2026? / Khamenei out of power?',
            event_date='2026-02-28',
            public_record_notes=(
                'Public reporting places initial activity roughly 71 minutes before the strike window.',
                'Observed gains remained tied to a pseudonymous public label as of the cutoff date.',
            ),
            evidence_sources=common_sources,
            components=(
                LikelihoodComponent(
                    key='temporal',
                    label='Temporal precision',
                    raw_score=6.407,
                    narrative='Entry timing was unusually close to the subsequent public event window.',
                    evidence_sources=common_sources,
                ),
                LikelihoodComponent(
                    key='skill',
                    label='Positioning skill anomaly',
                    raw_score=4.851,
                    narrative='Sizing and concentration exceeded an ordinary retail timing pattern.',
                    evidence_sources=common_sources,
                ),
                LikelihoodComponent(
                    key='prior',
                    label='Prior activity context',
                    raw_score=1.592,
                    narrative='Prior observed market activity raises the baseline anomaly score.',
                    evidence_sources=common_sources,
                ),
            ),
            coherence=0.70,
            energy_rate_per_minute_usd=7800.0,
        ),
        'bubblemaps6': GeopoliticalClusterCase(
            cluster_key='bubblemaps6',
            cluster_id='BUBBLEMAPS-6',
            display_name='Bubblemaps-6 cluster',
            public_labels=(
                'Planktonbets',
                'Dicedicedice',
                'Roeyha2026',
                'nothingeverhappens911',
                'Lettucehead718',
                'suffix-295',
            ),
            market_question='US strikes Iran by February 28, 2026?',
            event_date='2026-02-28',
            public_record_notes=(
                'Cluster characterization is based on public wallet-linkage reporting only.',
                'Uniform stake pattern and fresh-funding timing are treated as public-record anomaly inputs, not identity proof.',
            ),
            evidence_sources=common_sources,
            components=(
                LikelihoodComponent(
                    key='temporal',
                    label='Temporal precision',
                    raw_score=3.728,
                    narrative='Wallet funding and market entry clustered unusually close to the event window.',
                    evidence_sources=common_sources,
                ),
                LikelihoodComponent(
                    key='gini',
                    label='Stake concentration / Gini anomaly',
                    raw_score=6.906,
                    narrative='Stake distribution patterns indicate concentrated coordination beyond a diffuse retail baseline.',
                    evidence_sources=common_sources,
                ),
                LikelihoodComponent(
                    key='coordination',
                    label='Coordination anomaly',
                    raw_score=2.396,
                    narrative='Cross-wallet timing and pattern similarity exceeded a naive independent-actor model.',
                    evidence_sources=common_sources,
                ),
            ),
            coherence=0.74,
            energy_rate_per_minute_usd=12000.0,
        ),
    }


CASE_CATALOG = _build_case_catalog()
CASE_ALIASES = {
    'magamyman': 'magamyman',
    'mag': 'magamyman',
    'bubblemaps6': 'bubblemaps6',
    'bubblemaps-6': 'bubblemaps6',
    'bubble': 'bubblemaps6',
}


def _latex_escape(value: str) -> str:
    replacements = {
        '\\': r'\textbackslash{}',
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\textasciicircum{}',
    }
    escaped = value
    for old, new in replacements.items():
        escaped = escaped.replace(old, new)
    return escaped


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + '.tmp')
    tmp_path.write_text(content, encoding='utf-8')
    tmp_path.replace(path)


def _atomic_write_json(path: Path, payload: Mapping[str, object]) -> None:
    _atomic_write_text(path, json.dumps(payload, indent=2) + '\n')


class LatexNeutralReportBuilder:
    def build(self, findings: Sequence[ForensicFinding], report_stamp: str) -> str:
        lines = [
            r'\documentclass[11pt]{article}',
            r'\usepackage[margin=1in]{geometry}',
            r'\usepackage[T1]{fontenc}',
            r'\usepackage[utf8]{inputenc}',
            r'\usepackage{longtable}',
            r'\usepackage{array}',
            r'\begin{document}',
            r'\title{Public-Record Geopolitical Forensics Findings}',
            r'\date{' + _latex_escape(report_stamp) + r'}',
            r'\maketitle',
            r'\section*{Neutral Scope Notice}',
            _latex_escape(COURT_NEUTRAL_DISCLAIMER),
            '',
            r'\section*{Public-Record Cutoff}',
            _latex_escape(PUBLIC_RECORD_CUTOFF),
            '',
        ]

        for finding in findings:
            case = finding.case
            lines.extend([
                r'\section*{' + _latex_escape(case.display_name) + r'}',
                r'\textbf{Cluster ID:} ' + _latex_escape(case.cluster_id) + r'\\',
                r'\textbf{L(t):} ' + f'{finding.lt_score:.2f}' + r'\\',
                r'\textbf{Severity:} ' + _latex_escape(case.severity) + r'\\',
                r'\textbf{Public labels:} ' + _latex_escape(', '.join(case.public_labels)) + r'\\',
                r'\textbf{Identity status:} ' + _latex_escape(case.identity_status),
                '',
                r'\subsection*{Component Breakdown}',
                r'\begin{longtable}{p{0.18\linewidth}p{0.12\linewidth}p{0.58\linewidth}}',
                r'\textbf{Component} & \textbf{Score} & \textbf{Narrative}\\',
                r'\hline',
            ])
            for component in case.components:
                lines.append(
                    _latex_escape(component.label)
                    + ' & '
                    + f'{component.display_score:.2f}'
                    + ' & '
                    + _latex_escape(component.narrative)
                    + r'\\'
                )
            lines.extend([
                r'\end{longtable}',
                r'\subsection*{Public-Record Notes}',
            ])
            for note in case.public_record_notes:
                lines.append(r'\noindent ' + _latex_escape(note) + r'\\')
            lines.extend([
                '',
                r'\subsection*{Evidence Sources}',
                _latex_escape(', '.join(case.evidence_sources)),
                '',
            ])

        lines.append(r'\end{document}')
        return '\n'.join(lines) + '\n'


class GeopoliticalForensicsEngine:
    def __init__(self, output_root: Path | str | None = None):
        self.output_root = Path(output_root or Path(__file__).resolve().parents[1])
        self.report_builder = LatexNeutralReportBuilder()

    def resolve_selector(self, selector: str) -> Tuple[GeopoliticalClusterCase, ...]:
        normalized = selector.strip().lower()
        if normalized == 'both':
            return (CASE_CATALOG['magamyman'], CASE_CATALOG['bubblemaps6'])
        case_key = CASE_ALIASES.get(normalized)
        if not case_key:
            available = ', '.join(['magamyman', 'bubblemaps-6', 'both'])
            raise ValueError(f'Unknown cluster selector: {selector}. Available: {available}')
        return (CASE_CATALOG[case_key],)

    def analyze(self, selector: str = 'both') -> Tuple[ForensicFinding, ...]:
        generated_at = datetime.now(timezone.utc).isoformat()
        return tuple(
            ForensicFinding(case=case, generated_at=generated_at)
            for case in self.resolve_selector(selector)
        )

    def write_outputs(
        self,
        findings: Sequence[ForensicFinding],
        report_stamp: str | None = None,
    ) -> OutputArtifacts:
        stamp = report_stamp or datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        evidence_dir = self.output_root / 'evidence'
        report_dir = self.output_root / 'reports'
        evidence_paths = []

        for finding in findings:
            evidence_path = evidence_dir / finding.evidence_filename
            _atomic_write_json(evidence_path, finding.to_dict())
            evidence_paths.append(evidence_path)

        report_path = report_dir / f'findings_report_{stamp}.tex'
        report_content = self.report_builder.build(findings, stamp)
        _atomic_write_text(report_path, report_content)
        return OutputArtifacts(evidence_files=tuple(evidence_paths), report_file=report_path)

    def build_summary(self, findings: Sequence[ForensicFinding], artifacts: OutputArtifacts) -> Dict[str, object]:
        return {
            'status': 'ok',
            'public_record_cutoff': PUBLIC_RECORD_CUTOFF,
            'clusters': [finding.to_dict() for finding in findings],
            'evidence_files': [str(path) for path in artifacts.evidence_files],
            'report_file': str(artifacts.report_file),
        }


# ════════════════════════════════════════════════════════════════════════════
# ON-CHAIN STAKE CONCENTRATION (public, no identity attribution)
# ════════════════════════════════════════════════════════════════════════════

_POLYGON_TOP_HOLDERS_URL = (
    'https://api.polygonscan.com/api'
    '?module=token&action=tokenholderlist'
    '&contractaddress={contract}&page=1&offset={limit}'
)
_ETHERSCAN_TOP_HOLDERS_URL = (
    'https://api.etherscan.io/api'
    '?module=token&action=tokenholderlist'
    '&contractaddress={contract}&page=1&offset={limit}'
)


@dataclass(frozen=True)
class StakeConcentrationResult:
    """Public on-chain Gini-like concentration metric."""
    contract_address: str
    chain: str
    top_n: int
    total_supply_sampled: float
    top_n_share: float
    gini_coefficient: float
    herfindahl_index: float
    source: str
    fetched_at: str

    def to_dict(self) -> Dict[str, object]:
        return {
            'contract_address': self.contract_address,
            'chain': self.chain,
            'top_n': self.top_n,
            'total_supply_sampled': round(self.total_supply_sampled, 4),
            'top_n_share': round(self.top_n_share, 6),
            'gini_coefficient': round(self.gini_coefficient, 6),
            'herfindahl_index': round(self.herfindahl_index, 6),
            'source': self.source,
            'fetched_at': self.fetched_at,
        }


def _compute_gini(balances: Sequence[float]) -> float:
    """Gini coefficient from a list of non-negative balances."""
    if not balances or all(b == 0 for b in balances):
        return 0.0
    sorted_b = sorted(balances)
    n = len(sorted_b)
    cumulative = 0.0
    weighted_sum = 0.0
    for i, balance in enumerate(sorted_b, start=1):
        cumulative += balance
        weighted_sum += i * balance
    total = cumulative
    if total == 0:
        return 0.0
    return (2.0 * weighted_sum) / (n * total) - (n + 1) / n


def _compute_herfindahl(shares: Sequence[float]) -> float:
    """Herfindahl-Hirschman Index from market-share fractions."""
    return sum(s * s for s in shares)


def fetch_stake_concentration(
    contract_address: str,
    chain: str = 'polygon',
    top_n: int = 50,
    api_key: Optional[str] = None,
    timeout_seconds: int = 15,
) -> StakeConcentrationResult:
    """Fetch on-chain token holder distribution and compute concentration.

    Uses public Polygonscan / Etherscan tokenholderlist endpoint.
    No wallet-to-identity linkage is performed.
    """
    if chain == 'polygon':
        base_url = _POLYGON_TOP_HOLDERS_URL
        source = 'polygonscan'
    elif chain in ('ethereum', 'eth'):
        base_url = _ETHERSCAN_TOP_HOLDERS_URL
        source = 'etherscan'
    else:
        raise ValueError(f'Unsupported chain: {chain}')

    url = base_url.format(contract=contract_address, limit=top_n)
    if api_key:
        url += f'&apikey={api_key}'

    req = urllib.request.Request(url, headers={'User-Agent': 'Aureon/1.0'})
    with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
        data = json.loads(resp.read().decode())

    holders = data.get('result', [])
    if not holders or isinstance(holders, str):
        # API may return error string on rate-limit
        raise RuntimeError(f'{source} returned no holder data (rate-limited or invalid contract)')

    balances = []
    for holder in holders:
        raw = holder.get('TokenHolderQuantity', '0')
        balances.append(float(raw))

    total = sum(balances) or 1.0
    shares = [b / total for b in balances]
    top_share = sum(sorted(shares, reverse=True)[:top_n])

    return StakeConcentrationResult(
        contract_address=contract_address,
        chain=chain,
        top_n=min(top_n, len(balances)),
        total_supply_sampled=total,
        top_n_share=top_share,
        gini_coefficient=_compute_gini(balances),
        herfindahl_index=_compute_herfindahl(shares),
        source=source,
        fetched_at=datetime.now(timezone.utc).isoformat(),
    )


# ════════════════════════════════════════════════════════════════════════════
# PDF BUILD HOOK
# ════════════════════════════════════════════════════════════════════════════

def build_pdf(tex_path: Path | str, output_dir: Optional[Path | str] = None) -> Path:
    """Compile a .tex file to PDF using pdflatex.

    Returns the path to the generated .pdf.
    Raises RuntimeError if pdflatex is not installed or compilation fails.
    """
    tex_path = Path(tex_path)
    if not tex_path.exists():
        raise FileNotFoundError(f'TeX source not found: {tex_path}')

    pdflatex = shutil.which('pdflatex')
    if pdflatex is None:
        raise RuntimeError(
            'pdflatex is not installed. '
            'Install texlive-latex-base (apt install texlive-latex-base) '
            'or use an alternative TeX distribution.'
        )

    out_dir = Path(output_dir) if output_dir else tex_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        pdflatex,
        '-interaction=nonstopmode',
        '-halt-on-error',
        f'-output-directory={out_dir}',
        str(tex_path),
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(tex_path.parent),
    )
    if result.returncode != 0:
        logger.error('pdflatex stderr: %s', result.stderr[-2000:] if result.stderr else '(none)')
        raise RuntimeError(
            f'pdflatex exited with code {result.returncode}. '
            f'Check log: {out_dir / tex_path.with_suffix(".log").name}'
        )

    pdf_path = out_dir / tex_path.with_suffix('.pdf').name
    if not pdf_path.exists():
        raise RuntimeError(f'Expected PDF not found at {pdf_path}')
    return pdf_path


def _iter_paths(paths: Iterable[Path]) -> str:
    return '\n'.join(str(path) for path in paths)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description='Generate public-record geopolitical forensics artifacts.'
    )
    parser.add_argument(
        '--cluster',
        default='both',
        choices=['magamyman', 'bubblemaps6', 'bubblemaps-6', 'both'],
        help='Cluster selector to analyze.',
    )
    parser.add_argument(
        '--output-root',
        default=str(Path(__file__).resolve().parents[1]),
        help='Repository root used for evidence/ and reports/ output.',
    )
    parser.add_argument(
        '--report-stamp',
        default=None,
        help='Optional deterministic report timestamp override.',
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Print the output summary as JSON.',
    )
    parser.add_argument(
        '--pdf',
        action='store_true',
        help='Compile the generated .tex report to PDF via pdflatex.',
    )
    args = parser.parse_args(argv)

    engine = GeopoliticalForensicsEngine(output_root=args.output_root)
    findings = engine.analyze(args.cluster)
    artifacts = engine.write_outputs(findings, report_stamp=args.report_stamp)
    summary = engine.build_summary(findings, artifacts)

    if args.pdf:
        try:
            pdf_path = build_pdf(artifacts.report_file)
            summary['pdf_file'] = str(pdf_path)
        except (RuntimeError, FileNotFoundError) as exc:
            summary['pdf_error'] = str(exc)

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print('Generated evidence files:')
        print(_iter_paths(artifacts.evidence_files))
        print(f'Report file: {artifacts.report_file}')
        if 'pdf_file' in summary:
            print(f'PDF file: {summary["pdf_file"]}')
        elif 'pdf_error' in summary:
            print(f'PDF build failed: {summary["pdf_error"]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())