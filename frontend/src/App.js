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
const MAX_NODES = 10;

const METRIC_FIELDS = {
  cpu_total_ns: 'CPU Usage (ns)',
  memory_mb: 'Memory Usage (MB)'
};

const METRIC_KEYS = Object.keys(METRIC_FIELDS);
const getDisplayName = key => METRIC_FIELDS[key] || null;

const Dashboard = () => {
  const [nodeCount, setNodeCount] = useState(4);
  const [nodeStatus, setNodeStatus] = useState([]);
  const [metrics, setMetrics] = useState([]);
  const [selectedMetrics, setSelectedMetrics] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [nodeUptimes, setNodeUptimes] = useState({});
  const [config, setConfig] = useState({ displayMode: 'raw' });
  const [wsTrigger, setWsTrigger] = useState(0);

  const seenIdsRef = useRef(new Set());
  const wsRef = useRef(null);

  const nodeNames = useMemo(() => {
    const nodes = new Set();
    metrics.forEach(metric => metric.node && nodes.add(metric.node));
    return Array.from(nodes).sort();
  }, [metrics]);

  const fetchNodeStatus = useCallback(async () => {
    try {
      const { data } = await axios.get(`${API_BASE_URL}/nodes/status`);
      const newStatus = Array.isArray(data) ? data : [];
      setNodeStatus(newStatus);
      setError('');

      setNodeUptimes(prev => {
        const updated = { ...prev };
        for (const { name, status, started_at } of newStatus) {
          if (!name) continue;
          const isRunning = status?.toLowerCase() === 'running';
          const startTime = started_at ? new Date(started_at).getTime() : null;
          if (!updated[name]) {
            updated[name] = {
              startTime,
              elapsedMs: 0,
              isRunning
            };
          } else {
            updated[name] = {
              ...updated[name],
              startTime,
              isRunning
            };
          }
        }
        return updated;
      });
    } catch (err) {
      console.error('Error fetching node status:', err);
      setError('Failed to fetch node status');
    }
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      setNodeUptimes(prev => {
        const now = Date.now();
        const updated = {};
        for (const [node, info] of Object.entries(prev)) {
          const shouldUpdate = info.isRunning && info.startTime;
          updated[node] = {
            ...info,
            elapsedMs: shouldUpdate ? now - info.startTime : info.elapsedMs
          };
        }
        return updated;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const manageNodes = useCallback(async (endpoint, errorMessage, data = {}) => {
  try {
    setIsLoading(true);
    setError('');
    await axios.post(`${API_BASE_URL}${endpoint}`, data);
    await fetchNodeStatus();
  } catch (err) {
    console.error(`Error managing nodes (${endpoint}):`, err);
    if (err.response) {
      setError(`Request failed with status ${err.response.status}: ${err.response.data.detail || errorMessage}`);
    } else {
      setError(errorMessage);
    }
  } finally {
    setIsLoading(false);
  }
}, [fetchNodeStatus]);

  const loadInitialState = useCallback(async () => {
    try {
      setIsLoading(true);
      const { data } = await axios.get(`${API_BASE_URL}/metrics`);
      const unique = [];
      const ids = new Set();
      data.forEach(entry => {
        if (entry.id && !ids.has(entry.id)) {
          ids.add(entry.id);
          unique.push(entry);
        }
      });
      seenIdsRef.current = ids;
      setMetrics(unique);
      await fetchNodeStatus();
    } catch (err) {
      console.error("Failed to load initial state:", err);
      setError("Error loading metrics from server");
    } finally {
      setIsLoading(false);
    }
  }, [fetchNodeStatus]);

  const startNodes = useCallback(async () => {
    setMetrics([]);
    seenIdsRef.current = new Set();
    setSelectedMetrics([]);
    await manageNodes(`/nodes/start`, 'Failed to start nodes', { count: nodeCount });
    setWsTrigger(prev => prev + 1);

    await new Promise(resolve => setTimeout(resolve, 500));
    await loadInitialState();
  }, [manageNodes, nodeCount, loadInitialState]);

  const stopNodes = useCallback(() => manageNodes('/nodes/stop', 'Failed to stop nodes'), [manageNodes]);

  const clearStats = useCallback(() => {
    setMetrics([]);
    setNodeStatus([]);
    setNodeUptimes({});
    seenIdsRef.current = new Set();
    setSelectedMetrics([]);
  }, []);

  const buildChartData = useCallback((metricType) => {
    const timeMap = new Map();
    const nodePrevValues = {};

    metrics.forEach(({ timestamp, field, node, value }) => {
      if (!timestamp || field !== metricType) return;

      const dateObj = new Date(timestamp);
      const timeKey = dateObj.getTime();

      if (!timeMap.has(timeKey)) {
        timeMap.set(timeKey, {
          timestamp: dateObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
          originalTimestamp: dateObj
        });
      }

      const timeEntry = timeMap.get(timeKey);
      if (node && value !== undefined) {
        const numVal = Number(value);
        if (config.displayMode === 'delta') {
          const delta = nodePrevValues[node] !== undefined ? numVal - nodePrevValues[node] : 0;
          timeEntry[node] = delta;
          nodePrevValues[node] = numVal;
        } else {
          timeEntry[node] = numVal;
        }
      }
    });

    const result = Array.from(timeMap.values()).sort((a, b) => a.originalTimestamp - b.originalTimestamp);
    result.forEach(row => {
      nodeNames.forEach(node => {
        if (!(node in row)) row[node] = null;
      });
      delete row.originalTimestamp;
    });
    return result;
  }, [metrics, nodeNames, config.displayMode]);

  const renderMetricChart = useCallback((metricKey) => {
    const chartData = buildChartData(metricKey);
    const title = getDisplayName(metricKey);

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
                    stroke={CHART_PALETTE[index % CHART_PALETTE.length]}
                    strokeWidth={2}
                    fill={CHART_PALETTE[index % CHART_PALETTE.length]}
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
  }, [buildChartData, nodeNames]);

  useEffect(() => {
    loadInitialState();

    const statusInterval = setInterval(fetchNodeStatus, 5000);
    wsRef.current = new WebSocket('ws://localhost:8000/metrics/ws');

    wsRef.current.onmessage = (event) => {
      try {
        const newMetrics = JSON.parse(event.data);
        if (!Array.isArray(newMetrics)) return;

        setMetrics(prev => {
          const filtered = [];
          const newIds = new Set(seenIdsRef.current);
          newMetrics.forEach(entry => {
            if (entry.id && !newIds.has(entry.id)) {
              newIds.add(entry.id);
              filtered.push(entry);
            }
          });
          if (!filtered.length) return prev;
          seenIdsRef.current = newIds;
          return [...prev, ...filtered];
        });
      } catch (err) {
        console.error("Failed to parse WebSocket message:", err);
      }
    };

    wsRef.current.onerror = (err) => {
      console.error("WebSocket error:", err);
      setError("WebSocket connection error");
    };

    return () => {
      clearInterval(statusInterval);
      if (wsRef.current) wsRef.current.close();
    };
  }, [fetchNodeStatus, loadInitialState, wsTrigger]);

  const handleMetricToggle = useCallback((field) => {
    setSelectedMetrics(prev =>
      prev.includes(field)
        ? prev.filter(m => m !== field)
        : [...prev, field]
    );
  }, []);

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
          <label>Display Mode</label>
          <select
            value={config.displayMode}
            onChange={(e) => setConfig(prev => ({ ...prev, displayMode: e.target.value }))}
          >
            <option value="raw">Raw Values</option>
            <option value="delta">Difference</option>
          </select>
        </div>

        <div className="control-group">
          <label>Metrics Display</label>
          <div className="metric-toggle-container">
            {METRIC_KEYS.filter(field => getDisplayName(field)).map(field => (
              <button
                key={field}
                className={`metric-toggle ${selectedMetrics.includes(field) ? 'active' : ''}`}
                onClick={() => handleMetricToggle(field)}
              >
                {getDisplayName(field)}
              </button>
            ))}
          </div>
        </div>

        <div className="action-buttons">
          <button className="action-button start-button" onClick={startNodes} disabled={isLoading}>
            {isLoading ? 'Starting...' : 'Start Network'}
          </button>
          <button className="action-button clear-button" onClick={clearStats} disabled={isLoading}>
            Reset
          </button>
          <button className="action-button stop-button" onClick={stopNodes} disabled={isLoading}>
            Stop Network
          </button>
        </div>
      </section>

      {isLoading && (
        <div className="overlay-loading">
          <div className="spinner" />
          <div>Loading...</div>
        </div>
      )}

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
                    const uptimeInfo = nodeUptimes[node];
                    const displayUptime = uptimeInfo ? (() => {
                      const totalMs = uptimeInfo.elapsedMs;
                      const seconds = Math.floor(totalMs / 1000) % 60;
                      const minutes = Math.floor(totalMs / (1000 * 60)) % 60;
                      const hours = Math.floor(totalMs / (1000 * 60 * 60));
                      return `${hours}h ${minutes}m ${seconds}s`;
                    })() : '---';

                    return (
                      <tr key={node}>
                        <td style={{ color: CHART_PALETTE[index % CHART_PALETTE.length], fontWeight: 500 }}>{node}</td>
                        <td className={`status-${statusInfo?.status?.toLowerCase() ?? 'unknown'}`}>
                          {statusInfo?.status ?? 'Unknown'}
                        </td>
                        <td>{displayUptime}</td>
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
        <p>Data refreshes every 2 seconds | All entries are streamed with deduplication</p>
      </footer>
    </div>
  );
};

export default Dashboard;