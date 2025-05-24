export default function SimulationSettings({
  nodeCount, setNodeCount, maxNodes,
  rounds, setRounds, 
  stream, setStream,
  exitNodes, updateExitNodes,
  joinNodes, updateJoinNodes,
  displayMode, setDisplayMode,
  isLoading
}) {
  return (
    <>
      <div className="control-group-box">
        <h3>Basic Configuration</h3>
        <div className="control-row">
          <div className="control-group control-input-limited">
            <label htmlFor="nodeCount">Initial Nodes</label>
            <input
              id="nodeCount"
              type="number"
              min="1"
              max={maxNodes}
              value={nodeCount}
              onChange={(e) => {
                const value = Math.min(maxNodes, Math.max(1, parseInt(e.target.value, 10) || 1));
                setNodeCount(value);
              }}
              disabled={isLoading}
            />
          </div>

          <div className="control-group control-input-limited">
            <label htmlFor="rounds">Total Rounds</label>
            <input
              id="rounds"
              type="number"
              min="1"
              max="100"
              value={rounds}
              onChange={(e) => setRounds(Math.max(1, parseInt(e.target.value, 10) || 1))}
              disabled={isLoading}
            />
          </div>

          <div className="control-group control-input-limited">
            <label htmlFor="stream">Stream updates</label>
            <input
              type="checkbox"
              className="checkbox"
              id="stream"
              checked={stream}
              onChange={(e) => setStream(e.target.checked)}
              disabled={isLoading}
            />
          </div>
        </div>
      </div>

      <div className="control-group-box">
        <h3>Node Join/Exit Configuration</h3>
        <div className="control-row">
          <div className="control-group control-input-limited">
            <label htmlFor="exitCount">Total Nodes to Exit</label>
            <input
              id="exitCount"
              type="number"
              min="0"
              max={nodeCount}
              value={exitNodes}
              onChange={(e) => updateExitNodes(Math.max(0, parseInt(e.target.value, 10) || 0))}
              disabled={isLoading}
            />
          </div>

          <div className="control-group control-input-limited">
            <label htmlFor="joinCount">Total Nodes to Join</label>
            <input
              id="joinCount"
              type="number"
              min="0"
              max={maxNodes - nodeCount}
              value={joinNodes}
              onChange={(e) => updateJoinNodes(Math.max(0, parseInt(e.target.value, 10) || 0))}
              disabled={isLoading}
            />
          </div>
        </div>
      </div>
    </>
  );
}
