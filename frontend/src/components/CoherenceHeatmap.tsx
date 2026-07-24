import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Calendar, Clock, TrendingUp, BarChart3, RefreshCw } from 'lucide-react';
import { supabase } from '@/integrations/supabase/client';
import { useToast } from "@/hooks/use-toast";

interface HeatmapCell {
  day: number;
  hour: number;
  avgCoherence: number;
  count: number;
}

interface OptimalWindow {
  day: string;
  hours: number[];
  avgCoherence: number;
}

const DAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
const DAY_ABBR = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

interface CoherenceHeatmapProps {
  symbol?: string;
}

export const CoherenceHeatmap = ({ symbol = 'BTCUSDT' }: CoherenceHeatmapProps) => {
  const [heatmapData, setHeatmapData] = useState<HeatmapCell[]>([]);
  const [optimalWindows, setOptimalWindows] = useState<OptimalWindow[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [totalDataPoints, setTotalDataPoints] = useState(0);
  const [dateRange, setDateRange] = useState({ start: '', end: '' });
  const { toast } = useToast();

  const fetchCoherenceData = async () => {
    setIsLoading(true);
    try {
      // Fetch last 7 days of data
      const sevenDaysAgo = new Date();
      sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);

      const { data, error } = await supabase
        .from('coherence_history')
        .select('*')
        .eq('symbol', symbol)
        .gte('timestamp', sevenDaysAgo.toISOString())
        .order('timestamp', { ascending: false });

      if (error) throw error;

      if (!data || data.length === 0) {
        toast({
          title: "No Data Available",
          description: "Start the system to begin collecting coherence data for the heatmap.",
          variant: "default",
        });
        setIsLoading(false);
        return;
      }

      setTotalDataPoints(data.length);
      setDateRange({
        start: new Date(data[data.length - 1].timestamp).toLocaleDateString(),
        end: new Date(data[0].timestamp).toLocaleDateString(),
      });

      // Aggregate data by day of week and hour
      const aggregated = new Map<string, { sum: number; count: number }>();

      data.forEach(record => {
        const key = `${record.day_of_week}-${record.hour_of_day}`;
        const existing = aggregated.get(key) || { sum: 0, count: 0 };
        aggregated.set(key, {
          sum: existing.sum + Number(record.coherence),
          count: existing.count + 1,
        });
      });

      // Convert to heatmap cells
      const cells: HeatmapCell[] = [];
      for (let day = 0; day < 7; day++) {
        for (let hour = 0; hour < 24; hour++) {
          const key = `${day}-${hour}`;
          const agg = aggregated.get(key);
          if (agg) {
            cells.push({
              day,
              hour,
              avgCoherence: agg.sum / agg.count,
              count: agg.count,
            });
          } else {
            cells.push({
              day,
              hour,
              avgCoherence: 0,
              count: 0,
            });
          }
        }
      }

      setHeatmapData(cells);

      // Find optimal windows (high coherence periods)
      const windowsByDay = new Map<number, { hours: number[]; coherences: number[] }>();
      
      cells.forEach(cell => {
        if (cell.avgCoherence >= 0.92 && cell.count > 0) {
          const dayData = windowsByDay.get(cell.day) || { hours: [], coherences: [] };
          dayData.hours.push(cell.hour);
          dayData.coherences.push(cell.avgCoherence);
          windowsByDay.set(cell.day, dayData);
        }
      });

      const optimal: OptimalWindow[] = [];
      windowsByDay.forEach((value, day) => {
        if (value.hours.length > 0) {
          const avgCoh = value.coherences.reduce((a, b) => a + b, 0) / value.coherences.length;
          optimal.push({
            day: DAYS[day],
            hours: value.hours.sort((a, b) => a - b),
            avgCoherence: avgCoh,
          });
        }
      });

      setOptimalWindows(optimal.sort((a, b) => b.avgCoherence - a.avgCoherence));

    } catch (error) {
      console.error('Error fetching coherence data:', error);
      toast({
        title: "Error Loading Data",
        description: "Failed to load coherence history. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchCoherenceData();
    // Refresh every 5 minutes
    const interval = setInterval(fetchCoherenceData, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [symbol]);

  const getColorForCoherence = (coherence: number, count: number): string => {
    if (count === 0) return 'bg-gray-900/30';
    if (coherence >= 0.945) return 'bg-success';
    if (coherence >= 0.92) return 'bg-warning';
    if (coherence >= 0.85) return 'bg-primary';
    if (coherence >= 0.75) return 'bg-primary';
    if (coherence >= 0.65) return 'bg-primary';
    return 'bg-gray-600';
  };

  const formatHourRange = (hours: number[]): string => {
    if (hours.length === 0) return '';
    if (hours.length === 1) return `${hours[0]}:00`;
    
    // Group consecutive hours
    const ranges: string[] = [];
    let start = hours[0];
    let prev = hours[0];
    
    for (let i = 1; i <= hours.length; i++) {
      if (i === hours.length || hours[i] !== prev + 1) {
        if (start === prev) {
          ranges.push(`${start}:00`);
        } else {
          ranges.push(`${start}:00-${prev + 1}:00`);
        }
        if (i < hours.length) {
          start = hours[i];
          prev = hours[i];
        }
      } else {
        prev = hours[i];
      }
    }
    
    return ranges.join(', ');
  };

  return (
    <Card className="border-primary/20 bg-card/50 backdrop-blur">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-xl font-bold flex items-center gap-2">
              <Calendar className="h-5 w-5 text-primary" />
              Coherence Temporal Heatmap
              <Badge variant="outline">{symbol.replace('USDT', '/USDT')}</Badge>
            </CardTitle>
            <CardDescription>
              C(t) distribution across days and hours — Identify optimal trading windows
            </CardDescription>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={fetchCoherenceData}
            disabled={isLoading}
            className="gap-2"
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Stats */}
        <div className="grid grid-cols-3 gap-4">
          <Card className="bg-background/50">
            <CardContent className="p-4">
              <div className="text-center">
                <p className="text-xs text-muted-foreground mb-1">Data Points</p>
                <p className="text-2xl font-bold">{totalDataPoints.toLocaleString()}</p>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-background/50">
            <CardContent className="p-4">
              <div className="text-center">
                <p className="text-xs text-muted-foreground mb-1">Date Range</p>
                <p className="text-sm font-mono">{dateRange.start}</p>
                <p className="text-xs text-muted-foreground">to {dateRange.end}</p>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-background/50">
            <CardContent className="p-4">
              <div className="text-center">
                <p className="text-xs text-muted-foreground mb-1">Optimal Windows</p>
                <p className="text-2xl font-bold text-success">{optimalWindows.length}</p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Heatmap */}
        <Card className="bg-background/50">
          <CardHeader>
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <BarChart3 className="h-4 w-4" />
              Weekly Coherence Distribution
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="h-[400px] flex items-center justify-center">
                <div className="text-center space-y-2">
                  <RefreshCw className="h-8 w-8 animate-spin mx-auto text-primary" />
                  <p className="text-muted-foreground">Loading coherence data...</p>
                </div>
              </div>
            ) : heatmapData.length > 0 ? (
              <div className="space-y-2">
                {/* Hour labels */}
                <div className="flex items-center gap-1">
                  <div className="w-12 text-xs"></div>
                  {Array.from({ length: 24 }, (_, i) => (
                    <div key={i} className="w-6 text-[10px] text-center text-muted-foreground">
                      {i % 3 === 0 ? i : ''}
                    </div>
                  ))}
                </div>

                {/* Heatmap rows */}
                {DAYS.map((day, dayIdx) => (
                  <div key={day} className="flex items-center gap-1">
                    <div className="w-12 text-xs font-medium text-right pr-2">{DAY_ABBR[dayIdx]}</div>
                    {Array.from({ length: 24 }, (_, hour) => {
                      const cell = heatmapData.find(c => c.day === dayIdx && c.hour === hour);
                      const color = cell ? getColorForCoherence(cell.avgCoherence, cell.count) : 'bg-gray-900/30';
                      const title = cell && cell.count > 0
                        ? `${day} ${hour}:00 - Avg C(t): ${cell.avgCoherence.toFixed(3)} (${cell.count} samples)`
                        : `${day} ${hour}:00 - No data`;
                      
                      return (
                        <div
                          key={hour}
                          className={`w-6 h-6 ${color} rounded-sm cursor-help transition-all hover:scale-110 hover:z-10 hover:ring-2 hover:ring-primary`}
                          title={title}
                        />
                      );
                    })}
                  </div>
                ))}

                {/* Legend */}
                <div className="flex items-center gap-4 justify-center pt-4 text-xs">
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 bg-gray-900/30 rounded"></div>
                    <span>No data</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 bg-gray-600 rounded"></div>
                    <span>{'<'}0.65</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 bg-primary rounded"></div>
                    <span>0.65-0.75</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 bg-primary rounded"></div>
                    <span>0.75-0.85</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 bg-primary rounded"></div>
                    <span>0.85-0.92</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 bg-warning rounded"></div>
                    <span className="font-semibold">0.92-0.945 (High)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 bg-success rounded"></div>
                    <span className="font-semibold">≥0.945 (Optimal)</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="h-[400px] flex items-center justify-center">
                <div className="text-center space-y-2">
                  <Clock className="h-12 w-12 mx-auto opacity-50" />
                  <p className="text-muted-foreground">No coherence data available</p>
                  <p className="text-xs text-muted-foreground">Run the system to collect data</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Optimal Windows */}
        {optimalWindows.length > 0 && (
          <Card className="bg-background/50">
            <CardHeader>
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-success" />
                Optimal Trading Windows (C ≥ 0.92)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {optimalWindows.map((window, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 rounded-lg bg-primary/5 border border-primary/20">
                    <div className="flex items-center gap-3">
                      <Badge variant={window.avgCoherence >= 0.945 ? "default" : "secondary"}>
                        {window.day}
                      </Badge>
                      <span className="text-sm font-mono text-muted-foreground">
                        {formatHourRange(window.hours)}
                      </span>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-muted-foreground">Avg C(t)</p>
                      <p className="text-lg font-bold text-success">
                        {window.avgCoherence.toFixed(3)}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Information */}
        <Card className="bg-primary/5 border-primary/20">
          <CardContent className="p-3">
            <div className="space-y-2">
              <h4 className="font-semibold text-sm">How to Use This Heatmap</h4>
              <ul className="text-xs text-muted-foreground space-y-1">
                <li>• <strong>Green cells (C ≥ 0.945):</strong> Optimal trading windows with highest coherence</li>
                <li>• <strong>Yellow cells (0.92-0.945):</strong> High coherence periods, favorable for trading</li>
                <li>• <strong>Blue cells (0.65-0.92):</strong> Moderate coherence, system organizing</li>
                <li>• <strong>Darker cells:</strong> Lower coherence, wait for better conditions</li>
                <li>• Data aggregates last 7 days to identify recurring patterns</li>
                <li>• Hover over cells for detailed statistics</li>
              </ul>
            </div>
          </CardContent>
        </Card>
      </CardContent>
    </Card>
  );
};
