
import React from 'react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, Legend, CartesianGrid } from 'recharts';
import { CoherenceDataPoint } from './types';

interface DrivingForcesChartProps {
  data: CoherenceDataPoint[];
}

const DrivingForcesChart: React.FC<DrivingForcesChartProps> = ({ data }) => {
  const colors = {
    buyPressure: "#10B981", // emerald
    sellPressure: "#EF4444", // red
  };
  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data} margin={{ top: 5, right: 20, left: -10, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#4A5568" />
        <XAxis dataKey="time" stroke="#A0AEC0" name="Time" />
        <YAxis yAxisId="left" stroke={colors.buyPressure} />
        <YAxis yAxisId="right" orientation="right" stroke={colors.sellPressure} />
        <Tooltip
          contentStyle={{
            backgroundColor: 'rgba(31, 41, 55, 0.8)',
            borderColor: '#4A5568',
            color: '#F7FAFC'
          }}
          formatter={(value: number, name: string) => [value.toFixed(2), name]}
        />
        <Legend />
        <Line yAxisId="left" type="monotone" dataKey="sporeConcentration" name="Buy Pressure" stroke={colors.buyPressure} dot={false} strokeWidth={2} />
        <Line yAxisId="right" type="monotone" dataKey="systemRigidity" name="Sell Pressure" stroke={colors.sellPressure} dot={false} strokeWidth={2} />
      </LineChart>
    </ResponsiveContainer>
  );
};

export default DrivingForcesChart;
