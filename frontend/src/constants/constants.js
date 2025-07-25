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
    DELETED_CACHE_FOR_INACTIVE: 'deleted_cache_for_inactive',
    ROUND_TIME: 'round_time',
    UNACKED_MSG: 'unacked_msg',
    RECEIVED_DUPLICATE_MSG: 'received_duplicate_msg',
    CURRENT_STAGE: 'stage',
    AVG_RTT: 'avg_rtt',
    AVG_MSG_PER_SECOND: 'avg_msg_per_second',
    LAST_RTT: 'last_rtt',
    COVERS_SENT: 'covers_sent',
    COVERS_RECEIVED: 'covers_received',
    SENDING_COVERS: 'sending_covers',
    SENDING_MESSAGES: 'sending_messages',
    QUEUE_INTERVAL: 'out_interval',
  QUEUED_PACKAGES: 'queued_packages'
};

export const METRIC_FIELDS = {
    [METRIC_KEYS.TOTAL_SENT]: 'Msgs Sent',
    [METRIC_KEYS.TOTAL_RECEIVED]: 'Msgs Received',
    [METRIC_KEYS.TOTAL_MBYTES_SENT]: 'MB Sent',
    [METRIC_KEYS.TOTAL_MBYTES_RECEIVED]: 'MB Received',
    [METRIC_KEYS.FRAGMENTS_SENT]: 'Frags Sent',
    [METRIC_KEYS.FRAGMENTS_RECEIVED]: 'Frags Received',
    [METRIC_KEYS.RESENT]: 'Frags Resent',
    [METRIC_KEYS.FORWARDED]: 'Msgs Fwd',
    [METRIC_KEYS.SURB_REPLIED]: 'SURBs Replied',
    [METRIC_KEYS.SURB_RECEIVED]: 'SURBs Received',
    [METRIC_KEYS.ERRORS]: 'Errors',
    [METRIC_KEYS.CURRENT_ROUND]: 'Round',
    [METRIC_KEYS.ACCURACY]: 'Accuracy',
    [METRIC_KEYS.AGGREGATED_ACCURACY]: 'Agg Accuracy',
    [METRIC_KEYS.CPU_TOTAL_NS]: 'CPU (ns)',
    [METRIC_KEYS.MEMORY_MB]: 'Mem (MB)',
    [METRIC_KEYS.ACTIVE_PEERS]: 'Peers',
    [METRIC_KEYS.DELETED_CACHE_FOR_INACTIVE]: 'Cache Deleted',
    [METRIC_KEYS.ROUND_TIME]: 'Round Time',
    [METRIC_KEYS.UNACKED_MSG]: 'Unacked Frags',
    [METRIC_KEYS.RECEIVED_DUPLICATE_MSG]: 'Dup Msgs',
    [METRIC_KEYS.CURRENT_STAGE]: 'Stage',
    [METRIC_KEYS.AVG_RTT]: 'Avg RTT',
    [METRIC_KEYS.AVG_MSG_PER_SECOND]: 'Msg/sec',
    [METRIC_KEYS.LAST_RTT]: 'Last RTT',
    [METRIC_KEYS.COVERS_SENT]: 'Covers Sent',
    [METRIC_KEYS.COVERS_RECEIVED]: 'Covers Received',
    [METRIC_KEYS.SENDING_COVERS]: 'Sending Covers',
    [METRIC_KEYS.SENDING_MESSAGES]: 'Sending Msgs',
    [METRIC_KEYS.QUEUED_PACKAGES]: 'Queued Pkgs',
    [METRIC_KEYS.QUEUE_INTERVAL]: 'Queue Intvl',
};

