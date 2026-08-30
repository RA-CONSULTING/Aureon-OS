import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { supabase } from '@/integrations/supabase/client';
import { toast } from 'sonner';
import { Eye, EyeOff, Key, CheckCircle2, XCircle, RefreshCw, Save, Zap, Loader2, ExternalLink } from 'lucide-react';

interface ExchangeStatus {
  binance: boolean;
  kraken: boolean;
  alpaca: boolean;
  capital: boolean;
}

interface TestResult {
  success: boolean;
  message: string;
  details?: Record<string, any>;
}

interface LocalEnvCredentialStatus {
  ok?: boolean;
  env_file?: string;
  restart_required?: boolean;
  secret_policy?: string;
  hnc_packet_encryption?: {
    enabled?: boolean;
    format?: string;
    encoded_key_count?: number;
    encoded_keys?: string[];
    master_key_present?: boolean;
    evidence_file?: string;
    policy?: string;
  };
  credential_status?: LocalEnvCredentialStatus;
  exchanges?: Record<string, {
    present?: boolean;
    missing_keys?: string[];
    keys?: Record<string, { set?: boolean; length?: number; secret?: boolean }>;
  }>;
}

interface RuntimeExchangeSnapshot {
  generated_at?: string;
  tick_phase?: string;
  exchanges?: Record<string, boolean>;
}

interface ExchangeOnboarding {
  name: keyof ExchangeStatus;
  label: string;
  description: string;
  runs: string;
  requiredKeys: string[];
  setupUrl: string;
  docsUrl: string;
  permissionHint: string;
}

const exchangeOnboarding: ExchangeOnboarding[] = [
  {
    name: 'binance',
    label: 'Binance',
    description: 'Crypto spot and live market stream coverage',
    runs: 'Crypto symbols, websocket market data, signal confirmation, and order-intent routes.',
    requiredKeys: ['BINANCE_API_KEY', 'BINANCE_API_SECRET'],
    setupUrl: 'https://www.binance.com/en/my/settings/api-management',
    docsUrl: 'https://developers.binance.com/docs/binance-spot-api-docs',
    permissionHint: 'Enable read and trading permissions only. Keep withdrawals disabled.',
  },
  {
    name: 'kraken',
    label: 'Kraken',
    description: 'Crypto spot and margin-ready routes',
    runs: 'GBP/EUR crypto balance checks, spot/margin candidates, cost-aware profit capture, and Kraken tick phases.',
    requiredKeys: ['KRAKEN_API_KEY', 'KRAKEN_API_SECRET'],
    setupUrl: 'https://support.kraken.com/articles/how-to-create-an-api-key-on-kraken-pro',
    docsUrl: 'https://docs.kraken.com/api/',
    permissionHint: 'Use trading/query permissions needed by Aureon. Do not enable withdrawals.',
  },
  {
    name: 'alpaca',
    label: 'Alpaca',
    description: 'US stocks and crypto market access',
    runs: 'US equities, market data, stock/crypto candidates, and portfolio-side opportunity checks.',
    requiredKeys: ['ALPACA_API_KEY', 'ALPACA_SECRET_KEY'],
    setupUrl: 'https://docs.alpaca.markets/docs/getting-started-with-alpaca-api',
    docsUrl: 'https://docs.alpaca.markets/',
    permissionHint: 'Choose paper or live keys intentionally and keep the account scope minimal.',
  },
  {
    name: 'capital',
    label: 'Capital.com',
    description: 'CFDs, forex, indices, commodities, and stocks where available',
    runs: 'Capital account balance, open positions, fast profit closure checks, CFD/forex candidates, and WebSocket price streams.',
    requiredKeys: ['CAPITAL_API_KEY', 'CAPITAL_IDENTIFIER', 'CAPITAL_PASSWORD'],
    setupUrl: 'https://help.capital.com/hc/en-us/articles/6630772720402-How-to-start-using-Capital-com-API',
    docsUrl: 'https://open-api.capital.com/',
    permissionHint: 'Generate the API key in Settings > API integrations and use the matching account credentials.',
  },
];

