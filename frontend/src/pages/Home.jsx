import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import '../styles/Home.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

export default function Home() {
  const navigate = useNavigate();
  const [systemStatus, setSystemStatus] = useState(null);
  const [fps, setFps] = useState(0);
  const [isOnline, setIsOnline] = useState(false);

  // Fetch system status
  const fetchStatus = useCallback(() => {
    fetch(`${API_URL}/api/python/status`)
      .then((r) => {
        if (!r.ok) throw new Error('Status check failed');
        return r.json();
      })
      .then((data) => {
        setSystemStatus(data);
        setIsOnline(true);
        if (data.fps) setFps(data.fps);
      })
      .catch((error) => {
        console.error('Status check error:', error);
        setIsOnline(false);
      });
  }, []);

  // Initial status fetch and periodic updates
  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  const menuItems = [
    {
      id: 'live-feed',
      icon: '📹',
      path: '/live-feed',
      color: '#4CAF50'
    },
    {
      id: 'driving-mode',
      icon: '🚗',
      path: '/driving-mode',
      color: '#2196F3'
    },
    {
      id: 'settings',
      icon: '⚙️',
      path: '/settings',
      color: '#FF9800'
    },
    {
      id: 'logs',
      icon: '📊',
      path: '/logs',
      color: '#9C27B0'
    }
  ];

  return (
    <div className="home-container">
      <div className="home-center-block">
        <header className="home-header">
          <h1 className="home-title">Traffic Sign Detection</h1>
          <div className="system-status-home">
            <span className={isOnline && systemStatus?.running ? 'status-ok' : 'status-error'}>
              {isOnline && systemStatus?.running ? '● System Online' : '○ System Offline'}
            </span>
            {fps > 0 && <span className="fps-display">{fps} FPS</span>}
          </div>
        </header>
        <div className="menu-grid">
          {menuItems.map((item) => (
            <button
              key={item.id}
              className="menu-card"
              onClick={() => navigate(item.path)}
              style={{ '--card-color': item.color }}
            >
              <div className="menu-icon">{item.icon}</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
