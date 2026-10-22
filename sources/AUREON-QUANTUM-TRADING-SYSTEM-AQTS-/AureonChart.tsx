
import React from 'react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, Legend, CartesianGrid } from 'recharts';
import { AureonDataPoint } from './types';

interface AureonChartProps {
  data: AureonDataPoint[];
}

const AureonChart: React.FC<AureonChartProps> = ({ data }) => {
    if (!data || data.length === 0) return null;
    
  const colors = {
    gEff: "#FCD34D", // amber-300
    qSig: "#F87171",   // red-400
    sentiment: "#A78BFA",      // violet-400
    dataIntegrity: "#60A5FA",   // blue-400
  };

  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data} margin={{ top: 5, right: 20, left: -10, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#4A5568" />
        <XAxis dataKey="time" stroke="#A0AEC0" name="Time" />
        <YAxis stroke="#A0AEC0" />
        <Tooltip
          contentStyle={{
            backgroundColor: 'rgba(31, 41, 55, 0.8)',
            borderColor: '#4A5568',
            color: '#F7FAFC'
          }}
          formatter={(value: number, name: string) => [value.toFixed(3), name]}
        />
        <Legend />
        <Line type="monotone" dataKey="crystalCoherence" name="Geometric Anomaly (G_eff)" stroke={colors.gEff} dot={false} strokeWidth={2} />
        <Line type="monotone" dataKey="inerchaVector" name="Anomaly Pointer (Q_sig)" stroke={colors.qSig} dot={false} strokeWidth={2} />
        <Line type="monotone" dataKey="sentiment" name="Market Sentiment" stroke={colors.sentiment} dot={false} strokeWidth={1} strokeDasharray="5 5" />
         <Line type="monotone" dataKey="dataIntegrity" name="Data Integrity (Dₜ)" stroke={colors.dataIntegrity} dot={false} strokeWidth={1} strokeDasharray="2 8" />
      </LineChart>
    </ResponsiveContainer>
  );
};

export default AureonChart;
