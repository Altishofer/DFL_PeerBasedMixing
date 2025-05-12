import React, { useEffect, useRef, useState } from 'react';

export default function DockerLogs({ containerName }) {
  const [logs, setLogs] = useState([]);
  const logRef = useRef(null);
  const wsRef = useRef(null);

  useEffect(() => {
    if (!containerName) return;

    setLogs([]);

    const ws = new WebSocket(`ws://localhost:8000/logs/${containerName}`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      setLogs(prev => [...prev.slice(-500), event.data]);
    };

    ws.onerror = (err) => {
      console.error(`WebSocket error for container ${containerName}:`, err);
    };

    ws.onclose = () => {
      console.log(`WebSocket closed for container ${containerName}`);
    };

    return () => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.close();
      }
    };
  }, [containerName]);

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [logs]);

return (
  <div className="docker-logs-container">
    <div className="docker-logs-header">
      <h3>Node Logs</h3>
      Viewing logs for: <strong>{containerName}</strong>
    </div>
    <div ref={logRef} className="docker-logs-text">
      {logs.map((line, index) => (
        <div key={index}>{line}</div>
      ))}
    </div>
  </div>
);




}
