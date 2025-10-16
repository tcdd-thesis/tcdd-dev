import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import '../styles/Logs.css';

export default function Logs() {
  const navigate = useNavigate();
  const [logs, setLogs] = useState([]);
  const [filter, setFilter] = useState('all');
  const [sortBy, setSortBy] = useState('newest');

  // Mock data - TODO: Replace with actual API call
  useEffect(() => {
    const mockLogs = [
      {
        id: 1,
        timestamp: new Date(Date.now() - 5000),
        label: 'Speed Limit 60',
        confidence: 0.95,
        location: { lat: 14.5995, lng: 120.9842 }
      },
      {
        id: 2,
        timestamp: new Date(Date.now() - 15000),
        label: 'Stop',
        confidence: 0.89,
        location: { lat: 14.5985, lng: 120.9832 }
      },
      {
        id: 3,
        timestamp: new Date(Date.now() - 30000),
        label: 'Red Light',
        confidence: 0.92,
        location: { lat: 14.5975, lng: 120.9822 }
      },
      {
        id: 4,
        timestamp: new Date(Date.now() - 120000),
        label: 'Speed Limit 40',
        confidence: 0.87,
        location: { lat: 14.5965, lng: 120.9812 }
      },
      {
        id: 5,
        timestamp: new Date(Date.now() - 180000),
        label: 'Green Light',
        confidence: 0.94,
        location: { lat: 14.5955, lng: 120.9802 }
      }
    ];
    setLogs(mockLogs);
  }, []);

  const formatTimestamp = (date) => {
    const now = new Date();
    const diff = Math.floor((now - date) / 1000); // seconds

    if (diff < 60) return `${diff}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return date.toLocaleDateString();
  };

  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.9) return '#4CAF50';
    if (confidence >= 0.7) return '#FF9800';
    return '#f44336';
  };

  const filteredLogs = logs.filter((log) => {
    if (filter === 'all') return true;
    if (filter === 'high') return log.confidence >= 0.9;
    if (filter === 'medium') return log.confidence >= 0.7 && log.confidence < 0.9;
    if (filter === 'low') return log.confidence < 0.7;
    return true;
  });

  const sortedLogs = [...filteredLogs].sort((a, b) => {
    if (sortBy === 'newest') return b.timestamp - a.timestamp;
    if (sortBy === 'oldest') return a.timestamp - b.timestamp;
    if (sortBy === 'confidence') return b.confidence - a.confidence;
    return 0;
  });

  const clearLogs = () => {
    if (window.confirm('Are you sure you want to clear all detection logs?')) {
      setLogs([]);
    }
  };

  return (
    <div className="logs-container">
      <header className="page-header">
        <button className="back-button" onClick={() => navigate('/')}>
          ← Back
        </button>
        <h1>Detection Logs</h1>
      </header>

      <div className="logs-controls">
        <div className="filter-controls">
          <label>Filter:</label>
          <select value={filter} onChange={(e) => setFilter(e.target.value)}>
            <option value="all">All ({logs.length})</option>
            <option value="high">High Confidence (≥90%)</option>
            <option value="medium">Medium Confidence (70-89%)</option>
            <option value="low">Low Confidence (&lt;70%)</option>
          </select>
        </div>

        <div className="sort-controls">
          <label>Sort by:</label>
          <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
            <option value="newest">Newest First</option>
            <option value="oldest">Oldest First</option>
            <option value="confidence">Highest Confidence</option>
          </select>
        </div>

        <button className="clear-logs-button" onClick={clearLogs}>
          🗑️ Clear All
        </button>
      </div>

      <div className="logs-stats">
        <div className="stat-card">
          <span className="stat-value">{logs.length}</span>
          <span className="stat-label">Total Detections</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">
            {logs.filter(l => l.confidence >= 0.9).length}
          </span>
          <span className="stat-label">High Confidence</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">
            {logs.length > 0 ? Math.round(logs.reduce((sum, l) => sum + l.confidence, 0) / logs.length * 100) : 0}%
          </span>
          <span className="stat-label">Avg Confidence</span>
        </div>
      </div>

      <div className="logs-list">
        {sortedLogs.length === 0 ? (
          <div className="no-logs">
            <p>📭 No detection logs available</p>
            <p className="no-logs-subtitle">Start using the Live Feed to generate logs</p>
          </div>
        ) : (
          sortedLogs.map((log) => (
            <div key={log.id} className="log-entry">
              <div className="log-header">
                <h3 className="log-label">{log.label}</h3>
                <span className="log-timestamp">{formatTimestamp(log.timestamp)}</span>
              </div>
              <div className="log-details">
                <div className="log-confidence">
                  <span>Confidence:</span>
                  <div className="confidence-bar">
                    <div
                      className="confidence-fill"
                      style={{
                        width: `${log.confidence * 100}%`,
                        backgroundColor: getConfidenceColor(log.confidence)
                      }}
                    />
                  </div>
                  <span style={{ color: getConfidenceColor(log.confidence) }}>
                    {Math.round(log.confidence * 100)}%
                  </span>
                </div>
                {log.location && (
                  <div className="log-location">
                    📍 {log.location.lat.toFixed(4)}, {log.location.lng.toFixed(4)}
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
