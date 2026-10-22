
import React from 'react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, Legend, CartesianGrid } from 'recharts';

interface HistoricalDataPoint {
  time: number; // Year
  cumulativeReturn: number; // Represents portfolio value factor
}

interface HistoricalChartProps {
  data: HistoricalDataPoint[];
}

const HistoricalCoherenceChart: React.FC<HistoricalChartProps> = ({ data }) => {

  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={data} margin={{ top: 5, right: 20, left: -10, bottom: 5 }}>
        <defs>
          <linearGradient id="colorHistory" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#22c55e" stopOpacity={0.8}/>
            <stop offset="95%" stopColor="#22c55e" stopOpacity={0}/>
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#4A5568" />
        <XAxis dataKey="time" stroke="#A0AEC0" name="Year" type="number" domain={[-500, 2025]} ticks={[-500, 0, 500, 1000, 1500, 2025]} />
        <YAxis stroke="#A0AEC0" domain={[0, 'dataMax + 0.2']} />
        <Tooltip
            contentStyle={{
              backgroundColor: 'rgba(31, 41, 55, 0.8)',
              borderColor: '#4A5568',
              color: '#F7FAFC'
            }}
            formatter={(value: number, name: string, props: any) => [`${(value * 100).toFixed(2)}% (Year ${props.payload.time})`, "Return"]}
        />
        <Legend verticalAlign="top" height={36}/>
        <Area type="monotone" dataKey="cumulativeReturn" name="Cumulative Return" stroke="#22c55e" fillOpacity={1} fill="url(#colorHistory)" />
      </AreaChart>
    </ResponsiveContainer>
  );
};

export default HistoricalCoherenceChart;
