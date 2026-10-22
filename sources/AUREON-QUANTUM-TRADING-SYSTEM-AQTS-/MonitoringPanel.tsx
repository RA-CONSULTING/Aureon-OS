
import React from 'react';
import { MonitoringEvent } from './types';

interface MonitoringPanelProps {
  events: MonitoringEvent[];
}

const StageTag: React.FC<{ stage: string }> = ({ stage }) => {
    const stageConfigMap: Record<string, {label: string, style: string}> = {
        aqts_initialized: { label: 'System Init', style: 'bg-blue-500/20 text-blue-300' },
        backtest_loaded: { label: 'Backtest Loaded', style: 'bg-purple-500/20 text-purple-300' },
        signal_detected: { label: 'Signal Detected', style: 'bg-amber-500/20 text-amber-300' },
        trade_executed: { label: 'Trade Executed', style: 'bg-green-500/20 text-green-300' },
        risk_update: { label: 'Risk Update', style: 'bg-sky-500/20 text-sky-300' },
    };
    const config = stageConfigMap[stage] || { label: stage.replace(/_/g, ' '), style: 'bg-gray-500/20 text-gray-300' };
    return <span className={`px-2 py-1 text-xs font-medium rounded-full ${config.style}`}>{config.label}</span>;
}

const MonitoringPanel: React.FC<MonitoringPanelProps> = ({ events }) => {
    const renderDetails = (event: MonitoringEvent) => {
        const { ts, stage, ...details } = event;
        if (Object.keys(details).length === 0) return null;
        
        const formattedDetails = Object.entries(details).map(([key, value]) => {
            let displayValue = value;
            if (typeof value === 'number') displayValue = value.toFixed(3);
            if (Array.isArray(value)) displayValue = value.join(', ');
            if (typeof value === 'object' && value !== null) return null; 

            // Special formatting for trade side
            if (key === 'side') {
                const color = String(value).toUpperCase().includes('LONG') || String(value).toUpperCase().includes('BUY') ? 'text-green-400' : 'text-red-400';
                 return <div key={key}><span className="font-semibold text-gray-300 capitalize">{key}:</span> <span className={color}>{String(displayValue)}</span></div>
            }

            return <div key={key}><span className="font-semibold text-gray-300 capitalize">{key.replace(/_/g, ' ')}:</span> {String(displayValue)}</div>
        }).filter(Boolean);

        if (formattedDetails.length === 0) return null;
        
        return (
            <div className="text-xs text-gray-400 mt-2 space-y-1 pl-2 border-l-2 border-gray-600 font-mono">
                {formattedDetails}
            </div>
        )
    }

  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded-lg shadow-lg flex flex-col h-[60vh] max-h-[700px]">
      <div className="p-4 border-b border-gray-700">
        <h3 className="text-xl font-semibold text-gray-200">AQTS Trade & Event Log</h3>
        <p className="text-sm text-gray-400">Live feed from the execution and detection engines.</p>
      </div>
      <div className="flex-grow p-4 overflow-y-auto space-y-4">
        {events.length > 0 ? [...events].reverse().map((event, index) => (
          <div key={index} className="flex items-start gap-3">
             <div className="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center flex-shrink-0 mt-1">
                <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V7a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
            </div>
            <div className="flex-grow">
                <div className="flex items-center justify-between">
                    <StageTag stage={event.stage} />
                    <span className="text-xs text-gray-500">{new Date(event.ts).toLocaleTimeString()}</span>
                </div>
               {renderDetails(event)}
            </div>
          </div>
        )) : (
            <div className="text-center text-gray-500 pt-8">
                <p>Awaiting system activation...</p>
            </div>
        )}
      </div>
    </div>
  );
};

export default MonitoringPanel;
