import React from 'react';

const formatUptime = (ms) => {
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}m ${seconds}s`;
};

const NodeStatus = ({ nodeNames, nodeStatus, nodeUptimes, palette }) => {
  return (
    <div className="dashboard-card">
      <h3>Node Status</h3>
      {nodeNames.length > 0 ? (
        <div className="status-table-container">
          <table>
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
                const displayUptime = uptimeInfo?.elapsedMs != null
                  ? formatUptime(uptimeInfo.elapsedMs)
                  : '---';

                return (
                  <tr key={node}>
                    <td style={{ color: palette[index % palette.length], fontWeight: 500 }}>
                      {node.replace(/^node_/, 'Node ')}
                    </td>

                    <td className={`status-${statusInfo?.status?.toLowerCase() ?? 'unknown'}`}>
                      {statusInfo?.status ?? 'Unknown'}
                    </td>
                    <td>{displayUptime}</td>
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
