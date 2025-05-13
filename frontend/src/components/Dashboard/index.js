import React, { useEffect, useState, useMemo, useCallback, useRef } from 'react';
import { Tabs, TabList, Tab, TabPanel } from 'react-tabs';
import 'react-tabs/style/react-tabs.css';
import axios from 'axios';
import NodeStatus from '../NodeStatus';
import MetricChart from '../MetricChart';
import ControlPanel from './ControlPanel/ControlPanel';
import BasicControls from "./ControlPanel/sections/BasicControl";
import SimulationSettings from "./ControlPanel/sections/SimulationSettings";
import MetricSelection from "./ControlPanel/sections/MetricSelection";
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
import DockerLogs from './ContainerLog/ContainerLog';
import { toast, ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

const Dashboard = () => {
  const [nodeCount, setNodeCount] = useState(4);
  const [nodeStatus, setNodeStatus] = useState([]);
  const [metrics, setMetrics] = useState([]);
  const [selectedMetrics, setSelectedMetrics] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [nodeUptimes, setNodeUptimes] = useState({});
  const [config, setConfig] = useState({
    displayMode: 'raw',
    rounds: 10,
    exitNodes: [],
    joinNodes: []
  });
  const [wsTrigger, setWsTrigger] = useState(0);
  const [selectedNode, setSelectedNode] = useState(null);
  const [activeRound, setActiveRound] = useState(0);
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
      const response = await axios.post(`${API_BASE_URL}${endpoint}`, data);
      await fetchNodeStatus();
      return response.data;
    } catch (err) {
      console.error(`Node management error (${endpoint}):`, err);
      setError(errorMessage);
      toast.error(errorMessage);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [fetchNodeStatus]);

  const startNodes = useCallback(async () => {
    setMetrics([]);
    setSelectedMetrics([]);
    setActiveRound(0);

    const data = {
      count: nodeCount,
      rounds: config.rounds,
      exitNodes: config.exitNodes,
      joinNodes: config.joinNodes
    };

    await manageNodes(`/nodes/start`, data, 'Failed to start nodes');
    setWsTrigger(prev => prev + 1);
    await new Promise(resolve => setTimeout(resolve, 500));
    await fetchNodeStatus();
  }, [manageNodes, nodeCount, fetchNodeStatus, config]);

  const stopNodes = useCallback(() => {
    return manageNodes('/nodes/stop', {}, 'Failed to stop nodes');
  }, [manageNodes]);

  const clearStats = useCallback(() => {
    setMetrics([]);
    setNodeStatus([]);
    setNodeUptimes({});
    setSelectedMetrics([]);
    setActiveRound(0);
    fetchNodeStatus();
  }, [fetchNodeStatus]);

  const toggleMetric = (field) => {
    setSelectedMetrics(prev =>
      prev.includes(field)
        ? prev.filter(m => m !== field)
        : [...prev, field]
    );
  };

  const updateExitNodes = useCallback((_, count) => {
    setConfig(prev => ({
      ...prev,
      exitNodes: count > 0 ? [{ round: 1, count }] : []
    }));
  }, []);

  const updateJoinNodes = useCallback((_, count) => {
    setConfig(prev => ({
      ...prev,
      joinNodes: count > 0 ? [{ round: 1, count }] : []
    }));
  }, []);

  useEffect(() => {
    let ws;
    let reconnectTimeout = null;
    let reconnectAttempts = 0;

    const connect = () => {
      if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return;

      ws = new WebSocket('ws://localhost:8000/metrics/ws');
      wsRef.current = ws;

      ws.onopen = () => {
        reconnectAttempts = 0;
        setError('');
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          const newMetrics = Array.isArray(data) ? data : data?.data;
          if (Array.isArray(newMetrics)) {
            setMetrics(prev => [...prev, ...newMetrics]);
          }
        } catch (err) {
          console.error('WebSocket message error:', err);
          setError('Failed to parse WebSocket data');
          toast.error('Failed to parse WebSocket data');
        }
      };

      ws.onerror = () => {
        setError('WebSocket connection error');
        toast.error('WebSocket connection error');
        ws.close();
      };

      ws.onclose = () => {
        setError('WebSocket disconnected. Attempting to reconnect...');
        toast.warn('WebSocket disconnected. Reconnecting...');
        reconnectAttempts += 1;
        const timeout = Math.min(30000, 1000 * 2 ** reconnectAttempts);
        reconnectTimeout = setTimeout(connect, timeout);
      };
    };

    connect();
    const statusInterval = setInterval(fetchNodeStatus, 10000);
    const uptimeInterval = setInterval(() => {
      setNodeUptimes(prev => {
        const updatedUptimes = {};
        Object.keys(prev).forEach((name) => {
          const { startTime, isRunning } = prev[name];
          if (isRunning && startTime) {
            updatedUptimes[name] = {
              ...prev[name],
              elapsedMs: Date.now() - startTime,
            };
          }
        });
        return { ...prev, ...updatedUptimes };
      });
    }, 1000);

    return () => {
      clearInterval(statusInterval);
      clearInterval(uptimeInterval);
      clearTimeout(reconnectTimeout);
      if (ws) {
        ws.onopen = ws.onmessage = ws.onerror = ws.onclose = null;
        ws.close();
      }
    };
  }, [fetchNodeStatus, wsTrigger]);

  return (
    <div className="dashboard-container">
      <ToastContainer position="top-right" autoClose={5000} />

      <header className="dashboard-header">
        <div className="header-content">
          <h1>DFL Mixnet Simulation Dashboard</h1>
          <p>Monitor and control your decentralized network simulation in real-time</p>
        </div>
      </header>

      <div className="dashboard-content">
        <Tabs>
  <TabList>
    <Tab>Basic Controls</Tab>
    <Tab>Simulation Settings</Tab>
    <Tab>Metrics Selection</Tab>
    <Tab>Charts</Tab>
    <Tab>Node Logs</Tab>
  </TabList>

<TabPanel>
  <div className="basic-controls-section">
    <div className="basic-controls-container">
      <BasicControls
        onStart={startNodes}
        onStop={stopNodes}
        onClear={clearStats}
        isLoading={isLoading}
      />
    </div>
    <div className="node-status-container">
      <NodeStatus
        nodeNames={nodeNames}
        nodeStatus={nodeStatus}
        nodeUptimes={nodeUptimes}
        palette={CHART_PALETTE}
        onSelectNode={setSelectedNode}
        selectedNode={selectedNode}
      />
    </div>
  </div>
</TabPanel>



  <TabPanel>
    <SimulationSettings
      nodeCount={nodeCount}
      setNodeCount={setNodeCount}
      maxNodes={MAX_NODES}
      rounds={config.rounds}
      setRounds={(r) => setConfig(prev => ({ ...prev, rounds: r }))}
      exitNodes={config.exitNodes}
      updateExitNodes={updateExitNodes}
      joinNodes={config.joinNodes}
      updateJoinNodes={updateJoinNodes}
      displayMode={config.displayMode}
      setDisplayMode={(mode) => setConfig(prev => ({ ...prev, displayMode: mode }))}
      isLoading={isLoading}
    />
  </TabPanel>

  <TabPanel>
    <MetricSelection
      selectedMetrics={selectedMetrics}
      metricKeys={METRIC_KEYS}
      getDisplayName={getDisplayName}
      onToggleMetric={toggleMetric}
    />
  </TabPanel>

  <TabPanel>
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
          activeRound={activeRound}
        />
      ))}
    </div>
  </TabPanel>

  <TabPanel>
    <div className="docker-logs-container">
      <div className="docker-logs-header">
        <h3>Node Logs</h3>
        <strong>{!selectedNode && "Select a node to view logs"}</strong>
      </div>
      <DockerLogs containerName={selectedNode} />
    </div>
  </TabPanel>
</Tabs>


        {error && <div className="status-message error">{error}</div>}
        {isLoading && (
          <div className="overlay-loading">
            <div className="spinner" />
            <div>Loading...</div>
          </div>
        )}
      </div>

      <footer className="dashboard-footer">
        <div className="footer-content">
          <p>DFL Mixnet Simulation Dashboard v1.2.0</p>
          <div className="footer-links">
            <span>Data refreshes every 2 seconds</span>
            <span>•</span>
            <a href="#">Documentation</a>
            <span>•</span>
            <a href="#">API Reference</a>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Dashboard;
