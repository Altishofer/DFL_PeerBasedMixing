import React, { useState } from 'react';
import { Tab, Tabs, TabList, TabPanel } from 'react-tabs';
import 'react-tabs/style/react-tabs.css';

const METRIC_GROUPS = {
  Communication: [
    'msg_sent',
    'bytes_sent',
    'bytes_received',
    'fragment_received',
    'fragment_resent',
    'surb_received',
    'fragments_forwarded'
  ],
  'Computational Resources': [
    'cpu_total_ns',
    'memory_mb'
  ],
  Learning: [
    'accuracy',
    'current_round'
  ]
};


const ControlPanel = ({
  nodeCount,
  setNodeCount,
  maxNodes,
  displayMode,
  setDisplayMode,
  rounds,
  setRounds,
  exitNodes,
  updateExitNodes,
  joinNodes,
  updateJoinNodes,
  selectedMetrics,
  metricKeys,
  getDisplayName,
  onStart,
  onStop,
  onClear,
  onToggleMetric,
  isLoading
}) => {
  const [activeTab, setActiveTab] = useState(0);

  const groupedMetrics = (() => {
    const allCategorized = new Set(Object.values(METRIC_GROUPS).flat());
    return {
      ...METRIC_GROUPS,
      Others: metricKeys
        .filter((key) => !allCategorized.has(key))
        .sort((a, b) => getDisplayName(a).localeCompare(getDisplayName(b)))
    };
  })();

  return (
    <div className="control-panel">
      <Tabs selectedIndex={activeTab} onSelect={setActiveTab}>
        <TabList>
          <Tab>Basic Controls</Tab>
          <Tab>Simulation Settings</Tab>
          <Tab>Metrics Selection</Tab>
        </TabList>

        <TabPanel>
          <div className="control-row">
            <div className="control-group">
              <label>Actions</label>
              <div className="control-buttons">
                <button className="action-button start-button" onClick={onStart} disabled={isLoading}>
                  {isLoading ? 'Starting…' : 'Start Simulation'}
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
        </TabPanel>

        <TabPanel>
          <div className="control-group-box">
            <h3>Simulation Parameters</h3>
            <div className="control-row">
              <div className="control-group control-input-limited">
                <label htmlFor="nodeCount">Initial Nodes</label>
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

              <div className="control-group control-input-limited">
                <label htmlFor="rounds">Total Rounds</label>
                <input
                  id="rounds"
                  type="number"
                  min="1"
                  max="100"
                  value={rounds}
                  onChange={(e) => setRounds(Math.max(1, parseInt(e.target.value, 10) || 1))}
                  disabled={isLoading}
                />
              </div>
            </div>
          </div>

          <div className="control-group-box">
            <h3>Node Join/Exit Configuration</h3>
            <div className="control-row">
              <div className="control-group control-input-limited">
                <label htmlFor="exitCount">Total Nodes to Exit</label>
                <input
                  id="exitCount"
                  type="number"
                  min="0"
                  max={nodeCount}
                  value={exitNodes.reduce((sum, e) => sum + e.count, 0)}
                  onChange={(e) => {
                    const count = Math.max(0, parseInt(e.target.value, 10) || 0);
                    updateExitNodes(1, count);
                  }}
                  disabled={isLoading}
                />
              </div>

              <div className="control-group control-input-limited">
                <label htmlFor="joinCount">Total Nodes to Join</label>
                <input
                  id="joinCount"
                  type="number"
                  min="0"
                  max={maxNodes - nodeCount}
                  value={joinNodes.reduce((sum, j) => sum + j.count, 0)}
                  onChange={(e) => {
                    const count = Math.max(0, parseInt(e.target.value, 10) || 0);
                    updateJoinNodes(1, count);
                  }}
                  disabled={isLoading}
                />
              </div>
            </div>
          </div>

          <div className="control-group-box">
            <h3>Display Settings</h3>
            <div className="control-row">
              <div className="control-group control-input-limited">
                <label htmlFor="displayMode">Display Mode</label>
                <select
                  id="displayMode"
                  value={displayMode}
                  onChange={(e) => setDisplayMode(e.target.value)}
                  disabled={isLoading}
                >
                  <option value="raw">Raw Values</option>
                  <option value="delta">Difference</option>
                  <option value="rate">Rate of Change</option>
                  <option value="normalized">Normalized</option>
                </select>
              </div>
            </div>
          </div>
        </TabPanel>
<TabPanel>
  <div className="control-group full-width">
    <label>Select Metrics to Display</label>
    <div className="metric-toggle-columns">
      {Object.entries(groupedMetrics).map(([groupName, groupMetrics]) => {
        if (!groupMetrics || groupMetrics.length === 0) return null;

        const sortedFields = groupMetrics
          .filter((key) => metricKeys.includes(key))
          .sort((a, b) => getDisplayName(a).localeCompare(getDisplayName(b)));

        return (
          <div key={groupName} className="metric-group">
            <div className="metric-group-label">{groupName}</div>
            <div className="metric-toggle-container">
              {sortedFields.map((field) => (
                <button
                  key={field}
                  className={`metric-toggle ${selectedMetrics.includes(field) ? 'active' : ''}`}
                  onClick={() => onToggleMetric(field)}
                >
                  {getDisplayName(field)}
                  {selectedMetrics.includes(field) && (
                    <span className="toggle-indicator">✓</span>
                  )}
                </button>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  </div>
</TabPanel>

      </Tabs>
    </div>
  );
};

export default ControlPanel;
