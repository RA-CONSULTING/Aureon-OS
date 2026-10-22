import React from 'react';

const RISK_WARNINGS = [
  {
    title: 'Financial Drawdown',
    body: 'Automated systems can accumulate losses before you notice. Only trade with capital you can afford to lose and define a maximum daily loss limit.'
  },
  {
    title: 'Credential Exposure',
    body: 'Anyone with a trading-enabled API key can place orders on your behalf. Rotate keys regularly, restrict access to trusted IPs, and disable withdrawals.'
  },
  {
    title: 'Software Bugs',
    body: 'Logic defects or bad market data can send malformed orders. Keep the bot under supervision during roll-outs and log every execution path.'
  },
  {
    title: 'Market Extremes',
    body: 'Volatility spikes and liquidity gaps can invalidate even high-confidence signals. Always pair autonomous execution with hard stop losses.'
  }
];

const BEST_PRACTICES = [
  'Start in paper-trading mode to validate the pipeline end-to-end.',
  'Keep a capped, dedicated exchange sub-account (e.g., £500-£1000) for live fire drills.',
  'IP whitelist the API key and monitor access logs.',
  'Disable withdrawals on all execution keys.',
  'Enforce position sizing, stop loss, and take profit guards at the strategy level.',
  'Set up 24/7 alerts and dashboards for fills, rejects, and connectivity.'
];

const PHASES = [
  {
    title: 'Phase 1 — Exchange API Configuration',
    items: [
      'Create a Binance API key with Reading + Spot & Margin Trading enabled.',
      'Explicitly disable withdrawals and enable IP access restrictions.',
      'Optional: enable universal transfers if you need to rebalance sub-accounts.',
      'Test connectivity with a signed /api/v3/account request before going live.'
    ]
  },
  {
    title: 'Phase 2 — QGITA Autonomous Bot Pipeline',
    items: [
      'Stream market data into the QGITA FTCP detector and Lighthouse consensus modules.',
      'Run risk filters (daily loss cap, max trades, position limits) before any order leaves the system.',
      'Use the execution module to send signed market orders in paper mode before enabling live trading.',
      'Continuously log decisions, fills, and PnL deltas for post-trade review.'
    ]
  }
];

const AutonomousTradingGuide: React.FC = () => {
  return (
    <section className="bg-gray-900/50 border border-amber-500/30 rounded-xl shadow-2xl overflow-hidden">
      <div className="bg-gradient-to-r from-amber-400/20 via-orange-400/10 to-amber-500/20 px-6 py-4 border-b border-amber-500/40">
        <h3 className="text-2xl font-bold text-amber-300 tracking-wide">Autonomous Execution Guardrails</h3>
        <p className="text-sm text-amber-100/80 mt-1">Read this before activating live trading on QGITA.</p>
      </div>

      <div className="p-6 space-y-8 text-sm text-gray-200 leading-relaxed">
        <div>
          <h4 className="text-lg font-semibold text-amber-200 mb-3">Critical Risk Disclosures</h4>
          <div className="grid gap-4 md:grid-cols-2">
            {RISK_WARNINGS.map((warning) => (
              <div key={warning.title} className="bg-gray-800/60 border border-amber-500/20 rounded-lg p-4">
                <h5 className="font-semibold text-amber-300 mb-2 uppercase tracking-wide text-xs">{warning.title}</h5>
                <p className="text-gray-200 text-sm leading-snug">{warning.body}</p>
              </div>
            ))}
          </div>
        </div>

        <div>
          <h4 className="text-lg font-semibold text-amber-200 mb-3">Operational Best Practices</h4>
          <ul className="list-disc list-inside space-y-2 text-gray-200">
            {BEST_PRACTICES.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>

        <div className="space-y-4">
          {PHASES.map((phase) => (
            <div key={phase.title} className="bg-gray-800/50 border border-gray-700 rounded-lg p-5">
              <h4 className="text-lg font-semibold text-amber-200 mb-3">{phase.title}</h4>
              <ol className="list-decimal list-inside space-y-2 text-gray-200">
                {phase.items.map((item, index) => (
                  <li key={`${phase.title}-${index}`}>{item}</li>
                ))}
              </ol>
            </div>
          ))}
        </div>

        <div className="bg-gray-800/80 border border-amber-400/40 rounded-lg p-5">
          <h4 className="text-lg font-semibold text-amber-200 mb-3">Binance Trading Permission Check (Python)</h4>
          <pre className="bg-black/60 text-emerald-200 text-xs p-4 rounded-lg overflow-x-auto">
            <code>{`import time, hmac, hashlib
from urllib.parse import urlencode
import requests

API_KEY = 'your_api_key'
API_SECRET = 'your_secret_key'
BASE_URL = 'https://api.binance.com'


def binance_signature(params, secret):
    query_string = urlencode(params)
    return hmac.new(secret.encode(), query_string.encode(), hashlib.sha256).hexdigest()


def get_account_info():
    endpoint = '/api/v3/account'
    timestamp = int(time.time() * 1000)
    params = {'timestamp': timestamp}
    params['signature'] = binance_signature(params, API_SECRET)
    headers = {'X-MBX-APIKEY': API_KEY}
    response = requests.get(BASE_URL + endpoint, params=params, headers=headers)
    response.raise_for_status()
    return response.json()


account = get_account_info()
print('Account Type:', account.get('accountType'))
print('Can Trade:', account.get('canTrade'))
print('Balances:', [(b['asset'], b['free']) for b in account['balances'] if float(b['free']) > 0])`}</code>
          </pre>
          <p className="text-xs text-gray-400 mt-3">
            Run this in a secure environment to validate permissions before flipping QGITA from paper trading to live fire.
          </p>
        </div>
      </div>
    </section>
  );
};

export default AutonomousTradingGuide;
