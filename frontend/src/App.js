// src/App.js
import { useEffect, useState, useMemo, useCallback } from 'react';
import axios from 'axios';
import {
  LineChart, Line,
  AreaChart, Area,
  BarChart, Bar,
  XAxis, YAxis,
  CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import './App.css';

const API_BASE_URL = 'http://localhost:8000';
const CHART_PALETTE = ['#2980b9', '#27ae60', '#f39c12', '#e74c3c', '#8e44ad', '#16a085', '#c0392b', '#d35400'];
const DATA_LIMIT = 50;
const POLL_INTERVAL = 1000;

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
    } catch {
      setError(errorMessage);
      setData([]);
    }
  }, []);

  const fetchNodeStatus = useCallback(
    () => fetchData('/status', setNodeStatus, 'Failed to fetch node status'),
    [fetchData]
  );

  const fetchMetricsData = useCallback(
    () => fetchData('/metrics', setMetrics, 'Failed to fetch metrics'),
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
    } catch {
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, [fetchNodeStatus]);

  const startNodes = useCallback(
    () => manageNodes(`/start/${nodeCount}`, 'Failed to start nodes'),
    [manageNodes, nodeCount]
  );

  const stopNodes = useCallback(
    () => manageNodes('/stop', 'Failed to stop nodes'),
    [manageNodes]
  );

  useEffect(() => {
    fetchNodeStatus();
    fetchMetricsData();

    const pollInterval = setInterval(() => {
      fetchNodeStatus();
      fetchMetricsData();
    }, POLL_INTERVAL);

    return () => clearInterval(pollInterval);
  }, [fetchNodeStatus, fetchMetricsData]);

  const nodeNames = useMemo(() => {
    const uniqueNodes = new Set();
    metrics.forEach(metric => metric.node && uniqueNodes.add(metric.node));
    return Array.from(uniqueNodes);
  }, [metrics]);

  const buildChartData = useCallback((metricType) => {
    const groupedData = {};

    metrics.forEach(({ timestamp, field, node, value }) => {
      if (!timestamp || field !== metricType) return;

      const timeKey = new Date(timestamp).toLocaleTimeString();
      if (!groupedData[timeKey]) groupedData[timeKey] = { timestamp: timeKey };
      if (node && value !== undefined) groupedData[timeKey][node] = value;
    });

    return Object.values(groupedData)
      .sort((a, b) => a.timestamp.localeCompare(b.timestamp))
      .map(row => {
        nodeNames.forEach(node => !(node in row) && (row[node] = null));
        return row;
      })
      .slice(-DATA_LIMIT);
  }, [metrics, nodeNames]);

  const renderChart = (title, metric, ChartComponent) => {
    const chartData = buildChartData(metric);
    const DataComponent = ChartComponent === AreaChart ? Area :
                         ChartComponent === BarChart ? Bar : Line;

    return (
      <div className="dashboard-card">
        <h3>{title}</h3>
        {!chartData.length ? (
          <p className="no-data">No data available</p>
        ) : (
          <ResponsiveContainer width="100%" height={280}>
            <ChartComponent data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="timestamp" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Legend />
              {nodeNames.map((node, index) => (
                <DataComponent
                  key={node}
                  dataKey={node}
                  name={node}
                  stroke={getNodeColor(index)}
                  fill={ChartComponent === AreaChart ? getNodeColor(index) : undefined}
                  fillOpacity={ChartComponent === AreaChart ? 0.15 : 1}
                  dot={false}
                  barSize={10}
                />
              ))}
            </ChartComponent>
          </ResponsiveContainer>
        )}
      </div>
    );
  };

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <h1>DFL Mixnet Dashboard</h1>
      </header>

      <section className="control-panel">
        <div className="control-group">
          <label htmlFor="nodeCount">Number of Nodes</label>
          <input
            id="nodeCount"
            type="number"
            min="1"
            value={nodeCount}
            onChange={(e) => setNodeCount(Math.max(1, +e.target.value))}
            disabled={isLoading}
          />
        </div>
        <div className="action-buttons">
          <button
            className="action-button start-button"
            onClick={startNodes}
            disabled={isLoading}
          >
            Start Network
          </button>
          <button
            className="action-button stop-button"
            onClick={stopNodes}
            disabled={isLoading}
          >
            Stop Network
          </button>
        </div>
      </section>

      {isLoading && <div className="status-message loading">Processing request...</div>}
      {error && <div className="status-message error">{error}</div>}

      <main className="dashboard-grid">
        <div className="dashboard-card">
          <h3>Node Status</h3>
          {!nodeNames.length ? (
            <p className="no-data">No nodes active</p>
          ) : (
            <div className="status-table-container">
              <table>
                <thead>
                  <tr>
                    <th>Node</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {nodeNames.map((node, index) => (
                    <tr key={node}>
                      <td style={{ color: getNodeColor(index) }}>{node}</td>
                      <td>{nodeStatus.find(({ name }) => name === node)?.status ?? 'unknown'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {renderChart("Messages Sent", "msg_sent", LineChart)}
        {renderChart("Payload Sent", "payload_sent", AreaChart)}
        {renderChart("Messages Received", "msg_recv", LineChart)}
        {renderChart("Error Count", "errors", BarChart)}
      </main>
    </div>
  );
};

export default Dashboard;