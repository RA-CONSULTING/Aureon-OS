/**
 * HUDMetricsPanel - Bottom-right circular gauges and metric indicators
 * Coherence, Lambda, Lighthouse, Prism State, HNC, Gaia
 */

interface HUDMetricsPanelProps {
  coherence: number;         // 0-1
  lambda: number;            // secondary metric
  lighthouseSignal: number;  // signal strength
  prismState: string;        // FORMING, BLUE, GOLD, RED
  hncFrequency: number;      // Hz
  hncMarketState: string;    // CONSOLIDATION, TRENDING, VOLATILE, BREAKOUT
  gaiaLatticeState: string;  // COHERENT, DISTORTION, NEUTRAL
  gaiaFrequency: number;     // Hz
  dominantNode: string;      // Tiger, Falcon, etc.
}

// SVG circular gauge
function CircularGauge({ value, max = 1, label, color, size = 52 }: {
  value: number;
  max?: number;
  label: string;
  color: string;
  size?: number;
}) {
  const radius = (size - 8) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = Math.min(value / max, 1);
  const strokeDashoffset = circumference * (1 - progress);

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size} className="transform -rotate-90">
        {/* Background ring */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="rgba(255,255,255,0.06)"
          strokeWidth="2"
          fill="none"
        />
        {/* Progress ring */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={color}
          strokeWidth="2"
          fill="none"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          style={{
            transition: 'stroke-dashoffset 1s ease',
            filter: `drop-shadow(0 0 4px ${color})`,
          }}
        />
      </svg>
      <div className="text-center -mt-[calc(50%-2px)]" style={{ marginTop: `-${size / 2 + 6}px` }}>
        <div className="text-[11px] font-medium" style={{ color, lineHeight: `${size}px` }}>
          {typeof value === 'number' ? (value < 10 ? value.toFixed(2) : value.toFixed(0)) : value}
        </div>
      </div>
      <div className="text-[8px] text-white/30 uppercase tracking-wider mt-1">{label}</div>
    </div>
  );
}

function StateBadge({ label, state, colorMap }: {
  label: string;
  state: string;
  colorMap: Record<string, string>;
}) {
  const color = colorMap[state] || '#8844ff';

  return (
    <div className="flex items-center gap-1.5">
      <div
        className="w-1.5 h-1.5 rounded-full"
        style={{ backgroundColor: color, boxShadow: `0 0 4px ${color}` }}
      />
      <span className="text-[9px] text-white/35 uppercase tracking-wider">{label}</span>
      <span className="text-[9px] font-medium" style={{ color }}>{state}</span>
    </div>
  );
}

export function HUDMetricsPanel({
  coherence = 0.5,
  lambda = 0.5,
  lighthouseSignal = 0.3,
  prismState = 'FORMING',
  hncFrequency = 432,
  hncMarketState = 'CONSOLIDATION',
  gaiaLatticeState = 'NEUTRAL',
  gaiaFrequency = 432,
  dominantNode = 'Tiger',
}: HUDMetricsPanelProps) {
  const prismColors: Record<string, string> = {
    FORMING: '#8844ff',
    BLUE: '#4488ff',
    GOLD: '#ffaa00',
    RED: '#ff4444',
  };

  const marketColors: Record<string, string> = {
    CONSOLIDATION: '#4488ff',
    TRENDING: '#00ff88',
    VOLATILE: '#ff4444',
    BREAKOUT: '#ffaa00',
  };

  const gaiaColors: Record<string, string> = {
    COHERENT: '#00ff88',
    DISTORTION: '#ff4444',
    NEUTRAL: '#4488ff',
  };

  return (
    <div className="absolute bottom-4 right-4 z-10 pointer-events-none">
      <div className="px-4 py-3 rounded-xl backdrop-blur-xl bg-black/30 border border-white/[0.06] shadow-[0_8px_32px_rgba(0,0,0,0.3)]">
        {/* Circular gauges row */}
        <div className="flex items-center gap-5 mb-3">
          <CircularGauge
            value={coherence}
            label="Gamma"
            color={coherence > 0.7 ? '#00ff88' : coherence > 0.4 ? '#4488ff' : '#8844ff'}
          />
          <CircularGauge
            value={lambda}
            label="Lambda"
            color="#44ccff"
          />
          <CircularGauge
            value={lighthouseSignal}
            label="Lighthouse"
            color="#ffaa00"
          />
        </div>

        {/* Divider */}
        <div className="h-px bg-white/[0.06] mb-2.5" />

        {/* State badges */}
        <div className="space-y-1.5">
          <StateBadge label="Prism" state={prismState} colorMap={prismColors} />
          <StateBadge label="Market" state={hncMarketState} colorMap={marketColors} />
          <StateBadge label="Gaia" state={gaiaLatticeState} colorMap={gaiaColors} />
          <div className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-warning shadow-[0_0_4px_rgba(251,146,60,0.6)]" />
            <span className="text-[9px] text-white/35 uppercase tracking-wider">Node</span>
            <span className="text-[9px] font-medium text-warning">{dominantNode}</span>
          </div>
        </div>

        {/* Frequency readout */}
        <div className="mt-2.5 pt-2 border-t border-white/[0.04] flex items-center justify-between">
          <div className="text-[9px] text-white/25">
            HNC {hncFrequency.toFixed(0)}Hz
          </div>
          <div className="text-[9px] text-white/25">
            Gaia {gaiaFrequency.toFixed(0)}Hz
          </div>
        </div>
      </div>
    </div>
  );
}
