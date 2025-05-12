import React from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';

const MetricChart = ({ metricKey, title, chartData, nodeNames, palette }) => (
  <div className="dashboard-card">
    <h3>{title}</h3>
    {!chartData.length ? (
      <p className="no-data">No data available</p>
    ) : (
      <ResponsiveContainer width="100%" height={280}>
        <AreaChart data={chartData} margin={{ top: 20, right: 30, left: 10, bottom: 20 }}>
          <CartesianGrid stroke="var(--color-grid)" strokeDasharray="2 2" />
          <XAxis
            dataKey="timestamp"
            stroke="var(--color-border)"
            tick={{ fill: 'var(--color-muted)', fontSize: 12 }}
            minTickGap={20}
          />
          <YAxis
            stroke="var(--color-border)"
            tick={{ fill: 'var(--color-muted)', fontSize: 12 }}
            tickFormatter={(v) => typeof v === 'number' ? v.toLocaleString() : v}
            allowDecimals
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'white',
              borderColor: 'var(--color-border)',
              borderRadius: 'var(--radius)',
              fontSize: '0.85rem',
              boxShadow: 'var(--shadow-md)',
              padding: '0.75rem'
            }}
            labelStyle={{ fontWeight: 600, color: 'var(--color-title)' }}
          />
          <Legend wrapperStyle={{ fontSize: '0.8rem', color: 'var(--color-muted)' }} />
          {nodeNames.map((node, index) => (
            <Area
              key={node}
              type="monotone"
              dataKey={node}
              name={node}
              stroke={palette[index % palette.length]}
              fill={palette[index % palette.length]}
              strokeWidth={1.5}
              fillOpacity={0.1}
              dot={false}
              activeDot={{ r: 3 }}
              connectNulls
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    )}
  </div>
);

export default MetricChart;
