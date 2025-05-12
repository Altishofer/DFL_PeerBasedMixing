import { useCallback } from 'react';
import NodeStatusService from '../services/NodeStatusService';

const useNodeStatus = (setNodeStatus, setError, setNodeUptimes) =>
  useCallback(() => {
    NodeStatusService.fetchStatus({
      onSetStatus: setNodeStatus,
      onSetUptimes: setNodeUptimes,
      onError: setError
    });
  }, [setNodeStatus, setError, setNodeUptimes]);

export default useNodeStatus;
