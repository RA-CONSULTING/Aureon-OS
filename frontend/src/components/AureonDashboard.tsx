import { useEffect, useState } from 'react';
import { supabase } from '@/integrations/supabase/client';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Sparkles, Activity, Zap, Brain, Radio, Database, Router, Play, Square, Wifi, WifiOff, Atom, Waves, Eye, BarChart3, Settings } from 'lucide-react';
import { DataSourceIndicator, DemoModeWarningBanner } from '@/components/DataSourceIndicator';
import { useNavigate } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { UserAssetsPanel } from '@/components/warroom/UserAssetsPanel';
import { SmartAlertBanner } from '@/components/SmartAlertBanner';
import { FloatingAIButton } from '@/components/FloatingAIButton';
import { ExchangeStatusSummary } from '@/components/ExchangeStatusSummary';
import Navbar from '@/components/Navbar';
// Tab content components - lazy loaded views of global state
import { QuantumTabContent } from '@/components/tabs/QuantumTabContent';
import { SystemsTabContent } from '@/components/tabs/SystemsTabContent';
import { AnalyticsTabContent } from '@/components/tabs/AnalyticsTabContent';
// Import hooks for global state - NO MORE LOCAL INITIALIZATION
import { 
  useGlobalState, 
  useGlobalTradingControls,
} from '@/hooks/useGlobalState';
import { globalSystemsManager } from '@/core/globalSystemsManager';

// Simple system indicator component
function SystemIndicator({ name, active, icon: Icon }: { name: string; active: boolean; icon: React.ElementType }) {
  return (
    <div className="flex items-center gap-2 text-xs">
      <div className={cn("h-2 w-2 rounded-full", active ? "bg-success" : "bg-muted-foreground")} />
      <Icon className="h-3 w-3 text-muted-foreground" />
      <span className={cn(active ? "text-foreground" : "text-muted-foreground")}>{name}</span>
    </div>
  );
}

