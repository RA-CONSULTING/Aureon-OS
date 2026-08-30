import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useBinanceCredentials } from '@/hooks/useBinanceCredentials';
import { useToast } from '@/hooks/use-toast';
import { Key, RefreshCw, Upload } from 'lucide-react';

export function CredentialManager() {
  const { credentialsCount, activeCount, refreshCredentials } = useBinanceCredentials();
  const { toast } = useToast();

  const handleRefresh = async () => {
    await refreshCredentials();
    toast({
      title: '✅ Credentials Refreshed',
      description: `${activeCount} active accounts`,
    });
  };

  return (
    <Card className="p-6">
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold flex items-center gap-2">
              <Key className="h-5 w-5" />
              Multi-Account Trading Pool
            </h3>
            <p className="text-sm text-muted-foreground">
              Testnet API credentials for parallel trading
            </p>
          </div>
          <Button onClick={handleRefresh} variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="p-4 rounded-lg bg-muted/50">
            <div className="text-2xl font-bold">{credentialsCount}</div>
            <div className="text-xs text-muted-foreground">Total Accounts</div>
          </div>
          <div className="p-4 rounded-lg bg-muted/50">
            <div className="text-2xl font-bold text-success">{activeCount}</div>
            <div className="text-xs text-muted-foreground">Active Accounts</div>
          </div>
        </div>

        {credentialsCount > 0 && (
          <div className="flex items-center gap-2">
            <Badge className="bg-success">
              <Upload className="h-3 w-3 mr-1" />
              {credentialsCount} Accounts Loaded
            </Badge>
            <Badge variant="outline">
              Max {credentialsCount * 50} trades/min
            </Badge>
          </div>
        )}
      </div>
    </Card>
  );
}
