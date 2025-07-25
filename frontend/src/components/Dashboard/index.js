import React, { useEffect, useState, useMemo, useCallback, useRef } from 'react';
import axios from 'axios';
import { toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

import NodeStatus from './NodeStatus';
import MetricChart from './MetricChart';
import MetricSelection from './MetricSelection';

import useNodeStatus from '../../hooks/useNodeStatus';
import { buildChartData } from '../../utils/chartUtils';
import {
  WS_BASE_URL, API_BASE_URL, CHART_PALETTE, METRIC_KEYS, getDisplayName, ALWAYS_ACTIVE_METRICS
} from '../../constants/constants';
import '../../App.css';
import { createSSEService } from '../../services/SseService';

const Dashboard = () => {
  const [nodeStatus, setNodeStatus] = useState([]);
  const [metrics, setMetrics] = useState([]);
  const [selectedMetrics, setSelectedMetrics] = useState(ALWAYS_ACTIVE_METRICS);
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

  const toggleMetric = useCallback(field => {
    setSelectedMetrics(prev =>
      prev.includes(field) ? prev.filter(m => m !== field) : [...prev, field]
    );
  }, []);

  const handleStartNodes = useCallback(async () => {
    setIsLoading(true);
    try {
      await axios.post(`${API_BASE_URL}/nodes/start`);
      toast.success('Nodes started');
      setWsTrigger(t => t + 1);
    } catch (e) {
      toast.error('Failed to start nodes');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleStopNodes = useCallback(async () => {
    setIsLoading(true);
    try {
      await axios.post(`${API_BASE_URL}/nodes/stop`);
      toast.success('Nodes stopped');
      setWsTrigger(t => t + 1);
    } catch (e) {
      toast.error('Failed to stop nodes');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    const handleMessage = data => {
      const newMetrics = Array.isArray(data) ? data : data?.data;
      if (Array.isArray(newMetrics)) {
        setMetrics(prev => [...prev, ...newMetrics]);
      }
    };

    wsService.initialize(`${WS_BASE_URL}/metrics/sse`, handleMessage);

    const statusInterval = setInterval(fetchNodeStatus, 3000);

    return () => {
      clearInterval(statusInterval);
      wsService.disconnect();
    };
  }, [fetchNodeStatus, wsService, wsTrigger]);

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
            onClick={handleStartNodes}
            disabled={isLoading}
          >
            Start
          </button>
          <button
            className="action-button stop-button"
            onClick={handleStopNodes}
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
          <MetricSelection
            selectedMetrics={selectedMetrics}
            metricKeys={METRIC_KEYS}
            getDisplayName={getDisplayName}
            onToggleMetric={toggleMetric}
          />
          <div className="metric-charts-container">
            {selectedMetrics.length === 0 ? (
              <div className="no-metrics-selected">Select metrics to display charts</div>
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
      {isLoading && (
        <div className="overlay-loading">
          <div className="spinner" />
          <div>Loading...</div>
        </div>
      )}

      <footer className="dashboard-footer">
        <div className="footer-content">
          <div className="footer-title">
            <a href="https://github.com/Altishofer/DFL_PeerBasedMixing">Peer Based Mixing for DFL v0.1</a>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Dashboard;
