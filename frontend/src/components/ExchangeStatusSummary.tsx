import { useState, useEffect } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { supabase } from '@/integrations/supabase/client';
import { useNavigate } from 'react-router-dom';
import { Wallet, Settings, CheckCircle2, AlertCircle } from 'lucide-react';

interface ExchangeStatus {
  binance: boolean;
  kraken: boolean;
  alpaca: boolean;
  capital: boolean;
}

export function ExchangeStatusSummary() {
  const navigate = useNavigate();
  const [status, setStatus] = useState<ExchangeStatus>({
    binance: false,
    kraken: false,
    alpaca: false,
    capital: false
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkCredentials();
  }, []);

  const checkCredentials = async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) return;

      const { data } = await supabase
        .from('aureon_user_sessions')
        .select('binance_api_key_encrypted, kraken_api_key_encrypted, alpaca_api_key_encrypted, capital_api_key_encrypted')
        .eq('user_id', session.user.id)
        .single();

      if (data) {
        setStatus({
          binance: !!data.binance_api_key_encrypted,
          kraken: !!data.kraken_api_key_encrypted,
          alpaca: !!data.alpaca_api_key_encrypted,
          capital: !!data.capital_api_key_encrypted
        });
      }
    } catch (err) {
      console.error('Error checking credentials:', err);
    } finally {
      setLoading(false);
    }
  };

  const connectedCount = Object.values(status).filter(Boolean).length;
  const hasAnyConnected = connectedCount > 0;

  if (loading) return null;

  return (
    <Card className={`border ${hasAnyConnected ? 'border-success/30' : 'border-warning/30 bg-warning/5'}`}>
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${hasAnyConnected ? 'bg-success/10' : 'bg-warning/10'}`}>
              <Wallet className={`h-5 w-5 ${hasAnyConnected ? 'text-success' : 'text-warning'}`} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-medium">Exchange Connections</span>
                {hasAnyConnected ? (
                  <CheckCircle2 className="h-4 w-4 text-success" />
                ) : (
                  <AlertCircle className="h-4 w-4 text-warning" />
                )}
              </div>
              <div className="flex gap-1.5 mt-1">
                <Badge variant={status.binance ? 'default' : 'outline'} className={`text-xs ${status.binance ? 'bg-warning' : ''}`}>
                  Binance
                </Badge>
                <Badge variant={status.kraken ? 'default' : 'outline'} className={`text-xs ${status.kraken ? 'bg-primary' : ''}`}>
                  Kraken
                </Badge>
                <Badge variant={status.alpaca ? 'default' : 'outline'} className={`text-xs ${status.alpaca ? 'bg-primary' : ''}`}>
                  Alpaca
                </Badge>
                <Badge variant={status.capital ? 'default' : 'outline'} className={`text-xs ${status.capital ? 'bg-primary' : ''}`}>
                  Capital
                </Badge>
              </div>
            </div>
          </div>
          
          <Button 
            variant={hasAnyConnected ? 'outline' : 'default'}
            size="sm"
            onClick={() => navigate('/settings')}
          >
            <Settings className="h-4 w-4 mr-2" />
            {hasAnyConnected ? 'Manage' : 'Connect'}
          </Button>
        </div>
        
        {!hasAnyConnected && (
          <p className="text-xs text-muted-foreground mt-3 pl-12">
            Connect at least one exchange to start trading
          </p>
        )}
      </CardContent>
    </Card>
  );
}
