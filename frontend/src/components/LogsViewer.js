import React, { useEffect, useState } from 'react';

const LogsViewer = ({ containerName }) => {
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    if (!containerName) return;

    const ws = new WebSocket(`ws://localhost:8000/ws/logs/${containerName}`);

    ws.onmessage = (event) => {
      setLogs((prevLogs) => [...prevLogs.slice(-500), event.data]);
    };

    ws.onerror = (err) => console.error('WebSocket error', err);
    ws.onclose = () => console.log('WebSocket closed');

    return () => ws.close();
  }, [containerName]);

  return (
    <div className="logs-box">
      {logs.map((line, i) => (
        <pre key={i}>{line}</pre>
      ))}
    </div>
  );
};

export default LogsViewer;
