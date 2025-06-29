import React, { useEffect, useState, useMemo, useCallback, useRef } from 'react';
import axios from 'axios';
import { toast} from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

import NodeStatus from './NodeStatus';
import MetricChart from './MetricChart';
import MetricSelection from './MetricSelection';

import useNodeStatus from '../../hooks/useNodeStatus';
import { buildChartData } from '../../utils/chartUtils';
import {
  WS_BASE_URL, API_BASE_URL, CHART_PALETTE, METRIC_KEYS, getDisplayName
} from '../../constants/constants';
import '../../App.css';
import { createSSEService } from "../../services/SseService";

const Dashboard = () => {
  const [nodeStatus, setNodeStatus] = useState([]);
  const [metrics, setMetrics] = useState([]);
  const [selectedMetrics, setSelectedMetrics] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [nodeUptimes, setNodeUptimes] = useState({});
  const [wsTrigger, setWsTrigger] = useState(0);
  const wsService = useRef(createSSEService()).current;

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
      setError(errorMessage);
      toast.error(errorMessage);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [fetchNodeStatus]);

  const resetDashboard = useCallback(() => {
    axios.get(`${WS_BASE_URL}/metrics/clear`);
    setNodeStatus([]);
    setMetrics([]);
    setSelectedMetrics([]);
    setIsLoading(false);
    setError('');
    setNodeUptimes({});
    setWsTrigger(prev => prev + 1);
    fetchNodeStatus();
  }, [fetchNodeStatus]);

  const startNodes = useCallback(async () => {
    resetDashboard();
    await manageNodes(`/nodes/start`, 'Failed to start nodes');
    await new Promise(resolve => setTimeout(resolve, 3000));
    await fetchNodeStatus();
  }, [manageNodes, resetDashboard, fetchNodeStatus]);

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
    const handleMessage = (data) => {
      const newMetrics = Array.isArray(data) ? data : data?.data;
      if (Array.isArray(newMetrics)) {
        setMetrics(prev => [...prev, ...newMetrics]);
      }
    };

    wsService.initialize(`${WS_BASE_URL}/metrics/sse`, handleMessage);

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
      wsService.disconnect();
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

      <header className="dashboard-header">
        <h1>Peer Based Mixing</h1>
        <div className="header-buttons">
          <button
            className="action-button start-button"
            onClick={startNodes}
            disabled={isLoading}
          >
            Start
          </button>
          <button
            className="action-button stop-button"
            onClick={stopNodes}
            disabled={isLoading}
          >
            Stop
          </button>
        </div>
      </header>



      <div className="dashboard-content">
        <NodeStatus
          nodeNames={nodeNames}
          nodeStatus={nodeStatus}
          nodeUptimes={nodeUptimes}
          palette={CHART_PALETTE}
          currentRounds={currentRoundByNode}
          totalRounds={10}
        />

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
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {error && <div className="status-message error">{error}</div>}
      {isLoading && <div className="overlay-loading"><div className="spinner" /><div>Loading...</div></div>}

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
