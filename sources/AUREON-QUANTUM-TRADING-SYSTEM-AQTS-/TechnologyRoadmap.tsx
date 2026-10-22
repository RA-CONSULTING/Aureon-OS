
import React from 'react';

const riskParameters = [
  { name: 'Kelly Criterion Sizing', value: '25%', status: 'ACTIVE', description: 'Optimal position sizing based on win probability and win/loss ratio.' },
  { name: 'Max Portfolio Drawdown', value: '15%', status: 'ACTIVE', description: 'System-wide circuit breaker if total portfolio value drops by this percentage.' },
  { name: 'Volatility-Adjusted Stops', value: '2x ATR', status: 'ACTIVE', description: 'Stop-loss levels are dynamically set based on the Average True Range.' },
  { name: 'Max Position Hold Time', value: '72 Hours', status: 'ACTIVE', description: 'Positions are automatically closed if they remain open longer than this period.' },
  { name: 'Dynamic Leverage', value: '1x - 5x', status: 'ACTIVE', description: 'Leverage is adjusted based on market volatility and signal confidence.' },
  { name: 'Emergency Kill Switch', value: 'MANUAL', status: 'STANDBY', description: 'Manual override to close all positions and pause trading.' },
];

const RiskManagementPanel: React.FC<{ currentDay: number }> = () => {
  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded-lg shadow-lg p-6">
      <h3 className="text-xl font-semibold text-gray-200 mb-1">Layer 4: Intelligent Risk Management Core</h3>
      <p className="text-sm text-gray-400 mb-6">Live parameters for portfolio protection and capital preservation.</p>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {riskParameters.map((param, index) => (
          <div key={index} className="bg-gray-900/50 p-4 rounded-md border border-gray-700" title={param.description}>
            <div className="flex justify-between items-center">
              <p className="font-semibold text-gray-300 text-sm">{param.name}</p>
              <span className={`text-xs font-bold px-2 py-1 rounded-full ${param.status === 'ACTIVE' ? 'bg-green-500/20 text-green-300' : 'bg-yellow-500/20 text-yellow-300'}`}>{param.status}</span>
            </div>
            <p className="text-2xl font-mono text-cyan-400 mt-2">{param.value}</p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default RiskManagementPanel;
