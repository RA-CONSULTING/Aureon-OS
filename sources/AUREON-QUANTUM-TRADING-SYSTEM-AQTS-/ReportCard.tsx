
import React from 'react';
import { NexusReport } from './types';

interface ReportCardProps {
  report: NexusReport | null;
}

const MetricDisplay: React.FC<{ label: string; value: string | number; unit?: string, tooltip: string, valueColor?: string }> = ({ label, value, unit, tooltip, valueColor = 'text-sky-400' }) => (
    <div title={tooltip} className="bg-gray-900/50 p-3 rounded-md text-center flex-1">
        <p className={`text-2xl lg:text-3xl font-bold ${valueColor}`}>
          {value}
          {unit && <span className="text-lg ml-1 text-gray-400">{unit}</span>}
        </p>
        <p className="text-xs text-gray-400 mt-1 truncate">{label}</p>
    </div>
);


const ReportCard: React.FC<ReportCardProps> = ({ report }) => {
  if (!report) return null;

  const { simulationYear } = report;
  const days = (simulationYear - 2025) * 365;

  // Faked metrics for demonstration purposes
  const pnl = (days * 123.45).toFixed(2);
  const winRate = (62.5 + Math.sin(days / 30) * 5).toFixed(2);
  const sharpeRatio = (1.85 + Math.cos(days / 50) * 0.5).toFixed(2);
  const exposure = (35 + Math.sin(days/15) * 15).toFixed(2);

  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded-lg shadow-lg p-6 h-full">
      <h3 className="text-xl font-semibold text-gray-200 mb-4">Live Performance Metrics</h3>
      <div className="flex flex-col gap-4 h-full justify-between">
        <div className="flex flex-row gap-4">
           <MetricDisplay 
                label="Total P&L"
                value={`$${pnl}`}
                tooltip="Total profit and loss since the start of the session."
                valueColor="text-green-400"
            />
            <MetricDisplay 
                label="Sharpe Ratio" 
                value={sharpeRatio}
                tooltip="Risk-adjusted return. Higher is better."
            />
        </div>
        <div className="flex flex-row gap-4">
            <MetricDisplay
                label="Win Rate"
                value={winRate}
                unit="%"
                tooltip="Percentage of profitable trades out of all closed trades."
            />
            <MetricDisplay 
                label="Current Exposure" 
                value={exposure}
                unit="%"
                tooltip="Percentage of capital currently allocated to open positions."
            />
        </div>
      </div>
    </div>
  );
};

export default ReportCard;
