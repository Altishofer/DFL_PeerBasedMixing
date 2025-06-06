import React, { useEffect, useRef, useState } from 'react';
import LogService from '../../../services/LogService';

export default function ContainerLog({ containerName, resetTrigger }) {
  const [logs, setLogs] = useState([]);
  const logRef = useRef(null);
  const serviceRef = useRef(null);

  useEffect(() => {
    setLogs([]);
  }, [resetTrigger]);

  useEffect(() => {
    if (!containerName) return;

    setLogs([]);
    serviceRef.current = new LogService(
      containerName,
        (line) =>
      setLogs((prev) => {
        const recent = prev.slice(-20);
        if (recent.includes(line)) return prev;
        return [...prev.slice(-499), line];
      }),

      (err) => console.error(`LogService error:`, err)
    );

    serviceRef.current.start();

    return () => {
      serviceRef.current?.stop();
    };
  }, [containerName]);

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div ref={logRef} className="docker-logs-text">
      {logs.map((line, idx) => (
        <div key={idx}>{line}</div>
      ))}
    </div>
  );
}
