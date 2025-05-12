import React from 'react';

const ControlPanel = ({
  nodeCount,
  setNodeCount,
  maxNodes,
  displayMode,
  setDisplayMode,
  selectedMetrics,
  metricKeys,
  getDisplayName,
  onStart,
  onStop,
  onClear,
  onToggleMetric,
  isLoading
}) => {
  return (
    <div className="control-panel">

      <div className="control-row">
        <div className="control-group control-input-limited">
          <label htmlFor="nodeCount">Nodes to Start</label>
          <input
            id="nodeCount"
            type="number"
            min="1"
            max={maxNodes}
            value={nodeCount}
            onChange={(e) => {
              const value = Math.min(maxNodes, Math.max(1, parseInt(e.target.value, 10) || 1));
              setNodeCount(value);
            }}
            disabled={isLoading}
          />
        </div>
      </div>

      <div className="control-row">
        <div className="control-group control-input-limited">
          <label>Display Mode</label>
          <select
            value={displayMode}
            onChange={(e) => setDisplayMode(e.target.value)}
            disabled={isLoading}
          >
            <option value="raw">Raw</option>
            <option value="delta">Difference</option>
          </select>
        </div>
      </div>

<div className="control-row">
  <div className="control-group">
    <label>Control</label>
    <div className="control-buttons">
      <button className="action-button start-button" onClick={onStart} disabled={isLoading}>
        {isLoading ? 'Starting…' : 'Start'}
      </button>
      <button className="action-button clear-button" onClick={onClear} disabled={isLoading}>
        Reset
      </button>
      <button className="action-button stop-button" onClick={onStop} disabled={isLoading}>
        Stop
      </button>
    </div>
  </div>
</div>


      <div className="control-row">
        <div className="control-group" style={{ flex: '1 1 100%' }}>
          <label>Visible Metrics</label>
          <div className="metric-toggle-container">
            {metricKeys.map((field) => (
              <button
                key={field}
                className={`metric-toggle ${selectedMetrics.includes(field) ? 'active' : ''}`}
                onClick={() => onToggleMetric(field)}
              >
                {getDisplayName(field)}
              </button>
            ))}
          </div>
        </div>
      </div>

    </div>
  );
};

export default ControlPanel;
