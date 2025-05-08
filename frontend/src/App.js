// src/App.js
import './App.css';
import { useEffect, useState, useMemo } from 'react';
import axios from 'axios';
import {
  LineChart, Line,
  AreaChart, Area,
  BarChart, Bar,
  XAxis, YAxis,
  CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';

const BACKEND = 'http://localhost:8000';

function App() {
  const [nodes, setNodes] = useState(2);
  const [status, setStatus] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [log, setLog] = useState([]);

  const fetchStatus = async () => {
    try {
      const res = await axios.get(`${BACKEND}/status`);
      setStatus(res.data?.node_status || res.data || []);
      setError('');
    } catch {
      setStatus([]);
      setError('Failed to fetch node status.');
    }
  };

  const fetchMetrics = async () => {
    try {
      const res = await axios.get(`${BACKEND}/metrics`);
      setLog(res.data || []);
    } catch {
      setError('Failed to fetch metrics log.');
    }
  };

  const startNodes = async () => {
    try {
      setLoading(true);
      setError('');
      setLog([]);
      setStatus([]);
      await axios.post(`${BACKEND}/start/${nodes}`);
      await fetchStatus();
    } catch {
      setError('Failed to start nodes.');
    } finally {
      setLoading(false);
    }
  };

  const stopNodes = async () => {
    try {
      setLoading(true);
      setError('');
      await axios.post(`${BACKEND}/stop`);
      setLog([]);
      setStatus([]);
    } catch {
      setError('Failed to stop nodes.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    fetchMetrics();
    const id = setInterval(() => {
      fetchStatus();
      fetchMetrics();
    }, 1000);
    return () => clearInterval(id);
  }, []);

  const palette = ['#2980b9', '#27ae60', '#f39c12', '#e74c3c', '#8e44ad', '#16a085', '#c0392b', '#d35400'];
  const colour = i => palette[i % palette.length];

  const nodeNames = useMemo(() => {
    const set = new Set();
    log.forEach(e => {
      if (e.node) set.add(e.node);
    });
    return [...set];
  }, [log]);

const buildChartData = (metric) => {
  const grouped = {};
  log.forEach(e => {
    if (!e.timestamp || e.field !== metric) return;
    const ts = new Date(e.timestamp).toLocaleTimeString();
    if (!grouped[ts]) grouped[ts] = { timestamp: ts };
    if (e.node && e.value !== undefined) {
      grouped[ts][e.node] = e.value;
    }
  });

  // fill missing values with null for each node to ensure lines render
  const allNodes = nodeNames;
  const sorted = Object.values(grouped)
    .sort((a, b) => a.timestamp.localeCompare(b.timestamp))
    .map(row => {
      allNodes.forEach(n => {
        if (!(n in row)) row[n] = null;
      });
      return row;
    });

  return sorted.slice(-50);
};


  const renderChart = (title, metric, Comp) => {
  const data = buildChartData(metric);
  const NodeComponent = Comp === AreaChart ? Area : Comp === BarChart ? Bar : Line;

  return (
    <div className="card">
      <h2>{title}</h2>
      {!data.length
        ? <p>No data.</p>
        : (
          <ResponsiveContainer width="100%" height={280}>
            <Comp data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="timestamp" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Legend />
              {nodeNames.map((n, i) =>
                <NodeComponent
                  key={n}
                  dataKey={n}
                  name={n}
                  stroke={colour(i)}
                  fill={Comp === AreaChart ? colour(i) : undefined}
                  fillOpacity={Comp === AreaChart ? 0.15 : 1}
                  dot={false}
                  barSize={10}
                />
              )}
            </Comp>
          </ResponsiveContainer>
        )}
    </div>
  );
};

  return (
    <div className="container">
      <h1>DFL Mixnet Dashboard</h1>

      <div className="controls">
        <div className="input-card">
          <label>Number&nbsp;of&nbsp;Nodes</label>
          <input
            type="number"
            min="1"
            value={nodes}
            onChange={e => setNodes(+e.target.value)}
            disabled={loading}
          />
        </div>
        <div className="button-group">
          <button className="start" onClick={startNodes} disabled={loading}>Start</button>
          <button className="stop" onClick={stopNodes} disabled={loading}>Stop</button>
        </div>
      </div>

      {loading && <p className="loading">Loading…</p>}
      {error && <p className="error">{error}</p>}

      <div className="grid">
        <div className="card">
          <h2>Node Status</h2>
          {!nodeNames.length
            ? <p>No data.</p>
            : (
              <table>
                <thead><tr><th>Name</th><th>Status</th></tr></thead>
                <tbody>
                  {nodeNames.map((n, i) =>
                    <tr key={n}>
                      <td style={{ color: colour(i) }}>{n}</td>
                      <td>{status.find(s => s.name === n)?.status ?? 'unknown'}</td>
                    </tr>
                  )}
                </tbody>
              </table>
            )}
        </div>

        {renderChart("Messages Sent", "msg_sent", LineChart)}
        {renderChart("Payload Sent", "payload_sent", AreaChart)}
        {renderChart("Messages Received", "msg_recv", LineChart)}
        {renderChart("Errors", "errors", BarChart)}
      </div>
    </div>
  );
}

export default App;
