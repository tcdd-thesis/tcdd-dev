import React from 'react';
import { useNavigate } from 'react-router-dom';
import '../styles/DrivingMode.css';

export default function DrivingMode() {
  const navigate = useNavigate();

  const modes = [
    {
      id: 'casual',
      title: 'Casual',
      icon: '🚙'
    },
    {
      id: 'gamified',
      title: 'Gamified',
      icon: '🎮'
    }
  ];

  const startMode = (modeId) => {
    console.log(`Starting ${modeId} mode...`);
    alert(`${modeId.toUpperCase()} MODE - Coming Soon!`);
  };

  return (
    <div className="driving-mode-container">
      <header className="page-header">
        <button className="back-button" onClick={() => navigate('/')}>
          ← Back
        </button>
        <h1>Driving Mode</h1>
      </header>

      <div className="mode-selection">
        <div className="modes-grid">
          {modes.map((mode) => (
            <button
              key={mode.id}
              className="mode-card"
              onClick={() => startMode(mode.id)}
            >
              <div className="mode-icon">{mode.icon}</div>
              <div className="mode-title">{mode.title}</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
