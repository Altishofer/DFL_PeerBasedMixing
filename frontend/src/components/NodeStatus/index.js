import React from 'react';

const NodeStatus = ({ nodeNames, nodeStatus, nodeUptimes, palette, onSelectNode }) => {
  return (
    <div className="dashboard-card">
      <h3>Node Status</h3>
      {nodeNames.length > 0 ? (
        <div className="status-table-container">
          <table className="status-table">
            <thead>
              <tr>
                <th>Node</th>
                <th>Status</th>
                <th>Uptime</th>
              </tr>
            </thead>
            <tbody>
              {nodeNames.map((node, index) => {
                const statusInfo = nodeStatus.find(({ name }) => name === node);
                const uptimeInfo = nodeUptimes[node];
                const isRunning = statusInfo?.status?.toLowerCase() === 'running';

                const displayUptime =
                  uptimeInfo && !isNaN(uptimeInfo.elapsedMs)
                    ? (() => {
                        const totalMs = uptimeInfo.elapsedMs;
                        const seconds = Math.floor(totalMs / 1000) % 60;
                        const minutes = Math.floor(totalMs / (1000 * 60)) % 60;
                        return `${minutes}m ${seconds}s`;
                      })()
                    : '--';

                return (
                  <tr
                    key={node}
                    onClick={() => onSelectNode?.(node)}
                    style={{ cursor: 'pointer' }}
                  >
                    <td style={{ color: palette[index % palette.length], fontWeight: 500 }}>
                      {node}
                    </td>
                    <td className={`status-${statusInfo?.status?.toLowerCase() || 'unknown'}`}>
                      {statusInfo?.status || 'Unknown'}
                    </td>
                    <td>{isRunning ? displayUptime : '--'}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="no-data">No active nodes</p>
      )}
    </div>
  );
};

export default NodeStatus;
