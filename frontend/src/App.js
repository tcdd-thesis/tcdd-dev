import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Home from './pages/Home';
import LiveFeed from './pages/LiveFeed';
import DrivingMode from './pages/DrivingMode';
import Settings from './pages/Settings';
import Logs from './pages/Logs';

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/live-feed" element={<LiveFeed />} />
        <Route path="/driving-mode" element={<DrivingMode />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/logs" element={<Logs />} />
      </Routes>
    </Router>
  );
}
