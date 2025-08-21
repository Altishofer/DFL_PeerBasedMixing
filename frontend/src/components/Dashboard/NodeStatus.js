import React from 'react';

const NodeStatus = ({
                        nodeNames,
                        nodeStatus,
                        nodeUptimes,
                        palette,
                        currentRounds,
                        totalRounds
                    }) => {
    const renderNodeRow = (node, index) => {
        const statusInfo = nodeStatus.find(({name}) => name === node);
        const uptimeInfo = nodeUptimes[node];
        const isRunning = statusInfo?.status?.toLowerCase() === 'running';

        const displayUptime =
            uptimeInfo && !isNaN(uptimeInfo.elapsedMs)
                ? (() => {
                    const totalMs = uptimeInfo.elapsedMs;
                    const seconds = Math.max(Math.floor(totalMs / 1000) % 60, 0);
                    const minutes = Math.max(Math.floor(totalMs / (1000 * 60)) % 60, 0);
                    return `${minutes}m ${seconds}s`;
                })()
                : '--';

        const currentRound = currentRounds?.[node];
        const displayRound =
            typeof currentRound === 'number' &&
            totalRounds &&
            uptimeInfo?.elapsedMs &&
            !isNaN(uptimeInfo.elapsedMs)
                ? `${currentRound}/${totalRounds}`
                : '--';

        const estimatedRemaining =
            typeof currentRound === 'number' &&
            currentRound > 0 &&
            totalRounds &&
            uptimeInfo?.elapsedMs &&
            !isNaN(uptimeInfo.elapsedMs)
                ? (() => {
                    const elapsed = uptimeInfo.elapsedMs;
                    const estimatedMs = elapsed * (totalRounds - currentRound) / currentRound;
                    let minutes = Math.floor(estimatedMs / 60000);
                    minutes = Math.max(0, minutes);
                    return `${minutes}m`;
                })()
                : '--';

        return (
            <tr key={node}>
                <td style={{color: palette[index % palette.length]}}>{node}</td>
                <td className={`status-${statusInfo?.status?.toLowerCase() || 'unknown'}`}>
                    {statusInfo?.status || 'Unknown'}
                </td>
                <td>{isRunning ? displayUptime : '--'}</td>
                <td>{displayRound}</td>
                <td>{isRunning ? estimatedRemaining : '--'}</td>
            </tr>
        );
    };

    const filteredNodes = nodeNames.filter(node => {
        const status = nodeStatus.find(({name}) => name === node)?.status;
        return status && status.toLowerCase() !== 'unknown';
    });

    return (
        <div className="dashboard-card">
            <h3>Node Status</h3>
            {filteredNodes.length > 0 ? (
                <div className="status-table-container">
                    <table className="status-table">
                        <thead>
                        <tr>
                            <th>Node</th>
                            <th>Status</th>
                            <th>Uptime</th>
                            <th>Round</th>
                            <th>ETA</th>
                        </tr>
                        </thead>
                        <tbody>
                        {filteredNodes.map((node, index) => renderNodeRow(node, index))}
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
