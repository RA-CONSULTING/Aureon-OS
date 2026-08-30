import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Loader2, CheckCircle2, XCircle, RefreshCw, Key } from 'lucide-react';
import { supabase } from '@/integrations/supabase/client';
import { useToast } from '@/hooks/use-toast';
import { Link } from 'react-router-dom';

interface ExchangeStatus {
  name: string;
  configured: boolean;
  connected: boolean | null;
  loading: boolean;
  lastChecked: Date | null;
}

interface CredentialStatusPanelProps {
  userId?: string | null;
}

export function CredentialStatusPanel({ userId }: CredentialStatusPanelProps) {
  const [exchanges, setExchanges] = useState<ExchangeStatus[]>([
    { name: 'Binance', configured: false, connected: null, loading: false, lastChecked: null },
    { name: 'Kraken', configured: false, connected: null, loading: false, lastChecked: null },
    { name: 'Alpaca', configured: false, connected: null, loading: false, lastChecked: null },
    { name: 'Capital.com', configured: false, connected: null, loading: false, lastChecked: null },
  ]);
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();

  // Check which exchanges have credentials
  useEffect(() => {
    async function checkCredentials() {
      if (!userId) {
        setLoading(false);
        return;
      }

      const { data } = await supabase
        .from('aureon_user_sessions')
        .select('binance_api_key_encrypted, kraken_api_key_encrypted, alpaca_api_key_encrypted, capital_api_key_encrypted')
        .eq('user_id', userId)
        .single();

      if (data) {
        setExchanges(prev => prev.map(ex => {
          switch (ex.name) {
            case 'Binance':
              return { ...ex, configured: !!data.binance_api_key_encrypted };
            case 'Kraken':
              return { ...ex, configured: !!data.kraken_api_key_encrypted };
            case 'Alpaca':
              return { ...ex, configured: !!data.alpaca_api_key_encrypted };
            case 'Capital.com':
              return { ...ex, configured: !!data.capital_api_key_encrypted };
            default:
              return ex;
          }
        }));
      }
      setLoading(false);
    }

    checkCredentials();
  }, [userId]);

  const testConnection = async (exchangeName: string) => {
    setExchanges(prev => prev.map(ex => 
      ex.name === exchangeName ? { ...ex, loading: true } : ex
    ));

    try {
      const { data, error } = await supabase.functions.invoke('test-exchange-connection', {
        body: { exchange: exchangeName.toLowerCase().replace('.', '') }
      });

      setExchanges(prev => prev.map(ex => 
        ex.name === exchangeName 
          ? { 
              ...ex, 
              loading: false, 
              connected: !error && data?.success, 
              lastChecked: new Date() 
            } 
          : ex
      ));

      if (error || !data?.success) {
        toast({
          title: `${exchangeName} Connection Failed`,
          description: data?.error || 'Unable to connect to exchange',
          variant: 'destructive',
        });
      } else {
        toast({
          title: `${exchangeName} Connected!`,
          description: `Balance: $${data?.balance?.toFixed(2) || 'N/A'}`,
        });
      }
    } catch (err) {
      setExchanges(prev => prev.map(ex => 
        ex.name === exchangeName 
          ? { ...ex, loading: false, connected: false, lastChecked: new Date() } 
          : ex
      ));
    }
  };

  const testAllConnections = () => {
    exchanges.filter(ex => ex.configured).forEach(ex => {
      testConnection(ex.name);
    });
  };

  const configuredCount = exchanges.filter(ex => ex.configured).length;
  const connectedCount = exchanges.filter(ex => ex.connected === true).length;

  if (loading) {
    return (
      <Card className="bg-card/50 backdrop-blur border-primary/20">
        <CardContent className="p-6 flex items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-card/50 backdrop-blur border-primary/20">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between text-base">
          <span className="flex items-center gap-2">
            <Key className="h-4 w-4" />
            Exchange Credentials
          </span>
          <div className="flex items-center gap-2">
            <Badge variant={configuredCount > 0 ? 'default' : 'secondary'}>
              {configuredCount}/4 configured
            </Badge>
            <Button
              variant="ghost"
              size="icon"
              onClick={testAllConnections}
              disabled={configuredCount === 0}
              className="h-7 w-7"
            >
              <RefreshCw className="h-3.5 w-3.5" />
            </Button>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {exchanges.map(exchange => (
          <div
            key={exchange.name}
            className="flex items-center justify-between p-2 rounded-lg bg-background/50"
          >
            <div className="flex items-center gap-2">
              {exchange.loading ? (
                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
              ) : exchange.connected === true ? (
                <CheckCircle2 className="h-4 w-4 text-success" />
              ) : exchange.connected === false ? (
                <XCircle className="h-4 w-4 text-destructive" />
              ) : exchange.configured ? (
                <div className="h-4 w-4 rounded-full bg-warning/50 border border-warning" />
              ) : (
                <div className="h-4 w-4 rounded-full bg-muted border border-muted-foreground/30" />
              )}
              <span className="text-sm font-medium">{exchange.name}</span>
            </div>
            
            <div className="flex items-center gap-2">
              {exchange.configured ? (
                <>
                  <Badge variant="outline" className="text-xs">
                    {exchange.connected === true ? ' LIVE' : exchange.connected === false ? ' OFFLINE' : ' Untested'}
                  </Badge>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => testConnection(exchange.name)}
                    disabled={exchange.loading}
                    className="h-7 text-xs"
                  >
                    Test
                  </Button>
                </>
              ) : (
                <Button variant="outline" size="sm" asChild className="h-7 text-xs">
                  <Link to="/settings">Configure</Link>
                </Button>
              )}
            </div>
          </div>
        ))}
        
        {configuredCount === 0 && (
          <div className="text-center py-4">
            <p className="text-sm text-muted-foreground mb-3">
              No exchange credentials configured. Add your API keys to enable live trading.
            </p>
            <Button asChild>
              <Link to="/settings">Configure API Keys</Link>
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
