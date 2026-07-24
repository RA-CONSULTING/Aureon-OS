import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { supabase } from '@/integrations/supabase/client';
import { useToast } from '@/hooks/use-toast';
import { 
  Shield, RefreshCw, AlertCircle, CheckCircle2, 
  Key, Lock, Pencil, Save, X 
} from 'lucide-react';

interface Credential {
  id: string;
  name: string;
  is_active: boolean;
  created_at: string;
  last_used_at: string | null;
  hasError?: boolean;
}

export function BinanceCredentialsAdmin() {
  const [credentials, setCredentials] = useState<Credential[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [apiKey, setApiKey] = useState('');
  const [apiSecret, setApiSecret] = useState('');
  const { toast } = useToast();

  useEffect(() => {
    fetchCredentials();
  }, []);

  const fetchCredentials = async () => {
    setLoading(true);
    try {
      const { data, error } = await supabase
        .from('binance_credentials')
        .select('*')
        .order('name');

      if (error) throw error;

      // Check balances to see which accounts have errors using authenticated endpoint
      const { data: { session } } = await supabase.auth.getSession();
      let failedAccounts = new Set<string>();
      
      if (session) {
        const balancesResponse = await supabase.functions.invoke('get-user-balances', {
          headers: { Authorization: `Bearer ${session.access_token}` }
        });
        failedAccounts = new Set(
          balancesResponse.data?.balances
            ?.filter((b: any) => b.error)
            ?.map((b: any) => b.exchange) || []
        );
      }

      const enriched = (data || []).map(cred => ({
        ...cred,
        hasError: failedAccounts.has(cred.name)
      }));

      setCredentials(enriched);
    } catch (error: any) {
      console.error('Failed to fetch credentials:', error);
      toast({
        title: '❌ Failed to fetch credentials',
        description: error.message,
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateCredential = async (id: string, name: string) => {
    if (!apiKey.trim() || !apiSecret.trim()) {
      toast({
        title: '⚠️ Invalid input',
        description: 'Both API Key and Secret are required',
        variant: 'destructive',
      });
      return;
    }

    try {
      // Auto-sync: Update ALL bots with the same credentials since they share the same wallet
      const allBotCredentials = credentials.map(cred => ({
        name: cred.name,
        apiKey: apiKey.trim(),
        apiSecret: apiSecret.trim(),
      }));

      const { data, error } = await supabase.functions.invoke('update-bot-credentials', {
        body: {
          credentials: allBotCredentials,
        },
      });

      if (error) throw error;

      const successCount = data?.summary?.successful || 0;
      const totalCount = data?.summary?.total || 0;

      toast({
        title: '✅ All Bots Synced',
        description: `Successfully updated ${successCount}/${totalCount} bots with new credentials`,
      });

      setEditingId(null);
      setApiKey('');
      setApiSecret('');
      await fetchCredentials();
    } catch (error: any) {
      console.error('Failed to update credentials:', error);
      toast({
        title: '❌ Update Failed',
        description: error.message,
        variant: 'destructive',
      });
    }
  };

  const handleToggleActive = async (id: string, currentActive: boolean) => {
    try {
      const { error } = await supabase
        .from('binance_credentials')
        .update({ is_active: !currentActive })
        .eq('id', id);

      if (error) throw error;

      toast({
        title: currentActive ? '⏸️ Deactivated' : '▶️ Activated',
        description: `Credential ${currentActive ? 'deactivated' : 'activated'} successfully`,
      });

      await fetchCredentials();
    } catch (error: any) {
      console.error('Failed to toggle active:', error);
      toast({
        title: '❌ Toggle Failed',
        description: error.message,
        variant: 'destructive',
      });
    }
  };

  return (
    <Card className="p-6">
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold flex items-center gap-2">
              <Shield className="h-5 w-5 text-primary" />
              Binance Credentials Management
            </h3>
            <p className="text-sm text-muted-foreground mt-1">
              Manage and fix bot API credentials
            </p>
          </div>
          <Button onClick={fetchCredentials} disabled={loading} variant="outline" size="sm">
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>

        {/* Info Alert */}
        <Alert className="bg-primary/10 border-primary/20">
          <CheckCircle2 className="h-4 w-4 text-primary" />
          <AlertDescription className="text-primary">
            <strong>🔄 Auto-Sync Enabled</strong> - All {credentials.length} bots share the same wallet.
            Updating any bot will automatically sync credentials to all bots.
          </AlertDescription>
        </Alert>

        {/* Error Alert */}
        {credentials.some(c => c.hasError) && (
          <Alert className="bg-destructive/10 border-destructive/20">
            <AlertCircle className="h-4 w-4 text-destructive" />
            <AlertDescription className="text-destructive">
              <strong>⚠️ Signature Errors Detected</strong> - Some credentials are failing validation.
              Update any bot below to sync new credentials to all bots.
            </AlertDescription>
          </Alert>
        )}

        {/* Credentials List */}
        <div className="space-y-3">
          {loading ? (
            <div className="text-center py-8 text-muted-foreground">
              Loading credentials...
            </div>
          ) : credentials.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No credentials found
            </div>
          ) : (
            credentials.map((cred) => (
              <div
                key={cred.id}
                className={`p-4 rounded-lg border transition-all ${
                  cred.hasError
                    ? 'bg-destructive/5 border-destructive/30 hover:border-destructive/50'
                    : 'bg-muted/30 border-border/30 hover:border-primary/30'
                }`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 space-y-2">
                    <div className="flex items-center gap-3">
                      <span className="font-medium text-sm">{cred.name}</span>
                      {cred.hasError ? (
                        <Badge variant="destructive" className="text-xs">
                          <AlertCircle className="h-3 w-3 mr-1" />
                          Invalid Signature
                        </Badge>
                      ) : cred.is_active ? (
                        <Badge className="bg-success text-xs">
                          <CheckCircle2 className="h-3 w-3 mr-1" />
                          Active
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="text-xs">
                          Inactive
                        </Badge>
                      )}
                    </div>

                    {editingId === cred.id ? (
                      <div className="space-y-3 mt-3">
                        <div className="space-y-2">
                          <div className="flex items-center gap-2">
                            <Key className="h-4 w-4 text-muted-foreground" />
                            <span className="text-xs text-muted-foreground">API Key</span>
                          </div>
                          <Input
                            type="text"
                            placeholder="Enter API Key"
                            value={apiKey}
                            onChange={(e) => setApiKey(e.target.value)}
                            className="font-mono text-sm"
                          />
                        </div>
                        <div className="space-y-2">
                          <div className="flex items-center gap-2">
                            <Lock className="h-4 w-4 text-muted-foreground" />
                            <span className="text-xs text-muted-foreground">API Secret</span>
                          </div>
                          <Input
                            type="password"
                            placeholder="Enter API Secret"
                            value={apiSecret}
                            onChange={(e) => setApiSecret(e.target.value)}
                            className="font-mono text-sm"
                          />
                        </div>
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            onClick={() => handleUpdateCredential(cred.id, cred.name)}
                            disabled={!apiKey.trim() || !apiSecret.trim()}
                          >
                            <Save className="h-4 w-4 mr-2" />
                            Sync All Bots
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => {
                              setEditingId(null);
                              setApiKey('');
                              setApiSecret('');
                            }}
                          >
                            <X className="h-4 w-4 mr-2" />
                            Cancel
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-center gap-4 text-xs text-muted-foreground">
                        <span>Created: {new Date(cred.created_at).toLocaleDateString()}</span>
                        {cred.last_used_at && (
                          <span>Last used: {new Date(cred.last_used_at).toLocaleDateString()}</span>
                        )}
                      </div>
                    )}
                  </div>

                  {editingId !== cred.id && (
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        variant={cred.hasError ? 'default' : 'outline'}
                        onClick={() => setEditingId(cred.id)}
                      >
                        <Pencil className="h-4 w-4 mr-2" />
                        {cred.hasError ? 'Fix' : 'Edit'}
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleToggleActive(cred.id, cred.is_active)}
                      >
                        {cred.is_active ? 'Disable' : 'Enable'}
                      </Button>
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>

        <Alert>
          <Lock className="h-4 w-4" />
          <AlertDescription>
            <strong>🔐 Security:</strong> All credentials are encrypted with AES-256-GCM before storage.
            <br />
            <strong>🔄 Auto-Sync:</strong> Updating any bot automatically syncs credentials to all {credentials.length} bots
            since they all access the same wallet.
          </AlertDescription>
        </Alert>
      </div>
    </Card>
  );
}
