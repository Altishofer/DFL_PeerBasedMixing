import React, { useState } from 'react';
import NodeStatus from './NodeStatus';
import MetricChart from './MetricChart';
import ControlPanel from './ControlPanel';
import LogsViewer from './LogsViewer';
import useDashboardLogic from './useDashboardLogic';

const DashboardContainer = () => {
  const [selectedNode, setSelectedNode] = useState(null);

  const {
    nodeCount, setNodeCount, config, setConfig, selectedMetrics,
    handleMetricToggle, startNodes, stopNodes, clearStats,
    isLoading, error, nodeNames, nodeStatus, nodeUptimes,
    buildChartData, CHART_PALETTE, METRIC_KEYS, getDisplayName,
  } = useDashboardLogic();

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
        metricKeys={METRIC_KEYS}
        getDisplayName={getDisplayName}
      />

      {isLoading && (
        <div className="overlay-loading">
          <div className="spinner" />
          <div>Loading...</div>
        </div>
      )}

      {error && <div className="status-message error">{error}</div>}

      <main className="dashboard-grid">
        <NodeStatus
          nodeNames={nodeNames}
          nodeStatus={nodeStatus}
          nodeUptimes={nodeUptimes}
          palette={CHART_PALETTE}
          onNodeClick={setSelectedNode}
        />

        {selectedMetrics.map(metricKey => (
          <MetricChart
            key={metricKey}
            metricKey={metricKey}
            title={getDisplayName(metricKey)}
            chartData={buildChartData(metricKey)}
            nodeNames={nodeNames}
            palette={CHART_PALETTE}
            displayMode={config.displayMode}
          />
        ))}
      </main>

      {selectedNode && (
        <section className="logs-panel">
          <LogsViewer containerName={selectedNode} />
        </section>
      )}

      <footer className="dashboard-footer">
        <p>Data refreshes every 2 seconds | All entries are streamed with deduplication</p>
      </footer>
    </div>
  );
};

export default DashboardContainer;
