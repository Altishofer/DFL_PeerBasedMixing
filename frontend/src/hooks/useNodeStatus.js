import { useCallback } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../constants';

const useNodeStatus = (setNodeStatus, setError, setNodeUptimes) =>
  useCallback(async () => {
    try {
      const { data } = await axios.get(`${API_BASE_URL}/nodes/status`);
      const fetchedStatus = data?.node_status || data || [];

      setError('');
      setNodeStatus(fetchedStatus);

      setNodeUptimes((prev) => {
        const updated = { ...prev };
        const knownNames = new Set();

        fetchedStatus.forEach(({ name, status, started_at }) => {
          if (!name) return;
          const isRunning = status?.toLowerCase() === 'running';
          const startTime = started_at ? new Date(started_at).getTime() : null;

          updated[name] = {
            startTime,
            isRunning,
            status,
            elapsedMs: isRunning ? Date.now() - startTime : prev[name]?.elapsedMs || 0,
          };

          knownNames.add(name);
        });

        Object.keys(prev).forEach((name) => {
          if (!knownNames.has(name)) {
            updated[name] = {
              ...prev[name],
              isRunning: false,
              status: 'unknown',
            };
          }
        });

        return updated;
      });
    } catch (err) {
      console.error('Error fetching node status:', err);
      setError('Failed to fetch node status');
    }
  }, [setNodeStatus, setError, setNodeUptimes]);

export default useNodeStatus;
