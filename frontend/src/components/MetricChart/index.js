import React, { useEffect, useState } from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine
} from 'recharts';

const MetricChart = ({ metricKey, title, chartData, nodeNames, palette }) => {
  const [data, setData] = useState(chartData);

  useEffect(() => {
    setData(chartData);
  }, [chartData]);

  return (
    <div className="dashboard-card" style={{ backgroundColor: 'var(--color-bg)', borderRadius: '8px' }}>
      <h3 style={{ color: 'var(--color-title)' }}>{title}</h3>
      {!data.length ? (
        <p className="no-data" style={{ color: 'var(--color-muted)' }}>No data available</p>
      ) : (
        <ResponsiveContainer width="100%" height={280}>
          <AreaChart data={data} margin={{ top: 20, right: 40, left: 20, bottom: 50 }}>
            <CartesianGrid
              stroke="var(--color-grid)"
              strokeDasharray="5 5"
              horizontal={true}
              vertical={true}
            />

            <XAxis
              dataKey="timestamp"
              stroke="var(--color-border)"
              tick={{ fill: 'var(--color-muted)', fontSize: 12, angle: -25, textAnchor: 'end' }}
              minTickGap={20}
              interval={Math.floor(data.length / 10)}
            />
            <YAxis
              stroke="var(--color-border)"
              tick={{ fill: 'var(--color-muted)', fontSize: 12 }}
              tickFormatter={(v) => typeof v === 'number' ? v.toLocaleString() : v}
              allowDecimals
              tickCount={6}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'var(--color-surface)',
                borderColor: 'var(--color-border)',
                borderRadius: '8px',
                fontSize: '0.85rem',
                boxShadow: 'var(--shadow-md)',
                padding: '0.75rem',
              }}
              labelStyle={{ fontWeight: 600, color: 'var(--color-title)' }}
            />
            <Legend
              wrapperStyle={{
                fontSize: '1rem',
                color: 'var(--color-muted)',
                marginTop: '1.5em',
                paddingLeft: '0.5em',
              }}
            />
            {nodeNames.map((node, index) => (
              <Area
                key={node}
                type="monotone"
                dataKey={node}
                name={node}
                stroke={palette[index % palette.length] || `var(--color-area-${(index % 5) + 1})`}
                fill={palette[index % palette.length] || `var(--color-area-${(index % 5) + 1})`}
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
};

export default MetricChart;
