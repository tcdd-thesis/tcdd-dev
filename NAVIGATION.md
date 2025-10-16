# Frontend Navigation Structure

## Overview
The frontend features a main dashboard/home page with 4 primary navigation options and system status monitoring. Home serves as the central hub showing system health before navigating to specific features.

## Pages & Routes

### 1. Home (Dashboard) (`/`)
**File:** `frontend/src/pages/Home.jsx`
**Style:** `frontend/src/styles/Home.css`

Main landing page/dashboard with:
- **System Status Display**
  - Live connection indicator (● Online / ○ Offline)
  - Real-time FPS counter
  - Updates every 5 seconds via backend API
  
- **4 Navigation Cards:**
  - **Live Feed** 📹 - Real-time traffic sign detection
  - **Driving Mode** 🚗 - Casual or Gamified experience
  - **Settings** ⚙️ - Brightness, Color & Language
  - **Detection Logs** 📊 - View detection history

### 2. Live Feed (`/live-feed`)
**File:** `frontend/src/pages/LiveFeed.jsx`
**Style:** `frontend/src/styles/App.css`

Real-time camera feed page:
- Full-screen live video feed
- Exit button (top right) to return to home
- Minimal overlay interface
- No status display (shown on home page instead)

### 3. Driving Mode (`/driving-mode`)
**File:** `frontend/src/pages/DrivingMode.jsx`
**Style:** `frontend/src/styles/DrivingMode.css`

Choose between two driving experiences:
- **Casual Mode** 🚙
  - Real-time sign detection
  - Audio alerts
  - Simple display
  - No scoring
  
- **Gamified Mode** 🎮
  - Points & scoring system
  - Achievement badges
  - Leaderboards
  - Performance analytics

### 4. Settings (`/settings`)
**File:** `frontend/src/pages/Settings.jsx`
**Style:** `frontend/src/styles/Settings.css`

Configuration options:
- **Brightness** 💡 - Slider control (0-100%)
- **Color Theme** 🎨 - Light / Dark / Auto
- **Language** 🌍 - English, Español, Français, Deutsch, Tagalog

### 5. Detection Logs (`/logs`)
**File:** `frontend/src/pages/Logs.jsx`
**Style:** `frontend/src/styles/Logs.css`

View detection history:
- Filter by confidence level (All, High, Medium, Low)
- Sort by newest/oldest/confidence
- Statistics dashboard (total detections, high confidence count, avg confidence)
- Individual log entries with:
  - Sign label
  - Timestamp (relative time)
  - Confidence percentage with color-coded bar
  - GPS coordinates (if available)
- Clear all logs functionality

## Routing Setup

**Main Router:** `frontend/src/App.js`

Using React Router v6:
```javascript
<Router>
  <Routes>
    <Route path="/" element={<Home />} />
    <Route path="/live-feed" element={<Dashboard />} />
    <Route path="/driving-mode" element={<DrivingMode />} />
    <Route path="/settings" element={<Settings />} />
    <Route path="/logs" element={<Logs />} />
  </Routes>
</Router>
```

## Dependencies

### Added Package
```bash
npm install react-router-dom
```

### Import in Components
```javascript
import { useNavigate } from 'react-router-dom';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
```

## Navigation Pattern

All pages (except Home) include an exit/back button to return to home:
```javascript
const navigate = useNavigate();

// Live Feed page - overlay exit button
<button className="exit-button-overlay" onClick={() => navigate('/')}>✕</button>

// Other pages - standard back button
<button onClick={() => navigate('/')}>← Back</button>
```

Home page uses direct navigation to features:
```javascript
<button onClick={() => navigate('/live-feed')}>Live Feed</button>
```

## System Status Integration

**Home Page Status Display:**
- Polls backend API every 5 seconds: `GET /api/python/status`
- Shows connection status with colored indicator
- Displays real-time FPS when available
- Gracefully handles offline state

```javascript
// Status polling in Home.jsx
useEffect(() => {
  fetchStatus();
  const interval = setInterval(fetchStatus, 5000);
  return () => clearInterval(interval);
}, [fetchStatus]);
```

## Design Features

### Consistent UI Elements
- Gradient backgrounds (unique color per page)
- White content cards with rounded corners
- Consistent back buttons with hover effects
- Smooth animations and transitions
- Responsive grid layouts

### Color Scheme by Page
- **Home (Dashboard):** Purple gradient (`#667eea` → `#764ba2`) with system status in header
- **Live Feed:** Full-screen video with minimal overlay (exit button only)
- **Driving Mode:** Blue (`#2196F3` → `#1976D2`)
- **Settings:** Orange (`#FF9800` → `#F57C00`)
- **Logs:** Purple (`#9C27B0` → `#7B1FA2`)

### Icons Used
- Live Feed: 📹
- Driving Mode: 🚗 (Casual: 🚙, Gamified: 🎮)
- Settings: ⚙️
- Detection Logs: 📊
- Additional: 💡 🎨 🌍 📭

## Responsive Design

All pages include mobile-friendly breakpoints at 768px:
- Grid layouts collapse to single column
- Font sizes adjust for smaller screens
- Touch-friendly button sizes
- Flexible spacing and padding

## Future Enhancements

### Driving Mode
- [ ] Implement actual casual driving interface
- [ ] Build gamified scoring system
- [ ] Add achievement system
- [ ] Create leaderboard backend

### Settings
- [ ] Persist settings to localStorage or backend
- [ ] Apply theme changes in real-time
- [ ] Implement i18n for language switching
- [ ] Add audio settings

### Logs
- [ ] Connect to backend API for real logs
- [ ] Add export functionality (CSV/JSON)
- [ ] Include GPS mapping visualization
- [ ] Add date range filtering
- [ ] Implement pagination for large datasets

### General
- [ ] Add loading states
- [ ] Implement error boundaries
- [ ] Add offline support (PWA)
- [ ] Keyboard navigation support
- [ ] Accessibility improvements (ARIA labels)
