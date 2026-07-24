import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Wifi, WifiOff, RefreshCw, AlertCircle, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";

interface BinanceConnectionStatusProps {
  isConnected: boolean;
  isHealthy: boolean;
  reconnectAttempts: number;
  onReconnect?: () => void;
  lastError?: string | null;
}

export function BinanceConnectionStatus({
  isConnected,
  isHealthy,
  reconnectAttempts,
  onReconnect,
  lastError
}: BinanceConnectionStatusProps) {
  const getStatusColor = () => {
    if (!isConnected) return 'text-destructive';
    if (!isHealthy) return 'text-warning';
    return 'text-success';
  };

  const getStatusText = () => {
    if (!isConnected) return 'DISCONNECTED';
    if (!isHealthy) return 'UNSTABLE';
    return 'CONNECTED';
  };

  const getStatusIcon = () => {
    if (!isConnected) return <WifiOff className="h-4 w-4" />;
    if (!isHealthy) return <AlertCircle className="h-4 w-4" />;
    return <CheckCircle2 className="h-4 w-4" />;
  };

  return (
    <Card className="bg-card/50 backdrop-blur border-border/50">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span className="flex items-center gap-2">
            <Wifi className="h-5 w-5" />
            Binance Connection Status
          </span>
          <Badge variant={isConnected && isHealthy ? "default" : "destructive"} className="gap-2">
            {getStatusIcon()}
            {getStatusText()}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div className="p-3 rounded-lg border border-border bg-muted/20">
            <div className="flex items-center gap-2 mb-1">
              <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-success' : 'bg-destructive'} animate-pulse`} />
              <span className="text-xs text-muted-foreground">WebSocket</span>
            </div>
            <p className={`text-sm font-semibold ${getStatusColor()}`}>
              {isConnected ? 'Active' : 'Inactive'}
            </p>
          </div>

          <div className="p-3 rounded-lg border border-border bg-muted/20">
            <div className="flex items-center gap-2 mb-1">
              <div className={`w-2 h-2 rounded-full ${isHealthy ? 'bg-success' : 'bg-warning'}`} />
              <span className="text-xs text-muted-foreground">Health</span>
            </div>
            <p className={`text-sm font-semibold ${getStatusColor()}`}>
              {isHealthy ? 'Good' : 'Poor'}
            </p>
          </div>

          <div className="p-3 rounded-lg border border-border bg-muted/20">
            <div className="flex items-center gap-2 mb-1">
              <RefreshCw className="h-3 w-3 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">Reconnect Attempts</span>
            </div>
            <p className="text-sm font-semibold">{reconnectAttempts}/10</p>
          </div>

          <div className="p-3 rounded-lg border border-border bg-muted/20">
            <div className="flex items-center gap-2 mb-1">
              <Wifi className="h-3 w-3 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">Data Stream</span>
            </div>
            <p className="text-sm font-semibold">
              {isConnected ? 'Real-time' : 'Offline'}
            </p>
          </div>
        </div>

        {lastError && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription className="text-xs">
              {lastError}
            </AlertDescription>
          </Alert>
        )}

        {(!isConnected || !isHealthy) && onReconnect && (
          <Button 
            onClick={onReconnect} 
            className="w-full gap-2"
            variant={isConnected ? "outline" : "default"}
          >
            <RefreshCw className="h-4 w-4" />
            Force Reconnect
          </Button>
        )}

        <div className="text-xs text-muted-foreground space-y-1">
          <p>• Connection: wss://stream.binance.com:443</p>
          <p>• Streams: aggTrade, depth, miniTicker</p>
          <p>• Health check: Every 30s</p>
          <p>• Auto-reconnect: Max 30s delay</p>
          <p>• Timeout: 10s per connection attempt</p>
        </div>
      </CardContent>
    </Card>
  );
}