async function runtimeCredentialEndpoints(): Promise<string[]> {
  const endpoints = new Set<string>();
  try {
    const response = await fetch('/aureon_wake_up_manifest.json', { cache: 'no-store' });
    if (response.ok) {
      const manifest = await response.json();
      const feed = String(manifest?.runtime_feed_url || '');
      if (feed) endpoints.add(feed.replace(/\/api\/terminal-state$/, '/api/env-credentials'));
    }
  } catch {
    // Fall through to the standard local ports.
  }
  endpoints.add('http://127.0.0.1:8791/api/env-credentials');
  endpoints.add('http://127.0.0.1:8790/api/env-credentials');
  return Array.from(endpoints);
}

async function loadLocalEnvCredentialStatus(): Promise<LocalEnvCredentialStatus | null> {
  for (const endpoint of await runtimeCredentialEndpoints()) {
    try {
      const response = await fetch(endpoint, { cache: 'no-store' });
      if (!response.ok) continue;
      return await response.json();
    } catch {
      // Try the next runtime endpoint.
    }
  }
  return null;
}

async function saveLocalEnvCredentials(exchange: string, credentials: Record<string, string>): Promise<LocalEnvCredentialStatus> {
  let lastError = 'local runtime credential endpoint unavailable';
  for (const endpoint of await runtimeCredentialEndpoints()) {
    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Aureon-Local-Operator': '1',
        },
        body: JSON.stringify({ exchange, credentials }),
      });
      const payload = await response.json().catch(() => ({}));
      if (response.ok && payload?.ok) return payload;
      lastError = String(payload?.error || response.statusText || lastError);
    } catch (error) {
      lastError = error instanceof Error ? error.message : lastError;
    }
  }
  throw new Error(lastError);
}

async function runtimeTerminalEndpoints(): Promise<string[]> {
  const endpoints = new Set<string>();
  try {
    const response = await fetch('/aureon_wake_up_manifest.json', { cache: 'no-store' });
    if (response.ok) {
      const manifest = await response.json();
      const feed = String(manifest?.runtime_feed_url || '');
      if (feed) endpoints.add(feed);
    }
  } catch {
    // Fall through to the standard local ports.
  }
  endpoints.add('http://127.0.0.1:8791/api/terminal-state');
  endpoints.add('http://127.0.0.1:8790/api/terminal-state');
  return Array.from(endpoints);
}

async function loadRuntimeExchangeSnapshot(): Promise<RuntimeExchangeSnapshot | null> {
  for (const endpoint of await runtimeTerminalEndpoints()) {
    try {
      const response = await fetch(endpoint, { cache: 'no-store' });
      if (!response.ok) continue;
      const payload = await response.json();
      const exchanges = payload?.exchanges || {};
      return {
        generated_at: payload?.generated_at || payload?.dashboard_generated_at,
        tick_phase: payload?.tick_phase,
        exchanges: {
          binance: Boolean(exchanges.binance_ready),
          kraken: Boolean(exchanges.kraken_ready),
          alpaca: Boolean(exchanges.alpaca_ready),
          capital: Boolean(exchanges.capital_ready),
        },
      };
    } catch {
      // Try the next runtime endpoint.
    }
  }
  return null;
}

