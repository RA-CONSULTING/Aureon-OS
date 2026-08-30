import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { LineChart, Line, ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Cell } from 'recharts';
import { TrendingUp, TrendingDown, Minus, Sparkles, Clock, Zap } from 'lucide-react';
import type { CurvaturePoint } from '@/core/ftcpDetector';
import { useState, useEffect } from 'react';
import { format } from 'date-fns';
import fibonacciFtcpWindowing from '@/assets/research/fibonacci-ftcp-windowing.png';

interface FTCPTimelineProps {
  ftcpPoint: CurvaturePoint | null;
  currentPrice: number;
  currentSymbol: string;
}

interface FTCPHistoryPoint {
  timestamp: number;
  value: number;
  curvature: number;
  isFTCP: boolean;
  goldenRatioScore: number;
  price: number;
  priceChange: number;
  timeIntervalRatio?: number;
}

const PHI = (1 + Math.sqrt(5)) / 2; // Golden ratio ≈ 1.618

export const FTCPTimeline = ({ ftcpPoint, currentPrice, currentSymbol }: FTCPTimelineProps) => {
  const [history, setHistory] = useState<FTCPHistoryPoint[]>([]);
  const [lastPrice, setLastPrice] = useState(currentPrice);

  useEffect(() => {
    if (!ftcpPoint) return;

    const priceChange = currentPrice - lastPrice;
    
    const newPoint: FTCPHistoryPoint = {
      timestamp: ftcpPoint.timestamp,
      value: ftcpPoint.value,
      curvature: ftcpPoint.curvature,
      isFTCP: ftcpPoint.isFTCP,
      goldenRatioScore: ftcpPoint.goldenRatioScore,
      price: currentPrice,
      priceChange,
    };

    setHistory((prev) => {
      const updated = [...prev, newPoint];
      
      // Calculate time interval ratios for golden ratio detection
      if (updated.length >= 2) {
        for (let i = 1; i < updated.length; i++) {
          const currentInterval = updated[i].timestamp - updated[i - 1].timestamp;
          if (i > 1) {
            const prevInterval = updated[i - 1].timestamp - updated[i - 2].timestamp;
            if (prevInterval > 0) {
              updated[i].timeIntervalRatio = currentInterval / prevInterval;
            }
          }
        }
      }
      
      // Keep last 100 points
      if (updated.length > 100) {
        updated.shift();
      }
      return updated;
    });

    setLastPrice(currentPrice);
  }, [ftcpPoint, currentPrice]);

  const ftcpEvents = history.filter(p => p.isFTCP);
  const recentFTCPs = ftcpEvents.slice(-10).reverse();

  // Prepare chart data
  const chartData = history.map((point, idx) => ({
    time: idx,
    curvature: point.curvature,
    isFTCP: point.isFTCP,
    goldenRatioScore: point.goldenRatioScore,
    price: point.price,
  }));

  // Golden ratio intervals
  const goldenRatioPoints = history.filter(p => 
    p.timeIntervalRatio && Math.abs(p.timeIntervalRatio - PHI) / PHI < 0.1
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card className="p-6 bg-gradient-to-br from-warning/5 to-background border-2 border-warning/20">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-xl font-bold flex items-center gap-2">
              <Sparkles className="h-6 w-6 text-warning" />
              FTCP Timeline
            </h3>
            <p className="text-sm text-muted-foreground mt-1">
              Fibonacci-Tightened Curvature Points with Golden Ratio (φ ≈ 1.618) Timing
            </p>
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold text-warning">{ftcpEvents.length}</div>
            <div className="text-xs text-muted-foreground">FTCP Events</div>
          </div>
        </div>

        {/* Current FTCP Status */}
        {ftcpPoint && ftcpPoint.isFTCP && (
          <div className="p-4 rounded-lg bg-warning/10 border border-warning/30 animate-pulse">
            <div className="flex items-center gap-3">
              <Zap className="h-8 w-8 text-warning" />
              <div>
                <div className="font-bold text-lg">FTCP Detected!</div>
                <div className="text-sm text-muted-foreground">
                  Curvature: {ftcpPoint.curvature.toFixed(3)} | Golden Ratio Score: {(ftcpPoint.goldenRatioScore * 100).toFixed(0)}%
                </div>
              </div>
            </div>
          </div>
        )}
      </Card>

      {/* Curvature Time Series */}
      <Card className="p-6">
        <h4 className="text-lg font-semibold mb-4">Curvature Over Time</h4>
        <p className="text-sm text-muted-foreground mb-4">
          FTCP events marked where discrete curvature spikes (highlighted points)
        </p>

        {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis 
                dataKey="time" 
                stroke="hsl(var(--muted-foreground))"
                tick={{ fill: 'hsl(var(--muted-foreground))' }}
              />
              <YAxis 
                stroke="hsl(var(--muted-foreground))"
                tick={{ fill: 'hsl(var(--muted-foreground))' }}
              />
              <Tooltip 
                contentStyle={{
                  backgroundColor: 'hsl(var(--background))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px',
                }}
                formatter={(value: number) => value.toFixed(4)}
              />
              
              <ReferenceLine 
                y={0.5} 
                stroke="hsl(var(--destructive))" 
                strokeDasharray="5 5"
                label={{ value: 'Threshold', fill: 'hsl(var(--destructive))' }}
              />
              
              <Line
                type="monotone"
                dataKey="curvature"
                stroke="rgb(234, 179, 8)"
                strokeWidth={2}
                dot={(props: any) => {
                  const point = chartData[props.index];
                  if (point?.isFTCP) {
                    return (
                      <circle
                        cx={props.cx}
                        cy={props.cy}
                        r={8}
                        fill="rgb(234, 179, 8)"
                        stroke="hsl(var(--background))"
                        strokeWidth={3}
                      />
                    );
                  }
                  return <circle cx={props.cx} cy={props.cy} r={2} fill="rgb(234, 179, 8)" />;
                }}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-[300px] flex items-center justify-center text-muted-foreground">
            <p>Collecting curvature data...</p>
          </div>
        )}
      </Card>

      {/* Golden Ratio Timing Patterns */}
      <Card className="p-6">
        <h4 className="text-lg font-semibold mb-4">Golden Ratio Timing Patterns</h4>
        <p className="text-sm text-muted-foreground mb-4">
          Time intervals between points approaching φ ≈ 1.618 (golden ratio)
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="p-4 rounded-lg bg-muted/50 border border-border">
            <div className="text-xs text-muted-foreground mb-1">Golden Ratio (φ)</div>
            <div className="text-3xl font-bold text-warning">1.618</div>
          </div>
          
          <div className="p-4 rounded-lg bg-muted/50 border border-border">
            <div className="text-xs text-muted-foreground mb-1">φ Pattern Matches</div>
            <div className="text-3xl font-bold">{goldenRatioPoints.length}</div>
          </div>
          
          <div className="p-4 rounded-lg bg-muted/50 border border-border">
            <div className="text-xs text-muted-foreground mb-1">Match Rate</div>
            <div className="text-3xl font-bold">
              {history.length > 0 ? ((goldenRatioPoints.length / history.length) * 100).toFixed(1) : '0'}%
            </div>
          </div>
        </div>

        {/* Golden Ratio Scatter Plot */}
        {goldenRatioPoints.length > 0 && (
          <ResponsiveContainer width="100%" height={250}>
            <ScatterChart>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis 
                type="number" 
                dataKey="timestamp" 
                name="Time"
                stroke="hsl(var(--muted-foreground))"
                tick={{ fill: 'hsl(var(--muted-foreground))' }}
                tickFormatter={(value) => format(new Date(value), 'HH:mm:ss')}
              />
              <YAxis 
                type="number" 
                dataKey="timeIntervalRatio" 
                name="Ratio"
                stroke="hsl(var(--muted-foreground))"
                tick={{ fill: 'hsl(var(--muted-foreground))' }}
              />
              <Tooltip 
                contentStyle={{
                  backgroundColor: 'hsl(var(--background))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px',
                }}
                formatter={(value: number) => value.toFixed(3)}
              />
              
              <ReferenceLine 
                y={PHI} 
                stroke="rgb(234, 179, 8)" 
                strokeWidth={2}
                strokeDasharray="5 5"
                label={{ value: 'φ = 1.618', fill: 'rgb(234, 179, 8)', position: 'right' }}
              />
              
              <Scatter 
                data={goldenRatioPoints} 
                fill="rgb(234, 179, 8)"
              >
                {goldenRatioPoints.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill="rgb(234, 179, 8)" />
                ))}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
        )}
      </Card>

      {/* Recent FTCP Events List */}
      <Card className="p-6">
        <h4 className="text-lg font-semibold mb-4">Recent FTCP Events</h4>
        
        {recentFTCPs.length > 0 ? (
          <ScrollArea className="h-[400px] pr-4">
            <div className="space-y-3">
              {recentFTCPs.map((point, idx) => {
                const isRecent = idx === 0;
                const priceDirection = point.priceChange > 0 ? 'up' : point.priceChange < 0 ? 'down' : 'neutral';
                const DirectionIcon = priceDirection === 'up' ? TrendingUp : priceDirection === 'down' ? TrendingDown : Minus;
                const directionColor = priceDirection === 'up' ? 'text-success' : priceDirection === 'down' ? 'text-destructive' : 'text-muted-foreground';
                
                return (
                  <div 
                    key={point.timestamp}
                    className={`p-4 rounded-lg border transition-all ${
                      isRecent 
                        ? 'bg-warning/10 border-warning/30 animate-pulse' 
                        : 'bg-muted/30 border-border hover:border-warning/30'
                    }`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <Sparkles className="h-4 w-4 text-warning" />
                        <span className="text-sm font-semibold">
                          {format(new Date(point.timestamp), 'HH:mm:ss.SSS')}
                        </span>
                        {isRecent && (
                          <Badge variant="default" className="text-xs bg-warning">
                            LATEST
                          </Badge>
                        )}
                      </div>
                      
                      <div className={`flex items-center gap-1 ${directionColor}`}>
                        <DirectionIcon className="h-4 w-4" />
                        <span className="text-sm font-mono">
                          ${point.price.toFixed(2)}
                        </span>
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-3 gap-3 text-xs">
                      <div>
                        <div className="text-muted-foreground">Curvature</div>
                        <div className="font-mono font-semibold">{point.curvature.toFixed(3)}</div>
                      </div>
                      
                      <div>
                        <div className="text-muted-foreground">φ Score</div>
                        <div className="font-mono font-semibold">{(point.goldenRatioScore * 100).toFixed(0)}%</div>
                      </div>
                      
                      <div>
                        <div className="text-muted-foreground">Price Δ</div>
                        <div className={`font-mono font-semibold ${directionColor}`}>
                          {point.priceChange >= 0 ? '+' : ''}{point.priceChange.toFixed(2)}
                        </div>
                      </div>
                    </div>

                    {point.timeIntervalRatio && (
                      <div className="mt-2 pt-2 border-t border-border/50">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-muted-foreground">Time Interval Ratio</span>
                          <span className="font-mono font-semibold">
                            {point.timeIntervalRatio.toFixed(3)}
                            {Math.abs(point.timeIntervalRatio - PHI) / PHI < 0.1 && (
                              <span className="ml-2 text-warning">≈ φ</span>
                            )}
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </ScrollArea>
        ) : (
          <div className="py-12 text-center text-muted-foreground">
            <Clock className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No FTCP events detected yet</p>
            <p className="text-xs mt-2">FTCP events trigger when curvature spikes align with golden ratio timing</p>
          </div>
        )}
      </Card>

      {/* Legend */}
      <Card className="p-4 bg-muted/30">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div>
            <h5 className="font-semibold mb-2">What is FTCP?</h5>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Fibonacci-Tightened Curvature Points identify structural anomalies where discrete 
              curvature spikes coincide with near-golden-ratio (φ ≈ 1.618) spacing of temporal events.
            </p>
          </div>
          <div>
            <h5 className="font-semibold mb-2">Detection Criteria</h5>
            <ul className="text-xs text-muted-foreground space-y-1">
              <li>• Curvature exceeds threshold (0.5)</li>
              <li>• Golden ratio score &gt; 70%</li>
              <li>• Time intervals approach φ ratio</li>
            </ul>
          </div>
        </div>
        
        {/* FTCP Windowing Research Image */}
        <div className="mt-6 border-t border-border/30 pt-4">
          <h5 className="text-sm font-semibold mb-3 text-muted-foreground">Research: Fibonacci Windowing</h5>
          <img 
            src={fibonacciFtcpWindowing}
            alt="Fibonacci-Tightened Curvature Point Windowing Research"
            className="w-full rounded-lg border border-border/50"
          />
        </div>
      </Card>
    </div>
  );
};
