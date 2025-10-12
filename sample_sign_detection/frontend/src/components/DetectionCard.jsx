import React from 'react';
import ConfidenceBar from './ConfidenceBar';

export default function DetectionCard({ detection }) {
  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp * 1000);
    return date.toLocaleTimeString();
  };

  return (
    <div className="detection-card">
      <h4>{detection.label.replace(/_/g, ' ')}</h4>
      <ConfidenceBar value={detection.confidence} />
      <p>Position: [{detection.bbox.join(', ')}]</p>
      {detection.timestamp && (
        <p className="timestamp">Detected: {formatTimestamp(detection.timestamp)}</p>
      )}
    </div>
  );
}
