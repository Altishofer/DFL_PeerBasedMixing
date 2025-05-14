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
  const [logsResetCounter, setLogsResetCounter] = useState(0);
  const [config, setConfig] = useState({
    displayMode: 'raw',
    rounds: 40,
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
    await new Promise(resolve => setTimeout(resolve, 3000));
    await fetchNodeStatus();
  }, [manageNodes, nodeCount, fetchNodeStatus, config]);

const stopNodes = useCallback(async () => {
  await manageNodes('/nodes/stop', {}, 'Failed to stop nodes');
  resetDashboard();
}, [manageNodes]);


  const clearStats = useCallback(() => {
    resetDashboard();
  }, [fetchNodeStatus]);

  const toggleMetric = (field) => {
    setSelectedMetrics(prev =>
      prev.includes(field)
        ? prev.filter(m => m !== field)
        : [...prev, field]
    );
  };

  const resetDashboard = useCallback(() => {
  setNodeCount(4);
  axios.post(`${API_BASE_URL}/logs/clear`);
  setNodeStatus([]);
  setMetrics([]);
  setSelectedMetrics([]);
  setIsLoading(false);
  setSelectedNode(null);
  setLogsResetCounter(prev => prev + 1);

  setError('');
  setNodeUptimes({});
  setConfig({
    displayMode: 'raw',
    rounds: 40,
    exitNodes: [],
    joinNodes: []
  });
  setSelectedNode(null);
  setActiveRound(0);
  setWsTrigger(prev => prev + 1);
  fetchNodeStatus();
}, [fetchNodeStatus]);


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

  const currentRoundByNode = useMemo(() => {
  const roundMetrics = metrics
    .filter(m => m.field === 'current_round')
    .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp)); // get latest values first

  const latestByNode = {};
  for (const metric of roundMetrics) {
    if (!(metric.node in latestByNode)) {
      latestByNode[metric.node] = metric.value;
    }
  }
  return latestByNode;
}, [metrics]);


  return (
    <div className="dashboard-container">
      <ToastContainer position="top-right" autoClose={5000} />

      <div className="fixed-controls">
        <BasicControls
          onStart={startNodes}
          onStop={stopNodes}
          onClear={clearStats}
          isLoading={isLoading}
        />
      </div>

      <header className="dashboard-header">
        <div className="header-content">
          <h1>Peer-Based Mixing</h1>
        </div>
      </header>

      <div className="dashboard-content">
        <Tabs className="custom-tabs">
          <TabList className="tab-list">
            <Tab className="tab" selectedClassName="tab--selected">
              <span className="tab-content">
                <svg className="tab-icon" viewBox="0 0 24 24">
                  <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V5h14v14zM7 12h2v5H7zm4-7h2v12h-2zm4 3h2v9h-2z"/>
                </svg>
                Nodes
              </span>
            </Tab>
            <Tab className="tab" selectedClassName="tab--selected">
              <span className="tab-content">
                <svg className="tab-icon" viewBox="0 0 24 24">
                  <path d="M19.43 12.98c.04-.32.07-.64.07-.98s-.03-.66-.07-.98l2.11-1.65c.19-.15.24-.42.12-.64l-2-3.46c-.12-.22-.39-.3-.61-.22l-2.49 1c-.52-.4-1.08-.73-1.69-.98l-.38-2.65C14.46 2.18 14.25 2 14 2h-4c-.25 0-.46.18-.49.42l-.38 2.65c-.61.25-1.17.59-1.69.98l-2.49-1c-.23-.09-.49 0-.61.22l-2 3.46c-.13.22-.07.49.12.64l2.11 1.65c-.04.32-.07.65-.07.98s.03.66.07.98l-2.11 1.65c-.19.15-.24.42-.12.64l2 3.46c.12.22.39.3.61.22l2.49-1c.52.4 1.08.73 1.69.98l.38 2.65c.03.24.24.42.49.42h4c.25 0 .46-.18.49-.42l.38-2.65c.61-.25 1.17-.59 1.69-.98l2.49 1c.23.09.49 0 .61-.22l2-3.46c.12-.22.07-.49-.12-.64l-2.11-1.65zM12 15.5c-1.93 0-3.5-1.57-3.5-3.5s1.57-3.5 3.5-3.5 3.5 1.57 3.5 3.5-1.57 3.5-3.5 3.5z"/>
                </svg>
                Settings
              </span>
            </Tab>
            <Tab className="tab" selectedClassName="tab--selected">
              <span className="tab-content">
                <svg className="tab-icon" viewBox="0 0 24 24">
                  <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zM9 17H7v-7h2v7zm4 0h-2V7h2v10zm4 0h-2v-4h2v4z"/>
                </svg>
                Metrics
              </span>
            </Tab>
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
                <DockerLogs
                  key={selectedNode || 'empty'}
                  containerName={selectedNode}
                  resetTrigger={logsResetCounter}
                />
              </div>
            </div>
          </TabPanel>

          <TabPanel className="tab-panel">
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
                  <div className="no-metrics-selected">

                    <p>Select metrics to display charts</p>
                  </div>
                ) : (
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
                )}
              </div>
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
    <div className="footer-title">
      <a href="https://github.com/Altishofer/DFL_PeerBasedMixing">
        Peer-Based Mixing for DFL v0.1
      </a>
    </div>
    <div className="footer-authors">
      <a href="https://github.com/Altishofer">Sandrin Hunkeler</a>
      <span className="separator">·</span>
      <a href="https://www.youtube.com/watch?v=dQw4w9WgXcQ">Linn Spitz</a>
    </div>
  </div>
</footer>


    </div>
  );
};

export default Dashboard;