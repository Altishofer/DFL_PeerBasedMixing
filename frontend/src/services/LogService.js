import { WS_BASE_URL } from '../constants/constants';
import { createSSEService } from './SseService';

export default class LogService {
  constructor(containerName, onLog, onError) {
    this.containerName = containerName;
    this.onLog = onLog;
    this.onError = onError;
    this.wsService = createSSEService();
  }

  start() {
    if (!this.containerName) return;
    const url = `${WS_BASE_URL}/logs/${this.containerName}`;
    this.wsService.initialize(url, this.handleMessage.bind(this));
  }

  handleMessage(data) {
    if (typeof data === 'string') {
      this.onLog?.(data);
    } else if (data?.data) {
      this.onLog?.(data.data);
    }
  }

  stop() {
    this.wsService.disconnect();
  }

  getSocket() {
    return this.wsService.getSocket();
  }
}
