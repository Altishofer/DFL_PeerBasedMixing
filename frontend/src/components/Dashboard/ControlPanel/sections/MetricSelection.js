import React from 'react';

// Define MetricField Enum
export const MetricField = Object.freeze({
  FRAGMENTS_RECEIVED: "fragments_received",
  FRAGMENTS_SENT: "fragments_sent",
  TOTAL_MSG_SENT: "total_sent",
  TOTAL_MSG_RECEIVED: "total_received",
  TOTAL_BYTES_SENT: "total_bytes_sent",
  TOTAL_BYTES_RECEIVED: "total_bytes_received",
  FORWARDED: "forwarded",
  SURB_REPLIED: "surb_replied",
  SURB_RECEIVED: "surb_received",
  ERRORS: "errors",
  CURRENT_ROUND: "current_round",
  TRAINING_ACCURACY: "accuracy",
  AGGREGATED_ACCURACY: "aggregated_accuracy",
  RESENT: "resent"
});

// Generate METRIC_FIELDS dynamically
export const METRIC_FIELDS = Object.fromEntries(
  Object.values(MetricField).map(field => [
    field,
    field
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')
  ])
);

export default function MetricSelection({ selectedMetrics, metricKeys, getDisplayName, onToggleMetric }) {
  // Define METRIC_GROUPS using MetricField
  const METRIC_GROUPS = {
    Communication: [
      MetricField.TOTAL_MSG_SENT,
      MetricField.TOTAL_MSG_RECEIVED,
      MetricField.TOTAL_BYTES_SENT,
      MetricField.TOTAL_BYTES_RECEIVED
    ],
    'Model Exchange': [
      MetricField.FRAGMENTS_SENT,
      MetricField.FRAGMENTS_RECEIVED
    ],
    Mixnet: [
      MetricField.RESENT,
      MetricField.FORWARDED,
      MetricField.SURB_REPLIED,
      MetricField.SURB_RECEIVED
    ],
    Errors: [
      MetricField.ERRORS
    ],
    Learning: [
      MetricField.TRAINING_ACCURACY,
      MetricField.AGGREGATED_ACCURACY,
      MetricField.CURRENT_ROUND
    ]
  };

  // Group metrics and include uncategorized ones under "Others"
  const groupedMetrics = (() => {
    const allCategorized = new Set(Object.values(METRIC_GROUPS).flat());
    return {
      ...METRIC_GROUPS,
      Others: metricKeys.filter(k => !allCategorized.has(k))
    };
  })();

  return (
    <div className="metric-toggle-columns">
      {Object.entries(groupedMetrics).map(([groupName, group]) => {
        const sorted = group
          .filter((k) => metricKeys.includes(k))
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
