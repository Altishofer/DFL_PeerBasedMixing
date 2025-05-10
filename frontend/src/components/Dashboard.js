import React, { useEffect, useState, useMemo, useCallback, useRef } from 'react';
import axios from 'axios';
import { ResponsiveContainer } from 'recharts';
import '../App.css';
import ControlPanel from './ControlPanel';
import NodeMetrics from './NodeMetrics';

const API_BASE_URL = 'http://localhost:8000';
const CHART_PALETTE = ['#3182CE', '#38A169', '#DD6B20', '#805AD5', '#E53E3E', '#D69E2E', '#319795', '#00B5D8'];

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

  const calculateElapsedTime = useCallback((startTime) => {
    return Date.now() - startTime;
  }, []);

  const fetchNodeStatus = useCallback(async () => {
    try {
      const { data } = await axios.get(`${API_BASE_URL}/status`);
      const newStatus = data?.node_status || data || [];
      setNodeStatus(newStatus);
      setError('');

      const now = Date.now();
      setNodeUptimes(prev => {
        const updated = { ...prev };
        const seen = new Set();

        for (const { name, status, started_at } of newStatus) {
          if (!name) continue;
          const isRunning = status?.toLowerCase() === 'running';
          const startTime = started_at ? new Date(started_at).getTime() : null;

          seen.add(name);

          if (!updated[name]) {
            updated[name] = {
              startTime,
              elapsedMs: isRunning ? calculateElapsedTime(startTime) : 0,
              isRunning,
              lastUpdate: now
            };
          } else {
            const prevInfo = updated[name];
            let elapsedMs = prevInfo.elapsedMs;

            if (prevInfo.isRunning && !isRunning) {
              elapsedMs += now - prevInfo.lastUpdate;
            }

            updated[name] = {
              ...prevInfo,
              startTime: startTime ?? prevInfo.startTime,
              elapsedMs,
              isRunning,
              lastUpdate: now
            };
          }
        }

        for (const name of Object.keys(updated)) {
          if (!seen.has(name)) {
            const info = updated[name];
            if (info.isRunning) {
              updated[name] = {
                ...info,
                isRunning: false,
                elapsedMs: info.elapsedMs + (now - info.lastUpdate),
                lastUpdate: now
              };
            }
          }
        }

        localStorage.setItem('nodeUptimes', JSON.stringify(updated));
        return updated;
      });
    } catch (err) {
      console.error('Error fetching node status:', err);
      setError('Failed to fetch node status');
    }
  }, [calculateElapsedTime]);

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

  // Define manageNodes here
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
    setSelectedMetrics([]);
    await manageNodes(`/start/${nodeCount}`, 'Failed to start nodes');
    setWsTrigger(prev => prev + 1);
    await new Promise(resolve => setTimeout(resolve, 500));
    await loadInitialState();
  }, [manageNodes, nodeCount, loadInitialState]);

  const stopNodes = useCallback(() => manageNodes('/stop', 'Failed to stop nodes'), [manageNodes]);

  const clearStats = useCallback(() => {
    setMetrics([]);
    setNodeStatus([]);
    setNodeUptimes({});
    seenIdsRef.current = new Set();
    setSelectedMetrics([]);
    localStorage.removeItem('nodeUptimes');
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

  const handleMetricToggle = useCallback((field) => {
    setSelectedMetrics(prev =>
      prev.includes(field)
        ? prev.filter(m => m !== field)
        : [...prev, field]
    );
  }, []);

  useEffect(() => {
    loadInitialState();
    const statusInterval = setInterval(fetchNodeStatus, 2000);
    wsRef.current = new WebSocket('ws://localhost:8000/ws/metrics');

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

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <h1>DFL Mixnet Dashboard</h1>
        <p>Real-time network monitoring and control</p>
      </header>

      <ControlPanel
        nodeCount={nodeCount}
        setNodeCount={setNodeCount}
        config={config}
        setConfig={setConfig}
        selectedMetrics={selectedMetrics}
        handleMetricToggle={handleMetricToggle}
        startNodes={startNodes}
        stopNodes={stopNodes}
        clearStats={clearStats}
        isLoading={isLoading}
      />

      {isLoading && (
        <div className="overlay-loading">
          <div className="spinner" />
          <div>Loading...</div>
        </div>
      )}

      {error && <div className="status-message error">{error}</div>}

      <NodeMetrics
        nodeNames={nodeNames}
        nodeStatus={nodeStatus}
        nodeUptimes={nodeUptimes}
        selectedMetrics={selectedMetrics}
        buildChartData={buildChartData}
        config={config}
        CHART_PALETTE={CHART_PALETTE}
      />

      <footer className="dashboard-footer">
        <p>Data refreshes every 2 seconds | All entries are streamed with deduplication</p>
      </footer>
    </div>
  );
};

export default Dashboard;
