export default function MetricSelection({ selectedMetrics, metricKeys, getDisplayName, onToggleMetric }) {
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