export function ExchangeCredentialsManager() {
  const [loading, setLoading] = useState(false);
  const [checking, setChecking] = useState(true);
  const [testing, setTesting] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, TestResult>>({});
  const [localEnvStatus, setLocalEnvStatus] = useState<LocalEnvCredentialStatus | null>(null);
  const [localEnvError, setLocalEnvError] = useState('');
  const [runtimeExchangeStatus, setRuntimeExchangeStatus] = useState<RuntimeExchangeSnapshot | null>(null);
  const [status, setStatus] = useState<ExchangeStatus>({
    binance: false,
    kraken: false,
    alpaca: false,
    capital: false
  });

  // Credential inputs
  const [binanceApiKey, setBinanceApiKey] = useState('');
  const [binanceApiSecret, setBinanceApiSecret] = useState('');
  const [krakenApiKey, setKrakenApiKey] = useState('');
  const [krakenApiSecret, setKrakenApiSecret] = useState('');
  const [alpacaApiKey, setAlpacaApiKey] = useState('');
  const [alpacaSecretKey, setAlpacaSecretKey] = useState('');
  const [capitalApiKey, setCapitalApiKey] = useState('');
  const [capitalPassword, setCapitalPassword] = useState('');
  const [capitalIdentifier, setCapitalIdentifier] = useState('');

  // Visibility toggles
  const [showSecrets, setShowSecrets] = useState<Record<string, boolean>>({});

  useEffect(() => {
    checkExistingCredentials();
  }, []);

  const checkExistingCredentials = async () => {
    setChecking(true);
    try {
      const [local, runtime] = await Promise.all([
        loadLocalEnvCredentialStatus(),
        loadRuntimeExchangeSnapshot(),
      ]);
      setLocalEnvStatus(local);
      setRuntimeExchangeStatus(runtime);
      setLocalEnvError(local ? '' : 'Local .env runtime endpoint is not available yet');
      const localStatus: ExchangeStatus = {
        binance: Boolean(local?.exchanges?.binance?.present),
        kraken: Boolean(local?.exchanges?.kraken?.present),
        alpaca: Boolean(local?.exchanges?.alpaca?.present),
        capital: Boolean(local?.exchanges?.capital?.present),
      };
      let mergedStatus = localStatus;

      const { data: { session } } = await supabase.auth.getSession();
      if (session) {
        const { data } = await supabase
          .from('aureon_user_sessions')
          .select('binance_api_key_encrypted, kraken_api_key_encrypted, alpaca_api_key_encrypted, capital_api_key_encrypted')
          .eq('user_id', session.user.id)
          .single();

        if (data) {
          mergedStatus = {
            binance: localStatus.binance || !!data.binance_api_key_encrypted,
            kraken: localStatus.kraken || !!data.kraken_api_key_encrypted,
            alpaca: localStatus.alpaca || !!data.alpaca_api_key_encrypted,
            capital: localStatus.capital || !!data.capital_api_key_encrypted
          };
        }
      }
      setStatus(mergedStatus);
    } catch (err) {
      console.error('Error checking credentials:', err);
    } finally {
      setChecking(false);
    }
  };

  const testConnection = async (exchange: string) => {
    let apiKey = '';
    let apiSecret = '';
    let identifier = '';
    let password = '';

    switch (exchange) {
      case 'binance':
        apiKey = binanceApiKey;
        apiSecret = binanceApiSecret;
        break;
      case 'kraken':
        apiKey = krakenApiKey;
        apiSecret = krakenApiSecret;
        break;
      case 'alpaca':
        apiKey = alpacaApiKey;
        apiSecret = alpacaSecretKey;
        break;
      case 'capital':
        apiKey = capitalApiKey;
        password = capitalPassword;
        identifier = capitalIdentifier;
        break;
    }

    if (!apiKey || (!apiSecret && exchange !== 'capital') || (exchange === 'capital' && !password)) {
      toast.error('Please enter credentials first');
      return;
    }

    setTesting(exchange);
    try {
      const { data, error } = await supabase.functions.invoke('test-exchange-connection', {
        body: { exchange, apiKey, apiSecret, identifier, password }
      });

      if (error) throw error;

      setTestResults(prev => ({ ...prev, [exchange]: data }));

      if (data.success) {
        toast.success(`${exchange} connection verified!`);
      } else {
        toast.error(data.message || `${exchange} connection failed`);
      }
    } catch (err) {
      console.error('Connection test error:', err);
      setTestResults(prev => ({ 
        ...prev, 
        [exchange]: { success: false, message: 'Test failed - network error' } 
      }));
      toast.error('Connection test failed');
    } finally {
      setTesting(null);
    }
  };

  const handleSaveCredentials = async (exchange: string) => {
    setLoading(true);
    try {
      let body: Record<string, string> = {};

      switch (exchange) {
        case 'binance':
          if (!binanceApiKey || !binanceApiSecret) {
            toast.error('Both API Key and Secret are required');
            return;
          }
          body = { binanceApiKey, binanceApiSecret };
          break;
        case 'kraken':
          if (!krakenApiKey || !krakenApiSecret) {
            toast.error('Both API Key and Secret are required');
            return;
          }
          body = { krakenApiKey, krakenApiSecret };
          break;
        case 'alpaca':
          if (!alpacaApiKey || !alpacaSecretKey) {
            toast.error('Both API Key and Secret are required');
            return;
          }
          body = { alpacaApiKey, alpacaSecretKey };
          break;
        case 'capital':
          if (!capitalApiKey || !capitalPassword) {
            toast.error('API Key and Password are required');
            return;
          }
          body = { capitalApiKey, capitalPassword, capitalIdentifier };
          break;
      }

      const localResult = await saveLocalEnvCredentials(exchange, body);
      setLocalEnvStatus(localResult.credential_status || localResult);
      setLocalEnvError('');

      let cloudSaved = false;
      const { data: { session } } = await supabase.auth.getSession();
      if (session) {
        try {
          const { error } = await supabase.functions.invoke('update-user-credentials', {
            body
          });
          if (error) throw error;
          cloudSaved = true;
        } catch (cloudError) {
          console.warn('Saved to local .env, but user-vault sync failed:', cloudError);
        }
      }

      toast.success(
        `${exchange.charAt(0).toUpperCase() + exchange.slice(1)} credentials saved to local .env${cloudSaved ? ' and user vault' : ''}. Restart is queued.`
      );
      
      // Clear inputs and refresh status
      switch (exchange) {
        case 'binance':
          setBinanceApiKey('');
          setBinanceApiSecret('');
          break;
        case 'kraken':
          setKrakenApiKey('');
          setKrakenApiSecret('');
          break;
        case 'alpaca':
          setAlpacaApiKey('');
          setAlpacaSecretKey('');
          break;
        case 'capital':
          setCapitalApiKey('');
          setCapitalPassword('');
          setCapitalIdentifier('');
          break;
      }
      
      // Clear test result for this exchange
      setTestResults(prev => {
        const updated = { ...prev };
        delete updated[exchange];
        return updated;
      });
      
      await checkExistingCredentials();
    } catch (err) {
      console.error('Error saving credentials:', err);
      toast.error('Failed to save credentials. Please check encryption key configuration.');
    } finally {
      setLoading(false);
    }
  };

  const toggleSecret = (key: string) => {
    setShowSecrets(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const ExchangeCard = ({ 
    name, 
    label, 
    description,
    onboarding,
    isConnected,
    apiKeyValue,
    apiKeyOnChange,
    secretValue,
    secretOnChange,
    secretLabel = 'API Secret',
    secretKey,
    extraFields
  }: {
    name: keyof ExchangeStatus;
    label: string;
    description: string;
    isConnected: boolean;
    apiKeyValue: string;
    apiKeyOnChange: (v: string) => void;
    secretValue: string;
    secretOnChange: (v: string) => void;
    secretLabel?: string;
    secretKey: string;
    extraFields?: React.ReactNode;
    onboarding: ExchangeOnboarding;
  }) => {
    const testResult = testResults[name];
    const isTesting = testing === name;
    const runtimeFiring = Boolean(runtimeExchangeStatus?.exchanges?.[name]);
    const envMissing = localEnvStatus?.exchanges?.[name]?.missing_keys || onboarding.requiredKeys;

    return (
      <Card className={`border ${isConnected ? 'border-success/30 bg-success/5' : 'border-border'}`}>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base flex items-center gap-2">
                <Key className="h-4 w-4" />
                {label}
              </CardTitle>
              <CardDescription className="text-xs">{description}</CardDescription>
            </div>
            <div className="flex flex-col items-end gap-1">
              <Badge variant={isConnected ? 'default' : 'secondary'} className={isConnected ? 'bg-success' : ''}>
                {isConnected ? (
                  <><CheckCircle2 className="h-3 w-3 mr-1" /> .env ready</>
                ) : (
                  <><XCircle className="h-3 w-3 mr-1" /> missing keys</>
                )}
              </Badge>
              <Badge variant={runtimeFiring ? 'default' : 'outline'} className={runtimeFiring ? 'bg-primary' : ''}>
                {runtimeFiring ? 'runtime firing' : 'runtime waiting'}
              </Badge>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="rounded-md border border-border/40 bg-muted/20 p-3">
            <div className="text-xs font-medium">What this unlocks</div>
            <p className="mt-1 text-xs text-muted-foreground">{onboarding.runs}</p>
            <div className="mt-2 flex flex-wrap gap-1">
              {onboarding.requiredKeys.map((key) => (
                <Badge key={key} variant={envMissing.includes(key) ? 'destructive' : 'outline'} className="font-mono text-[10px]">
                  {key}
                </Badge>
              ))}
            </div>
            <p className="mt-2 text-[11px] text-muted-foreground">{onboarding.permissionHint}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <a className="inline-flex items-center gap-1 text-xs text-primary hover:underline" href={onboarding.setupUrl} target="_blank" rel="noopener noreferrer">
                Get keys <ExternalLink className="h-3 w-3" />
              </a>
              <a className="inline-flex items-center gap-1 text-xs text-primary hover:underline" href={onboarding.docsUrl} target="_blank" rel="noopener noreferrer">
                API docs <ExternalLink className="h-3 w-3" />
              </a>
            </div>
          </div>

          <div className="space-y-2">
            <Label className="text-xs">API Key</Label>
            <Input
              type="text"
              placeholder={isConnected ? '••••••••' : 'Enter API Key'}
              value={apiKeyValue}
              onChange={(e) => apiKeyOnChange(e.target.value)}
              className="h-9"
            />
          </div>
          <div className="space-y-2">
            <Label className="text-xs">{secretLabel}</Label>
            <div className="relative">
              <Input
                type={showSecrets[secretKey] ? 'text' : 'password'}
                placeholder={isConnected ? '••••••••' : `Enter ${secretLabel}`}
                value={secretValue}
                onChange={(e) => secretOnChange(e.target.value)}
                className="h-9 pr-10"
              />
              <button
                type="button"
                onClick={() => toggleSecret(secretKey)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                {showSecrets[secretKey] ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>
          {extraFields}
          
          {/* Test result display */}
          {testResult && (
            <div className={`text-xs p-2 rounded ${testResult.success ? 'bg-success/10 text-success' : 'bg-destructive/10 text-destructive'}`}>
              {testResult.success ? '✓' : '✗'} {testResult.message}
            </div>
          )}
          
          <div className="flex gap-2">
            <Button 
              onClick={() => testConnection(name)} 
              disabled={isTesting || loading}
              variant="outline"
              size="sm"
              className="flex-1"
            >
              {isTesting ? (
                <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Testing...</>
              ) : (
                <><Zap className="h-4 w-4 mr-2" /> Test</>
              )}
            </Button>
            <Button 
              onClick={() => handleSaveCredentials(name)} 
              disabled={loading || isTesting}
              size="sm"
              className="flex-1"
            >
              <Save className="h-4 w-4 mr-2" />
              {isConnected ? 'Update' : 'Save'}
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  };

  if (checking) {
    return (
      <div className="flex items-center justify-center p-8">
        <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const connectedCount = Object.values(status).filter(Boolean).length;
  const localConnectedCount = Object.values(localEnvStatus?.exchanges || {}).filter((exchange) => exchange?.present).length;
  const runtimeFiringCount = exchangeOnboarding.filter((exchange) => runtimeExchangeStatus?.exchanges?.[exchange.name]).length;
  const operationalPercent = Math.round(((localConnectedCount + runtimeFiringCount) / (exchangeOnboarding.length * 2)) * 100);
  const restartRequired = Boolean(localEnvStatus?.restart_required);
  const hncPacketEncryption = localEnvStatus?.hnc_packet_encryption;
  const hncPacketEnabled = Boolean(hncPacketEncryption?.enabled);

  return (
    <div className="space-y-6">
      <div className="rounded-md border border-border/40 bg-muted/10 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-lg font-semibold">First-run operational cockpit</h3>
            <p className="text-sm text-muted-foreground">
              Boot Aureon, add missing exchange keys, validate the local .env, then let the supervisor reload the runtime when approved.
            </p>
          </div>
          <div className="text-right">
            <div className="text-2xl font-semibold">{operationalPercent}%</div>
            <div className="text-xs uppercase text-muted-foreground">operational wiring</div>
          </div>
        </div>
        <div className="mt-4 h-3 overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-success transition-all"
            style={{ width: `${Math.max(0, Math.min(100, operationalPercent))}%` }}
          />
        </div>
        <div className="mt-3 grid gap-2 sm:grid-cols-4">
          <div className="rounded-md border border-border/40 bg-black/20 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">.env connected</div>
            <div className="mt-1 font-mono text-sm font-semibold">{localConnectedCount}/4</div>
          </div>
          <div className="rounded-md border border-border/40 bg-black/20 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">runtime firing</div>
            <div className="mt-1 font-mono text-sm font-semibold">{runtimeFiringCount}/4</div>
          </div>
          <div className="rounded-md border border-border/40 bg-black/20 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">tick phase</div>
            <div className="mt-1 truncate font-mono text-sm font-semibold">{runtimeExchangeStatus?.tick_phase || 'waiting'}</div>
          </div>
          <div className="rounded-md border border-border/40 bg-black/20 p-3">
            <div className="text-[11px] uppercase text-muted-foreground">restart</div>
            <div className="mt-1 font-mono text-sm font-semibold">{restartRequired ? 'queued' : 'not required'}</div>
          </div>
        </div>
        <div className="mt-3 rounded-md border border-border/40 bg-black/20 p-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <div className="text-[11px] uppercase text-muted-foreground">HNC packet encryption</div>
              <div className="mt-1 text-sm">
                {hncPacketEnabled
                  ? `active (${hncPacketEncryption?.encoded_key_count || 0} packet keys stored)`
                  : 'waiting for AUREON_HNC_PACKET_MASTER_KEY'}
              </div>
            </div>
            <Badge variant={hncPacketEnabled ? 'default' : 'outline'}>
              {hncPacketEnabled ? 'hncqp1 active' : 'plain .env mode'}
            </Badge>
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            When the local HNC master key is present, new exchange secrets are stored as harmonic packet tokens and decoded by Aureon at boot.
          </p>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">Exchange Connections</h3>
          <p className="text-sm text-muted-foreground">
            {connectedCount}/4 exchanges connected
          </p>
          <p className="text-xs text-muted-foreground">
            Local .env readiness: {localConnectedCount}/4 exchanges{restartRequired ? ' - restart queued' : ''}
          </p>
          {localEnvStatus?.env_file && (
            <p className="mt-1 font-mono text-[11px] text-muted-foreground">
              {localEnvStatus.env_file}
            </p>
          )}
        </div>
        <Button variant="outline" size="sm" onClick={checkExistingCredentials}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>
      {localEnvError && (
        <div className="rounded-md border border-warning/30 bg-warning/10 p-3 text-xs text-warning">
          {localEnvError}
        </div>
      )}
      {restartRequired && (
        <div className="rounded-md border border-success/30 bg-success/10 p-3 text-xs text-success">
          New .env credentials are staged. The production supervisor will reload them on the next approved restart window.
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <ExchangeCard
          name="binance"
          label="Binance"
          description="Primary crypto exchange"
          onboarding={exchangeOnboarding[0]}
          isConnected={status.binance}
          apiKeyValue={binanceApiKey}
          apiKeyOnChange={setBinanceApiKey}
          secretValue={binanceApiSecret}
          secretOnChange={setBinanceApiSecret}
          secretKey="binance"
        />

        <ExchangeCard
          name="kraken"
          label="Kraken"
          description="Crypto exchange (GBP/EUR)"
          onboarding={exchangeOnboarding[1]}
          isConnected={status.kraken}
          apiKeyValue={krakenApiKey}
          apiKeyOnChange={setKrakenApiKey}
          secretValue={krakenApiSecret}
          secretOnChange={setKrakenApiSecret}
          secretKey="kraken"
        />

        <ExchangeCard
          name="alpaca"
          label="Alpaca"
          description="US Stocks & Crypto"
          onboarding={exchangeOnboarding[2]}
          isConnected={status.alpaca}
          apiKeyValue={alpacaApiKey}
          apiKeyOnChange={setAlpacaApiKey}
          secretValue={alpacaSecretKey}
          secretOnChange={setAlpacaSecretKey}
          secretKey="alpaca"
        />

        <ExchangeCard
          name="capital"
          label="Capital.com"
          description="CFDs & Forex"
          onboarding={exchangeOnboarding[3]}
          isConnected={status.capital}
          apiKeyValue={capitalApiKey}
          apiKeyOnChange={setCapitalApiKey}
          secretValue={capitalPassword}
          secretOnChange={setCapitalPassword}
          secretLabel="Password"
          secretKey="capital"
          extraFields={
            <div className="space-y-2">
              <Label className="text-xs">Identifier (optional)</Label>
              <Input
                type="text"
                placeholder="Account Identifier"
                value={capitalIdentifier}
                onChange={(e) => setCapitalIdentifier(e.target.value)}
                className="h-9"
              />
            </div>
          }
        />
      </div>
    </div>
  );
}
