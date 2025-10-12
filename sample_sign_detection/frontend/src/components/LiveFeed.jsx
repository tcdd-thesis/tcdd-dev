import React, { useState, useRef, useEffect } from 'react';

export default function LiveFeed({ apiUrl = 'http://localhost:5000' }) {
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [reconnectAttempt, setReconnectAttempt] = useState(0);
  const imgRef = useRef(null);
  const reconnectTimerRef = useRef(null);
  
  const videoUrl = `${apiUrl}/video_feed?t=${Date.now()}`; // Cache buster
  
  const handleLoad = () => {
    setIsLoading(false);
    setError(null);
    setReconnectAttempt(0);
  };
  
  const handleError = () => {
    setIsLoading(false);
    setError('Camera feed unavailable');
    
    // Auto-reconnect after 3 seconds
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
    }
    
    reconnectTimerRef.current = setTimeout(() => {
      setReconnectAttempt(prev => prev + 1);
      setIsLoading(true);
      setError(null);
    }, 3000);
  };
  
  useEffect(() => {
    return () => {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
    };
  }, []);
  
  // Force reload on reconnect attempt
  const currentVideoUrl = reconnectAttempt > 0 
    ? `${apiUrl}/video_feed?t=${Date.now()}&attempt=${reconnectAttempt}`
    : videoUrl;
  
  return (
    <div className="live-feed">
      {isLoading && (
        <div className="loading">
          Loading camera feed{reconnectAttempt > 0 ? ` (attempt ${reconnectAttempt})` : ''}...
        </div>
      )}
      {error && (
        <div className="error">
          {error}. Reconnecting...
        </div>
      )}
      <img 
        ref={imgRef}
        src={currentVideoUrl}
        alt="Live camera feed with detections"
        onLoad={handleLoad}
        onError={handleError}
        style={{ display: isLoading || error ? 'none' : 'block' }}
      />
    </div>
  );
}
