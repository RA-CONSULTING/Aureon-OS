import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { 
  Search, 
  TrendingUp, 
  TrendingDown, 
  Target, 
  CheckCircle2, 
  XCircle, 
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Activity,
  Zap
} from "lucide-react";
import { z } from "zod";

// Trade data validation schema
const tradeSchema = z.object({
  id: z.string(),
  entryTime: z.string(),
  exitTime: z.string(),
  side: z.enum(['LONG', 'SHORT']),
  entryPrice: z.number().positive(),
  exitPrice: z.number().positive(),
  quantity: z.number().positive(),
  pnl: z.number(),
  pnlPercent: z.number(),
  entryCoherence: z.number().min(0).max(1),
  exitCoherence: z.number().min(0).max(1),
  entryLighthouse: z.number().min(0).max(1),
  prismLevel: z.number().int().min(1).max(5),
  isLHE: z.boolean(),
  nodeVotes: z.object({
    Tiger: z.number(),
    Falcon: z.number(),
    Hummingbird: z.number(),
    Dolphin: z.number(),
    Deer: z.number(),
    Owl: z.number(),
    Panda: z.number(),
    CargoShip: z.number(),
    Clownfish: z.number(),
  }),
  exitReason: z.enum(['TAKE_PROFIT', 'STOP_LOSS', 'SIGNAL_EXIT', 'COHERENCE_DROP']),
  duration: z.number().positive(),
});

type Trade = z.infer<typeof tradeSchema>;

interface TradeAnalyzerProps {
  trades?: Trade[];
}