export const METRIC_UNITS = {
    [METRIC_KEYS.TOTAL_SENT]: 'msgs',
    [METRIC_KEYS.TOTAL_RECEIVED]: 'msgs',
    [METRIC_KEYS.TOTAL_MBYTES_SENT]: 'MB',
    [METRIC_KEYS.TOTAL_MBYTES_RECEIVED]: 'MB',
    [METRIC_KEYS.FRAGMENTS_SENT]: 'frags',
    [METRIC_KEYS.FRAGMENTS_RECEIVED]: 'frags',
    [METRIC_KEYS.RESENT]: 'frags',
    [METRIC_KEYS.FORWARDED]: 'msgs',
    [METRIC_KEYS.SURB_REPLIED]: 'SURBs',
    [METRIC_KEYS.SURB_RECEIVED]: 'SURBs',
    [METRIC_KEYS.ERRORS]: 'errs',
    [METRIC_KEYS.CURRENT_ROUND]: 'rnds',
    [METRIC_KEYS.ACCURACY]: '%',
    [METRIC_KEYS.AGGREGATED_ACCURACY]: '%',
    [METRIC_KEYS.CPU_TOTAL_NS]: 'ns',
    [METRIC_KEYS.MEMORY_MB]: 'MB',
    [METRIC_KEYS.ACTIVE_PEERS]: 'prs',
    [METRIC_KEYS.DELETED_CACHE_FOR_INACTIVE]: 'items',
    [METRIC_KEYS.ROUND_TIME]: 's',
    [METRIC_KEYS.UNACKED_MSG]: 'frags',
    [METRIC_KEYS.RECEIVED_DUPLICATE_MSG]: 'msgs',
    [METRIC_KEYS.CURRENT_STAGE]: 'stgs',
    [METRIC_KEYS.AVG_RTT]: 'ms',
    [METRIC_KEYS.AVG_MSG_PER_SECOND]: 'msgs/s',
    [METRIC_KEYS.LAST_RTT]: 'ms',
    [METRIC_KEYS.COVERS_SENT]: 'covs',
    [METRIC_KEYS.COVERS_RECEIVED]: 'covs',
    [METRIC_KEYS.SENDING_COVERS]: 'covs',
    [METRIC_KEYS.SENDING_MESSAGES]: 'msgs',
    [METRIC_KEYS.QUEUED_PACKAGES]: 'pkgs',
    [METRIC_KEYS.QUEUE_INTERVAL]: 's',
};

export const METRIC_GROUPS = {
    Communication: [
        METRIC_KEYS.TOTAL_SENT,
        METRIC_KEYS.TOTAL_RECEIVED,
        METRIC_KEYS.TOTAL_MBYTES_SENT,
        METRIC_KEYS.TOTAL_MBYTES_RECEIVED,
        METRIC_KEYS.UNACKED_MSG,
        METRIC_KEYS.RESENT,
        METRIC_KEYS.RECEIVED_DUPLICATE_MSG,
        METRIC_KEYS.AVG_RTT,
        METRIC_KEYS.LAST_RTT,
        METRIC_KEYS.AVG_MSG_PER_SECOND
    ],
    'Model Exchange': [
        METRIC_KEYS.FRAGMENTS_SENT,
        METRIC_KEYS.FRAGMENTS_RECEIVED,
        METRIC_KEYS.ACTIVE_PEERS
    ],
    Mixnet: [
        METRIC_KEYS.FORWARDED,
        METRIC_KEYS.SURB_REPLIED,
        METRIC_KEYS.SURB_RECEIVED,
        METRIC_KEYS.COVERS_SENT,
        METRIC_KEYS.COVERS_RECEIVED,
        METRIC_KEYS.SENDING_COVERS,
        METRIC_KEYS.SENDING_MESSAGES,
        METRIC_KEYS.QUEUED_PACKAGES,
        METRIC_KEYS.QUEUE_INTERVAL,
    ],
    Miscellaneous: [
        METRIC_KEYS.ERRORS,
        METRIC_KEYS.DELETED_CACHE_FOR_INACTIVE,
    ],
    Learning: [
        METRIC_KEYS.ACCURACY,
        METRIC_KEYS.AGGREGATED_ACCURACY,
        METRIC_KEYS.CURRENT_ROUND,
        METRIC_KEYS.ROUND_TIME,
        METRIC_KEYS.CURRENT_STAGE
    ]
};

export const ALWAYS_ACTIVE_METRICS = [
    METRIC_KEYS.TOTAL_SENT,
    METRIC_KEYS.CURRENT_ROUND,
    METRIC_KEYS.ACTIVE_PEERS,
    METRIC_KEYS.RECEIVED_DUPLICATE_MSG,
    METRIC_KEYS.UNACKED_MSG,
    METRIC_KEYS.RESENT
];

export const getDisplayName = key => METRIC_FIELDS[key] || null;
export const getUnit = key => METRIC_UNITS[key] || '';
