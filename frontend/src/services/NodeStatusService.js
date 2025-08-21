import axios from 'axios';
import {API_BASE_URL} from '../constants/constants';

export default class NodeStatusService {
    static async fetchStatus({onSetStatus, onSetUptimes, onError}) {
        try {
            const {data} = await axios.get(`${API_BASE_URL}/nodes/status`);
            const statusData = data?.node_status || data || [];
            onSetStatus(statusData);

            const updatedUptimes = {};
            const knownNames = new Set();

            statusData.forEach(({name, status, started_at}) => {
                if (!name) return;
                const isRunning = status?.toLowerCase() === 'running';
                const startTime = started_at ? new Date(started_at).getTime() : null;

                updatedUptimes[name] = {
                    startTime,
                    isRunning,
                    status,
                    elapsedMs: isRunning ? Date.now() - startTime : 0,
                };

                knownNames.add(name);
            });

            onSetUptimes((prev) => {
                const all = {...prev, ...updatedUptimes};
                Object.keys(prev).forEach((name) => {
                    if (!knownNames.has(name)) {
                        all[name] = {...prev[name], isRunning: false, status: 'unknown'};
                    }
                });
                return all;
            });

            onError('');
        } catch (err) {
            console.error('Node status fetch error:', err);
            onError('Failed to fetch node status');
        }
    }
}