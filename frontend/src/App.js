import React, { useEffect, useState, useMemo, useCallback, useRef } from 'react';
import axios from 'axios';
import {
  AreaChart, Area,
  XAxis, YAxis,
  CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import './App.css';

const API_BASE_URL = 'http://localhost:8000';
const CHART_PALETTE = ['#3182CE', '#38A169', '#DD6B20', '#805AD5', '#E53E3E', '#D69E2E', '#319795', '#00B5D8'];
const POLL_INTERVAL = 1000;
const MAX_NODES = 10;


const formatMetricTitle = (key) =>
  key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase())
    .replace(/\bCpu\b/, 'CPU')
    .replace(/\bRam\b/, 'RAM');

const Dashboard = () => {
  const [nodeCount, setNodeCount] = useState(4);
  const [nodeStatus, setNodeStatus] = useState([]);
  const [now, setNow] = useState(Date.now());
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [metrics, setMetrics] = useState([]);
  const [selectedMetrics, setSelectedMetrics] = useState([]);
  const seenIdsRef = useRef(new Set());

  const getNodeColor = useCallback(index => CHART_PALETTE[index % CHART_PALETTE.length], []);

  const nodeNames = useMemo(() => {
    const uniqueNodes = new Set();
    metrics.forEach(metric => metric.node && uniqueNodes.add(metric.node));
    return Array.from(uniqueNodes).sort();
  }, [metrics]);

  const formatUptime = (startedAt, isRunning) => {
  if (!startedAt) return 'N/A';
  const start = new Date(startedAt);
  const end = isRunning ? new Date(now) : start;
  const diffMs = end - start;

  const seconds = Math.floor(diffMs / 1000) % 60;
  const minutes = Math.floor(diffMs / (1000 * 60)) % 60;
  const hours = Math.floor(diffMs / (1000 * 60 * 60));

  return `${hours}h ${minutes}m ${seconds}s`;
};

  const uniqueMetricFields = useMemo(() => {
    return [...new Set(metrics.map(m => m.field))].sort();
  }, [metrics]);

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
    () => fetchData('/status', setNodeStatus, 'Failed to fetch node status'),
    [fetchData]
  );

  useEffect(() => {
  const interval = setInterval(() => {
    fetchNodeStatus();
  }, 2000);

  return () => clearInterval(interval);
}, [fetchNodeStatus]);


  const manageNodes = useCallback(async (endpoint, errorMessage) => {
    try {
      setIsLoading(true);
      setError('');
      await axios.post(`${API_BASE_URL}${endpoint}`);
      await fetchNodeStatus();
    } catch (err) {
      console.error(`Error managing nodes (${endpoint}):`, err);
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, [fetchNodeStatus]);

  const startNodes = useCallback(async () => {
    setMetrics([]);
    seenIdsRef.current = new Set();
    await manageNodes(`/start/${nodeCount}`, 'Failed to start nodes');
  }, [manageNodes, nodeCount]);

  const stopNodes = useCallback(
    () => manageNodes('/stop', 'Failed to stop nodes'),
    [manageNodes]
  );

  const clearStats = useCallback(async () => {
    setMetrics([]);
    seenIdsRef.current = new Set();
    await manageNodes('/clear', 'Failed to clear stats');
  }, [manageNodes]);

  useEffect(() => {
  const interval = setInterval(() => {
    setNow(Date.now());
  }, 1000);
  return () => clearInterval(interval);
}, []);


  useEffect(() => {
    if (uniqueMetricFields.length && selectedMetrics.length === 0) {
      setSelectedMetrics(uniqueMetricFields.slice(0, 2));
    }
  }, [uniqueMetricFields]);

  useEffect(() => {
    const loadInitialMetrics = async () => {
      try {
        const { data } = await axios.get(`${API_BASE_URL}/metrics`);
        const unique = [];
        const ids = new Set();

        for (const entry of data) {
          if (entry.id && !ids.has(entry.id)) {
            ids.add(entry.id);
            unique.push(entry);
          }
        }

        seenIdsRef.current = ids;
        setMetrics(unique);
      } catch (err) {
        console.error("Failed to load initial metrics:", err);
        setError("Error loading metrics from server");
      }
    };

    loadInitialMetrics();
    fetchNodeStatus();
  }, [fetchNodeStatus]);

  useEffect(() => {
    fetchNodeStatus();

    const ws = new WebSocket('ws://localhost:8000/ws/metrics');

    ws.onmessage = (event) => {
      try {
        const newMetrics = JSON.parse(event.data);
        if (!Array.isArray(newMetrics) || newMetrics.length === 0) return;

        setMetrics(prev => {
          const filtered = [];

          for (const entry of newMetrics) {
            if (entry.id && !seenIdsRef.current.has(entry.id)) {
              seenIdsRef.current.add(entry.id);
              filtered.push(entry);
            }
          }

          if (filtered.length === 0) return prev;
          return [...prev, ...filtered];
        });
      } catch (err) {
        console.error("Failed to parse WebSocket message:", err);
        setError("Error processing metrics stream");
      }
    };

    ws.onerror = (err) => {
      console.error("WebSocket error:", err);
      setError("WebSocket connection error");
    };

    ws.onclose = () => {
      console.warn("WebSocket connection closed");
    };

    return () => ws.close();
  }, [fetchNodeStatus]);

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
      });
  }, [metrics, nodeNames]);

  const renderMetricChart = (metricKey) => {
    const chartData = buildChartData(metricKey);
    const title = formatMetricTitle(metricKey);

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
                    stroke={getNodeColor(index)}
                    strokeWidth={2}
                    fill={getNodeColor(index)}
                    fillOpacity={0.2}
                    activeDot={{ r: 6, strokeWidth: 1, stroke: getNodeColor(index), fill: '#fff' }}
                    connectNulls
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

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <h1>DFL Mixnet Dashboard</h1>
        <p>Real-time network monitoring and control</p>
      </header>

      <section className="control-panel">
        <div className="control-group">
          <label htmlFor="nodeCount">Nodes to Start</label>
          <input
            id="nodeCount"
            type="number"
            min="1"
            max={MAX_NODES}
            value={nodeCount}
            onChange={(e) => {
              const value = Math.min(MAX_NODES, Math.max(1, parseInt(e.target.value, 10) || 1));
              setNodeCount(value);
            }}
            disabled={isLoading}
          />
        </div>

        <div className="control-group">
          <label>Metrics Display</label>
          <div className="metric-toggle-container">
            {uniqueMetricFields.map(field => {
              const isActive = selectedMetrics.includes(field);
              return (
                <button
                  key={field}
                  className={`metric-toggle ${isActive ? 'active' : ''}`}
                  onClick={() => {
                    setSelectedMetrics(prev =>
                      isActive
                        ? prev.filter(m => m !== field)
                        : [...prev, field]
                    );
                  }}
                >
                  {formatMetricTitle(field)}
                </button>
              );
            })}
          </div>
        </div>

        <div className="action-buttons">
          <button className="action-button start-button" onClick={startNodes} disabled={isLoading}>
            {isLoading ? 'Starting...' : 'Start Network'}
          </button>
          <button className="action-button clear-button" onClick={clearStats} disabled={isLoading}>
            Clear Stats
          </button>
          <button className="action-button stop-button" onClick={stopNodes} disabled={isLoading}>
            Stop Network
          </button>
        </div>
      </section>

      {isLoading && <div className="status-message loading">Processing request...</div>}
      {error && <div className="status-message error">{error}</div>}

      <main className="dashboard-grid">
        <div className="dashboard-card">
          <h3>Node Status</h3>
          {nodeNames.length > 0 ? (
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
                  {nodeNames.map((node, index) => {
                    const statusInfo = nodeStatus.find(({ name }) => name === node);
                    const isRunning = statusInfo?.status === 'running';

                    return (
                      <tr key={node}>
                        <td style={{ color: getNodeColor(index), fontWeight: 500 }}>{node}</td>
                        <td className={`status-${statusInfo?.status?.toLowerCase() ?? 'unknown'}`}>
                          {statusInfo?.status ?? 'Unknown'}
                        </td>
                        <td>{formatUptime(statusInfo?.started_at, isRunning)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="no-data">No active nodes</p>
          )}
        </div>

        {selectedMetrics.map(renderMetricChart)}
      </main>

      <footer className="dashboard-footer">
        <p>Data refreshes every {POLL_INTERVAL / 1000} seconds | All entries are streamed with deduplication</p>
      </footer>
    </div>
  );
};

export default Dashboard;