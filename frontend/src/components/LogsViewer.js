import React, { useState, useEffect } from 'react';

const LogsViewer = ({ containerName }) => {
  const [logs, setLogs] = useState([]);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    const socket = new WebSocket(`ws://localhost:8000/ws/logs/${containerName}`);

    socket.onopen = () => {
      setIsConnected(true);
    };

    socket.onmessage = (event) => {
      const newLog = event.data;
      setLogs((prevLogs) => [...prevLogs, newLog]);
    };

    socket.onclose = () => {
      setIsConnected(false);
    };

    return () => {
      socket.close();
    };
  }, [containerName]);

  return (
    <div className="logs-container">
      <h3>Logs for {containerName}</h3>
      {isConnected ? (
        <div>
          <p>Connected to container logs stream...</p>
          <div className="logs">
            {logs.map((log, index) => (
              <div key={index} className="log-entry">
                {log}
              </div>
            ))}
          </div>
        </div>
      ) : (
        <p>Connecting...</p>
      )}
    </div>
  );
};

export default LogsViewer;