export default function AureonDashboard() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('overview');
  
  // Get ALL state from global manager - no local state management
  // Systems run CONTINUOUSLY in GlobalSystemsManager regardless of which tab is active
  const state = useGlobalState();
  const { startTrading, stopTrading } = useGlobalTradingControls();
  
  // Extract what we need from global state
  const {
    userId,
    userEmail,
    isAuthenticated,
    coherence,
    lambda,
    lighthouseSignal,
    dominantNode,
    prismLevel,
    prismState,
    isActive,
    totalEquity,
    totalTrades,
    winningTrades,
    totalPnl,
    gasTankBalance,
    recentTrades,
    lastSignal,
    lastDecision,
    nextCheckIn,
    systemStatus,
    ecosystemHealth,
    isInitialized,
    marketData,
    busSnapshot,
    consensusSignal,
    consensusConfidence,
    prismOutput,
  } = state;
  
  // Redirect to auth if not authenticated
  useEffect(() => {
    if (isInitialized && !isAuthenticated) {
      navigate('/auth');
    }
  }, [isInitialized, isAuthenticated, navigate]);


  const winRate = totalTrades > 0 
    ? ((winningTrades / totalTrades) * 100).toFixed(0)
    : '0';

  const getPrismColor = () => {
    switch (prismState) {
      case 'MANIFEST': return 'text-success';
      case 'CONVERGING': return 'text-warning';
      default: return 'text-muted-foreground';
    }
  };

  // Count active systems
  const activeSystemCount = Object.values(systemStatus).filter(Boolean).length;
  const totalSystemCount = Object.keys(systemStatus).length;

  // Show loading if not initialized
  if (!isInitialized) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="h-8 w-8 rounded-full border-2 border-primary border-t-transparent animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Navigation */}
      <Navbar />
      
      {/* Demo Mode Warning Banner */}
      <DemoModeWarningBanner />
      
      {/* Smart Alert Banner - only shows when there are issues */}
      <SmartAlertBanner />

      <main className="container mx-auto px-4 py-6 pt-20 space-y-6">
        {/* Status Bar - Always visible regardless of tab */}
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-2">
            <DataSourceIndicator compact />
            
            {/* Ecosystem Health */}
            <Badge 
              variant={ecosystemHealth === 'connected' ? 'default' : ecosystemHealth === 'stale' ? 'secondary' : 'destructive'} 
              className="gap-1"
            >
              {ecosystemHealth === 'connected' ? <Wifi className="h-3 w-3" /> : <WifiOff className="h-3 w-3" />}
              {ecosystemHealth === 'connected' ? 'OK' : ecosystemHealth === 'stale' ? 'STALE' : 'DOWN'}
            </Badge>
            
            {/* Systems Summary */}
            <Badge variant={activeSystemCount === totalSystemCount ? "default" : "secondary"} className="gap-1">
              <Brain className="h-3 w-3" />
              {activeSystemCount}/{totalSystemCount}
            </Badge>
            
            <Badge variant={isActive ? "default" : "secondary"} className="gap-1">
              <div className={cn("h-1.5 w-1.5 rounded-full", isActive ? "bg-success animate-pulse" : "bg-muted-foreground")} />
              {isActive ? 'ACTIVE' : 'IDLE'}
            </Badge>
            
            {/* Live coherence indicator */}
            <Badge variant="outline" className="gap-1 font-mono">
              Γ {coherence.toFixed(3)}
            </Badge>
          </div>
          
          {/* Trading Controls - Always accessible */}
          <div className="flex gap-2">
            {!isActive ? (
              <Button size="sm" onClick={startTrading} className="gap-1">
                <Play className="h-3 w-3" /> Start
              </Button>
            ) : (
              <Button size="sm" variant="destructive" onClick={stopTrading} className="gap-1">
                <Square className="h-3 w-3" /> Stop
              </Button>
            )}
          </div>
        </div>

        {/* Exchange Connection Status */}
        <ExchangeStatusSummary />
        
        {/* Main Tabbed Interface - Systems run continuously regardless of which tab is shown */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-4 bg-muted/50">
            <TabsTrigger value="overview" className="gap-2 data-[state=active]:bg-background">
              <Activity className="h-4 w-4" />
              <span className="hidden sm:inline">Overview</span>
            </TabsTrigger>
            <TabsTrigger value="quantum" className="gap-2 data-[state=active]:bg-background">
              <Atom className="h-4 w-4" />
              <span className="hidden sm:inline">Quantum</span>
            </TabsTrigger>
            <TabsTrigger value="systems" className="gap-2 data-[state=active]:bg-background">
              <Brain className="h-4 w-4" />
              <span className="hidden sm:inline">Systems</span>
            </TabsTrigger>
            <TabsTrigger value="analytics" className="gap-2 data-[state=active]:bg-background">
              <BarChart3 className="h-4 w-4" />
              <span className="hidden sm:inline">Analytics</span>
            </TabsTrigger>
          </TabsList>
          
          {/* OVERVIEW TAB */}
          <TabsContent value="overview" className="space-y-4 mt-4">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Quantum State */}
              <Card className="border-border/50">
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                    <Activity className="h-3 w-3" /> QUANTUM STATE
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-1">
                  <div className="flex justify-between">
                    <span className="text-xs text-muted-foreground">Γ (Coherence)</span>
                    <span className="text-sm font-mono font-bold">{coherence.toFixed(3)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-xs text-muted-foreground">Λ (Lambda)</span>
                    <span className="text-sm font-mono">{lambda.toFixed(3)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-xs text-muted-foreground">Prism</span>
                    <span className={cn("text-sm font-medium", getPrismColor())}>{prismState}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-xs text-muted-foreground">Node</span>
                    <span className="text-sm">{dominantNode}</span>
                  </div>
                </CardContent>
              </Card>

              {/* Performance */}
              <Card className="border-border/50">
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                    <Zap className="h-3 w-3" /> PERFORMANCE
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-1">
                  <div className="flex justify-between">
                    <span className="text-xs text-muted-foreground">Balance</span>
                    <span className="text-sm font-mono font-bold">${totalEquity.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-xs text-muted-foreground">P/L</span>
                    <span className={cn("text-sm font-mono", totalPnl >= 0 ? "text-success" : "text-destructive")}>
                      {totalPnl >= 0 ? '+' : ''}${totalPnl.toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-xs text-muted-foreground">Trades</span>
                    <span className="text-sm font-mono">{totalTrades} ({winRate}% win)</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-xs text-muted-foreground">Gas Tank</span>
                    <span className="text-sm font-mono">£{gasTankBalance.toFixed(2)}</span>
                  </div>
                </CardContent>
              </Card>

              {/* Market Data */}
              <Card className="border-border/50">
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                    <Eye className="h-3 w-3" /> MARKET DATA
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-1">
                  <div className="flex justify-between">
                    <span className="text-xs text-muted-foreground">Price</span>
                    <span className="text-sm font-mono font-bold">${marketData.price.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-xs text-muted-foreground">Volatility</span>
                    <span className="text-sm font-mono">{(marketData.volatility * 100).toFixed(2)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-xs text-muted-foreground">Momentum</span>
                    <span className={cn("text-sm font-mono", marketData.momentum >= 0 ? "text-success" : "text-destructive")}>
                      {marketData.momentum >= 0 ? '+' : ''}{(marketData.momentum * 100).toFixed(2)}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-xs text-muted-foreground">Next Check</span>
                    <span className="text-sm font-mono">{nextCheckIn}s</span>
                  </div>
                </CardContent>
              </Card>

              {/* Systems Status */}
              <Card className="border-border/50">
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                    <Brain className="h-3 w-3" /> SYSTEMS
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-1">
                    <SystemIndicator name="Master Equation" active={systemStatus.masterEquation} icon={Activity} />
                    <SystemIndicator name="Lighthouse" active={systemStatus.lighthouse} icon={Radio} />
                    <SystemIndicator name="Rainbow Bridge" active={systemStatus.rainbowBridge} icon={Sparkles} />
                    <SystemIndicator name="Elephant Memory" active={systemStatus.elephantMemory} icon={Database} />
                    <SystemIndicator name="Order Router" active={systemStatus.orderRouter} icon={Router} />
                  </div>
                </CardContent>
              </Card>
            </div>
            
            {/* User Assets Panel */}
            <UserAssetsPanel />

            {/* Last Signal & Recent Trades */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {/* Last Signal */}
              <Card className="border-border/50">
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs font-medium text-muted-foreground">LAST SIGNAL</CardTitle>
                </CardHeader>
                <CardContent>
                  {lastSignal ? (
                    <div className="space-y-2">
                      <p className="text-sm font-mono">{lastSignal}</p>
                      {lastDecision && (
                        <>
                          <p className="text-xs text-muted-foreground">
                            Reason: {lastDecision.finalDecision.reason}
                          </p>
                          <div className="flex gap-2">
                            <Badge variant="outline">Consensus: {consensusSignal}</Badge>
                            <Badge variant="outline">Confidence: {(consensusConfidence * 100).toFixed(0)}%</Badge>
                          </div>
                        </>
                      )}
                    </div>
                  ) : (
                    <p className="text-xs text-muted-foreground text-center py-4">
                      Waiting for first signal...
                    </p>
                  )}
                </CardContent>
              </Card>

              {/* Recent Trades */}
              <Card className="border-border/50">
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs font-medium text-muted-foreground">RECENT TRADES</CardTitle>
                </CardHeader>
                <CardContent>
                  {recentTrades.length === 0 ? (
                    <p className="text-xs text-muted-foreground text-center py-4">
                      No trades yet. Start trading to see activity.
                    </p>
                  ) : (
                    <div className="space-y-2">
                      {recentTrades.slice(0, 5).map((trade, i) => (
                        <div key={i} className="flex items-center justify-between text-xs border-b border-border/30 pb-2 last:border-0">
                          <div className="flex items-center gap-2">
                            <Badge variant={trade.side === 'BUY' ? 'default' : 'secondary'} className="text-[9px]">
                              {trade.side}
                            </Badge>
                            <span className="font-mono">{trade.symbol}</span>
                          </div>
                          <div className="flex items-center gap-3">
                            <span className="text-muted-foreground">{trade.quantity}</span>
                            <span className={cn("font-mono", trade.pnl >= 0 ? "text-success" : "text-destructive")}>
                              {trade.pnl >= 0 ? '+' : ''}{trade.pnl.toFixed(2)}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>
          
          {/* QUANTUM TAB - Shows quantum visualizers, reading from global state */}
          <TabsContent value="quantum" className="mt-4">
            <QuantumTabContent globalState={state} />
          </TabsContent>
          
          {/* SYSTEMS TAB - Shows all system statuses */}
          <TabsContent value="systems" className="mt-4">
            <SystemsTabContent globalState={state} />
          </TabsContent>
          
          {/* ANALYTICS TAB */}
          <TabsContent value="analytics" className="mt-4">
            <AnalyticsTabContent globalState={state} />
          </TabsContent>
        </Tabs>
      </main>
      
      {/* Floating AI Button */}
      <FloatingAIButton />
    </div>
  );
}
