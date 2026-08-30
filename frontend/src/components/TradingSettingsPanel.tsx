import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Key, 
  Lock, 
  CheckCircle2, 
  ExternalLink,
  Settings,
  Shield,
  Eye,
  EyeOff
} from 'lucide-react';
import { supabase } from '@/integrations/supabase/client';
import { toast } from 'sonner';
import { LiveTradingTestPanel } from './LiveTradingTestPanel';

export const TradingSettingsPanel = () => {
  const [apiKey, setApiKey] = useState('');
  const [apiSecret, setApiSecret] = useState('');
  const [saving, setSaving] = useState(false);
  const [hasCredentials, setHasCredentials] = useState(false);
  const [showSecret, setShowSecret] = useState(false);
  const [userId, setUserId] = useState<string | undefined>();

  useEffect(() => {
    checkCredentials();
  }, []);

  const checkCredentials = async () => {
    try {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) return;
      
      setUserId(user.id);

      // Check user_binance_credentials table
      const { data: credentials } = await supabase
        .from('user_binance_credentials')
        .select('id')
        .eq('user_id', user.id)
        .single();

      setHasCredentials(!!credentials);
    } catch (error) {
      console.error('Failed to check credentials:', error);
    }
  };

  const handleSave = async () => {
    if (!apiKey.trim() || !apiSecret.trim()) {
      toast.error('Please enter both API Key and Secret');
      return;
    }

    const { data: { user } } = await supabase.auth.getUser();
    if (!user) {
      toast.error('Please log in first');
      return;
    }

    setSaving(true);
    try {
      const { data, error } = await supabase.functions.invoke('store-binance-credentials', {
        body: {
          userId: user.id,
          apiKey: apiKey.trim(),
          apiSecret: apiSecret.trim()
        }
      });

      if (error) throw error;

      toast.success('Binance credentials stored securely');
      setApiKey('');
      setApiSecret('');
      setHasCredentials(true);
      await checkCredentials();
    } catch (error) {
      console.error('Failed to store credentials:', error);
      toast.error('Failed to store credentials');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <Tabs defaultValue="credentials" className="w-full">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="credentials" className="flex items-center gap-2">
            <Key className="h-4 w-4" />
            API Credentials
          </TabsTrigger>
          <TabsTrigger value="test" className="flex items-center gap-2">
            <Settings className="h-4 w-4" />
            Live Test
          </TabsTrigger>
        </TabsList>

        <TabsContent value="credentials" className="mt-4">
          <Card className="p-6">
            <div className="space-y-6">
              {/* Header */}
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold flex items-center gap-2">
                    <Key className="h-5 w-5" />
                    Binance API Credentials
                  </h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    Store your Binance API keys for live trading
                  </p>
                </div>
                <Badge variant={hasCredentials ? "default" : "secondary"}>
                  {hasCredentials ? (
                    <><CheckCircle2 className="h-3 w-3 mr-1" /> Configured</>
                  ) : (
                    'Not Configured'
                  )}
                </Badge>
              </div>

              {/* Security Notice */}
              <Alert>
                <Lock className="h-4 w-4" />
                <AlertDescription>
                  Your API keys are encrypted using AES-256-GCM before storage.
                  Only use keys with <strong>Spot Trading</strong> permissions.
                  <strong className="text-destructive"> Never enable withdrawals.</strong>
                </AlertDescription>
              </Alert>

              {/* Credential Inputs */}
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="api-key">API Key</Label>
                  <Input
                    id="api-key"
                    type="text"
                    placeholder="Enter your Binance API Key"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    disabled={saving}
                    className="font-mono"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="api-secret">API Secret</Label>
                  <div className="relative">
                    <Input
                      id="api-secret"
                      type={showSecret ? "text" : "password"}
                      placeholder="Enter your Binance API Secret"
                      value={apiSecret}
                      onChange={(e) => setApiSecret(e.target.value)}
                      disabled={saving}
                      className="font-mono pr-10"
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="absolute right-0 top-0 h-full px-3"
                      onClick={() => setShowSecret(!showSecret)}
                    >
                      {showSecret ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </Button>
                  </div>
                </div>

                <Button
                  onClick={handleSave}
                  disabled={!apiKey.trim() || !apiSecret.trim() || saving}
                  className="w-full"
                >
                  <Shield className="mr-2 h-4 w-4" />
                  {saving ? 'Encrypting & Storing...' : hasCredentials ? 'Update Credentials' : 'Store Credentials'}
                </Button>

                <Button
                  variant="outline"
                  className="w-full"
                  asChild
                >
                  <a
                    href="https://www.binance.com/en/my/settings/api-management"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <ExternalLink className="h-4 w-4 mr-2" />
                    Get API Keys from Binance
                  </a>
                </Button>
              </div>

              {/* Status */}
              {hasCredentials && (
                <Alert className="bg-success/10 border-success/20">
                  <CheckCircle2 className="h-4 w-4 text-success" />
                  <AlertDescription className="text-success">
                    ✓ Credentials configured and ready for live trading
                  </AlertDescription>
                </Alert>
              )}
            </div>
          </Card>
        </TabsContent>

        <TabsContent value="test" className="mt-4">
          <LiveTradingTestPanel 
            hasCredentials={hasCredentials} 
            userId={userId}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
};
