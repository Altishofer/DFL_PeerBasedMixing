export const API_BASE_URL = 'http://localhost:8000';

export const CHART_PALETTE = [
  '#3182CE', '#38A169', '#DD6B20', '#805AD5',
  '#E53E3E', '#D69E2E', '#319795', '#00B5D8'
];

export const MAX_NODES = 10;

export const METRIC_FIELDS = {
  total_sent: 'Total Messages Sent',
  total_received: 'Total Messages Received',
  total_bytes_sent: 'Total Bytes Sent',
  total_bytes_received: 'Total Bytes Received',
  fragments_sent: 'Fragments Sent',
  fragments_received: 'Fragments Received',
  resent: 'Fragments Resent',
  forwarded: 'Fragments Forwarded',
  surb_replied: 'SURBs Replied',
  surb_received: 'SURBs Received',
  errors: 'Errors',
  current_round: 'Current Round',
  accuracy: 'Training Accuracy',
  aggregated_accuracy: 'Aggregated Accuracy',
  cpu_total_ns: 'CPU Total Ns',
  memory_mb: 'Memory (MB)',
};

export const METRIC_KEYS = Object.keys(METRIC_FIELDS);

export const getDisplayName = key => METRIC_FIELDS[key] || null;
