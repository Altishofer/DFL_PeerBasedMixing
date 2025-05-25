import React, { useEffect, useState, useMemo, useCallback, useRef } from 'react';
import { Tabs, TabList, Tab, TabPanel } from 'react-tabs';
import axios from 'axios';
import { toast, ToastContainer } from 'react-toastify';
import 'react-tabs/style/react-tabs.css';
import 'react-toastify/dist/ReactToastify.css';

import NodeStatus from '../NodeStatus';
import MetricChart from '../MetricChart';
import DockerLogs from './ContainerLog/ContainerLog';
import BasicControls from './ControlPanel/sections/BasicControl';
import SimulationSettings from './ControlPanel/sections/SimulationSettings';
import MetricSelection from './ControlPanel/sections/MetricSelection';

import useNodeStatus from '../../hooks/useNodeStatus';
import { buildChartData } from '../../utils/chartUtils';
import {
  API_BASE_URL, CHART_PALETTE, MAX_NODES, METRIC_KEYS, getDisplayName
} from '../../constants';
import '../../App.css';

const defaultConfig = {
  displayMode: 'raw',
  rounds: 10,
  exitNodes: 0,
  joinNodes: 0,
  stream: false
};

const Dashboard = () => {
  const [nodeCount, setNodeCount] = useState(6);
  const [nodeStatus, setNodeStatus] = useState([]);
  const [metrics, setMetrics] = useState([]);
  const [selectedMetrics, setSelectedMetrics] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [nodeUptimes, setNodeUptimes] = useState({});
  const [logsResetCounter, setLogsResetCounter] = useState(0);
  const [config, setConfig] = useState(defaultConfig);
  const [wsTrigger, setWsTrigger] = useState(0);
  const [selectedNode, setSelectedNode] = useState(null);
  const [activeRound, setActiveRound] = useState(0);
  const wsRef = useRef(null);

  const fetchNodeStatus = useNodeStatus(setNodeStatus, setError, setNodeUptimes);

  const updateConfig = useCallback((updates) => {
    setConfig(prev => ({ ...prev, ...updates }));
  }, []);

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
      setError(errorMessage);
      toast.error(errorMessage);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [fetchNodeStatus]);

  const resetDashboard = useCallback(() => {
    setNodeCount(6);
    axios.post(`${API_BASE_URL}/logs/clear`);
    setNodeStatus([]);
    setMetrics([]);
    setSelectedMetrics([]);
    setIsLoading(false);
    setSelectedNode(null);
    setLogsResetCounter(prev => prev + 1);
    setError('');
    setNodeUptimes({});
    setConfig(defaultConfig);
    setActiveRound(0);
    setWsTrigger(prev => prev + 1);
    fetchNodeStatus();
  }, [fetchNodeStatus]);

  const startNodes = useCallback(async () => {
    resetDashboard();
    const data = { count: nodeCount, ...config };
    await manageNodes(`/nodes/start`, data, 'Failed to start nodes');
    await new Promise(resolve => setTimeout(resolve, 3000));
    await fetchNodeStatus();
  }, [nodeCount, config, manageNodes, resetDashboard, fetchNodeStatus]);

  const stopNodes = useCallback(async () => {
    await manageNodes('/nodes/stop', {}, 'Failed to stop nodes');
    resetDashboard();
  }, [manageNodes, resetDashboard]);

  const toggleMetric = (field) => {
    setSelectedMetrics(prev =>
      prev.includes(field)
        ? prev.filter(m => m !== field)
        : [...prev, field]
    );
  };

  useEffect(() => {
  let ws;
  let reconnectTimeout;

  const connect = () => {
    if (ws?.readyState === WebSocket.OPEN || ws?.readyState === WebSocket.CONNECTING) return;

    ws = new WebSocket('ws://localhost:8000/metrics/ws');
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const newMetrics = Array.isArray(data) ? data : data?.data;
        if (Array.isArray(newMetrics)) {
          setMetrics(prev => [...prev, ...newMetrics]);
        }
      } catch {
        console.warn('Failed to parse WebSocket data');
      }
    };

    ws.onerror = () => {
      console.warn('WebSocket connection error');
      ws.close();
    };

    ws.onclose = () => {
      console.info('WebSocket disconnected. Reconnecting...');
      reconnectTimeout = setTimeout(connect, 2000);
    };
  };

  connect();
  const statusInterval = setInterval(fetchNodeStatus, 3000);
  const uptimeInterval = setInterval(() => {
    setNodeUptimes(prev => {
      const updated = {};
      Object.entries(prev).forEach(([name, { startTime, isRunning }]) => {
        if (isRunning && startTime) {
          updated[name] = { ...prev[name], elapsedMs: Date.now() - startTime };
        }
      });
      return { ...prev, ...updated };
    });
  }, 1000);

  return () => {
    clearInterval(statusInterval);
    clearInterval(uptimeInterval);
    clearTimeout(reconnectTimeout);
    ws?.close();
  };
}, [fetchNodeStatus, wsTrigger]);

  const currentRoundByNode = useMemo(() => {
    const latest = {};
    metrics
      .filter(m => m.field === 'current_round')
      .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
      .forEach(m => {
        if (!(m.node in latest)) latest[m.node] = m.value;
      });
    return latest;
  }, [metrics]);

  return (
    <div className="dashboard-container">
      <ToastContainer position="top-right" autoClose={5000} />
      <div className="fixed-controls">
        <BasicControls onStart={startNodes} onStop={stopNodes} onClear={resetDashboard} isLoading={isLoading} />
      </div>

      <header className="dashboard-header">
        <div className="header-content"><h1>Peer-Based Mixing</h1></div>
      </header>

      <div className="dashboard-content">
        <Tabs className="custom-tabs">
          <TabList className="tab-list">
            <Tab className="tab" selectedClassName="tab--selected"><span className="tab-content">Nodes</span></Tab>
            <Tab className="tab" selectedClassName="tab--selected"><span className="tab-content">Settings</span></Tab>
            <Tab className="tab" selectedClassName="tab--selected"><span className="tab-content">Metrics</span></Tab>
          </TabList>

          <TabPanel className="tab-panel">
            <div className="panel-grid">
              <div className="node-status-container">
                <NodeStatus
                  nodeNames={nodeNames}
                  nodeStatus={nodeStatus}
                  nodeUptimes={nodeUptimes}
                  palette={CHART_PALETTE}
                  onSelectNode={setSelectedNode}
                  selectedNode={selectedNode}
                  currentRounds={currentRoundByNode}
                  totalRounds={config.rounds}
                />
              </div>
              <div className="docker-logs-container">
                <div className="docker-logs-header">
                  <h3>Node Logs</h3>
                  <strong>{!selectedNode && "Select a node to view logs"}</strong>
                </div>
                <DockerLogs key={selectedNode || 'empty'} containerName={selectedNode} resetTrigger={logsResetCounter} />
              </div>
            </div>
          </TabPanel>

          <TabPanel className="tab-panel">
            <SimulationSettings
              nodeCount={nodeCount}
              setNodeCount={setNodeCount}
              maxNodes={MAX_NODES}
              rounds={config.rounds}
              stream={config.stream}
              setRounds={(r) => updateConfig({ rounds: r })}
              setStream={(b) => updateConfig({ stream: b })}
              exitNodes={config.exitNodes}
              updateExitNodes={(_, count) => updateConfig({ exitNodes: count > 0 ? [{ round: 1, count }] : [] })}
              joinNodes={config.joinNodes}
              updateJoinNodes={(_, count) => updateConfig({ joinNodes: count > 0 ? [{ round: 1, count }] : [] })}
              displayMode={config.displayMode}
              setDisplayMode={(mode) => updateConfig({ displayMode: mode })}
              isLoading={isLoading}
            />
          </TabPanel>

          <TabPanel className="tab-panel">
            <div className="metrics-grid">
              <div className="metric-selection-container">
                <MetricSelection
                  selectedMetrics={selectedMetrics}
                  metricKeys={METRIC_KEYS}
                  getDisplayName={getDisplayName}
                  onToggleMetric={toggleMetric}
                />
              </div>
              <div className="metric-charts-container">
                {selectedMetrics.length === 0 ? (
                  <div className="no-metrics-selected"><p>Select metrics to display charts</p></div>
                ) : (
                  <div className="metric-charts-grid">
                    {selectedMetrics.map(metricKey => (
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
                )}
              </div>
            </div>
          </TabPanel>
        </Tabs>

        {error && <div className="status-message error">{error}</div>}
        {isLoading && <div className="overlay-loading"><div className="spinner" /><div>Loading...</div></div>}
      </div>

      <footer className="dashboard-footer">
        <div className="footer-content">
          <div className="footer-title">
            <a href="https://github.com/Altishofer/DFL_PeerBasedMixing">Peer-Based Mixing for DFL v0.1</a>
          </div>
          <div className="footer-authors">
            <a href="https://github.com/Altishofer">Sandrin Hunkeler</a>
            <span className="separator">·</span>
            <a href="https://github.com/Ringdinglinn">Linn Spitz</a>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Dashboard;
