export default function BasicControls({ onStart, onStop, onClear, isLoading }) {
  return (
    <div className="control-row">
      <div className="control-group">
        <label>Actions</label>
        <div className="control-buttons">
          <button className="action-button start-button" onClick={onStart} disabled={isLoading}>
            {isLoading ? 'Starting…' : 'Start Simulation'}
          </button>
          <button className="action-button clear-button" onClick={onClear} disabled={isLoading}>
            Reset
          </button>
          <button className="action-button stop-button" onClick={onStop} disabled={isLoading}>
            Stop
          </button>
        </div>
      </div>
    </div>
  );
}
