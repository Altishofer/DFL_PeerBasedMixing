import React from 'react';

const MAX_NODES = 10;

const ControlPanel = ({
  nodeCount,
  setNodeCount,
  config,
  setConfig,
  selectedMetrics,
  handleMetricToggle,
  startNodes,
  stopNodes,
  clearStats,
  isLoading,
  metricKeys,
  getDisplayName
}) => (
  <section className="control-panel">
    <div className="control-group">
      <label htmlFor="nodeCount">Nodes to Start</label>
      <input
        id="nodeCount"
        type="number"
        min="1"
        max={MAX_NODES}
        value={nodeCount}
        onChange={(e) => {
          const value = Math.min(MAX_NODES, Math.max(1, parseInt(e.target.value, 10) || 1));
          setNodeCount(value);
        }}
        disabled={isLoading}
      />
    </div>

    <div className="control-group">
      <label>Display Mode</label>
      <select
        value={config.displayMode}
        onChange={(e) => setConfig(prev => ({ ...prev, displayMode: e.target.value }))}
      >
        <option value="raw">Raw Values</option>
        <option value="delta">Difference</option>
      </select>
    </div>

    <div className="control-group">
      <label>Metrics Display</label>
      <div className="metric-toggle-container">
        {metricKeys.filter(field => getDisplayName(field)).map(field => (
          <button
            key={field}
            className={`metric-toggle ${selectedMetrics.includes(field) ? 'active' : ''}`}
            onClick={() => handleMetricToggle(field)}
          >
            {getDisplayName(field)}
          </button>
        ))}
      </div>
    </div>

    <div className="action-buttons">
      <button className="action-button start-button" onClick={startNodes} disabled={isLoading}>
        {isLoading ? 'Starting...' : 'Start Network'}
      </button>
      <button className="action-button clear-button" onClick={clearStats} disabled={isLoading}>
        Reset
      </button>
      <button className="action-button stop-button" onClick={stopNodes} disabled={isLoading}>
        Stop Network
      </button>
    </div>
  </section>
);

export default ControlPanel;
