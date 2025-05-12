import React, { useEffect, useState, useMemo, useCallback, useRef } from 'react';
import axios from 'axios';
import NodeStatus from '../NodeStatus';
import MetricChart from '../MetricChart';
import ControlPanel from './ControlPanel/ControlPanel';
import {
  API_BASE_URL,
  CHART_PALETTE,
  MAX_NODES,
  METRIC_KEYS,
  getDisplayName
} from '../../constants';
import useNodeStatus from '../../hooks/useNodeStatus';
import { buildChartData } from '../../utils/chartUtils';
import '../../App.css';
import DockerLogs from "./ContainerLog/ContainerLog";

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
  const [selectedNode, setSelectedNode] = useState(null);
  const wsRef = useRef(null);

  const fetchNodeStatus = useNodeStatus(setNodeStatus, setError, setNodeUptimes);

  const nodeNames = useMemo(() => {
    const nodes = new Set();
    metrics.forEach(m => m.node && nodes.add(m.node));
    nodeStatus.forEach(({ name }) => name && nodes.add(name));
    return Array.from(nodes).sort();
  }, [metrics, nodeStatus]);

  const manageNodes = useCallback(async (endpoint, data, errorMessage) => {
    try {
      setIsLoading(true);
      setError('');
      await axios.post(`${API_BASE_URL}${endpoint}`, data);
      await fetchNodeStatus();
    } catch (err) {
      console.error(`Node management error (${endpoint}):`, err);
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, [fetchNodeStatus]);

  const startNodes = useCallback(async () => {
    setMetrics([]);
    setSelectedMetrics([]);
    await manageNodes(`/nodes/start`, { count: nodeCount }, 'Failed to start nodes');
    setWsTrigger(prev => prev + 1);
    await new Promise(resolve => setTimeout(resolve, 500));
    await fetchNodeStatus();
  }, [manageNodes, nodeCount, fetchNodeStatus]);

  const stopNodes = useCallback(() => {
    return manageNodes('/nodes/stop', {}, 'Failed to stop nodes');
  }, [manageNodes]);

  const clearStats = useCallback(() => {
    setMetrics([]);
    setNodeStatus([]);
    setNodeUptimes({});
    setSelectedMetrics([]);
    fetchNodeStatus();
  }, []);

  const toggleMetric = (field) => {
    setSelectedMetrics(prev =>
      prev.includes(field)
        ? prev.filter(m => m !== field)
        : [...prev, field]
    );
  };

  useEffect(() => {
    const interval = setInterval(fetchNodeStatus, 1000);
    const ws = new WebSocket('ws://localhost:8000/metrics/ws');
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const newMetrics = JSON.parse(event.data);
        if (!Array.isArray(newMetrics)) return;
        setMetrics(prev => [...prev, ...newMetrics]);
      } catch (err) {
        console.error('WebSocket message error:', err);
        setError('Failed to parse WebSocket data');
      }
    };

    ws.onerror = () => setError('WebSocket connection error');

    return () => {
      clearInterval(interval);
      if (ws) ws.close();
    };
  }, [fetchNodeStatus, wsTrigger]);

  useEffect(() => {
    const interval = setInterval(() => {
      setNodeUptimes((prev) => {
        const now = Date.now();
        const updated = { ...prev };
        Object.entries(prev).forEach(([name, info]) => {
          if (info.isRunning && info.startTime) {
            updated[name] = {
              ...info,
              elapsedMs: now - info.startTime,
            };
          }
        });
        return updated;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <h1>DFL Mixnet Dashboard</h1>
      </header>

      <div className="dashboard-content">
        <ControlPanel
          nodeCount={nodeCount}
          setNodeCount={setNodeCount}
          maxNodes={MAX_NODES}
          displayMode={config.displayMode}
          setDisplayMode={(mode) => setConfig(prev => ({ ...prev, displayMode: mode }))}
          selectedMetrics={selectedMetrics}
          metricKeys={METRIC_KEYS}
          getDisplayName={getDisplayName}
          onStart={startNodes}
          onStop={stopNodes}
          onClear={clearStats}
          onToggleMetric={toggleMetric}
          isLoading={isLoading}
        />

        {error && <div className="status-message error">{error}</div>}

        {isLoading && (
          <div className="overlay-loading">
            <div className="spinner" />
            <div>Loading...</div>
          </div>
        )}

        <main className="dashboard-main">
          <div className="dashboard-row">
            <div className="node-status-container">
              <NodeStatus
                nodeNames={nodeNames}
                nodeStatus={nodeStatus}
                nodeUptimes={nodeUptimes}
                palette={CHART_PALETTE}
                onSelectNode={setSelectedNode}
              />
            </div>
            <div className="docker-logs-container">
              {selectedNode ? (
                <DockerLogs containerName={selectedNode} />
              ) : (
                <div className="docker-logs-placeholder">Select a node to view logs</div>
              )}
            </div>
          </div>

          <div className="metric-charts-grid">
            {selectedMetrics.map((metricKey) => (
              <MetricChart
                key={metricKey}
                metricKey={metricKey}
                title={getDisplayName(metricKey)}
                chartData={buildChartData(metrics, metricKey)}
                nodeNames={nodeNames}
                palette={CHART_PALETTE}
                displayMode={config.displayMode}
              />
            ))}
          </div>
        </main>
      </div>

      <footer className="dashboard-footer">
        <p>Data refreshes every 2 seconds | All metrics cached locally</p>
      </footer>
    </div>
  );
};

export default Dashboard;
