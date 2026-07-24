import { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Key, Lock, CheckCircle2, ExternalLink } from 'lucide-react';
import { useBinanceCredentials } from '@/hooks/useBinanceCredentials';

export const BinanceCredentialsSettings = () => {
  const [apiKey, setApiKey] = useState('');
  const [apiSecret, setApiSecret] = useState('');
  const [saving, setSaving] = useState(false);
  const { hasCredentials, storeCredentials, refreshCredentials } = useBinanceCredentials();

  const handleSave = async () => {
    if (!apiKey.trim() || !apiSecret.trim()) return;
    
    setSaving(true);
    try {
      await storeCredentials([{
        name: 'primary',
        apiKey: apiKey.trim(),
        apiSecret: apiSecret.trim(),
      }]);
      setApiKey('');
      setApiSecret('');
      await refreshCredentials();
    } catch (error) {
      console.error('Failed to store credentials:', error);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card className="p-6">
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold flex items-center gap-2">
              <Key className="h-5 w-5" />
              Binance API Credentials
            </h3>
            <p className="text-sm text-muted-foreground mt-1">
              Securely store your Binance API keys for live trading
            </p>
          </div>
          {hasCredentials && (
            <CheckCircle2 className="h-6 w-6 text-success" />
          )}
        </div>

        <Alert>
          <Lock className="h-4 w-4" />
          <AlertDescription>
            Your API keys are encrypted using AES-256-GCM before storage and never exposed in plain text.
            Only use API keys with <strong>Spot Trading</strong> permissions. Never enable withdrawals.
          </AlertDescription>
        </Alert>

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
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="api-secret">API Secret</Label>
            <Input
              id="api-secret"
              type="password"
              placeholder="Enter your Binance API Secret"
              value={apiSecret}
              onChange={(e) => setApiSecret(e.target.value)}
              disabled={saving}
            />
          </div>

          <Button
            onClick={handleSave}
            disabled={!apiKey.trim() || !apiSecret.trim() || saving}
            className="w-full"
          >
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
  );
};
