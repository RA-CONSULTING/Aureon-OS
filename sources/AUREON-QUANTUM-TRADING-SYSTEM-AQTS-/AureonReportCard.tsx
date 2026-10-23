
import React from 'react';
import { AureonReport } from './types';

interface AureonReportCardProps {
  report: AureonReport | null;
}

const SignalDisplay: React.FC<{ status: 'Blue' | 'Gold' | 'Red' | 'Unknown' }> = ({ status }) => {
    const statusConfig = {
        'Blue': { color: 'bg-sky-500', text: 'NEUTRAL', description: "No significant LHEs detected. Market is in a low-conviction phase." },
        'Gold': { color: 'bg-amber-400', text: 'WATCH', description: "Anomalies detected. A Lighthouse Event may be forming. Risk is moderate." },
        'Red': { color: 'bg-red-500', text: 'ACTION', description: "High-confidence LHE triggered. A significant market move is imminent." },
        'Unknown': { color: 'bg-gray-600', text: 'CALIBRATING...', description: "Awaiting sufficient data to determine market state." },
    };
    const config = statusConfig[status];

    return (
        <div title={config.description} className={`p-4 rounded-lg text-center flex-grow ${config.color}`}>
            <p className="text-sm font-bold tracking-widest text-gray-900/70">QGITA SIGNAL STATUS</p>
            <p className="text-2xl font-bold text-white mt-1">{config.text}</p>
        </div>
    );
};

const MetricDisplay: React.FC<{ label: string; value: string | number; tooltip: string }> = ({ label, value, tooltip }) => (
    <div title={tooltip} className="bg-gray-900/50 p-3 rounded-md text-center flex-1">
        <p className="text-2xl font-bold text-amber-300">{value}</p>
        <p className="text-xs text-gray-400 mt-1 truncate">{label}</p>
    </div>
);

const AureonReportCard: React.FC<AureonReportCardProps> = ({ report }) => {
  if (!report) return null;
  
  const { prismStatus, unityIndex, inerchaVector } = report;

  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded-lg shadow-lg p-6">
      <h3 className="text-xl font-semibold text-gray-200 mb-4">QGITA Signal Report</h3>
      <div className="flex flex-col gap-4">
        <SignalDisplay status={prismStatus || 'Unknown'} />
        <div className="flex flex-row gap-4">
           <MetricDisplay 
                label="LHE Confidence"
                value={unityIndex > 0 ? unityIndex.toFixed(3) : '...'}
                tooltip="Signal Confidence Score (0-1). High scores indicate a probable Lighthouse Event."
            />
            <MetricDisplay 
                label="Anomaly Pointer (Q_sig)" 
                value={inerchaVector > 0 ? inerchaVector.toFixed(3) : '...'} 
                tooltip="Rate of change in market structure. Spikes can precede LHEs."
            />
        </div>
      </div>
    </div>
  );
};

export default AureonReportCard;
