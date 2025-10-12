import React from 'react';

export default function ConfidenceBar({ value }) {
  const pct = Math.round((value || 0) * 100);
  return (
    <div className="confidence-bar">
      <div className="fill" style={{ width: `${pct}%` }} />
      <span className="label">{pct}%</span>
    </div>
  );
}