export function TradeAnalyzer({ trades: externalTrades }: TradeAnalyzerProps) {
  const [selectedTrade, setSelectedTrade] = useState<Trade | null>(null);
  const [filterType, setFilterType] = useState<'all' | 'winners' | 'losers'>('all');
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState<'date' | 'pnl' | 'coherence'>('date');

  // Generate sample trades if none provided
  const sampleTrades: Trade[] = externalTrades || [
    {
      id: "1",
      entryTime: "2024-01-15T14:23:00Z",
      exitTime: "2024-01-15T18:45:00Z",
      side: "LONG",
      entryPrice: 42350.50,
      exitPrice: 43120.75,
      quantity: 0.1,
      pnl: 77.03,
      pnlPercent: 1.82,
      entryCoherence: 0.967,
      exitCoherence: 0.823,
      entryLighthouse: 0.892,
      prismLevel: 4,
      isLHE: true,
      nodeVotes: {
        Tiger: 0.85,
        Falcon: 0.92,
        Hummingbird: 0.78,
        Dolphin: 0.88,
        Deer: 0.81,
        Owl: 0.90,
        Panda: 0.87,
        CargoShip: 0.79,
        Clownfish: 0.84,
      },
      exitReason: "TAKE_PROFIT",
      duration: 262,
    },
    {
      id: "2",
      entryTime: "2024-01-16T09:12:00Z",
      exitTime: "2024-01-16T10:30:00Z",
      side: "SHORT",
      entryPrice: 43500.00,
      exitPrice: 44100.25,
      quantity: 0.15,
      pnl: -90.04,
      pnlPercent: -1.38,
      entryCoherence: 0.952,
      exitCoherence: 0.891,
      entryLighthouse: 0.785,
      prismLevel: 3,
      isLHE: false,
      nodeVotes: {
        Tiger: 0.82,
        Falcon: 0.76,
        Hummingbird: 0.88,
        Dolphin: 0.79,
        Deer: 0.84,
        Owl: 0.81,
        Panda: 0.77,
        CargoShip: 0.80,
        Clownfish: 0.86,
      },
      exitReason: "STOP_LOSS",
      duration: 78,
    },
    {
      id: "3",
      entryTime: "2024-01-17T15:45:00Z",
      exitTime: "2024-01-17T22:18:00Z",
      side: "LONG",
      entryPrice: 44250.75,
      exitPrice: 45890.50,
      quantity: 0.12,
      pnl: 196.77,
      pnlPercent: 3.70,
      entryCoherence: 0.978,
      exitCoherence: 0.945,
      entryLighthouse: 0.925,
      prismLevel: 5,
      isLHE: true,
      nodeVotes: {
        Tiger: 0.91,
        Falcon: 0.95,
        Hummingbird: 0.83,
        Dolphin: 0.94,
        Deer: 0.89,
        Owl: 0.96,
        Panda: 0.92,
        CargoShip: 0.88,
        Clownfish: 0.90,
      },
      exitReason: "TAKE_PROFIT",
      duration: 393,
    },
  ];

  const filteredTrades = sampleTrades
    .filter(trade => {
      if (filterType === 'winners') return trade.pnl > 0;
      if (filterType === 'losers') return trade.pnl < 0;
      return true;
    })
    .filter(trade => {
      if (!searchQuery) return true;
      const query = searchQuery.toLowerCase();
      return (
        trade.id.toLowerCase().includes(query) ||
        trade.side.toLowerCase().includes(query) ||
        trade.exitReason.toLowerCase().includes(query)
      );
    })
    .sort((a, b) => {
      if (sortBy === 'pnl') return b.pnl - a.pnl;
      if (sortBy === 'coherence') return b.entryCoherence - a.entryCoherence;
      return new Date(b.entryTime).getTime() - new Date(a.entryTime).getTime();
    });

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatDuration = (minutes: number) => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;
  };

  const getExitReasonColor = (reason: string) => {
    switch (reason) {
      case 'TAKE_PROFIT': return 'text-success';
      case 'STOP_LOSS': return 'text-destructive';
      case 'SIGNAL_EXIT': return 'text-warning';
      case 'COHERENCE_DROP': return 'text-warning';
      default: return 'text-muted-foreground';
    }
  };

  const getExitReasonIcon = (reason: string) => {
    switch (reason) {
      case 'TAKE_PROFIT': return <CheckCircle2 className="h-4 w-4" />;
      case 'STOP_LOSS': return <XCircle className="h-4 w-4" />;
      case 'SIGNAL_EXIT': return <Activity className="h-4 w-4" />;
      case 'COHERENCE_DROP': return <AlertCircle className="h-4 w-4" />;
      default: return null;
    }
  };

  const calculateVotingConsensus = (votes: Record<string, number>) => {
    const threshold = 0.8;
    const votesAboveThreshold = Object.values(votes).filter(v => v >= threshold).length;
    return { count: votesAboveThreshold, percentage: (votesAboveThreshold / 9) * 100 };
  };

  return (
    <Card className="bg-card/50 backdrop-blur border-border/50">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-xl font-bold">Trade-by-Trade Analyzer</CardTitle>
            <CardDescription>Detailed entry/exit analysis with coherence and node voting data</CardDescription>
          </div>
          <Badge variant="outline" className="text-primary">
            {filteredTrades.length} Trades
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="overview" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="overview">Trade Overview</TabsTrigger>
            <TabsTrigger value="details" disabled={!selectedTrade}>Trade Details</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-4 mt-6">
            {/* Filters and Search */}
            <div className="flex flex-col md:flex-row gap-3">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search trades by ID, side, or exit reason..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value.slice(0, 100))}
                  className="pl-10"
                  maxLength={100}
                />
              </div>
              <Select value={filterType} onValueChange={(value: any) => setFilterType(value)}>
                <SelectTrigger className="w-full md:w-40">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Trades</SelectItem>
                  <SelectItem value="winners">Winners Only</SelectItem>
                  <SelectItem value="losers">Losers Only</SelectItem>
                </SelectContent>
              </Select>
              <Select value={sortBy} onValueChange={(value: any) => setSortBy(value)}>
                <SelectTrigger className="w-full md:w-40">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="date">Sort by Date</SelectItem>
                  <SelectItem value="pnl">Sort by P&L</SelectItem>
                  <SelectItem value="coherence">Sort by Coherence</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Trades Table */}
            <div className="rounded-lg border border-border/30 overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/30">
                    <TableHead>Trade ID</TableHead>
                    <TableHead>Entry Time</TableHead>
                    <TableHead>Side</TableHead>
                    <TableHead className="text-right">Entry Price</TableHead>
                    <TableHead className="text-right">Exit Price</TableHead>
                    <TableHead className="text-right">P&L</TableHead>
                    <TableHead className="text-center">Coherence</TableHead>
                    <TableHead className="text-center">LHE</TableHead>
                    <TableHead>Exit Reason</TableHead>
                    <TableHead></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredTrades.map((trade) => (
                    <TableRow 
                      key={trade.id}
                      className="cursor-pointer hover:bg-muted/50 transition-colors"
                      onClick={() => setSelectedTrade(trade)}
                    >
                      <TableCell className="font-mono text-sm">#{trade.id}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {formatDate(trade.entryTime)}
                      </TableCell>
                      <TableCell>
                        <Badge 
                          variant={trade.side === 'LONG' ? 'default' : 'secondary'}
                          className={trade.side === 'LONG' ? 'bg-success/20 text-success' : 'bg-destructive/20 text-destructive'}
                        >
                          {trade.side}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm">
                        ${trade.entryPrice.toLocaleString()}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm">
                        ${trade.exitPrice.toLocaleString()}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex flex-col items-end">
                          <span className={`font-mono font-semibold ${trade.pnl > 0 ? 'text-success' : 'text-destructive'}`}>
                            {trade.pnl > 0 ? '+' : ''}${trade.pnl.toFixed(2)}
                          </span>
                          <span className={`text-xs ${trade.pnl > 0 ? 'text-success/70' : 'text-destructive/70'}`}>
                            {trade.pnl > 0 ? '+' : ''}{trade.pnlPercent.toFixed(2)}%
                          </span>
                        </div>
                      </TableCell>
                      <TableCell className="text-center">
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger>
                              <Badge 
                                variant="outline" 
                                className={trade.entryCoherence >= 0.95 ? 'text-success' : 'text-warning'}
                              >
                                {trade.entryCoherence.toFixed(3)}
                              </Badge>
                            </TooltipTrigger>
                            <TooltipContent>
                              <p className="text-xs">Entry: {trade.entryCoherence.toFixed(3)}</p>
                              <p className="text-xs">Exit: {trade.exitCoherence.toFixed(3)}</p>
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                      </TableCell>
                      <TableCell className="text-center">
                        {trade.isLHE ? (
                          <Badge variant="default" className="bg-primary/20 text-primary">
                            <Zap className="h-3 w-3 mr-1" />
                            YES
                          </Badge>
                        ) : (
                          <Badge variant="outline" className="text-muted-foreground">NO</Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className={`flex items-center gap-1 ${getExitReasonColor(trade.exitReason)}`}>
                          {getExitReasonIcon(trade.exitReason)}
                          <span className="text-xs">{trade.exitReason.replace('_', ' ')}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <ChevronDown className="h-4 w-4 text-muted-foreground" />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            {filteredTrades.length === 0 && (
              <div className="text-center py-12 text-muted-foreground">
                <p>No trades match your filters</p>
              </div>
            )}
          </TabsContent>

          <TabsContent value="details" className="space-y-6 mt-6">
            {selectedTrade && (
              <>
                {/* Trade Summary */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="p-4 bg-muted/30 rounded-lg border border-border/30">
                    <p className="text-xs text-muted-foreground mb-1">Trade ID</p>
                    <p className="text-lg font-bold font-mono text-foreground">#{selectedTrade.id}</p>
                  </div>
                  <div className="p-4 bg-muted/30 rounded-lg border border-border/30">
                    <p className="text-xs text-muted-foreground mb-1">Duration</p>
                    <p className="text-lg font-bold font-mono text-foreground">
                      {formatDuration(selectedTrade.duration)}
                    </p>
                  </div>
                  <div className="p-4 bg-muted/30 rounded-lg border border-border/30">
                    <p className="text-xs text-muted-foreground mb-1">Prism Level</p>
                    <p className="text-lg font-bold font-mono text-primary">
                      Level {selectedTrade.prismLevel}
                    </p>
                  </div>
                  <div className={`p-4 rounded-lg border ${selectedTrade.pnl > 0 ? 'bg-success/10 border-success/30' : 'bg-destructive/10 border-destructive/30'}`}>
                    <p className="text-xs text-muted-foreground mb-1">Final P&L</p>
                    <p className={`text-lg font-bold font-mono ${selectedTrade.pnl > 0 ? 'text-success' : 'text-destructive'}`}>
                      {selectedTrade.pnl > 0 ? '+' : ''}${selectedTrade.pnl.toFixed(2)}
                    </p>
                  </div>
                </div>

                {/* Entry Analysis */}
                <div className="p-6 bg-gradient-to-br from-success/10 to-primary/10 rounded-lg border border-success/30">
                  <h3 className="text-lg font-bold mb-4 flex items-center gap-2 text-foreground">
                    <TrendingUp className="h-5 w-5 text-success" />
                    Entry Analysis
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm text-muted-foreground mb-2">Entry Conditions</p>
                      <div className="space-y-2">
                        <div className="flex items-center justify-between p-2 bg-background/50 rounded">
                          <span className="text-sm">Entry Time</span>
                          <span className="font-mono text-sm text-foreground">
                            {formatDate(selectedTrade.entryTime)}
                          </span>
                        </div>
                        <div className="flex items-center justify-between p-2 bg-background/50 rounded">
                          <span className="text-sm">Entry Price</span>
                          <span className="font-mono text-sm text-foreground">
                            ${selectedTrade.entryPrice.toLocaleString()}
                          </span>
                        </div>
                        <div className="flex items-center justify-between p-2 bg-background/50 rounded">
                          <span className="text-sm">Side</span>
                          <Badge variant={selectedTrade.side === 'LONG' ? 'default' : 'secondary'}>
                            {selectedTrade.side}
                          </Badge>
                        </div>
                      </div>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground mb-2">Field Metrics</p>
                      <div className="space-y-2">
                        <div className="flex items-center justify-between p-2 bg-background/50 rounded">
                          <span className="text-sm">Coherence (Γ)</span>
                          <Badge variant="outline" className="text-success font-mono">
                            {selectedTrade.entryCoherence.toFixed(3)}
                          </Badge>
                        </div>
                        <div className="flex items-center justify-between p-2 bg-background/50 rounded">
                          <span className="text-sm">Lighthouse Signal</span>
                          <Badge variant="outline" className="font-mono text-foreground">
                            {selectedTrade.entryLighthouse.toFixed(3)}
                          </Badge>
                        </div>
                        <div className="flex items-center justify-between p-2 bg-background/50 rounded">
                          <span className="text-sm">LHE Status</span>
                          {selectedTrade.isLHE ? (
                            <Badge className="bg-primary text-primary-foreground">
                              <Zap className="h-3 w-3 mr-1" />
                              Lighthouse Event
                            </Badge>
                          ) : (
                            <Badge variant="outline">Standard Entry</Badge>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Node Voting Analysis */}
                <div className="p-6 bg-muted/30 rounded-lg border border-border/30">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-bold text-foreground">9 Auris Node Votes</h3>
                    <Badge variant="outline">
                      {calculateVotingConsensus(selectedTrade.nodeVotes).count}/9 Consensus
                    </Badge>
                  </div>
                  <div className="space-y-3">
                    {Object.entries(selectedTrade.nodeVotes).map(([node, vote]) => (
                      <div key={node}>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm font-semibold text-foreground">{node}</span>
                          <span className={`text-sm font-mono ${vote >= 0.8 ? 'text-success' : 'text-warning'}`}>
                            {vote.toFixed(3)}
                          </span>
                        </div>
                        <Progress 
                          value={vote * 100} 
                          className="h-2"
                          style={{
                            '--progress-background': vote >= 0.8 ? 'hsl(var(--chart-1))' : 'hsl(var(--chart-4))'
                          } as React.CSSProperties}
                        />
                      </div>
                    ))}
                  </div>
                  <div className="mt-4 p-3 bg-background/50 rounded">
                    <p className="text-xs text-muted-foreground">
                      <strong>Decision Reasoning:</strong> {calculateVotingConsensus(selectedTrade.nodeVotes).count} nodes 
                      exceeded threshold (≥0.80), achieving {calculateVotingConsensus(selectedTrade.nodeVotes).percentage.toFixed(1)}% 
                      consensus. Combined with Γ = {selectedTrade.entryCoherence.toFixed(3)} 
                      {selectedTrade.isLHE ? ' and Lighthouse Event confirmation' : ''}, 
                      entry criteria were satisfied for {selectedTrade.side} position.
                    </p>
                  </div>
                </div>

                {/* Exit Analysis */}
                <div className="p-6 bg-gradient-to-br from-destructive/10 to-warning/10 rounded-lg border border-destructive/30">
                  <h3 className="text-lg font-bold mb-4 flex items-center gap-2 text-foreground">
                    <TrendingDown className="h-5 w-5 text-destructive" />
                    Exit Analysis
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm text-muted-foreground mb-2">Exit Conditions</p>
                      <div className="space-y-2">
                        <div className="flex items-center justify-between p-2 bg-background/50 rounded">
                          <span className="text-sm">Exit Time</span>
                          <span className="font-mono text-sm text-foreground">
                            {formatDate(selectedTrade.exitTime)}
                          </span>
                        </div>
                        <div className="flex items-center justify-between p-2 bg-background/50 rounded">
                          <span className="text-sm">Exit Price</span>
                          <span className="font-mono text-sm text-foreground">
                            ${selectedTrade.exitPrice.toLocaleString()}
                          </span>
                        </div>
                        <div className="flex items-center justify-between p-2 bg-background/50 rounded">
                          <span className="text-sm">Exit Reason</span>
                          <div className={`flex items-center gap-1 ${getExitReasonColor(selectedTrade.exitReason)}`}>
                            {getExitReasonIcon(selectedTrade.exitReason)}
                            <span className="text-sm font-semibold">
                              {selectedTrade.exitReason.replace('_', ' ')}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground mb-2">Performance</p>
                      <div className="space-y-2">
                        <div className="flex items-center justify-between p-2 bg-background/50 rounded">
                          <span className="text-sm">Price Change</span>
                          <span className={`font-mono text-sm ${selectedTrade.pnl > 0 ? 'text-success' : 'text-destructive'}`}>
                            {selectedTrade.pnl > 0 ? '+' : ''}{selectedTrade.pnlPercent.toFixed(2)}%
                          </span>
                        </div>
                        <div className="flex items-center justify-between p-2 bg-background/50 rounded">
                          <span className="text-sm">Exit Coherence</span>
                          <Badge variant="outline" className="font-mono text-foreground">
                            {selectedTrade.exitCoherence.toFixed(3)}
                          </Badge>
                        </div>
                        <div className="flex items-center justify-between p-2 bg-background/50 rounded">
                          <span className="text-sm">Coherence Change</span>
                          <span className={`font-mono text-sm ${selectedTrade.exitCoherence >= selectedTrade.entryCoherence ? 'text-success' : 'text-warning'}`}>
                            {selectedTrade.exitCoherence >= selectedTrade.entryCoherence ? '+' : ''}
                            {((selectedTrade.exitCoherence - selectedTrade.entryCoherence) * 100).toFixed(1)}%
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className="mt-4 p-3 bg-background/50 rounded">
                    <p className="text-xs text-muted-foreground">
                      <strong>Exit Reasoning:</strong> Position exited via {selectedTrade.exitReason.replace('_', ' ').toLowerCase()} 
                      {selectedTrade.exitReason === 'TAKE_PROFIT' && ' - target profit level reached'}
                      {selectedTrade.exitReason === 'STOP_LOSS' && ' - risk management stop triggered'}
                      {selectedTrade.exitReason === 'COHERENCE_DROP' && ' - field coherence dropped below threshold'}
                      {selectedTrade.exitReason === 'SIGNAL_EXIT' && ' - counter-signal detected'}
                      . Final coherence: {selectedTrade.exitCoherence.toFixed(3)}, 
                      representing a {Math.abs((selectedTrade.exitCoherence - selectedTrade.entryCoherence) * 100).toFixed(1)}% 
                      {selectedTrade.exitCoherence >= selectedTrade.entryCoherence ? 'improvement' : 'degradation'} from entry.
                    </p>
                  </div>
                </div>

                {/* Back Button */}
                <Button 
                  onClick={() => setSelectedTrade(null)} 
                  variant="outline"
                  className="w-full"
                >
                  <ChevronUp className="h-4 w-4 mr-2" />
                  Back to Trade Overview
                </Button>
              </>
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
