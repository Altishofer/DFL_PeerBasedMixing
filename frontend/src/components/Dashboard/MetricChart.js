import React, { useEffect, useState } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';

const MetricChart = ({ metricKey, title, nodeNames, chartData, palette }) => {
  const [data, setData] = useState(chartData);

  useEffect(() => {
    setData(chartData);
  }, [chartData]);

  return (
    <div className="dashboard-card">
      <h3>{title}</h3>
      {!data.length ? (
        <p className="no-data">No data available</p>
      ) : (
        <div style={{ height: '240px', width: '100%' }}>
          <ResponsiveContainer width="100%" height={260}>
          <AreaChart
            data={data}
            margin={{ top: 10, right: 20, left: 10, bottom: 30 }}
          >
            <CartesianGrid stroke="#ccc" strokeDasharray="3 3" />
            <XAxis
              dataKey="timestamp"
              tick={{
                fontSize: 11,
                fill: 'var(--color-text-muted)',
                angle: -25,
                textAnchor: 'end',
              }}
              interval={Math.floor(data.length / 10)}
              height={40}
              stroke="var(--color-border)"
            />
            <YAxis
              stroke="var(--color-border)"
              tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }}
              tickFormatter={(v) => typeof v === 'number' ? v.toLocaleString() : v}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'var(--color-surface)',
                borderColor: 'var(--color-border)',
                borderRadius: '8px',
                fontSize: '0.85rem',
                boxShadow: 'var(--shadow-sm)',
                padding: '0.75rem'
              }}
              labelStyle={{
                fontWeight: 600,
                color: 'var(--color-title)'
              }}
            />
            <Legend
              verticalAlign="top"
              align="center"
              height={30}
              wrapperStyle={{
                marginBottom: '-10px',
                fontSize: '0.85rem',
                color: 'var(--color-muted)'
              }}
            />
            {nodeNames.map((node, index) => (
              <Area
                key={node}
                type="linear"
                dataKey={node}
                name={node}
                stroke={palette[index % palette.length]}
                fill={palette[index % palette.length]}
                strokeWidth={1.5}
                fillOpacity={0.15}
                dot={false}
                activeDot={{ r: 3 }}
                connectNulls
                isAnimationActive={false}
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
