export const buildChartData = (metrics, metricType) => {
  const timeMap = new Map();

  metrics.forEach(({ timestamp, field, node, value }) => {
    if (!timestamp || field !== metricType) return;

    const dateObj = new Date(timestamp);
    const timeKey = dateObj.getTime();

    if (!timeMap.has(timeKey)) {
      timeMap.set(timeKey, {
        timestamp: dateObj.toLocaleTimeString([], {
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
        }),
      });
    }

    const timeEntry = timeMap.get(timeKey);
    if (node && value !== undefined) {
      const num = Number(value);
      timeEntry[node] = Number.isFinite(num) ? parseFloat(num.toFixed(4)) : num;
    }
  });

  return Array.from(timeMap.values()).sort((a, b) => a.timestamp - b.timestamp);
};
