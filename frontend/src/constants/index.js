export const API_BASE_URL = 'http://localhost:8000';

export const CHART_PALETTE = [
  '#3182CE', '#38A169', '#DD6B20', '#805AD5',
  '#E53E3E', '#D69E2E', '#319795', '#00B5D8'
];

export const MAX_NODES = 10;

export const METRIC_FIELDS = {
  msg_sent: 'Messages Sent',
  errors: 'Errors',
  surb_received: 'SURBs Received',
  fragment_received: 'Fragments Received',
  bytes_received: 'Bytes Received',
  current_round: 'Current Round',
  accuracy: 'Accuracy',
  aggregated_accuracy: 'Aggregated Accuracy',
  fragment_resent: 'Fragments Resent',
  bytes_sent: 'Bytes Sent',
  fragments_forwarded: 'Fragments Forwarded',
  cpu_total_ns: 'CPU Total Ns',
  memory_mb: 'Memory (MB)',
};

export const METRIC_KEYS = Object.keys(METRIC_FIELDS);

export const getDisplayName = key => METRIC_FIELDS[key] || null;
