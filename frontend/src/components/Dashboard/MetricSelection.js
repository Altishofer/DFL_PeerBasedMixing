import React from 'react';
import { METRIC_GROUPS, METRIC_UNITS } from '../../constants/constants';

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
    <div className="metric-selection-container">
      {Object.entries(groupedMetrics).map(([groupName, group]) => {
        const sorted = group
          .filter((k) => metricKeysArray.includes(k))
          .sort((a, b) => getDisplayName(a).localeCompare(getDisplayName(b)));
        if (sorted.length === 0) return null;

        return (
          <div key={groupName} className="metric-group">
            <h3 className="metric-group-label">{groupName}</h3>
            <table className="metric-table">
              <tbody>
                {sorted.map((key) => (
                  <tr
                    key={key}
                    className={`metric-row ${selectedMetrics.includes(key) ? 'active' : ''}`}
                    onClick={() => onToggleMetric(key)}
                  >
                    <td className="metric-name">{getDisplayName(key)}</td>
                    <td className="metric-unit">{METRIC_UNITS[key] || ''}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      })}
    </div>
  );
}
