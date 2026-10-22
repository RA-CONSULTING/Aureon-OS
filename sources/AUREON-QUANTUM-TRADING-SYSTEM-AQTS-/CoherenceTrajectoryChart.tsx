
import React from 'react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, Legend, CartesianGrid, Scatter, ReferenceLine } from 'recharts';
import { CoherenceDataPoint, DejaVuEvent } from './types';

interface CoherenceTrajectoryChartProps {
  data: CoherenceDataPoint[];
  dejaVuEvents: DejaVuEvent[];
}

const CoherenceTrajectoryChart: React.FC<CoherenceTrajectoryChartProps> = ({ data, dejaVuEvents }) => {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data} margin={{ top: 5, right: 20, left: -10, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#4A5568" />
        <XAxis dataKey="time" stroke="#A0AEC0" name="Time" />
        <YAxis stroke="#A0AEC0" domain={[0, 'dataMax + 0.2']} />
        <Tooltip
            contentStyle={{
              backgroundColor: 'rgba(31, 41, 55, 0.8)',
              borderColor: '#4A5568',
              color: '#F7FAFC'
            }}
            formatter={(value: number, name: string) => [value.toFixed(3), name]}
        />
        <Legend />
        <ReferenceLine y={0.7} label={{ value: "High-Confidence Threshold", position: 'insideTopRight', fill: '#A0AEC0' }} stroke="#FBBF24" strokeDasharray="4 4" />
        <Line type="monotone" dataKey="cognitiveCapacity" name="LHE Confidence Score" stroke="#38BDF8" strokeWidth={2} dot={false} />
        <Scatter name="FTCP Marker" data={dejaVuEvents} fill="#FACC15" shape="star" />
      </LineChart>
    </ResponsiveContainer>
  );
};

export default CoherenceTrajectoryChart;
