import React from 'react';
import {
  AreaChart, Area,
  XAxis, YAxis,
  CartesianGrid, Tooltip, Legend
} from 'recharts';
import { ResponsiveContainer } from 'recharts';


const MetricChart = ({ metricKey, title, chartData, nodeNames, palette, displayMode }) => {
  return (
    <div className="dashboard-card" key={metricKey}>
      <h3>{title}</h3>
      {!chartData.length ? (
        <p className="no-data">No data available</p>
      ) : (
        <div className="chart-container">
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={chartData} margin={{ top: 20, right: 20, left: 20, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-grid)" />
              <XAxis dataKey="timestamp" tick={{ fill: 'var(--color-text-muted)' }} stroke="var(--color-border)" />
              <YAxis
                tick={{ fill: 'var(--color-text-muted)' }}
                stroke="var(--color-border)"
                tickFormatter={value => typeof value === 'number' ? value.toLocaleString() : value}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'var(--color-surface)',
                  borderColor: 'var(--color-border)',
                  borderRadius: 'var(--border-radius-sm)',
                  boxShadow: 'var(--shadow-sm)'
                }}
              />
              <Legend />
              {nodeNames.map((node, index) => (
                <Area
                  key={node}
                  type="monotoneX"
                  dataKey={node}
                  name={node}
                  stroke={palette[index % palette.length]}
                  strokeWidth={2}
                  fill={palette[index % palette.length]}
                  fillOpacity={0.2}
                  activeDot={{ r: 6 }}
                  connectNulls
                  dot={{ r: 1 }}
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
};

export default MetricChart;