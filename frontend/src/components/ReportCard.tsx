import React from 'react';
import { NexusReport } from '@/types';
import { useEcosystemData } from '@/hooks/useEcosystemData';

interface ReportCardProps {
  report: NexusReport | null;
}

const MetricDisplay: React.FC<{ label: string; value: string | number; unit?: string, tooltip: string, valueColor?: string }> = ({ label, value, unit, tooltip, valueColor = 'text-primary' }) => (
    <div title={tooltip} className="bg-gray-900/50 p-3 rounded-md text-center flex-1">
        <p className={`text-2xl lg:text-3xl font-bold ${valueColor}`}>
          {value}
          {unit && <span className="text-lg ml-1 text-gray-400">{unit}</span>}
        </p>
        <p className="text-xs text-gray-400 mt-1 truncate">{label}</p>
    </div>
);


const ReportCard: React.FC<ReportCardProps> = ({ report }) => {
  const { metrics, isInitialized } = useEcosystemData();
  
  if (!report) return null;

  // LIVE DATA ONLY - Use real ecosystem metrics
  // Show loading state when not initialized
  if (!isInitialized) {
    return (
      <div className="bg-gray-800/50 border border-gray-700 rounded-lg shadow-lg p-6 h-full">
        <h3 className="text-xl font-semibold text-gray-200 mb-4">Live Performance Metrics</h3>
        <div className="text-warning text-center py-8">
          ⚠️ AWAITING LIVE DATA - No simulation
        </div>
      </div>
    );
  }

  // Use real coherence and harmonic data 
  const coherence = (metrics.coherence * 100).toFixed(2);
  const lambda = metrics.lambda?.toFixed(4) || '0.0000';
  const harmonicFidelity = (metrics.harmonicFidelity * 100).toFixed(2);
  const prismLevel = metrics.prismLevel || 0;

  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded-lg shadow-lg p-6 h-full">
      <h3 className="text-xl font-semibold text-gray-200 mb-4">Live Performance Metrics</h3>
      <div className="flex flex-col gap-4 h-full justify-between">
        <div className="flex flex-row gap-4">
           <MetricDisplay 
                label="Coherence (Γ)"
                value={`${coherence}%`}
                tooltip="Real-time field coherence from Master Equation."
                valueColor={parseFloat(coherence) >= 70 ? 'text-success' : parseFloat(coherence) >= 45 ? 'text-warning' : 'text-destructive'}
            />
            <MetricDisplay 
                label="Lambda (Λ)" 
                value={lambda}
                tooltip="Master Equation lambda value."
            />
        </div>
        <div className="flex flex-row gap-4">
            <MetricDisplay
                label="Harmonic Fidelity"
                value={harmonicFidelity}
                unit="%"
                tooltip="HNC Imperial harmonic fidelity measure."
            />
            <MetricDisplay 
                label="Prism Level" 
                value={prismLevel}
                tooltip="Current Prism transformation level (0-5)."
            />
        </div>
      </div>
    </div>
  );
};

export default ReportCard;
