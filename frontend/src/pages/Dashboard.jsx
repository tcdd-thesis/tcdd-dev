import React, { useEffect, useState, useRef, useCallback } from 'react';
import DetectionCard from '../components/DetectionCard';
import LiveFeed from '../components/LiveFeed';
import configService from '../services/configService';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';
let POLL_INTERVAL = 500; // Will be updated from config
const STATUS_CHECK_INTERVAL = 5000;

export default function Dashboard() {
  const [detections, setDetections] = useState([]);
  const [systemStatus, setSystemStatus] = useState(null);
  const [fps, setFps] = useState(0);
  const [isOnline, setIsOnline] = useState(true);
  const [maxDetections, setMaxDetections] = useState(5);
  const pollTimerRef = useRef(null);
  const statusTimerRef = useRef(null);
  const abortControllerRef = useRef(null);

  // Load configuration on mount
  useEffect(() => {
    configService.ensureLoaded().then(() => {
      POLL_INTERVAL = configService.getPollInterval();
      setMaxDetections(configService.getMaxDetectionsDisplay());
      console.log('✓ Dashboard configuration loaded');
      console.log(`  Poll Interval: ${POLL_INTERVAL}ms`);
      console.log(`  Max Detections: ${configService.getMaxDetectionsDisplay()}`);
    });
  }, []);

  // Fetch system status periodically
  const fetchStatus = useCallback(() => {
    fetch(`${API_URL}/api/python/status`, { 
      signal: abortControllerRef.current?.signal 
    })
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
        if (error.name !== 'AbortError') {
          console.error('Status check error:', error);
          setIsOnline(false);
        }
      });
  }, []);

  // Fetch detections with error handling
  const fetchDetections = useCallback(() => {
    fetch(`${API_URL}/api/python/detections`, {
      signal: abortControllerRef.current?.signal
    })
      .then((r) => {
        if (!r.ok) throw new Error('Detection fetch failed');
        return r.json();
      })
      .then((data) => {
        if (data.ok && data.detections) {
          setDetections(data.detections);
          if (data.fps) setFps(data.fps);
        }
        setIsOnline(true);
      })
      .catch((error) => {
        if (error.name !== 'AbortError') {
          console.error('Detection fetch error:', error);
          setIsOnline(false);
        }
      });
  }, []);

  // Initial status fetch
  useEffect(() => {
    abortControllerRef.current = new AbortController();
    fetchStatus();

    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [fetchStatus]);

  // Poll detections continuously
  useEffect(() => {
    fetchDetections();
    pollTimerRef.current = setInterval(fetchDetections, POLL_INTERVAL);

    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
      }
    };
  }, [fetchDetections]);

  // Poll status periodically
  useEffect(() => {
    statusTimerRef.current = setInterval(fetchStatus, STATUS_CHECK_INTERVAL);

    return () => {
      if (statusTimerRef.current) {
        clearInterval(statusTimerRef.current);
      }
    };
  }, [fetchStatus]);

  return (
    <div className="page-dashboard">
      <header className="dashboard-header">
        <h1>🚦 Sign Detection System</h1>
        {systemStatus && (
          <div className="system-status">
            <span className={isOnline && systemStatus.running ? 'status-ok' : 'status-error'}>
              {isOnline && systemStatus.running ? '● Live' : '○ Offline'}
            </span>
            <span className="status-detail">
              {fps > 0 && `${fps} FPS | `}
              Camera: {systemStatus.camera ? '✓' : '✗'} | 
              Model: {systemStatus.model ? '✓' : '✗'}
            </span>
          </div>
        )}
      </header>

      <div className="dashboard-content">
        <div className="video-section">
          <LiveFeed apiUrl={API_URL} />
        </div>

        <div className="detections-section">
          <h3>Recent Detections ({detections.length})</h3>
          <div className="detections-list">
            {detections.length === 0 ? (
              <div className="no-detections">
                {isOnline ? 'No signs detected' : 'System offline - reconnecting...'}
              </div>
            ) : (
              detections.slice(0, maxDetections).map((d, idx) => (
                <DetectionCard key={`${d.id}-${d.timestamp}-${idx}`} detection={d} />
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
