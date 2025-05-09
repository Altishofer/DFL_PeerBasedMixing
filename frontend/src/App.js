import { useEffect, useState, useMemo, useCallback } from 'react';
import axios from 'axios';
import {
  AreaChart, Area,
  XAxis, YAxis,
  CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import './App.css';

const API_BASE_URL = 'http://localhost:8000';
const CHART_PALETTE = ['#2980b9', '#27ae60', '#f39c12', '#e74c3c', '#8e44ad', '#16a085', '#c0392b', '#d35400'];
const DATA_LIMIT = 200;
const POLL_INTERVAL = 1000;

const formatUptime = (startedAt, frozen = false) => {
  const start = new Date(startedAt);
  const end = frozen ? new Date(startedAt) : new Date();
  const diffMs = end - start;

  const seconds = Math.floor(diffMs / 1000) % 60;
  const minutes = Math.floor(diffMs / (1000 * 60)) % 60;
  const hours = Math.floor(diffMs / (1000 * 60 * 60));

  return `${hours}h ${minutes}m ${seconds}s`;
};

const Dashboard = () => {
  const [nodeCount, setNodeCount] = useState(2);
  const [nodeStatus, setNodeStatus] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [metrics, setMetrics] = useState([]);

  const getNodeColor = useCallback((index) => CHART_PALETTE[index % CHART_PALETTE.length], []);

  const fetchData = useCallback(async (endpoint, setData, errorMessage) => {
    try {
      const { data } = await axios.get(`${API_BASE_URL}${endpoint}`);
      setData(data?.node_status || data || []);
      setError('');
    } catch (err) {
      console.error(`Error fetching ${endpoint}:`, err);
      setError(errorMessage);
    }
  }, []);

  const fetchNodeStatus = useCallback(
    () => fetchData('/status', setNodeStatus, 'Failed to fetch node status. Please ensure the backend is running and accessible.'),
    [fetchData]
  );

  const fetchMetricsData = useCallback(
    () => fetchData('/metrics', (data) => {
      setMetrics(data || []);
    }, 'Failed to fetch metrics. Please ensure the backend is running and accessible.'),
    [fetchData]
  );

  const manageNodes = useCallback(async (endpoint, errorMessage) => {
    try {
      setIsLoading(true);
      setError('');
      setMetrics([]);
      setNodeStatus([]);
      await axios.post(`${API_BASE_URL}${endpoint}`);
      await fetchNodeStatus();
    } catch (err) {
      console.error(`Error managing nodes (${endpoint}):`, err);
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, [fetchNodeStatus]);

  const startNodes = useCallback(
    () => manageNodes(`/start/${nodeCount}`, 'Failed to start nodes. Please check backend logs.'),
    [manageNodes, nodeCount]
  );

  const stopNodes = useCallback(
    () => manageNodes('/stop', 'Failed to stop nodes. Please check backend logs.'),
    [manageNodes]
  );

  const clearStats = useCallback(
    () => manageNodes('/clear', 'Failed to clear stats. Please check backend logs.'),
    [manageNodes]
  );

  useEffect(() => {
    fetchNodeStatus();
    fetchMetricsData();

    const pollId = setInterval(() => {
      fetchNodeStatus();
      fetchMetricsData();
    }, POLL_INTERVAL);

    return () => clearInterval(pollId);
  }, [fetchNodeStatus, fetchMetricsData]);

  const nodeNames = useMemo(() => {
    const uniqueNodes = new Set();
    metrics.forEach(metric => metric.node && uniqueNodes.add(metric.node));
    return Array.from(uniqueNodes).sort();
  }, [metrics]);

  const buildChartData = useCallback((metricType) => {
    const groupedData = {};

    metrics.forEach(({ timestamp, field, node, value }) => {
      if (!timestamp || field !== metricType) return;

      const dateObj = new Date(timestamp);
      const timeKey = dateObj.toISOString();

      if (!groupedData[timeKey]) {
        groupedData[timeKey] = {
          timestamp: dateObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
          originalTimestamp: dateObj,
        };
      }
      if (node && value !== undefined) {
        groupedData[timeKey][node] = Number(value);
      }
    });

    return Object.values(groupedData)
      .sort((a, b) => a.originalTimestamp - b.originalTimestamp)
      .map(row => {
        nodeNames.forEach(node => {
          if (!(node in row)) {
            row[node] = null;
          }
        });
        delete row.originalTimestamp;
        return row;
      })
      .slice(-DATA_LIMIT);
  }, [metrics, nodeNames]);

  const renderMetricChart = (title, metricKey) => {
    const chartData = buildChartData(metricKey);

    return (
      <div className="dashboard-card" key={metricKey}>
        <h3>{title}</h3>
        {!chartData.length ? (
          <p className="no-data">No data available for {title.toLowerCase()}</p>
        ) : (
          <div style={{ width: '100%', height: '280px' }}>
            <ResponsiveContainer>
              <AreaChart
                data={chartData}
                margin={{ top: 20, right: 20, left: 20, bottom: 20 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-grid)" />
                <XAxis
                  dataKey="timestamp"
                  fontSize="0.75rem"
                  tick={{ fill: 'var(--color-text-muted)' }}
                  stroke="var(--color-border)"
                />
                <YAxis
                  allowDecimals={false}
                  fontSize="0.75rem"
                  tick={{ fill: 'var(--color-text-muted)' }}
                  stroke="var(--color-border)"
                  tickFormatter={(value) => typeof value === 'number' ? value.toLocaleString() : value}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'var(--color-surface)',
                    borderColor: 'var(--color-border)',
                    borderRadius: 'var(--border-radius-sm)',
                    boxShadow: 'var(--shadow-sm)'
                  }}
                  itemStyle={{ color: 'var(--color-text)' }}
                  cursor={{ stroke: 'var(--color-primary)', strokeWidth: 1, strokeDasharray: '3 3' }}
                />
                <Legend wrapperStyle={{ fontSize: "0.85rem", paddingTop: "10px" }} />
                {nodeNames.map((node, index) => (
                  <Area
                    key={node}
                    type="monotoneX"
                    dataKey={node}
                    name={node}
                    stroke={getNodeColor(index)}
                    strokeWidth={2}
                    fill={getNodeColor(index)}
                    fillOpacity={0.25}
                    activeDot={{ r: 6, strokeWidth: 1, stroke: getNodeColor(index), fill: '#fff' }}
                    connectNulls={true}
                    dot={false}
                  />
                ))}
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    );
  };

  const uniqueMetricFields = useMemo(() => {
    return [...new Set(metrics.map(m => m.field))].sort();
  }, [metrics]);

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <h1>DFL Mixnet Dashboard</h1>
      </header>

      <section className="control-panel">
        <div className="control-group">
          <label htmlFor="nodeCount">Number of Nodes to Start</label>
          <input
            id="nodeCount"
            type="number"
            min="1"
            max="10"
            value={nodeCount}
            onChange={(e) => setNodeCount(Math.max(1, parseInt(e.target.value, 10) || 1))}
            disabled={isLoading}
          />
        </div>
        <div className="action-buttons">
          <button className="action-button start-button" onClick={startNodes} disabled={isLoading}>
            {isLoading ? 'Starting...' : 'Start Network'}
          </button>
          <button className="action-button clear-button" onClick={clearStats} disabled={isLoading}>
            {isLoading ? 'Cleaning...' : 'Clear Stats'}
          </button>
          <button className="action-button stop-button" onClick={stopNodes} disabled={isLoading}>
            {isLoading ? 'Stopping...' : 'Stop Network'}
          </button>
        </div>
      </section>

      {isLoading && <div className="status-message loading">Processing request, please wait...</div>}
      {error && <div className="status-message error">{error}</div>}

      <main className="dashboard-grid">
        <div className="dashboard-card">
          <h3>Node Status</h3>
          {!nodeStatus.length && !nodeNames.length ? (
            <p className="no-data">No nodes active or status unavailable.</p>
          ) : (
            <div className="status-table-container">
              <table>
                <thead>
                  <tr>
                    <th>Node</th>
                    <th>Status</th>
                    <th>Uptime</th>
                  </tr>
                </thead>
                <tbody>
                  {nodeNames.length > 0 ? nodeNames.map((node, index) => {
                    const statusInfo = nodeStatus.find(({ name }) => name === node);
                    const isRunning = statusInfo?.status === 'running';
                    const uptime = statusInfo?.started_at
                      ? formatUptime(statusInfo.started_at, !isRunning)
                      : 'N/A';

                    return (
                      <tr key={node}>
                        <td style={{ color: getNodeColor(index), fontWeight: '500' }}>{node}</td>
                        <td className={`status-${statusInfo?.status?.toLowerCase() ?? 'unknown'}`}>
                          {statusInfo?.status ?? 'Unknown'}
                        </td>
                        <td>{uptime}</td>
                      </tr>
                    );
                  }) : (
                    <tr>
                      <td colSpan="3" className="no-data">Fetching status or no nodes configured.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {uniqueMetricFields.map((metricKey) => {
          const title = metricKey
            .replace(/_/g, ' ')
            .replace(/\b\w/g, c => c.toUpperCase());
          return renderMetricChart(title, metricKey);
        })}
      </main>

      <footer className="dashboard-footer">
        <p>Data polls every {POLL_INTERVAL / 1000}s. Displaying last {DATA_LIMIT} data points per metric.</p>
      </footer>
    </div>
  );
};

export default Dashboard;
