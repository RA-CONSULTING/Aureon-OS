
import React from 'react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, Legend, CartesianGrid, ReferenceLine } from 'recharts';
import { CoherenceDataPoint } from './types';

interface SporeConcentrationChartProps {
  data: CoherenceDataPoint[];
}

const SporeConcentrationChart: React.FC<SporeConcentrationChartProps> = ({ data }) => {
  const CRITICAL_THRESHOLD = 5000;
  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={data} margin={{ top: 5, right: 20, left: -10, bottom: 5 }}>
        <defs>
          <linearGradient id="colorCt" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#6366f1" stopOpacity={0.8}/>
            <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#4A5568" />
        <XAxis dataKey="time" stroke="#A0AEC0" name="Time" />
        <YAxis stroke="#A0AEC0" domain={[0, 'dataMax + 1000']} />
        <Tooltip
            contentStyle={{
              backgroundColor: 'rgba(31, 41, 55, 0.8)',
              borderColor: '#4A5568',
              color: '#F7FAFC'
            }}
            formatter={(value: number) => [value.toFixed(0), 'Mentions/hr']}
        />
        <Legend />
        <Area type="monotone" dataKey="sporeConcentration" name="Social Hype Index" stroke="#6366f1" fillOpacity={1} fill="url(#colorCt)" />
        <ReferenceLine y={CRITICAL_THRESHOLD} label={{ value: "Extreme Hype Threshold", position: 'insideTopRight', fill: '#f87171' }} stroke="#f87171" strokeDasharray="4 4" />
      </AreaChart>
    </ResponsiveContainer>
  );
};

export default SporeConcentrationChart;
