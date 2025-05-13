import React from 'react';

const SimulationProgress = ({ progress, onRoundSelect, activeRound }) => {
  if (!progress) {
    return (
      <div className="simulation-progress idle">
        <div className="progress-header">
          <h3>Simulation Progress</h3>
          <span>No simulation running</span>
        </div>
        <div className="progress-bar-container empty">
          <div className="progress-bar" style={{ width: '0%' }} />
        </div>
      </div>
    );
  }

  const { currentRound, totalRounds } = progress;
  const percentage = Math.min(100, Math.max(0, (currentRound / totalRounds) * 100));

  return (
    <div className="simulation-progress active">
      <div className="progress-header">
        <h3>Simulation Progress</h3>
        <span>Round {currentRound} of {totalRounds}</span>
      </div>
      <div className="progress-bar-container">
        <div className="progress-bar" style={{ width: `${percentage}%` }} />
      </div>
      <div className="round-selector">
        {Array.from({ length: totalRounds }, (_, i) => i + 1).map(round => (
          <button
            key={round}
            className={`round-button ${round === activeRound ? 'active' : ''} ${round <= currentRound ? 'completed' : ''}`}
            onClick={() => onRoundSelect(round)}
            disabled={round > currentRound}
          >
            {round}
          </button>
        ))}
      </div>
    </div>
  );
};

export default SimulationProgress;
