import React from 'react';
import { METRIC_GROUPS } from '../../constants/constants';

export default function MetricSelection({ selectedMetrics, metricKeys, getDisplayName, onToggleMetric }) {
  const metricKeysArray = Array.isArray(metricKeys) ? metricKeys : Object.values(metricKeys);

  const groupedMetrics = (() => {
    const allCategorized = new Set(Object.values(METRIC_GROUPS).flat());
    return {
      ...METRIC_GROUPS,
      Others: metricKeysArray.filter(k => !allCategorized.has(k))
    };
  })();

  return (
    <div className="metric-toggle-columns">
      {Object.entries(groupedMetrics).map(([groupName, group]) => {
        const sorted = group
          .filter((k) => metricKeysArray.includes(k))
          .sort((a, b) => getDisplayName(a).localeCompare(getDisplayName(b)));
        if (sorted.length === 0) return null;

        return (
          <div key={groupName} className="metric-group">
            <div className="metric-group-label">{groupName}</div>
            <div className="metric-toggle-container">
              {sorted.map((key) => (
                <button
                  key={key}
                  className={`metric-toggle ${selectedMetrics.includes(key) ? 'active' : ''}`}
                  onClick={() => onToggleMetric(key)}
                >
                  {getDisplayName(key)}
                  {selectedMetrics.includes(key) && <span className="toggle-indicator">✓</span>}
                </button>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
