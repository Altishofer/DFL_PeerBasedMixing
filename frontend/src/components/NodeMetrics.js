import React from 'react';
import NodeStatus from './NodeStatus';
import MetricChart from './MetricChart';

const NodeMetrics = ({ nodeNames, nodeStatus, nodeUptimes, selectedMetrics, buildChartData, config, CHART_PALETTE }) => {
  return (
    <main className="dashboard-grid">
      <NodeStatus
        nodeNames={nodeNames}
        nodeStatus={nodeStatus}
        nodeUptimes={nodeUptimes}
        palette={CHART_PALETTE}
      />

      {selectedMetrics.map(metricKey => (
        <MetricChart
          key={metricKey}
          metricKey={metricKey}
          title={metricKey}
          chartData={buildChartData(metricKey)}
          nodeNames={nodeNames}
          palette={CHART_PALETTE}
          displayMode={config.displayMode}
        />
      ))}
    </main>
  );
};

export default NodeMetrics;
