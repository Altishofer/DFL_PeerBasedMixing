export const API_BASE_URL = 'http://localhost:8000';
export const WS_BASE_URL = 'http://localhost:8000';

export const CHART_PALETTE = [
  '#3182CE', '#38A169', '#DD6B20', '#805AD5',
  '#E53E3E', '#D69E2E', '#319795', '#00B5D8'
];

export const METRIC_KEYS = {
  TOTAL_SENT: 'total_sent',
  TOTAL_RECEIVED: 'total_received',
  TOTAL_MBYTES_SENT: 'total_mbytes_sent',
  TOTAL_MBYTES_RECEIVED: 'total_mbytes_received',
  FRAGMENTS_SENT: 'fragments_sent',
  FRAGMENTS_RECEIVED: 'fragments_received',
  RESENT: 'resent',
  FORWARDED: 'forwarded',
  SURB_REPLIED: 'surb_replied',
  SURB_RECEIVED: 'surb_received',
  ERRORS: 'errors',
  CURRENT_ROUND: 'current_round',
  ACCURACY: 'accuracy',
  AGGREGATED_ACCURACY: 'aggregated_accuracy',
  CPU_TOTAL_NS: 'cpu_total_ns',
  MEMORY_MB: 'memory_mb',
  ACTIVE_PEERS: 'active_peers',
  STAGE: 'stage'
};

export const METRIC_FIELDS = {
  [METRIC_KEYS.TOTAL_SENT]: 'Total Messages Sent',
  [METRIC_KEYS.TOTAL_RECEIVED]: 'Total Messages Received',
  [METRIC_KEYS.TOTAL_MBYTES_SENT]: 'Total Megabytes Sent',
  [METRIC_KEYS.TOTAL_MBYTES_RECEIVED]: 'Total Megabytes Received',
  [METRIC_KEYS.FRAGMENTS_SENT]: 'Fragments Sent',
  [METRIC_KEYS.FRAGMENTS_RECEIVED]: 'Fragments Received',
  [METRIC_KEYS.RESENT]: 'Fragments Resent',
  [METRIC_KEYS.FORWARDED]: 'Fragments Forwarded',
  [METRIC_KEYS.SURB_REPLIED]: 'SURBs Replied',
  [METRIC_KEYS.SURB_RECEIVED]: 'SURBs Received',
  [METRIC_KEYS.ERRORS]: 'Errors',
  [METRIC_KEYS.CURRENT_ROUND]: 'Current Round',
  [METRIC_KEYS.ACCURACY]: 'Training Accuracy',
  [METRIC_KEYS.AGGREGATED_ACCURACY]: 'Aggregated Accuracy',
  [METRIC_KEYS.CPU_TOTAL_NS]: 'CPU Total Ns',
  [METRIC_KEYS.MEMORY_MB]: 'Memory (MB)',
  [METRIC_KEYS.ACTIVE_PEERS]: 'Active Peers',
  [METRIC_KEYS.STAGE]: 'Node Stage',
};

export const METRIC_GROUPS = {
  Communication: [
    METRIC_KEYS.TOTAL_SENT,
    METRIC_KEYS.TOTAL_RECEIVED,
    METRIC_KEYS.TOTAL_MBYTES_SENT,
    METRIC_KEYS.TOTAL_MBYTES_RECEIVED
  ],
  'Model Exchange': [
    METRIC_KEYS.FRAGMENTS_SENT,
    METRIC_KEYS.FRAGMENTS_RECEIVED,
    METRIC_KEYS.RESENT,
    METRIC_KEYS.ACTIVE_PEERS
  ],
  Mixnet: [
    METRIC_KEYS.FORWARDED,
    METRIC_KEYS.SURB_REPLIED,
    METRIC_KEYS.SURB_RECEIVED
  ],
  Miscellaneous: [
      METRIC_KEYS.ERRORS,
      METRIC_KEYS.STAGE
  ],
  Learning: [
    METRIC_KEYS.ACCURACY,
    METRIC_KEYS.AGGREGATED_ACCURACY,
    METRIC_KEYS.CURRENT_ROUND
  ]
};

export const getDisplayName = key => METRIC_FIELDS[key] || null;
