import React from 'react';
import { useNavigate } from 'react-router-dom';
import LiveFeedComponent from '../components/LiveFeed';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

export default function LiveFeedPage() {
  const navigate = useNavigate();

  return (
    <div className="dashboard">
      <div className="dashboard-content">
        <div className="video-section">
          <div className="overlay-controls">
            <button className="exit-button-overlay" onClick={() => navigate('/')}>
              ✕
            </button>
          </div>
          <LiveFeedComponent apiUrl={API_URL} />
        </div>
      </div>
    </div>
  );
}
