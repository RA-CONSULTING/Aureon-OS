import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { QuantumState } from '@/hooks/useQuantumWarRoom';

interface Props {
  quantumState: QuantumState;
}

const NODE_NAMES = [
  'Tiger', 'Falcon', 'Hummingbird', 'Dolphin', 'Deer',
  'Owl', 'Panda', 'CargoShip', 'Clownfish'
];

const NODE_EMOJIS = ['', '', '', '', '', '', '', '', ''];

export function AurisNodesOrbit({ quantumState }: Props) {
  const maxWeight = Math.max(...quantumState.waveFunction);

  return (
    <Card className="bg-card/50 backdrop-blur border-primary/20">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span> 9 Auris Nodes (Real-time)</span>
          {quantumState.dominantNode && (
            <span className="text-sm text-warning">
              Dominant: {quantumState.dominantNode}
            </span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="relative h-64 flex items-center justify-center">
          {/* Center point */}
          <div className="absolute w-3 h-3 bg-primary rounded-full animate-pulse" />
          
          {/* Nodes in orbit */}
          {NODE_NAMES.map((name, idx) => {
            const angle = (idx / NODE_NAMES.length) * 2 * Math.PI - Math.PI / 2;
            const radius = 100;
            const x = Math.cos(angle) * radius;
            const y = Math.sin(angle) * radius;
            const weight = quantumState.waveFunction[idx] || 0;
            const isDominant = name.toLowerCase() === quantumState.dominantNode?.toLowerCase();
            const scale = 0.8 + (weight / maxWeight) * 0.7;

            return (
              <div
                key={name}
                className={`absolute transition-all duration-300 ${
                  isDominant ? 'z-10' : ''
                }`}
                style={{
                  left: `calc(50% + ${x}px)`,
                  top: `calc(50% + ${y}px)`,
                  transform: `translate(-50%, -50%) scale(${scale})`,
                }}
              >
                <div className="relative group">
                  {/* Node */}
                  <div
                    className={`w-12 h-12 rounded-full flex items-center justify-center text-2xl transition-all
                      ${isDominant 
                        ? 'bg-warning/30 border-2 border-warning animate-pulse shadow-lg shadow-warning/50' 
                        : 'bg-primary/20 border border-primary/50'
                      }`}
                  >
                    {NODE_EMOJIS[idx]}
                  </div>
                  
                  {/* Tooltip */}
                  <div className="absolute -bottom-8 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap bg-card border border-border rounded px-2 py-1 text-xs">
                    <div className="font-bold">{name}</div>
                    <div className="text-muted-foreground">{(weight * 100).toFixed(1)}%</div>
                  </div>

                  {/* Connection line to center */}
                  <svg className="absolute inset-0 pointer-events-none" style={{ overflow: 'visible' }}>
                    <line
                      x1="50%"
                      y1="50%"
                      x2={-x}
                      y2={-y}
                      stroke={isDominant ? 'rgb(234, 179, 8)' : 'hsl(var(--primary))'}
                      strokeWidth={isDominant ? '2' : '1'}
                      opacity={weight}
                      className="transition-all duration-300"
                    />
                  </svg>
                </div>
              </div>
            );
          })}
        </div>

        {/* Legend */}
        <div className="mt-4 flex flex-wrap gap-2 justify-center">
          {NODE_NAMES.map((name, idx) => {
            const weight = quantumState.waveFunction[idx] || 0;
            const isDominant = name.toLowerCase() === quantumState.dominantNode?.toLowerCase();
            
            return (
              <div
                key={name}
                className={`text-xs px-2 py-1 rounded border ${
                  isDominant
                    ? 'bg-warning/20 border-warning text-warning'
                    : 'bg-primary/10 border-primary/30'
                }`}
              >
                {NODE_EMOJIS[idx]} {name}: {(weight * 100).toFixed(0)}%
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
