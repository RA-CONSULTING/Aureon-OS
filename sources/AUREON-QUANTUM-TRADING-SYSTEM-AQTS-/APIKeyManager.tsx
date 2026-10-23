import React, { useState, useEffect } from 'react';
import {
  getStoredCredentials,
  storeCredentials,
  clearStoredCredentials,
} from './tradingService.browser';

interface APIKeyManagerProps {
  isApiActive: boolean;
  onToggleApiStatus: () => void;
}

const APIKeyManager: React.FC<APIKeyManagerProps> = ({ isApiActive, onToggleApiStatus }) => {
  const [apiKeyInput, setApiKeyInput] = useState('');
  const [apiSecretInput, setApiSecretInput] = useState('');
  const [mode, setMode] = useState<'live' | 'testnet'>('testnet');
  const [keysSaved, setKeysSaved] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [hasStoredSecret, setHasStoredSecret] = useState(false);

  useEffect(() => {
    async function loadStored() {
      const stored = await getStoredCredentials();
      if (stored) {
        setApiKeyInput(stored.apiKey);
        setMode(stored.mode);
        setKeysSaved(true);
        setHasStoredSecret(Boolean(stored.apiSecret));
      }
    }
    loadStored();
  }, []);

  const handleSave = async () => {
    const trimmedKey = apiKeyInput.trim();
    const trimmedSecret = apiSecretInput.trim();

    if (!trimmedKey) {
      alert('API Key cannot be empty.');
      return;
    }
    // If the secret input is empty but a secret already exists for this key,
    // keep the existing secret. Otherwise require a secret.
    let secretToPersist = trimmedSecret;
    if (!secretToPersist) {
      const existing = await getStoredCredentials(trimmedKey);
      const existingSecret = existing?.apiSecret ?? '';
      if (!existingSecret) {
        alert('Secret Key cannot be empty.');
        return;
      }
      secretToPersist = existingSecret;
    }

    await storeCredentials({ apiKey: trimmedKey, apiSecret: secretToPersist, mode });
    setKeysSaved(true);
    setIsEditing(false);
    setApiSecretInput('');
    setHasStoredSecret(true);
    alert('API keys saved successfully.');
  };

  const handleEdit = async () => {
    const stored = await getStoredCredentials(apiKeyInput.trim());
    if (stored) {
      setApiKeyInput(stored.apiKey);
      setMode(stored.mode);
      setHasStoredSecret(Boolean(stored.apiSecret));
    } else {
      setApiKeyInput('');
      setMode('testnet');
      setHasStoredSecret(false);
    }
    setApiSecretInput('');
    setIsEditing(true);
  };

  const handleDelete = () => {
    if (window.confirm('Are you sure you want to delete the API keys? This action cannot be undone.')) {
      clearStoredCredentials();
      setApiKeyInput('');
      setApiSecretInput('');
      setMode('testnet');
      setKeysSaved(false);
      setIsEditing(false);
      setHasStoredSecret(false);
      if (isApiActive) {
        onToggleApiStatus();
      }
    }
  };

  const handleCancelEdit = async () => {
    setIsEditing(false);
    const stored = await getStoredCredentials();
    if (stored) {
      setApiKeyInput(stored.apiKey);
      setMode(stored.mode);
      setHasStoredSecret(Boolean(stored.apiSecret));
    } else {
      setApiKeyInput('');
      setMode('testnet');
      setHasStoredSecret(false);
    }
    setApiSecretInput('');
  };

  const maskApiKey = (key: string) => {
    if (key.length <= 8) return '****';
    return `${key.substring(0, 4)}...${key.substring(key.length - 4)}`;
  };

  const effectiveApiStatus = isApiActive && keysSaved;
  const modeLabel = mode === 'testnet' ? 'TESTNET' : 'LIVE';

  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded-lg shadow-lg p-6 h-full flex flex-col">
      <div className="flex justify-between items-start">
        <div>
          <h3 className="text-xl font-semibold text-gray-200 mb-1">Layer 5: API Management</h3>
          <p className="text-sm text-gray-400 mb-4">Manage API keys for trade execution.</p>
        </div>
        <div className="flex items-center space-x-3">
          <span className={`text-sm font-bold ${effectiveApiStatus ? 'text-green-400' : 'text-red-400'}`}>
            {keysSaved ? (effectiveApiStatus ? 'API ACTIVE' : 'API INACTIVE') : 'NO KEY SET'}
          </span>
          {keysSaved && (
            <span className="text-xs font-semibold text-sky-300 bg-sky-700/40 border border-sky-500/60 px-2 py-1 rounded">
              {modeLabel} MODE
            </span>
          )}
          <button
            role="switch"
            aria-checked={effectiveApiStatus}
            onClick={onToggleApiStatus}
            disabled={!keysSaved}
            className={`${effectiveApiStatus ? 'bg-green-500' : 'bg-gray-600'} relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 focus:ring-offset-gray-800 disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            <span className={`${effectiveApiStatus ? 'translate-x-6' : 'translate-x-1'} inline-block h-4 w-4 transform rounded-full bg-white transition-transform`}/>
          </button>
        </div>
      </div>

      <div className="bg-gray-900/50 border border-gray-700 rounded-lg p-4 mt-4 flex-grow flex flex-col">
        {keysSaved && !isEditing ? (
          <div className="flex flex-col flex-grow">
            <div className="flex-grow">
              <div className="flex justify-between items-center mb-4">
                <div className="flex items-center gap-3">
                  <span className="bg-gray-600 text-gray-200 text-xs font-bold px-2 py-1 rounded">HMAC</span>
                  <h4 className="text-lg font-semibold text-white">Primary Trading Key</h4>
                  <span className="bg-sky-600/30 text-sky-200 text-xs font-bold px-2 py-1 rounded border border-sky-500/60">
                    {modeLabel} MODE
                  </span>
                </div>
                <div className="flex items-center gap-4 text-sm font-medium">
                  <button onClick={handleEdit} className="text-yellow-500 hover:underline">Edit</button>
                  <button onClick={handleDelete} className="text-red-500 hover:underline">Delete</button>
                </div>
              </div>

              <div className="space-y-2">
                <div>
                  <p className="text-xs text-gray-400">API Key</p>
                  <p className="font-mono text-gray-300 break-all text-sm">{maskApiKey(apiKeyInput)}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400 mt-2">Secret Key</p>
                  <p className="font-mono text-gray-300 break-all text-sm">**************************************************</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400 mt-2">Trading Mode</p>
                  <p className="text-sm font-semibold text-sky-300">
                    {mode === 'testnet' ? 'Binance Testnet (Paper Trading)' : 'Binance Live Trading'}
                  </p>
                </div>
              </div>

              <div className="mt-4 pt-4 border-t border-gray-700 text-xs text-gray-400">
                <p className="font-bold mb-1">Permissions:</p>
                <div className="flex gap-4">
                  <span className="text-green-400">✓ Read Info</span>
                  <span className="text-green-400">✓ Enable Trading</span>
                  <span className="text-gray-500 line-through">✗ Enable Withdrawals</span>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex-grow flex flex-col">
            <h4 className="text-lg font-semibold text-white mb-4">{isEditing ? 'Edit API Keys' : 'Add New API Key'}</h4>
            <div className="space-y-4 flex-grow">
              <div>
                <label htmlFor="api-key" className="block text-sm font-medium text-gray-400 mb-1">API Key</label>
                <input
                  type="text"
                  id="api-key"
                  value={apiKeyInput}
                  onChange={(e) => setApiKeyInput(e.target.value)}
                  placeholder="Enter your API key"
                  className="w-full bg-gray-700 border border-gray-600 rounded-md py-2 px-3 focus:outline-none focus:ring-2 focus:ring-sky-500 text-gray-200"
                />
              </div>
              <div>
                <label htmlFor="api-secret" className="block text-sm font-medium text-gray-400 mb-1">
                  Secret Key {hasStoredSecret && (isEditing || keysSaved) ? '(leave blank to keep existing)' : ''}
                </label>
                <input
                  type="password"
                  id="api-secret"
                  value={apiSecretInput}
                  onChange={(e) => setApiSecretInput(e.target.value)}
                  placeholder="Enter your secret key"
                  className="w-full bg-gray-700 border border-gray-600 rounded-md py-2 px-3 focus:outline-none focus:ring-2 focus:ring-sky-500 text-gray-200"
                />
              </div>
              <div>
                <label htmlFor="api-mode" className="block text-sm font-medium text-gray-400 mb-1">Trading Mode</label>
                <select
                  id="api-mode"
                  value={mode}
                  onChange={(e) => setMode(e.target.value as 'live' | 'testnet')}
                  className="w-full bg-gray-700 border border-gray-600 rounded-md py-2 px-3 focus:outline-none focus:ring-2 focus:ring-sky-500 text-gray-200"
                >
                  <option value="testnet">Paper Trading (Binance Testnet)</option>
                  <option value="live">Live Trading (Binance Production)</option>
                </select>
              </div>
            </div>
            <div className="mt-4 flex justify-end gap-3">
              {isEditing && (
                <button onClick={handleCancelEdit} className="bg-gray-600 hover:bg-gray-500 text-white font-bold py-2 px-4 rounded text-sm">
                  Cancel
                </button>
              )}
              <button onClick={handleSave} className="bg-yellow-500 hover:bg-yellow-600 text-black font-bold py-2 px-4 rounded text-sm">
                Save Keys
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default APIKeyManager;

