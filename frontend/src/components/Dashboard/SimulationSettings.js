export default function SimulationSettings({
  nodeCount, setNodeCount, maxNodes,
  rounds, setRounds, 
  stream, setStream,
  exitNodes, updateExitNodes,
  joinNodes, updateJoinNodes,
  isLoading,
  mixing, mixingLambda, mixingMu,
  setMixing, setMixingLambda, setMixingMu
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

      <div className="control-group-box">
      <h3>Mixing</h3>
        <div className="control-row">
          <div className="control-group control-input-limited">
            <label htmlFor="mixingToggle">Enable Mixing</label>
            <input
              type="checkbox"
              className="checkbox"
              id="mixingToggle"
              checked={mixing}
              onChange={(e) => {
                mixing = e.target.checked;
                setMixing(mixing);
              }}
              disabled={isLoading}
            />
          </div>
        </div>

        <div className="control-row">
          <div className="control-group control-input-limited">
            <label htmlFor="mixingLambda" className={!mixing || isLoading ? 'label-disabled' : ''}>Avg. Traffic Interval (s)</label>
            <input
              id="mixingLambda"
              type="number"
              value={mixingLambda}
              min="0"
              step="0.1"
              onChange={(e) => {
                mixingLambda = parseFloat(e.target.value) || 0;
                setMixingLambda(mixingLambda);
              }}
              disabled={!mixing || isLoading}
            />
          </div>

          <div className="control-group control-input-limited">
            <label htmlFor="mixingMu" className={!mixing || isLoading ? 'label-disabled' : ''} >Avg. Delay (s)</label>
            <input
              id="mixingMu"
              type="number"
              value={mixingMu}
              min="0"
              step="0.1"
              onChange={(e) => {
                mixingMu = parseFloat(e.target.value) || 0;
                setMixingMu(mixingMu);
              }}
              disabled={!mixing || isLoading}
            />
          </div>
        </div>
      </div>
    </>
  );
}
