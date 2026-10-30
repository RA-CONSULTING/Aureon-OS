import { metricRingCaption } from '@/lib/reading';

interface MetricRingLegendProps {
  totalEquity: unknown;
  coherence: unknown;
  totalTrades: unknown;
  winRate: unknown;
  totalPnl: unknown;
}

/** Screen label for orbital rings whose source reading was not reported. */
export function MetricRingLegend({
  totalEquity,
  coherence,
  totalTrades,
  winRate,
  totalPnl,
}: MetricRingLegendProps) {
  const caption = metricRingCaption([
    { name: 'equity', value: totalEquity },
    { name: 'coherence', value: coherence },
    { name: 'trades', value: totalTrades },
    { name: 'win rate', value: winRate },
    { name: 'pnl', value: totalPnl },
  ]);
  if (!caption) return null;
  return (
    <div className="absolute bottom-16 left-1/2 z-10 -translate-x-1/2 pointer-events-none text-[10px] uppercase tracking-wider text-white/50">
      {caption}
    </div>
  );
}
