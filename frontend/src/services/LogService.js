export default class LogService {
  constructor(containerName, onLog, onError) {
    this.containerName = containerName;
    this.onLog = onLog;
    this.onError = onError;
    this.ws = null;
  }

  start() {
    if (!this.containerName) return;

    this.ws = new WebSocket(`ws://localhost:8000/logs/${this.containerName}`);

    this.ws.onmessage = (event) => {
      if (this.onLog) this.onLog(event.data);
    };

    this.ws.onerror = (err) => {
      console.error(`WebSocket error for ${this.containerName}:`, err);
      if (this.onError) this.onError(err);
    };

    this.ws.onclose = () => {
      console.log(`WebSocket closed for ${this.containerName}`);
    };
  }

  stop() {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.close();
    }
  }
}
